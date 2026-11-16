from __future__ import annotations

from weather_intelligence.runtime import peak_working_set_bytes


def test_peak_working_set_measurement_is_supported_or_explicitly_unavailable() -> None:
    value = peak_working_set_bytes()
    assert value is None or value > 0
