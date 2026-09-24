"""Central encoding and simulator configuration."""

DNA_2BIT_ENCODING: dict[str, str] = {
    "A": "00",
    "C": "01",
    "G": "10",
    "T": "11",
}

# The paper explicitly introduces the terminator code 100. It does not give a
# full three-bit DNA table, so these zero-prefixed DNA codes are an engineering
# extension of Table 1 for boundary-safe mode.
DNA_3BIT_TERMINATOR_ENCODING: dict[str, str] = {
    "A": "000",
    "C": "001",
    "G": "010",
    "T": "011",
    "$": "100",
}

DEFAULT_SHOTS = 8192
DEFAULT_SEED = 42
