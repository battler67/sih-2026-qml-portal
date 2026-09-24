from __future__ import annotations

import hashlib
import json
import math
import os
from typing import Any

import httpx


OPENAI_REPORT_SYSTEM_PROMPT = """
You are the scientific report writer for QDNA, a quantum DNA research simulator.

Your only evidence is the MEASURED_FACTS JSON supplied in the user message. Treat
every present value as measured or computed by the application. Treat every
missing or null field as unavailable. Never infer, estimate, fabricate, repair,
or silently recompute a result.

Write five concise interpretation sections:
1. executive_summary
2. dna_interpretation
3. circuit_resource_analysis
4. noise_mitigation_comparison
5. reliability_limitations_conclusion

Hard scientific boundaries:
- Keep factual measurements separate from interpretation. The application
  renders MEASURED_FACTS separately; your text must refer to facts without
  relabeling an interpretation as a measurement.
- Repeat numeric values exactly as supplied when a number is material. Do not
  create percentages, ratios, thresholds, confidence scores, or significance
  claims that are absent from MEASURED_FACTS.
- Hybrid mode: discuss measured mismatch-candidate positions only when
  measuredMismatchCandidatePositionsZeroBased is present. Call them measured
  candidates, not clinically confirmed mutations. Discuss YLC iterations only
  when ylcIterations is present.
- Grover mode: discuss bounded candidate-state or exact-pattern-search behavior.
  Do not discuss mutations, mismatch positions, YLC iterations, FRQI similarity,
  or whole-database quantum search.
- FRQI mode: discuss the supplied strip-qubit/count distribution or similarity
  only when present. Do not discuss mutations, mismatch positions, or YLC
  iterations.
- Discuss ideal/noisy/mitigated behavior only when noiseComparison is present.
  If it is absent, state that no noise comparison was available for this report.
- Do not claim quantum advantage, hardware execution, biological causation,
  pathogenicity, diagnosis, treatment relevance, clinical validity, or medical
  significance.
- Simulator output is not evidence from fault-tolerant quantum hardware.
- Probability concentration is not automatically proof of a biological match or
  mutation. State this limitation where relevant.
- Keep each section to 2-4 sentences. Avoid generic filler and recommendations
  that are not grounded in the supplied facts.

Return only the required structured JSON fields. Do not add citations, Markdown
headings, tables, or extra keys.
""".strip()


REPORT_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "executive_summary": {"type": "string"},
        "dna_interpretation": {"type": "string"},
        "circuit_resource_analysis": {"type": "string"},
        "noise_mitigation_comparison": {"type": "string"},
        "reliability_limitations_conclusion": {"type": "string"},
    },
    "required": [
        "executive_summary",
        "dna_interpretation",
        "circuit_resource_analysis",
        "noise_mitigation_comparison",
        "reliability_limitations_conclusion",
    ],
}

REPORT_SECTION_KEYS = tuple(REPORT_JSON_SCHEMA["required"])


class ReportGenerationError(RuntimeError):
    pass


