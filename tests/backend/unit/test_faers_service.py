"""
Unit tests for pure functions in backend.services.faers_service.
No external API calls; no DB required.
"""

from backend.services.faers_service import _cusum_detect, _confidence_label


# ── _cusum_detect ─────────────────────────────────────────────────────────────

def test_cusum_spike_triggers_signal():
    # FAERS-U-01: stable baseline then a large spike → signal after spike
    counts = [10, 12, 11, 10, 9, 200, 15, 12, 11, 10, 9, 10]
    signals = _cusum_detect(counts)
    assert any(signals[5:]), "CUSUM should fire after the spike at index 5"


def test_cusum_stable_series_no_signal():
    # FAERS-U-02: near-constant series → zero signals
    counts = [50, 52, 48, 51, 49, 50, 53, 47, 50, 51, 49, 50]
    signals = _cusum_detect(counts)
    assert not any(signals), "Stable series should not trigger CUSUM signal"


def test_cusum_empty_series():
    assert _cusum_detect([]) == []


def test_cusum_all_zeros():
    signals = _cusum_detect([0, 0, 0, 0, 0])
    assert not any(signals)


def test_cusum_returns_same_length():
    counts = [5, 10, 15, 20]
    signals = _cusum_detect(counts)
    assert len(signals) == len(counts)


# ── _confidence_label ─────────────────────────────────────────────────────────

def test_confidence_high():
    # FAERS-U-03 upper bound
    assert _confidence_label(50) == "high"
    assert _confidence_label(200) == "high"


def test_confidence_medium():
    assert _confidence_label(10) == "medium"
    assert _confidence_label(49) == "medium"


def test_confidence_low():
    assert _confidence_label(3) == "low"
    assert _confidence_label(9) == "low"


def test_confidence_insufficient():
    # FAERS-U-03 lower bound
    assert _confidence_label(0) == "insufficient"
    assert _confidence_label(2) == "insufficient"
