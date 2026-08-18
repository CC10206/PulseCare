import numpy as np
import pytest

from scoring import alert_level
from seed_baseline import synthetic_trend


def test_synthetic_trend_flat_returns_constant_value():
    result = synthetic_trend(days=5, kind="flat", start=50.0)

    assert result == [50.0, 50.0, 50.0, 50.0, 50.0]


def test_synthetic_trend_down_starts_high_ends_low():
    result = synthetic_trend(days=7, kind="down", start=50.0, end=30.0)

    assert result[0] == pytest.approx(50.0)
    assert result[-1] == pytest.approx(30.0)
    assert all(result[i] >= result[i + 1] for i in range(len(result) - 1))


def test_synthetic_trend_down_triggers_real_yellow_alert():
    # 這條合成序列接上真實的 alert_level() 邏輯，應該要能真的算出 yellow，
    # 而不是畫面上「看起來」下滑而已。
    result = synthetic_trend(days=14, kind="down", start=50.0, end=30.0)

    assert alert_level(result) == "yellow"


def test_synthetic_trend_with_noise_is_reproducible_given_same_rng_seed():
    a = synthetic_trend(days=10, kind="down", noise_sd=1.5,
                         rng=np.random.default_rng(7))
    b = synthetic_trend(days=10, kind="down", noise_sd=1.5,
                         rng=np.random.default_rng(7))

    assert a == b


def test_synthetic_trend_invalid_kind_raises():
    with pytest.raises(ValueError):
        synthetic_trend(days=5, kind="sideways")
