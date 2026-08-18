"""
PulseCare — 聲學特徵抽取 (Phase 1)

全部在本地端執行。輸入一段 16kHz wav，輸出一組去識別化的數值特徵。
原始音檔在呼叫端負責銷毀，本模組不保留任何音訊。
"""
import numpy as np
import librosa
import parselmouth
import opensmile

# eGeMAPSv02 = 情感運算領域的標準最小特徵集 (88 維)
# 用標準特徵集而非自創特徵，是為了讓評審/心理師能對照既有文獻
_SMILE = opensmile.Smile(
    feature_set=opensmile.FeatureSet.eGeMAPSv02,
    feature_level=opensmile.FeatureLevel.Functionals,
)

# 我們只取 6 個可解釋的指標送進計分，其餘 82 維留在本地不外傳
FEATURE_KEYS = [
    "syll_rate",     # 音節速率 (語速代理指標)
    "pause_mean_s",  # 平均停頓長度
    "f0_sd_st",      # 音高變異度 (半音)
    "f0_range_st",   # 音高動態範圍 (半音)
    "loud_range",    # 音量動態範圍
    "hnr_db",        # 諧噪比 (越低越沙啞)
]


def extract_features(wav_path: str) -> dict:
    """回傳 6 個核心特徵 + 若干輔助資訊。"""
    y, sr = librosa.load(wav_path, sr=16000, mono=True)
    duration = len(y) / sr
    if duration < 3.0:
        raise ValueError(f"音檔太短 ({duration:.1f}s)，至少需 3 秒才能穩定估計特徵")

    eg = _SMILE.process_file(wav_path).iloc[0]

    # parselmouth 另外算一次 F0，作為 openSMILE 的交叉驗證
    snd = parselmouth.Sound(wav_path)
    pitch = snd.to_pitch(time_step=0.01, pitch_floor=60, pitch_ceiling=400)
    f0 = pitch.selected_array["frequency"]
    f0 = f0[f0 > 0]
    if len(f0) > 10:
        # 轉半音再取標準差：對不同基頻的人可比較 (男女/高低嗓音)
        f0_sd_st = float(np.std(12 * np.log2(f0 / np.median(f0))))
    else:
        f0_sd_st = 0.0

    feats = {
        "syll_rate":    float(eg["loudnessPeaksPerSec"]),
        "pause_mean_s": float(eg["MeanUnvoicedSegmentLength"]),
        "f0_sd_st":     round(f0_sd_st, 4),
        "f0_range_st":  float(eg["F0semitoneFrom27.5Hz_sma3nz_pctlrange0-2"]),
        "loud_range":   float(eg["loudness_sma3_pctlrange0-2"]),
        "hnr_db":       float(eg["HNRdBACF_sma3nz_amean"]),
    }

    meta = {
        "duration_s":     round(duration, 2),
        "voiced_per_sec": float(eg["VoicedSegmentsPerSec"]),
        "jitter":         float(eg["jitterLocal_sma3nz_amean"]),
        "shimmer_db":     float(eg["shimmerLocaldB_sma3nz_amean"]),
    }
    return {"features": feats, "meta": meta}


# ---- 詞彙層特徵 (需要逐字稿) ----------------------------------------

NEGATIVE_LEXICON = [
    "算了", "沒意思", "累了", "麻煩", "沒用", "無聊", "孤單",
    "懶得", "隨便", "不想", "沒差", "煩",
]


def lexical_features(transcript: str) -> dict:
    """對逐字稿做極簡的詞彙統計。刻意保持透明可稽核，不用黑箱模型。"""
    n_chars = len(transcript.strip())
    hits = [w for w in NEGATIVE_LEXICON if w in transcript]
    return {
        "n_chars": n_chars,
        "neg_word_count": len(hits),
        "neg_words": hits,
        "neg_ratio": round(len(hits) / max(n_chars / 20, 1), 4),
    }


if __name__ == "__main__":
    import sys, json
    print(json.dumps(extract_features(sys.argv[1]), indent=2, ensure_ascii=False))
