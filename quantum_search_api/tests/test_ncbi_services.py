import io
import zipfile

import httpx
import pytest

from quantum_search_api.services.ncbi.cache import TtlCache
from quantum_search_api.services.ncbi.blast_service import NcbiBlastService
from quantum_search_api.services.ncbi.client import NcbiClient
from quantum_search_api.services.ncbi.datasets_provider import NcbiDatasetsProvider
from quantum_search_api.services.ncbi.entrez_workflow import NcbiEntrezWorkflow
from quantum_search_api.services.ncbi.entrez_provider import NcbiEntrezProvider
from quantum_search_api.services.ncbi.exceptions import NcbiValidationError
from quantum_search_api.services.ncbi.models import SearchRequest
from quantum_search_api.services.ncbi.rate_limiter import RateLimiter


class MockTransport:
    def __init__(self):
        self.calls = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        if self.calls == 1:
            return httpx.Response(429, request=request)
        return httpx.Response(200, json={"ok": True}, request=request)


def test_client_retries_temporary_errors():
    transport = MockTransport()
    client = NcbiClient(http_client=httpx.Client(transport=httpx.MockTransport(transport)), max_retries=1, cache_ttl_seconds=60)
    assert client.get_json("https://example.test") == {"ok": True}
    assert transport.calls == 2


def test_cache_behavior():
    cache = TtlCache(60)
    cache.set("k", {"v": 1})
    assert cache.get("k") == {"v": 1}


def test_rate_limiter_smoke():
    limiter = RateLimiter(1000)
    limiter.wait()


def test_entrez_esearch_requires_genomic_term():
    seen = {"urls": []}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["urls"].append(str(request.url))
        if "esearch" in str(request.url):
            return httpx.Response(200, json={"esearchresult": {"idlist": ["NC_000001.1"]}}, request=request)
        return httpx.Response(
            200,
            json={"result": {"uids": ["NC_000001.1"], "NC_000001.1": {"caption": "NC_000001.1", "title": "genomic DNA chromosome", "taxid": 1}}},
            request=request,
        )

    provider = NcbiEntrezProvider(NcbiClient(http_client=httpx.Client(transport=httpx.MockTransport(handler))))
    request = SearchRequest(querySource="pasted", querySequence="ACGT", databaseScope="exact_genomic_nucleotide", nucleotideAccessions=["NC_000001.1"])
    records = provider.search_records(request)
    assert records[0].accession == "NC_000001.1"
    assert any("biomol_genomic" in url for url in seen["urls"])


def test_entrez_gene_search_term_excludes_transcripts():
    workflow = NcbiEntrezWorkflow()
    term = workflow._gene_search_term(
        "BRCA1",
        "Mus caroli",
        "all",
        min_length=10000,
        max_length=250000,
    )
    assert "biomol_genomic[PROP]" in term
    assert "mRNA" in term
    assert "10000:250000[SLEN]" in term


def test_taxonomy_search_resolves_scientific_name():
    taxonomy_xml = """<?xml version="1.0"?>
<TaxaSet>
  <Taxon>
    <TaxId>562</TaxId>
    <ScientificName>Escherichia coli</ScientificName>
    <Rank>species</Rank>
    <Division>Bacteria</Division>
    <ParentTaxId>561</ParentTaxId>
    <Lineage>Bacteria; Pseudomonadota; Gammaproteobacteria; Enterobacterales</Lineage>
    <LineageEx />
  </Taxon>
</TaxaSet>
"""

    def handler(request: httpx.Request) -> httpx.Response:
        if "esearch" in str(request.url):
            return httpx.Response(
                200,
                json={"esearchresult": {"count": "1", "idlist": ["562"]}},
                request=request,
            )
        return httpx.Response(200, text=taxonomy_xml, request=request)

    workflow = NcbiEntrezWorkflow(
        NcbiClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    )
    result = workflow.search_taxa("Escherichia coli")
    assert result["count"] == 1
    assert result["records"][0]["taxId"] == "562"
    assert result["records"][0]["scientificName"] == "Escherichia coli"


