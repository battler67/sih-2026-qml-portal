from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from quantum_search_api.services.ncbi.models import SearchRequest
from quantum_search_api.services.ncbi.blast_service import NcbiBlastService
from quantum_search_api.services.noise.config import NoiseSettings
from quantum_search_api.services.noise import run_noise_comparison
from quantum_search_api.services.search.search_orchestrator import SearchOrchestrator


JobStatus = str


@dataclass
class SearchJob:
    job_id: str
    status: JobStatus
    request: SearchRequest
    progress: list[dict[str, str]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    progress_percent: int = 0
    result: dict[str, Any] | None = None
    noise_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    latest_noise_key: str | None = None
    ai_reports: dict[str, dict[str, Any]] = field(default_factory=dict)
    error: str | None = None
    cancelled: bool = False

    def to_dict(self) -> dict[str, Any]:
        elapsed_seconds = max(
            0,
            int((datetime.now(timezone.utc) - datetime.fromisoformat(self.created_at)).total_seconds()),
        )
        estimated_remaining_seconds = None
        if 0 < self.progress_percent < 100:
            estimated_total = elapsed_seconds / (self.progress_percent / 100)
            estimated_remaining_seconds = max(0, int(estimated_total - elapsed_seconds))
        return {
            "jobId": self.job_id,
            "status": self.status,
            "progress": self.progress,
            "progressPercent": self.progress_percent,
            "elapsedSeconds": elapsed_seconds,
            "estimatedRemainingSeconds": estimated_remaining_seconds,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "error": self.error,
            "hasResults": self.result is not None,
        }


class InMemoryJobService:
    def __init__(self, orchestrator: SearchOrchestrator | None = None) -> None:
        self.orchestrator = orchestrator or SearchOrchestrator()
        self.jobs: dict[str, SearchJob] = {}
        self._lock = threading.Lock()

    def create_job(self, request: SearchRequest) -> SearchJob:
        job = SearchJob(job_id=str(uuid.uuid4()), status="queued", request=request)
        with self._lock:
            self.jobs[job.job_id] = job
        thread = threading.Thread(target=self._run, args=(job.job_id, request), daemon=True)
        thread.start()
        return job

    def get_job(self, job_id: str) -> SearchJob | None:
        return self.jobs.get(job_id)

    def cancel_job(self, job_id: str) -> bool:
        job = self.jobs.get(job_id)
        if not job:
            return False
        job.cancelled = True
        job.status = "cancelled"
        self._touch(job)
        return True

    def validate_candidates(self, job_id: str) -> dict[str, Any] | None:
        job = self.jobs.get(job_id)
        if not job or job.result is None:
            return None
        started = time.perf_counter()
        self.orchestrator.validate_result_candidates(job.request, job.result)
        validation_seconds = time.perf_counter() - started
        job.result.setdefault("quantumMetrics", {})["classicalValidationSeconds"] = validation_seconds
        self._set_progress(job, "validated", "Candidates validated classically", 100)
        self._touch(job)
        return job.result

    def blast_check(self, job_id: str, *, max_records: int = 25, entrez_query: str | None = None) -> dict[str, Any] | None:
        job = self.jobs.get(job_id)
        if not job or job.result is None:
            return None
        blast = NcbiBlastService().check_result(job.result, max_records=max_records, entrez_query=entrez_query)
        job.result["blastCheck"] = blast
        job.result.setdefault("quantumMetrics", {})["blastCheckedRecords"] = len(blast["records"])
        job.result.setdefault("quantumMetrics", {})["blastMatchedQuantumAccessions"] = len(blast["matchingQuantumAccessions"])
        self._touch(job)
        return blast

    def add_noise(
        self,
        job_id: str,
        settings: NoiseSettings | None = None,
    ) -> dict[str, Any] | None:
        job = self.jobs.get(job_id)
        if not job or job.result is None:
            return None
        resolved = (settings or NoiseSettings()).resolved(job.request.algorithm.value)
        cache_key = json.dumps(resolved, sort_keys=True, separators=(",", ":"))
        if cache_key in job.noise_results:
            job.latest_noise_key = cache_key
            self._touch(job)
            return job.noise_results[cache_key]
        hits = job.result.get("hits") or []
        if not hits:
            raise ValueError("The completed search has no processed window for noise simulation")
        hit = hits[0]
        details = hit.get("quantumDetails") or {}
        query_sequence = str(
            job.result.get("query", {}).get("sequence")
            or hit.get("querySequence")
            or ""
        )
        target_sequence = str(
            hit.get("quantumProcessedWindow")
            or hit.get("matchedWindow")
            or ""
        )
        expected_states = [
            int(value) for value in details.get("measuredCandidateIndices", [])
        ]
        if job.request.algorithm.value == "hybrid" and not expected_states:
            exact_probabilities = details.get("exactIndexProbabilities") or {}
            if exact_probabilities:
                highest = max(float(value) for value in exact_probabilities.values())
                expected_states = [
                    int(index)
                    for index, value in exact_probabilities.items()
                    if abs(float(value) - highest) <= 1e-12
                ]
        noise_result = run_noise_comparison(
            algorithm=job.request.algorithm.value,
            query_sequence=query_sequence,
            target_sequence=target_sequence,
            shots=job.request.shots,
            grover_boundary_mode=job.request.grover_boundary_mode,
            expected_states=expected_states,
            noise_parameters=resolved,
        )
        noise_result["jobId"] = job_id
        noise_result["comparedHit"] = {
            "rank": hit.get("rank"),
            "accession": hit.get("accession"),
            "start": hit.get("start"),
            "end": hit.get("end"),
            "targetSequence": target_sequence,
            "querySequence": query_sequence,
        }
        job.noise_results[cache_key] = noise_result
        job.latest_noise_key = cache_key
        self._touch(job)
        return noise_result

    def _run(self, job_id: str, request: SearchRequest) -> None:
        job = self.jobs[job_id]
        try:
            job.result = self.orchestrator.run(
                request,
                job_id=job_id,
                progress_callback=lambda status, message, percent: self._set_progress(
                    job, status, message, percent
                ),
            )
            self._set_progress(job, "completed", "Results are ready", 100)
        except Exception as exc:
            job.progress_percent = 100
            job.error = str(exc)
            self._set_progress(job, "failed", "Search failed; check server logs for details", 100)
        finally:
            self._touch(job)

    def _set_progress(self, job: SearchJob, status: str, message: str, percent: int) -> None:
        job.status = status
        job.progress_percent = max(0, min(100, percent))
        job.progress.append(
            {
                "status": status,
                "message": message,
                "percent": str(job.progress_percent),
            }
        )
        self._touch(job)

    def _touch(self, job: SearchJob) -> None:
        job.updated_at = datetime.now(timezone.utc).isoformat()
