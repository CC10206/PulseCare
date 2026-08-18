"""
產生 app/green_example.json 與 app/yellow_example.json，
供 family_view.html 在拍攝/開發時使用。

⚠️ 這裡的「今天」特徵值是手動指定的示意數字，不是真的錄音跑出來的
（本機沒有裝 librosa/opensmile，見 README 的環境設置）。但計分邏輯
(build_baseline / vitality_index / alert_level / build_report) 全部是
analyze.py 實際會呼叫的同一套真實程式碼，不是另外編的假資料。

正式錄好 normal.wav / low.wav 後，改用：
    python analyze.py normal.wav --baseline baseline_flat.json  --json app/green_example.json
    python analyze.py low.wav    --baseline baseline_down.json  --json app/yellow_example.json
取代這支腳本產生的範例檔。
"""
import json
import os

import numpy as np

from scoring import build_baseline, vitality_index, alert_level, build_report
from seed_baseline import TYPICAL, JITTER, synthetic_trend

# 依 scoring.DIRECTION 的方向、對 TYPICAL 做約 1.5 個標準單位的示意「低落
# 語氣」偏移 (刻意不用滿分 -3 的極端值，避免看起來像數值溢位而非真實分布)
LOW_TODAY = {
    "syll_rate": 2.73,
    "pause_mean_s": 0.33,
    "f0_sd_st": 2.21,
    "f0_range_st": 6.12,
    "loud_range": 0.72,
    "hnr_db": 10.47,
}


def _make_history(days: int, trend: str, seed: int = 42) -> list[dict]:
    rng = np.random.default_rng(seed)
    indices = synthetic_trend(days, kind=trend,
                               noise_sd=1.5 if trend != "flat" else 0.0, rng=rng)
    history = []
    for idx in indices:
        day = {k: float(v * (1 + rng.normal(0, JITTER[k]))) for k, v in TYPICAL.items()}
        day["_index"] = idx
        history.append(day)
    return history


def _build(today_feats: dict, history: list[dict], elder_name: str) -> dict:
    base = build_baseline(history)
    idx, contribs = vitality_index(today_feats, base)
    recent = [h["_index"] for h in history] + [idx]
    level = alert_level(recent)
    return build_report(idx, contribs, level, recent[-7:], elder_name=elder_name)


def main():
    out_dir = os.path.dirname(__file__)

    green = _build(dict(TYPICAL), _make_history(14, "flat"), elder_name="李奶奶")
    with open(os.path.join(out_dir, "green_example.json"), "w", encoding="utf-8") as f:
        json.dump(green, f, indent=2, ensure_ascii=False)
    print("green_example.json:", green["index"], green["level"])

    yellow = _build(LOW_TODAY, _make_history(14, "down"), elder_name="李奶奶")
    with open(os.path.join(out_dir, "yellow_example.json"), "w", encoding="utf-8") as f:
        json.dump(yellow, f, indent=2, ensure_ascii=False)
    print("yellow_example.json:", yellow["index"], yellow["level"])


if __name__ == "__main__":
    main()
