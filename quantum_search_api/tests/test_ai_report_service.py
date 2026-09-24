from __future__ import annotations

import json

import httpx
import pytest

from quantum_search_api.services.reports.ai_report import (
    OPENAI_REPORT_SYSTEM_PROMPT,
    OpenAIReportGenerator,
    ReportGenerationError,
    build_measured_facts,
    report_fingerprint,
)


def _result(algorithm: str) -> dict:
    return {
        "algorithm": algorithm,
        "executionType": "quantum_simulator",
        "query": {"sequence": "SECRET_QUERY_DNA"},
        "hits": [
            {
                "matchedWindow": "SECRET_REFERENCE_DNA",
                "recordTitle": "Not permitted in the report payload",
                "quantumDetails": {
                    "counts": {"00": 8, "01": 24},
                    "indexProbabilities": {"0": 0.25, "1": 0.75},
                    "successProbability": 0.75,
                    "falsePositiveProbability": 0.25,
                    "measuredCandidateIndices": [1, 3],
                    "iterationsExecuted": 2,
                    "executionTimeSeconds": 0.125,
                    "circuitMetrics": {
                        "logical_qubits": 7,
                        "depth": 20,
                        "size": 30,
                        "oneQubitGateCount": 18,
                        "twoQubitGateCount": 12,
                    },
                    "transpiledCircuitMetrics": {
                        "logical_qubits": 7,
                        "depth": 42,
                        "size": 55,
                        "oneQubitGateCount": 31,
                        "twoQubitGateCount": 24,
                    },
                },
            }
        ],
        "quantumMetrics": {
            "quantumExecutionSeconds": 0.5,
            "classicalValidationSeconds": 0.02,
        },
    }


def _noise() -> dict:
    return {
        "noiseType": "depolarizing",
        "mitigation": "zero-noise extrapolation",
        "simulator": "AerSimulator",
        "hardwareRun": False,
        "shots": 1024,
        "noiseModelScope": "Top-ranked bounded window",
        "noiseParameters": {"singleQubitError": 0.002, "twoQubitError": 0.01},
        "ideal": {
            "successProbability": 0.8,
            "falsePositiveProbability": 0.2,
            "topState": "01",
        },
        "noisy": {
            "successProbability": 0.62,
            "falsePositiveProbability": 0.38,
            "topState": "01",
        },
        "mitigated": {
            "successProbability": 0.73,
            "falsePositiveProbability": 0.27,
            "topState": "01",
        },
    }


def test_hybrid_facts_include_only_mode_appropriate_computed_fields():
    facts = build_measured_facts(_result("hybrid"), _noise())

    assert facts["measuredMismatchCandidatePositionsZeroBased"] == [1, 3]
    assert facts["ylcIterations"] == 2
    assert facts["circuitResources"]["logical"]["depth"] == 20
    assert facts["noiseComparison"]["mitigated"]["successProbability"] == 0.73
    serialized = json.dumps(facts)
    assert "SECRET_QUERY_DNA" not in serialized
    assert "SECRET_REFERENCE_DNA" not in serialized
    assert "recordTitle" not in serialized


def test_grover_and_frqi_facts_omit_mutations_and_ylc_fields():
    grover = build_measured_facts(_result("grover"))
    frqi_result = _result("frqi")
    frqi_result["hits"][0]["quantumDetails"]["stripQubitProbability"] = 0.4
    frqi_result["hits"][0]["quantumDetails"]["frqiSimilarity"] = 0.6
    frqi = build_measured_facts(frqi_result)

    for facts in (grover, frqi):
        assert "measuredMismatchCandidatePositionsZeroBased" not in facts
        assert "ylcIterations" not in facts
        assert "noiseComparison" not in facts
    assert grover["probabilityDistribution"]["successProbability"] == 0.75
    assert frqi["probabilityDistribution"]["frqiSimilarity"] == 0.6


def test_report_fingerprint_changes_when_noise_facts_change():
    ideal_only = build_measured_facts(_result("grover"))
    with_noise = build_measured_facts(_result("grover"), _noise())
    assert report_fingerprint(ideal_only) != report_fingerprint(with_noise)


def test_openai_request_uses_structured_output_and_allowlisted_facts_only():
    captured: dict = {}
    output = {
        "executive_summary": "Summary.",
        "dna_interpretation": "Interpretation.",
        "circuit_resource_analysis": "Resources.",
        "noise_mitigation_comparison": "No comparison was available.",
        "reliability_limitations_conclusion": "Limited simulator conclusion.",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": json.dumps(output)}],
                    }
                ]
            },
        )

    generator = OpenAIReportGenerator(
        api_key="test-key",
        model="gpt-test",
        transport=httpx.MockTransport(handler),
    )
    facts = build_measured_facts(_result("grover"))
    report = generator.generate(facts)

    assert report == output
    assert captured["store"] is False
    assert captured["text"]["format"]["strict"] is True
    assert captured["reasoning"]["effort"] == "low"
    assert "SECRET_QUERY_DNA" not in captured["input"]
    assert "medical" in OPENAI_REPORT_SYSTEM_PROMPT.lower()
    assert "quantum advantage" in OPENAI_REPORT_SYSTEM_PROMPT.lower()


def test_openai_key_must_be_configured_on_the_backend(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    generator = OpenAIReportGenerator()

    with pytest.raises(ReportGenerationError, match="quantum_search_api/.env"):
        generator.generate(build_measured_facts(_result("grover")))
