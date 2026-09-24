"""Build the full Hybrid YLC mutation circuit and submit it directly to IBM.

This standalone experiment does not call the Quantum Helix Lab hardware API,
HardwareJobService, or provider-selection feature.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from quantum_search_api.services.quantum.hybrid_search import (
    FixedPointSchedule,
    build_hybrid_fixed_point_circuits,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILE = PROJECT_ROOT / "quantum_search_api" / ".env"
DEFAULT_REFERENCE = (
    PROJECT_ROOT / "two_mutated_fastas_100k" / "reference_100000bp.fasta"
)
DEFAULT_MUTATED = (
    PROJECT_ROOT
    / "two_mutated_fastas_100k"
    / "mutated_100000bp_1percent.fasta"
)
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "cacheResults" / "hybrid"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build the complete equal-length Hybrid YLC circuit, transpile it "
            "for one IBM backend, submit it with SamplerV2, wait, and save raw counts."
        )
    )
    parser.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument("--mutated", type=Path, default=DEFAULT_MUTATED)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument(
        "--backend",
        help=(
            "IBM backend name. Defaults to the first QDNA_IBM_BACKENDS entry, "
            "then ibm_marrakesh."
        ),
    )
    parser.add_argument("--shots", type=int, default=1024)
    parser.add_argument(
        "--optimization-level",
        type=int,
        choices=(0, 1, 2, 3),
        default=1,
    )
    parser.add_argument("--timeout-seconds", type=int, default=86_400)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the interactive external-job confirmation.",
    )
    return parser.parse_args()


def require_runtime_dependencies() -> tuple[Any, Any, Any]:
    try:
        from qiskit.transpiler import generate_preset_pass_manager
        from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    except ImportError as exc:
        raise SystemExit(
            "IBM Runtime is not installed in this Python environment.\n"
            "Install the project requirements first:\n"
            "  python -m pip install -r quantum_search_api/requirements.txt"
        ) from exc
    return QiskitRuntimeService, SamplerV2, generate_preset_pass_manager


def read_fasta(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"FASTA file not found: {path}")
    lines = path.read_text(encoding="utf-8").splitlines()
    sequence = "".join(line.strip() for line in lines if not line.startswith(">")).upper()
    if not sequence:
        raise ValueError(f"FASTA contains no sequence: {path}")
    if re.fullmatch(r"[ACGT]+", sequence) is None:
        raise ValueError(f"FASTA must contain only A/C/G/T bases: {path}")
    return sequence


def mismatch_count(reference: str, mutated: str) -> int:
    return sum(left != right for left, right in zip(reference, mutated, strict=True))


def sequence_digest(sequence: str) -> str:
    return hashlib.sha256(sequence.encode("ascii")).hexdigest()


def backend_name(backend: Any) -> str:
    value = getattr(backend, "name", "")
    return str(value() if callable(value) else value)


def job_identifier(job: Any) -> str:
    value = getattr(job, "job_id", None)
    value = value() if callable(value) else value
    if not value:
        raise RuntimeError("IBM did not return a remote job ID")
    return str(value)


def normalize_counts(raw: dict[Any, Any]) -> dict[str, int]:
    return dict(
        sorted(
            (str(state).replace(" ", ""), int(count))
            for state, count in raw.items()
        )
    )


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def print_schedule(schedule: FixedPointSchedule) -> None:
    print(f"YLC sequence length:      {schedule.sequence_length}", flush=True)
    print(f"YLC iterations:           {schedule.generalized_iterations}", flush=True)
    print(f"YLC predicate queries:    {schedule.predicate_queries}", flush=True)
    print(f"YLC lambda lower bound:   {schedule.lambda_min:.12g}", flush=True)


def confirm_submission(*, yes: bool, length: int, backend: str, shots: int) -> None:
    if yes:
        return
    print()
    print("WARNING: this will build and transpile the complete circuit locally.")
    print("For 100,000 bases this can exhaust memory or run for a very long time")
    print("before IBM receives a job.")
    answer = input(
        f"Type SUBMIT to target {backend} with N={length} and {shots} shots: "
    )
    if answer.strip() != "SUBMIT":
        raise SystemExit("Submission cancelled.")


def main() -> int:
    args = parse_args()
    if not 1 <= args.shots <= 8192:
        raise SystemExit("--shots must be between 1 and 8192")
    if args.timeout_seconds < 30:
        raise SystemExit("--timeout-seconds must be at least 30")

    load_dotenv(args.env_file)
    token = (os.getenv("QISKIT_IBM_TOKEN") or "").strip()
    channel = (os.getenv("QISKIT_IBM_CHANNEL") or "ibm_quantum_platform").strip()
    instance = (os.getenv("QISKIT_IBM_INSTANCE") or "").strip()
    configured_backends = [
        name.strip()
        for name in (os.getenv("QDNA_IBM_BACKENDS") or "").split(",")
        if name.strip()
    ]
    requested_backend = (
        args.backend
        or (configured_backends[0] if configured_backends else None)
        or "ibm_marrakesh"
    )

    if not token:
        raise SystemExit(
            f"QISKIT_IBM_TOKEN is missing. Add it to {args.env_file}."
        )

    QiskitRuntimeService, SamplerV2, generate_preset_pass_manager = (
        require_runtime_dependencies()
    )

    reference = read_fasta(args.reference.resolve())
    mutated = read_fasta(args.mutated.resolve())
    if len(reference) != len(mutated):
        raise SystemExit(
            "Hybrid comparison requires equal lengths: "
            f"reference={len(reference)}, mutated={len(mutated)}"
        )

    mutations = mismatch_count(reference, mutated)
    length = len(reference)
    print(f"Reference:                {args.reference.resolve()}", flush=True)
    print(f"Mutated:                  {args.mutated.resolve()}", flush=True)
    print(f"Sequence length:          {length:,}", flush=True)
    print(f"Classical substitutions:  {mutations:,}", flush=True)
    print(f"Mutation fraction:        {mutations / length:.6%}", flush=True)
    print(
        "The classical count is metadata only and is not passed to the circuit "
        "or YLC schedule.",
        flush=True,
    )
    confirm_submission(
        yes=args.yes,
        length=length,
        backend=requested_backend,
        shots=args.shots,
    )

    print("\nBuilding the complete Hybrid YLC circuit...", flush=True)
    circuits = build_hybrid_fixed_point_circuits(reference, mutated)
    measured = circuits["measured"]
    schedule = circuits["schedule"]
    if not hasattr(measured, "num_qubits") or not isinstance(
        schedule, FixedPointSchedule
    ):
        raise RuntimeError("Hybrid circuit builder returned unexpected values")
    print_schedule(schedule)
    print(f"Logical qubits:           {measured.num_qubits}", flush=True)
    print(f"Logical classical bits:   {measured.num_clbits}", flush=True)
    print(f"Logical depth:            {measured.depth():,}", flush=True)
    print(f"Logical size:             {measured.size():,}", flush=True)

    service_kwargs: dict[str, Any] = {"channel": channel, "token": token}
    if instance:
        service_kwargs["instance"] = instance
    print(f"\nConnecting to IBM channel {channel!r}...", flush=True)
    service = QiskitRuntimeService(**service_kwargs)
    backend = service.backend(requested_backend)
    status = backend.status()
    if not bool(getattr(status, "operational", False)):
        raise RuntimeError(f"IBM backend {requested_backend} is not operational")
    if int(getattr(backend, "num_qubits", 0)) < measured.num_qubits:
        raise RuntimeError(
            f"IBM backend {requested_backend} has {backend.num_qubits} qubits, "
            f"but the circuit requires {measured.num_qubits}"
        )
    print(f"Backend:                  {backend_name(backend)}", flush=True)
    print(f"Backend qubits:           {backend.num_qubits}", flush=True)
    print(
        f"Queue snapshot:           {getattr(status, 'pending_jobs', 'unknown')}",
        flush=True,
    )

    print(
        f"\nTranspiling at optimization level {args.optimization_level}...",
        flush=True,
    )
    pass_manager = generate_preset_pass_manager(
        optimization_level=args.optimization_level,
        backend=backend,
    )
    isa_circuit = pass_manager.run(measured)
    isa_operations = {
        str(name): int(count) for name, count in isa_circuit.count_ops().items()
    }
    print(f"ISA qubits:               {isa_circuit.num_qubits}", flush=True)
    print(f"ISA depth:                {isa_circuit.depth():,}", flush=True)
    print(f"ISA size:                 {isa_circuit.size():,}", flush=True)

    print("\nSubmitting directly with IBM SamplerV2...", flush=True)
    sampler = SamplerV2(mode=backend)
    job = sampler.run([isa_circuit], shots=args.shots)
    remote_job_id = job_identifier(job)
    output_path = args.output_dir.resolve() / (
        f"direct_{backend_name(backend)}-{remote_job_id}.json"
    )
    submission_record: dict[str, Any] = {
        "schemaVersion": 1,
        "provenance": {
            "source": "direct_ibm_runtime_script",
            "script": str(Path(__file__).relative_to(PROJECT_ROOT)),
            "submittedAt": utc_now(),
        },
        "status": "submitted",
        "remoteJobId": remote_job_id,
        "backend": backend_name(backend),
        "shots": args.shots,
        "input": {
            "referencePath": str(args.reference.resolve()),
            "mutatedPath": str(args.mutated.resolve()),
            "sequenceLength": length,
            "classicalMismatchCountForMetadataOnly": mutations,
            "referenceSha256": sequence_digest(reference),
            "mutatedSha256": sequence_digest(mutated),
        },
        "schedule": {
            "lambdaMin": schedule.lambda_min,
            "delta": schedule.delta,
            "sequenceLength": schedule.sequence_length,
            "generalizedIterations": schedule.generalized_iterations,
            "predicateQueries": schedule.predicate_queries,
        },
        "logicalCircuit": {
            "qubits": measured.num_qubits,
            "classicalBits": measured.num_clbits,
            "depth": measured.depth(),
            "size": measured.size(),
        },
        "isaCircuit": {
            "qubits": isa_circuit.num_qubits,
            "depth": isa_circuit.depth(),
            "size": isa_circuit.size(),
            "operationCounts": isa_operations,
        },
        "rawHardwareMeasurements": True,
        "errorMitigationApplied": False,
        "scientificBoundaries": [
            "This direct physical-device run is not evidence of end-to-end quantum advantage.",
            "Classical strings are compiled into QROM-style circuit gates.",
            "Counts are raw IBM hardware measurements with no error mitigation.",
        ],
    }
    write_json(output_path, submission_record)
    print(f"Remote IBM job ID:        {remote_job_id}", flush=True)
    print(f"Submission record:        {output_path}", flush=True)
    print(
        f"Waiting up to {args.timeout_seconds:,} seconds for IBM results...",
        flush=True,
    )

    try:
        primitive_result = job.result(timeout=args.timeout_seconds)
        pub_result = primitive_result[0]
        register_data = getattr(pub_result.data, "c_pos")
        counts = normalize_counts(register_data.get_counts())
        returned_shots = sum(counts.values())
        submission_record.update(
            {
                "status": "completed",
                "completedAt": utc_now(),
                "providerStatus": str(job.status()),
                "returnedShots": returned_shots,
                "counts": counts,
                "probabilities": {
                    state: count / returned_shots
                    for state, count in counts.items()
                },
            }
        )
        write_json(output_path, submission_record)
        print(f"IBM job completed with {returned_shots:,} returned shots.", flush=True)
        print(f"Raw result saved to:      {output_path}", flush=True)
        return 0
    except Exception as exc:
        submission_record.update(
            {
                "status": "wait_failed",
                "waitFailedAt": utc_now(),
                "providerStatus": str(job.status()),
                "errorType": type(exc).__name__,
                "error": str(exc),
            }
        )
        write_json(output_path, submission_record)
        print(
            f"Waiting failed, but the remote job may still exist: {remote_job_id}",
            file=sys.stderr,
            flush=True,
        )
        print(f"Updated recovery record:  {output_path}", file=sys.stderr, flush=True)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
