import datetime

from scoring import build_report


def _sample_contribs():
    return {
        "syll_rate": -1.3,
        "pause_mean_s": -0.5,
        "f0_sd_st": -0.9,
        "f0_range_st": -0.2,
        "loud_range": 0.1,
        "hnr_db": -0.3,
    }


def test_build_report_contains_core_fields():
    report = build_report(
        idx=34.2,
        contribs=_sample_contribs(),
        level="yellow",
        trend=[50.0, 48.0, 40.0, 34.2],
        elder_name="李奶奶",
        date="2026-08-19",
    )

    assert report["elder_name"] == "李奶奶"
    assert report["date"] == "2026-08-19"
    assert report["index"] == 34.2
    assert report["level"] == "yellow"
    assert report["trend"] == [50.0, 48.0, 40.0, 34.2]
    assert report["disclaimer"] == "本指數為相對於個人基線的偏離程度，非臨床診斷工具。"


def test_build_report_default_date_is_today():
    report = build_report(
        idx=50.0,
        contribs=_sample_contribs(),
        level="green",
        trend=[50.0],
    )

    assert report["date"] == datetime.date.today().isoformat()


def test_build_report_explain_reflects_worst_contribs():
    report = build_report(
        idx=34.2,
        contribs=_sample_contribs(),
        level="yellow",
        trend=[34.2],
    )

    assert any("語速" in line for line in report["explain"])


def test_build_report_includes_contribs_and_transcript():
    report = build_report(
        idx=34.2,
        contribs=_sample_contribs(),
        level="yellow",
        trend=[34.2],
        transcript="早安，昨晚睡得不太好。",
    )

    assert report["contribs"] == _sample_contribs()
    assert report["transcript"] == "早安，昨晚睡得不太好。"


def test_build_report_transcript_defaults_to_none():
    report = build_report(
        idx=50.0,
        contribs=_sample_contribs(),
        level="green",
        trend=[50.0],
    )

    assert report["transcript"] is None
