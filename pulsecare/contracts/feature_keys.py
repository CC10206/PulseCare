"""共用常數：6 個核心聲學特徵的鍵名。

獨立成檔（而非放在 features.py）是為了讓 scoring.py 等純計分邏輯
可以在不安裝 librosa/opensmile/parselmouth 的環境下被匯入與測試——
這些模組只需要鍵名列表本身，不需要真的抽取特徵。
"""

# 我們只取 6 個可解釋的指標送進計分，其餘 82 維留在本地不外傳
FEATURE_KEYS = [
    "syll_rate",     # 音節速率 (語速代理指標)
    "pause_mean_s",  # 平均停頓長度
    "f0_sd_st",      # 音高變異度 (半音)
    "f0_range_st",   # 音高動態範圍 (半音)
    "loud_range",    # 音量動態範圍
    "hnr_db",        # 諧噪比 (越低越沙啞)
]
