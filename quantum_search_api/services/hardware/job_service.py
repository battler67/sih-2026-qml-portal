from __future__ import annotations

import os
import threading
import uuid
from typing import Any

from quantum_search_api.services.hardware.circuit_service import HardwareCircuitService
from quantum_search_api.services.hardware.models import (
    DeviceCandidate,
    HardwareJob,
    HardwareSubmissionRequest,
    PreparedHardwareCircuit,
)
from quantum_search_api.services.hardware.providers import (
    HardwareProvider,
    HardwareProviderError,
    IbmHardwareProvider,
    QbraidHardwareProvider,
    select_best_device,
)


class HardwareJobService:
    """In-memory asynchronous coordinator for explicitly confirmed QPU jobs."""

    def __init__(
        self,
        *,
        circuit_service: HardwareCircuitService | None = None,
        providers: list[HardwareProvider] | None = None,
        run_inline: bool = False,
    ) -> None:
        self.circuit_service = circuit_service or HardwareCircuitService()
        self.providers = providers or [
            QbraidHardwareProvider(),
            IbmHardwareProvider(),
        ]
        self.run_inline = run_inline
        self.jobs: dict[str, HardwareJob] = {}
        self._lock = threading.Lock()

    @property
    def max_hardware_shots(self) -> int:
        raw = os.getenv("QDNA_REAL_HARDWARE_MAX_SHOTS", "1024")
        try:
            return max(1, min(8192, int(raw)))
        except ValueError:
            return 1024

    def create_job(self, submission: HardwareSubmissionRequest) -> HardwareJob:
        if not submission.confirm_real_hardware:
            raise ValueError(
                "Real-hardware execution requires explicit confirmation"
            )
        job = HardwareJob(
            job_id=str(uuid.uuid4()),
            request=submission.search_request,
        )
        with self._lock:
            self.jobs[job.job_id] = job
        if self.run_inline:
            self._run(job.job_id)
        else:
            thread = threading.Thread(target=self._run, args=(job.job_id,), daemon=True)
            thread.start()
        return job

    def get_job(self, job_id: str) -> HardwareJob | None:
        return self.jobs.get(job_id)

    def get_result(self, job_id: str) -> dict[str, Any] | None:
        job = self.jobs.get(job_id)
        return job.result if job else None

    def preview(self, request) -> dict[str, Any]:
        prepared = self.circuit_service.prepare(request)
        candidates, errors = self._discover(prepared.circuit.num_qubits)
        selected = select_best_device(
            candidates,
            required_qubits=prepared.circuit.num_qubits,
        )
        return {
            "algorithm": prepared.algorithm,
            "requiredQubits": prepared.circuit.num_qubits,
            "selectedDevice": selected.public_dict(
                required_qubits=prepared.circuit.num_qubits
            ),
            "eligibleDevices": [
                item.public_dict(required_qubits=prepared.circuit.num_qubits)
                for item in sorted(
                    candidates,
                    key=lambda candidate: (
                        candidate.qubits - prepared.circuit.num_qubits,
                        candidate.queue_depth,
                        candidate.provider,
                        candidate.device_id,
                    ),
                )
            ],
            "providerErrors": errors,
            "submissionPerformed": False,
            "note": (
                "Metadata preview only. Device status and queue depth are snapshots "
                "and are checked again on submission."
            ),
        }

    def _run(self, job_id: str) -> None:
        job = self.jobs[job_id]
        try:
            self._progress(job, "preparing_circuit", 15, "Preparing one bounded circuit")
            prepared = self.circuit_service.prepare(job.request)
            required_qubits = prepared.circuit.num_qubits

            self._progress(
                job,
                "discovering_devices",
                35,
                f"Finding online free QPUs with at least {required_qubits} qubits",
            )
            candidates, provider_errors = self._discover(required_qubits)
            job.provider_errors = provider_errors
            selected = select_best_device(
                candidates,
                required_qubits=required_qubits,
            )
            submission_candidates = self._submission_candidates(
                selected=selected,
                candidates=candidates,
                required_qubits=required_qubits,
            )
            shots = min(job.request.shots, self.max_hardware_shots)
            execution = None

            for attempt_index, candidate in enumerate(submission_candidates):
                provider = next(
                    item
                    for item in self.providers
                    if item.provider_name == candidate.provider
                )
                job.selected_device = candidate
                job.touch()

                if attempt_index:
                    self._progress(
                        job,
                        "provider_fallback",
                        65,
                        (
                            "qBraid could not complete the submission; "
                            f"falling back to IBM device {candidate.name}"
                        ),
                    )
                self._progress(
                    job,
                    "submitting",
                    70 if attempt_index else 60,
                    (
                        f"Submitting {shots} raw shots to {candidate.name} "
                        f"through {self._provider_label(candidate.provider)}"
                    ),
                )
                try:
                    execution = provider.submit(
                        candidate,
                        prepared.circuit,
                        shots=shots,
                        classical_register=prepared.classical_register,
                    )
                except Exception as exc:
                    job.provider_errors.append(
                        self._submission_error(candidate.provider, exc)
                    )
                    job.touch()
                    continue

                selected = candidate
                break

            if execution is None:
                if selected.provider == "qbraid" and not any(
                    candidate.provider == "ibm"
                    for candidate in submission_candidates
                ):
                    job.provider_errors.append(self._ibm_unavailable_reason(candidates))
                raise HardwareProviderError(
                    "Hardware calls failed. No configured hardware provider "
                    "completed the request."
                )

            job.remote_job_id = execution.remote_job_id
            self._progress(
                job,
                "processing_results",
                90,
                "Mapping raw hardware measurement counts",
            )
            job.result = self._result_payload(
                job=job,
                prepared=prepared,
                selected=selected,
                candidates=candidates,
                shots=shots,
                execution=execution,
            )
            self._progress(job, "completed", 100, "Real-hardware results are ready")
        except Exception as exc:
            job.error = str(exc)
            self._progress(
                job,
                "failed",
                100,
                "Hardware calls failed; no provider completed the real-hardware request",
            )

    @staticmethod
    def _submission_candidates(
        *,
        selected: DeviceCandidate,
        candidates: list[DeviceCandidate],
        required_qubits: int,
    ) -> list[DeviceCandidate]:
        """Return one primary attempt and, for qBraid, one IBM fallback."""

        attempts = [selected]
        if selected.provider != "qbraid":
            return attempts

        ibm_candidates = [
            candidate for candidate in candidates if candidate.provider == "ibm"
        ]
        if ibm_candidates:
            attempts.append(
                select_best_device(
                    ibm_candidates,
                    required_qubits=required_qubits,
                )
            )
        return attempts

    def _ibm_unavailable_reason(
        self,
        candidates: list[DeviceCandidate],
    ) -> str:
        ibm = next(
            (provider for provider in self.providers if provider.provider_name == "ibm"),
            None,
        )
        if ibm is None or not ibm.configured():
            return "IBM fallback unavailable: IBM credentials are not configured."
        if not any(candidate.provider == "ibm" for candidate in candidates):
            return (
                "IBM fallback unavailable: no eligible online IBM QPU can fit "
                "the prepared circuit."
            )
        return "IBM fallback unavailable."

    @staticmethod
    def _submission_error(provider_name: str, exc: Exception) -> str:
        label = HardwareJobService._provider_label(provider_name)
        if isinstance(exc, HardwareProviderError):
            detail = str(exc).strip() or type(exc).__name__
        else:
            detail = type(exc).__name__
        return f"{label} attempt failed: {detail}"

    @staticmethod
    def _provider_label(provider_name: str) -> str:
        return {"qbraid": "qBraid", "ibm": "IBM"}.get(
            provider_name,
            provider_name,
        )

    def _discover(
        self,
        required_qubits: int,
    ) -> tuple[list[DeviceCandidate], list[str]]:
        candidates: list[DeviceCandidate] = []
        errors: list[str] = []
        configured_count = 0
        for provider in self.providers:
            if not provider.configured():
                continue
            configured_count += 1
            try:
                candidates.extend(provider.discover(required_qubits))
            except HardwareProviderError as exc:
                errors.append(str(exc))
        if configured_count == 0:
            raise HardwareProviderError(
                "No hardware provider is configured. Set rotated backend-only "
                "QBRAID_API_KEY and/or QISKIT_IBM_TOKEN credentials."
            )
        return candidates, errors

    @staticmethod
    def _result_payload(
        *,
        job: HardwareJob,
        prepared: PreparedHardwareCircuit,
        selected: DeviceCandidate,
        candidates: list[DeviceCandidate],
        shots: int,
        execution,
    ) -> dict[str, Any]:
        total_counts = sum(execution.counts.values())
        denominator = total_counts or shots
        fallback_used = selected.provider == "ibm" and any(
            error.startswith("qBraid")
            for error in job.provider_errors
        )
        probabilities = {
            state: count / denominator
            for state, count in execution.counts.items()
        }
        ranked_states = sorted(
            probabilities.items(),
            key=lambda item: (-item[1], item[0]),
        )
        warnings = [
            *prepared.warnings,
            "Counts are raw physical-device measurements; no mitigation was applied.",
            "Queue depth was a selection-time snapshot and does not guarantee start time.",
            (
                "A logical qubit fit does not guarantee low transpiled depth or useful "
                "signal on current noisy hardware."
            ),
        ]
        if shots < job.request.shots:
            warnings.append(
                f"Requested shots were capped from {job.request.shots} to {shots} "
                "by QDNA_REAL_HARDWARE_MAX_SHOTS."
            )
        if fallback_used:
            warnings.append(
                "IBM completed this run after qBraid was unavailable or failed."
            )
        return {
            "jobId": job.job_id,
            "remoteJobId": execution.remote_job_id,
            "status": "completed",
            "algorithm": prepared.algorithm,
            "provider": selected.provider,
            "device": selected.public_dict(
                required_qubits=prepared.circuit.num_qubits
            ),
            "providerErrors": list(job.provider_errors),
            "selection": {
                "policy": (
                    "qbraid_to_ibm_fallback"
                    if fallback_used
                    else "minimum_unused_qubits_then_queue_depth"
                ),
                "eligibleDeviceCount": len(candidates),
                "reason": (
                    (
                        "qBraid was unavailable or failed, so QDNA used the "
                        "smallest eligible IBM fallback device; queue depth "
                        "breaks equal-capacity IBM ties."
                    )
                    if fallback_used
                    else (
                        "Selected the smallest online zero-price/entitled QPU "
                        f"fitting {prepared.circuit.num_qubits} logical qubits; "
                        "queue depth breaks equal-capacity ties."
                    )
                ),
            },
            "query": {
                "sequence": prepared.query_sequence,
                "length": len(prepared.query_sequence),
            },
            "representativeWindow": prepared.window_metadata,
            "retrieval": prepared.retrieval_metadata,
            "execution": {
                "requestedShots": job.request.shots,
                "submittedShots": shots,
                "returnedShots": total_counts,
                "counts": execution.counts,
                "probabilities": probabilities,
                "rankedStates": [
                    {"state": state, "probability": probability}
                    for state, probability in ranked_states
                ],
                "providerStatus": execution.provider_status,
                "rawHardwareMeasurements": True,
                "errorMitigationApplied": False,
            },
            "circuit": {
                **prepared.circuit_metadata(),
                "transpiled": execution.transpiled_circuit_metrics,
            },
            "providerMetadata": execution.provider_metadata,
            "limitations": [
                "One representative bounded genomic window is submitted per click.",
                "The representative window is selected before QPU execution without Aer ranking.",
                "This is not an entire-genome coherent search and not evidence of quantum advantage.",
                "Provider access, quota, calibration, and queue state remain externally controlled.",
            ],
            "warnings": warnings,
        }

    @staticmethod
    def _progress(
        job: HardwareJob,
        status: str,
        percent: int,
        message: str,
    ) -> None:
        job.status = status
        job.progress_percent = max(0, min(100, percent))
        job.message = message
        job.touch()
