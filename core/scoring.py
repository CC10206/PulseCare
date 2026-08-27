"""
PulseCare — 個人化基線與語音活力指數 (Phase 1)

設計原則：
  1. 指數是「相對於這位長者自己的常態」的偏離，不是跨人比較，更不是診斷。
  2. 計分公式完全透明可稽核 —— 心理師能看懂、能調參數。
  3. 用 median/MAD 而非 mean/std：對離群值穩健 (感冒、訪客、電視聲)。
"""
import datetime
import json
import numpy as np
from feature_keys import FEATURE_KEYS

# +1 = 數值越高代表越有活力；-1 = 越高代表越低落
DIRECTION = {
    "syll_rate":    +1,   # 語速慢是高齡憂鬱的常見聲學特徵
    "pause_mean_s": -1,   # 停頓變長 = 言語遲緩
    "f0_sd_st":     +1,   # 音高平坦無起伏 = 情感表達減少
    "f0_range_st":  +1,
    "loud_range":   +1,   # 音量動態收窄
    "hnr_db":       +1,   # 諧噪比低 = 聲線沙啞無力
}

# 佔位權重，全部等權。實際部署前應由合作心理師依臨床經驗校準。
WEIGHTS = {k: 1.0 for k in FEATURE_KEYS}

MIN_BASELINE_DAYS = 14   # 校準期：前 14 天只蒐集不評分


def build_baseline(history: list[dict]) -> dict:
    """history: [{"syll_rate":..., ...}, ...] 每天一筆。回傳每個特徵的 (median, MAD)。"""
    base = {}
    for k in FEATURE_KEYS:
        vals = np.array([h[k] for h in history], dtype=float)
        med = float(np.median(vals))
        mad = float(np.median(np.abs(vals - med)))
        # MAD 為 0 時給一個下限，避免除零放大雜訊
        base[k] = (med, max(mad, abs(med) * 0.02 + 1e-6))
    return base


def vitality_index(today: dict, baseline: dict) -> tuple[float, dict]:
    """回傳 (0-100 指數, 各特徵的 robust z-score)。50 = 該長者的個人常態。"""
    contribs, z_sum, w_sum = {}, 0.0, 0.0
    for k in FEATURE_KEYS:
        med, mad = baseline[k]
        z = (today[k] - med) / (1.4826 * mad)      # robust z-score
        z = DIRECTION[k] * float(np.clip(z, -3, 3))  # 截斷，單一特徵不得主導
        contribs[k] = round(z, 2)
        z_sum += WEIGHTS[k] * z
        w_sum += WEIGHTS[k]
    index = 50 + (50 / 3) * (z_sum / w_sum)
    return round(float(np.clip(index, 0, 100)), 1), contribs


def alert_level(recent: list[float], threshold: float = 38.0,
                low_days: int = 5, window: int = 7) -> str:
    """連續觀察窗內有 low_days 天低於門檻 → 黃燈 (柔性關懷)。"""
    w = recent[-window:]
    if len(w) < window:
        return "calibrating"
    n_low = sum(1 for v in w if v < threshold)
    return "yellow" if n_low >= low_days else "green"


def build_report(idx: float, contribs: dict, level: str, trend: list[float],
                  elder_name: str = "長者", date: str | None = None,
                  transcript: str | None = None) -> dict:
    """組成給家屬/社工 App 畫面用的結構化報告 (見 analyze.py --json)。

    contribs/transcript 兩個附加欄位是給心理師示範頁面
    (app/clinician_demo.html) 用的完整資訊；family_view.html 只讀
    explain/disclaimer 等既有欄位，不受影響。
    """
    return {
        "elder_name": elder_name,
        "date": date or datetime.date.today().isoformat(),
        "index": idx,
        "level": level,
        "trend": trend,
        "contribs": contribs,
        "transcript": transcript,
        "explain": explain(contribs),
        "disclaimer": "本指數為相對於個人基線的偏離程度，非臨床診斷工具。",
    }


def explain(contribs: dict, top_n: int = 3) -> list[str]:
    """可解釋性：告訴家屬「為什麼是黃燈」。"""
    labels = {
        "syll_rate": "語速", "pause_mean_s": "停頓長度", "f0_sd_st": "語調起伏",
        "f0_range_st": "音高範圍", "loud_range": "音量變化", "hnr_db": "聲線清晰度",
    }
    worst = sorted(contribs.items(), key=lambda kv: kv[1])[:top_n]
    return [f"{labels[k]}較平常偏離 {abs(z):.1f} 個標準單位" for k, z in worst if z < -0.8]


if __name__ == "__main__":
    import sys
    with open(sys.argv[1], encoding="utf-8") as f:
        hist = json.load(f)
    base = build_baseline(hist[:-1])
    idx, contribs = vitality_index(hist[-1], base)
    print(f"活力指數 = {idx}")
    print("特徵貢獻:", contribs)
    print("說明:", explain(contribs))
