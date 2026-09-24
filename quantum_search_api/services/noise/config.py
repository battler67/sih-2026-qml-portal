from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .noise_models import (
    FRQI_SINGLE_QUBIT_ERROR,
    FRQI_TWO_QUBIT_ERROR,
    GROVER_SINGLE_QUBIT_ERROR,
    GROVER_TWO_QUBIT_ERROR,
    YLC_ONE_TO_ZERO_ERROR,
    YLC_ZERO_TO_ONE_ERROR,
)


class NoiseSettings(BaseModel):
    single_qubit_error: float | None = Field(
        default=None, ge=0.0, le=0.5, alias="singleQubitError"
    )
    two_qubit_error: float | None = Field(
        default=None, ge=0.0, le=0.5, alias="twoQubitError"
    )
    readout_zero_to_one: float | None = Field(
        default=None, ge=0.0, le=0.5, alias="readoutZeroToOne"
    )
    readout_one_to_zero: float | None = Field(
        default=None, ge=0.0, le=0.5, alias="readoutOneToZero"
    )

    model_config = ConfigDict(populate_by_name=True)

    def resolved(self, algorithm: str) -> dict[str, float]:
        if algorithm == "frqi":
            return {
                "singleQubitError": (
                    FRQI_SINGLE_QUBIT_ERROR
                    if self.single_qubit_error is None
                    else self.single_qubit_error
                ),
                "twoQubitError": (
                    FRQI_TWO_QUBIT_ERROR
                    if self.two_qubit_error is None
                    else self.two_qubit_error
                ),
            }
        if algorithm == "grover":
            return {
                "singleQubitError": (
                    GROVER_SINGLE_QUBIT_ERROR
                    if self.single_qubit_error is None
                    else self.single_qubit_error
                ),
                "twoQubitError": (
                    GROVER_TWO_QUBIT_ERROR
                    if self.two_qubit_error is None
                    else self.two_qubit_error
                ),
            }
        return {
            "readoutZeroToOne": (
                YLC_ZERO_TO_ONE_ERROR
                if self.readout_zero_to_one is None
                else self.readout_zero_to_one
            ),
            "readoutOneToZero": (
                YLC_ONE_TO_ZERO_ERROR
                if self.readout_one_to_zero is None
                else self.readout_one_to_zero
            ),
        }
