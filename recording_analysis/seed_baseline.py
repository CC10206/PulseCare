"""
產生一份合成的「前 N 天正常基線」，供 Demo 使用。

正式版本應由真實錄音累積 14 天。Demo 時誠實標註此為模擬資料。

用法:
    python seed_baseline.py --from-wav normal.wav --days 14 -o baseline.json
    python seed_baseline.py --days 14 -o baseline.json     # 用內建典型值
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))

# 一位高齡者在正常狀態下的典型值 (作為沒有真實錄音時的起點)
TYPICAL = {
    "syll_rate": 3.10, "pause_mean_s": 0.28, "f0_sd_st": 2.60,
    "f0_range_st": 7.20, "loud_range": 0.85, "hnr_db": 11.50,
}
# 日間自然波動幅度 (相對標準差)
JITTER = {
    "syll_rate": 0.08, "pause_mean_s": 0.12, "f0_sd_st": 0.10,
    "f0_range_st": 0.10, "loud_range": 0.10, "hnr_db": 0.06,
}


def synthetic_trend(days: int, kind: str = "flat", start: float = 50.0,
                     end: float = 30.0, noise_sd: float = 0.0,
                     rng: np.random.Generator | None = None) -> list[float]:
    """產生一段合成的每日活力指數序列，供 Demo 影片的「7日趨勢」畫面使用。

    kind="flat" 保留舊行為 (每天都是 start)；kind="down"/"up" 從 start
    線性趨向 end，讓黃燈畫面的下滑趨勢是接上真實 alert_level() 邏輯算出來的，
    而不是純視覺上的假象。
    """
    if kind == "flat":
        base = np.full(days, start, dtype=float)
    elif kind == "down":
        base = np.linspace(start, end, days)
    elif kind == "up":
        base = np.linspace(end, start, days)
    else:
        raise ValueError(f"未知的 trend kind: {kind!r} (可用 flat/down/up)")

    if noise_sd > 0:
        if rng is None:
            rng = np.random.default_rng()
        base = base + rng.normal(0, noise_sd, days)

    return [round(float(v), 2) for v in np.clip(base, 0, 100)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-wav", help="以這段真實錄音的特徵為中心產生基線")
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--trend", choices=["flat", "down", "up"], default="flat",
                    help="_index 欄位的示意趨勢，供家屬 App 畫面展示用")
    ap.add_argument("--trend-end", type=float, default=30.0,
                    help="trend=down/up 時的終點指數")
    ap.add_argument("-o", "--out", default="baseline.json")
    args = ap.parse_args()

    if args.from_wav:
        from features import extract_features
        center = extract_features(args.from_wav)["features"]
        print(f"以 {args.from_wav} 的特徵為中心")
    else:
        center = dict(TYPICAL)
        print("使用內建典型值為中心")

    rng = np.random.default_rng(args.seed)
    indices = synthetic_trend(args.days, kind=args.trend, end=args.trend_end,
                               noise_sd=1.5 if args.trend != "flat" else 0.0,
                               rng=rng)
    history = []
    for idx in indices:
        day = {k: float(v * (1 + rng.normal(0, JITTER[k]))) for k, v in center.items()}
        day["_index"] = idx
        history.append(day)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    print(f"已寫出 {args.days} 天基線 → {args.out}")


if __name__ == "__main__":
    main()