def test_organism_genome_viewer_builds_tree_and_image():
    taxonomy_xml = """<?xml version="1.0"?>
<TaxaSet>
  <Taxon>
    <TaxId>9606</TaxId>
    <ScientificName>Homo sapiens</ScientificName>
    <Rank>species</Rank>
    <Division>Primates</Division>
    <ParentTaxId>9605</ParentTaxId>
    <Lineage>Eukaryota; Metazoa; Chordata; Mammalia; Primates; Hominidae; Homo</Lineage>
    <LineageEx>
      <Taxon><TaxId>2759</TaxId><ScientificName>Eukaryota</ScientificName><Rank>superkingdom</Rank></Taxon>
      <Taxon><TaxId>33208</TaxId><ScientificName>Metazoa</ScientificName><Rank>kingdom</Rank></Taxon>
      <Taxon><TaxId>9443</TaxId><ScientificName>Primates</ScientificName><Rank>order</Rank></Taxon>
      <Taxon><TaxId>9605</TaxId><ScientificName>Homo</ScientificName><Rank>genus</Rank></Taxon>
    </LineageEx>
    <GeneticCode><GCId>1</GCId><GCName>Standard</GCName></GeneticCode>
    <MitoGeneticCode><MGCId>2</MGCId><MGCName>Vertebrate Mitochondrial</MGCName></MitoGeneticCode>
  </Taxon>
</TaxaSet>
"""

    def handler(request: httpx.Request) -> httpx.Response:
        if "w/api.php" in str(request.url):
            return httpx.Response(
                200,
                json={
                    "query": {
                        "pages": {
                            "1": {
                                "title": "Homo sapiens",
                                "description": "species of primate",
                                "fullurl": "https://en.wikipedia.org/wiki/Homo_sapiens",
                                "thumbnail": {"source": "https://upload.wikimedia.org/human.jpg"},
                            }
                        }
                    }
                },
                request=request,
            )
        return httpx.Response(200, text=taxonomy_xml, request=request)

    workflow = NcbiEntrezWorkflow(NcbiClient(http_client=httpx.Client(transport=httpx.MockTransport(handler))))
    context = workflow.organism_genome_viewer("9606")
    assert context["treeNodes"][-1]["isSelected"] is True
    assert context["treeNodes"][-1]["scientificName"] == "Homo sapiens"
    assert context["image"]["source"] == "Wikimedia/Wikipedia"
    assert context["links"]["genomeDataViewer"].endswith("homo-sapiens")


def test_entrez_rejects_non_genomic_genbank():
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "rettype=fasta" in url:
            return httpx.Response(200, text=">NM_1 transcript\nACGT\n", request=request)
        return httpx.Response(200, text='FEATURES             Location/Qualifiers\n /mol_type="mRNA"\n', request=request)

    provider = NcbiEntrezProvider(NcbiClient(http_client=httpx.Client(transport=httpx.MockTransport(handler))))
    with pytest.raises(NcbiValidationError):
        provider.fetch_sequences(["NM_1"])


def test_datasets_parses_genomic_fna_only():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("ncbi_dataset/data/GCF_000001/demo_genomic.fna", ">chr1 genomic\nACGT\n")
    provider = NcbiDatasetsProvider()
    records = provider._parse_genomic_fna_zip(buffer.getvalue(), ["GCF_000001.1"])
    assert records[0].sequence == "ACGT"


def test_blast_service_groups_genbank_hits(monkeypatch):
    xml = """<?xml version="1.0"?>
<BlastOutput>
  <BlastOutput_iterations>
    <Iteration>
      <Iteration_hits>
        <Hit>
          <Hit_accession>U00096</Hit_accession>
          <Hit_def>Escherichia coli K-12 complete genome [Escherichia coli]</Hit_def>
          <Hit_len>4641652</Hit_len>
          <Hit_hsps>
            <Hsp>
              <Hsp_identity>4</Hsp_identity>
              <Hsp_align-len>4</Hsp_align-len>
              <Hsp_evalue>1e-4</Hsp_evalue>
              <Hsp_bit-score>8</Hsp_bit-score>
              <Hsp_query-from>1</Hsp_query-from>
              <Hsp_query-to>4</Hsp_query-to>
              <Hsp_hit-from>10</Hsp_hit-from>
              <Hsp_hit-to>13</Hsp_hit-to>
            </Hsp>
          </Hit_hsps>
        </Hit>
      </Iteration_hits>
    </Iteration>
  </BlastOutput_iterations>
</BlastOutput>
"""

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.content.decode()
        url = str(request.url)
        if request.method == "POST":
            assert "ENTREZ_QUERY" in body
            return httpx.Response(200, text="RID = RID123\nRTOE = 0\n", request=request)
        if "FORMAT_OBJECT=SearchInfo" in url:
            return httpx.Response(200, text="Status=READY\nThereAreHits=yes\n", request=request)
        return httpx.Response(200, text=xml, request=request)

    monkeypatch.setattr("time.sleep", lambda _: None)
    service = NcbiBlastService(NcbiClient(http_client=httpx.Client(transport=httpx.MockTransport(handler))))
    result = service.search_sequence("ACGT", max_records=25)
    assert result["records"][0]["organismName"] == "Escherichia coli"
    assert result["organisms"][0]["recordCount"] == 1