def build_measured_facts(
    result: dict[str, Any],
    noise_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the only computed fields permitted to leave the QDNA backend."""

    algorithm = str(result.get("algorithm") or "").lower()
    if algorithm not in {"grover", "frqi", "hybrid"}:
        raise ValueError(f"Unsupported report algorithm: {algorithm or 'missing'}")

    hits = result.get("hits") if isinstance(result.get("hits"), list) else []
    first_hit = hits[0] if hits and isinstance(hits[0], dict) else {}
    details = (
        first_hit.get("quantumDetails")
        if isinstance(first_hit.get("quantumDetails"), dict)
        else {}
    )
    metrics = (
        result.get("quantumMetrics")
        if isinstance(result.get("quantumMetrics"), dict)
        else {}
    )

    facts: dict[str, Any] = {
        "algorithm": algorithm,
        "executionEnvironment": str(result.get("executionType") or "quantum_simulator"),
    }

    distribution = _probability_distribution(algorithm, details)
    if distribution:
        facts["probabilityDistribution"] = distribution

    circuit = _circuit_facts(details)
    if circuit:
        facts["circuitResources"] = circuit

    execution_times: dict[str, float] = {}
    quantum_seconds = _finite_number(metrics.get("quantumExecutionSeconds"))
    circuit_seconds = _finite_number(details.get("executionTimeSeconds"))
    validation_seconds = _finite_number(metrics.get("classicalValidationSeconds"))
    if quantum_seconds is not None:
        execution_times["quantumStageSeconds"] = quantum_seconds
    if circuit_seconds is not None:
        execution_times["topCircuitSeconds"] = circuit_seconds
    if validation_seconds is not None:
        execution_times["classicalValidationSeconds"] = validation_seconds
    if execution_times:
        facts["executionTimes"] = execution_times

    if algorithm == "hybrid":
        facts["measuredMismatchCandidatePositionsZeroBased"] = _integer_list(
            details.get("measuredCandidateIndices")
        )
        ylc_iterations = _integer(details.get("iterationsExecuted"))
        if ylc_iterations is not None:
            facts["ylcIterations"] = ylc_iterations

    if noise_result:
        facts["noiseComparison"] = _noise_facts(noise_result)

    return facts


def report_fingerprint(facts: dict[str, Any]) -> str:
    payload = json.dumps(facts, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class OpenAIReportGenerator:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    @property
    def model(self) -> str:
        return self._model or os.getenv("OPENAI_REPORT_MODEL", "gpt-5.6-sol")

    def generate(self, facts: dict[str, Any]) -> dict[str, str]:
        api_key = self._api_key or os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise ReportGenerationError(
                "OPENAI_API_KEY is not configured in quantum_search_api/.env"
            )

        timeout = self._timeout_seconds
        if timeout is None:
            try:
                timeout = float(os.getenv("OPENAI_REPORT_TIMEOUT_SECONDS", "60"))
            except ValueError:
                timeout = 60.0

        payload = {
            "model": self.model,
            "instructions": OPENAI_REPORT_SYSTEM_PROMPT,
            "input": (
                "MEASURED_FACTS\n"
                + json.dumps(facts, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
            ),
            "reasoning": {"effort": "low"},
            "text": {
                "verbosity": "low",
                "format": {
                    "type": "json_schema",
                    "name": "quantum_dna_analysis_report",
                    "strict": True,
                    "schema": REPORT_JSON_SCHEMA,
                },
            },
            "store": False,
        }

        try:
            with httpx.Client(
                timeout=max(5.0, timeout),
                transport=self._transport,
            ) as client:
                response = client.post(
                    "https://api.openai.com/v1/responses",
                    headers={
                        "authorization": f"Bearer {api_key}",
                        "content-type": "application/json",
                    },
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise ReportGenerationError("Could not reach the OpenAI Responses API") from exc

        if response.status_code >= 400:
            detail = _openai_error_detail(response)
            raise ReportGenerationError(
                f"OpenAI report generation failed ({response.status_code}): {detail}"
            )

        try:
            output = json.loads(_response_output_text(response.json()))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ReportGenerationError(
                "OpenAI returned an invalid structured report"
            ) from exc

        if not isinstance(output, dict):
            raise ReportGenerationError("OpenAI returned an invalid structured report")
        report: dict[str, str] = {}
        for key in REPORT_SECTION_KEYS:
            value = output.get(key)
            if not isinstance(value, str) or not value.strip():
                raise ReportGenerationError(
                    f"OpenAI report section {key} was missing or empty"
                )
            report[key] = value.strip()
        return report


def _probability_distribution(
    algorithm: str,
    details: dict[str, Any],
) -> dict[str, Any] | None:
    index_probabilities = _numeric_map(details.get("indexProbabilities"), limit=64)
    counts = _numeric_map(details.get("counts"), limit=64)
    distribution: dict[str, Any] = {}
    if index_probabilities:
        distribution["kind"] = "index_probabilities"
        distribution["values"] = index_probabilities["values"]
        distribution["truncated"] = index_probabilities["truncated"]
    elif counts:
        distribution["kind"] = "measurement_counts"
        distribution["values"] = counts["values"]
        distribution["truncated"] = counts["truncated"]

    if algorithm == "frqi":
        strip_probability = _finite_number(details.get("stripQubitProbability"))
        similarity = _finite_number(details.get("frqiSimilarity"))
        if strip_probability is not None:
            distribution["stripQubitProbability"] = strip_probability
        if similarity is not None:
            distribution["frqiSimilarity"] = similarity
    elif algorithm == "grover":
        success = _finite_number(details.get("successProbability"))
        false_positive = _finite_number(details.get("falsePositiveProbability"))
        if success is not None:
            distribution["successProbability"] = success
        if false_positive is not None:
            distribution["falsePositiveProbability"] = false_positive

    return distribution or None


def _circuit_facts(details: dict[str, Any]) -> dict[str, Any] | None:
    output: dict[str, Any] = {}
    for response_key, source_key in (
        ("logical", "circuitMetrics"),
        ("transpiled", "transpiledCircuitMetrics"),
    ):
        source = details.get(source_key)
        if not isinstance(source, dict):
            continue
        section: dict[str, int | float] = {}
        for output_key, possible_keys in (
            ("qubitCount", ("logical_qubits", "num_qubits", "qubits")),
            ("depth", ("depth",)),
            ("gateCount", ("size",)),
            ("oneQubitGateCount", ("oneQubitGateCount",)),
            ("twoQubitGateCount", ("twoQubitGateCount",)),
        ):
            value = _first_number(source, possible_keys)
            if value is not None:
                section[output_key] = value
        if section:
            output[response_key] = section
    return output or None


def _noise_facts(noise: dict[str, Any]) -> dict[str, Any]:
    comparison: dict[str, Any] = {
        "noiseType": str(noise.get("noiseType") or ""),
        "mitigationMethod": str(noise.get("mitigation") or ""),
        "simulator": str(noise.get("simulator") or ""),
        "hardwareRun": bool(noise.get("hardwareRun", False)),
    }
    for key in ("shots", "requestedShots"):
        value = _integer(noise.get(key))
        if value is not None:
            comparison[key] = value
    if noise.get("noiseModelScope"):
        comparison["noiseModelScope"] = str(noise["noiseModelScope"])

    parameters = noise.get("noiseParameters")
    if isinstance(parameters, dict):
        comparison["noiseParameters"] = _safe_scalar_map(parameters, limit=32)

    for section_name in ("ideal", "noisy", "mitigated"):
        section = noise.get(section_name)
        if not isinstance(section, dict):
            continue
        values: dict[str, Any] = {}
        for key in ("successProbability", "falsePositiveProbability", "similarity"):
            value = _finite_number(section.get(key))
            if value is not None:
                values[key] = value
        if section.get("topState") is not None:
            values["topState"] = str(section.get("topState"))
        if values:
            comparison[section_name] = values
    return comparison


def _numeric_map(value: Any, *, limit: int) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    items: list[tuple[str, float]] = []
    for key, raw in value.items():
        number = _finite_number(raw)
        if number is not None:
            items.append((str(key), number))
    if not items:
        return None
    items.sort(key=lambda item: (-item[1], item[0]))
    return {
        "values": dict(items[:limit]),
        "truncated": len(items) > limit,
    }


def _safe_scalar_map(value: dict[str, Any], *, limit: int) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key in sorted(value)[:limit]:
        raw = value[key]
        if isinstance(raw, bool) or raw is None or isinstance(raw, str):
            output[str(key)] = raw
        else:
            number = _finite_number(raw)
            if number is not None:
                output[str(key)] = number
    return output


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _integer(value: Any) -> int | None:
    number = _finite_number(value)
    if number is None or not number.is_integer():
        return None
    return int(number)


def _integer_list(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []
    output = []
    for item in value:
        integer = _integer(item)
        if integer is not None and integer >= 0:
            output.append(integer)
    return sorted(set(output))


def _first_number(source: dict[str, Any], keys: tuple[str, ...]) -> int | float | None:
    for key in keys:
        number = _finite_number(source.get(key))
        if number is not None:
            return int(number) if number.is_integer() else number
    return None


def _response_output_text(body: dict[str, Any]) -> str:
    output_text = body.get("output_text")
    if isinstance(output_text, str) and output_text:
        return output_text
    for item in body.get("output", []):
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and content.get("type") == "output_text":
                text = content.get("text")
                if isinstance(text, str) and text:
                    return text
    raise KeyError("output_text")


def _openai_error_detail(response: httpx.Response) -> str:
    try:
        body = response.json()
        message = body.get("error", {}).get("message")
        if isinstance(message, str) and message:
            return message[:300]
    except (TypeError, ValueError):
        pass
    return response.reason_phrase or "request failed"
