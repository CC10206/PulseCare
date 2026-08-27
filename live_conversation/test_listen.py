import pytest

from listen import EndOfTurnDetector, pick_input_device


def test_stops_when_end_event_received_after_start():
    detector = EndOfTurnDetector(chunk_s=0.032, max_total_s=20.0)

    assert detector.push({"start": 0.5}) is False
    assert detector.push(None) is False
    assert detector.push(None) is False
    assert detector.push({"end": 1.2}) is True


def test_does_not_stop_on_end_event_without_prior_start():
    detector = EndOfTurnDetector(chunk_s=0.032, max_total_s=20.0)

    assert detector.push({"end": 0.1}) is False


def test_does_not_stop_while_still_under_max_total_with_no_events():
    detector = EndOfTurnDetector(chunk_s=0.032, max_total_s=1.0)

    for _ in range(10):  # 10 * 0.032s = 0.32s, well under 1.0s cap
        assert detector.push(None) is False


def test_stops_at_max_total_duration_as_safety_cap():
    detector = EndOfTurnDetector(chunk_s=0.5, max_total_s=1.0)

    assert detector.push({"start": 0.0}) is False  # 0.5s elapsed
    assert detector.push(None) is True  # 1.0s elapsed, hits cap even without an end event


def test_started_is_false_when_no_speech_was_ever_detected():
    detector = EndOfTurnDetector(chunk_s=0.5, max_total_s=1.0)

    detector.push(None)
    detector.push(None)

    assert detector.started is False


def test_started_is_true_once_a_start_event_is_seen():
    detector = EndOfTurnDetector(chunk_s=0.032, max_total_s=20.0)

    detector.push({"start": 0.1})

    assert detector.started is True


def _devices():
    return [
        {"name": "speakers", "max_input_channels": 0},
        {"name": "mic array", "max_input_channels": 2},
        {"name": "mic", "max_input_channels": 2},
    ]


def test_pick_input_device_uses_default_when_it_has_input_channels():
    assert pick_input_device(_devices(), default_index=1) == 1


def test_pick_input_device_falls_back_when_default_is_out_of_range():
    assert pick_input_device(_devices(), default_index=-1) == 1


def test_pick_input_device_falls_back_when_default_has_no_input_channels():
    assert pick_input_device(_devices(), default_index=0) == 1


def test_pick_input_device_raises_when_nothing_has_input_channels():
    devices = [{"name": "speakers", "max_input_channels": 0}]

    with pytest.raises(RuntimeError):
        pick_input_device(devices, default_index=0)
