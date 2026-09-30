"""邊緣節點 → server 的 `POST /ingest` 請求契約。

**這個 schema 本身就是隱私邊界**：欄位裡沒有音訊、沒有逐字稿。原始錄音在
邊緣節點上抽完特徵就 `os.remove`，跨網路的只有 6 個浮點數 + meta。
新增欄位前先確認它不會讓原始內容重新離開裝置。
"""
from pulsecare.contracts.feature_keys import FEATURE_KEYS

#: 請求本體的必填頂層欄位。
REQUIRED_FIELDS = ("node_id", "captured_at", "duration_s", "features")

#: `features` 物件的必填鍵——就是六項核心特徵,不多不少。
REQUIRED_FEATURE_KEYS = FEATURE_KEYS

#: `meta` 為選填的輔助資訊（非計分用）。
OPTIONAL_META_KEYS = ("voiced_per_sec", "jitter", "shimmer_db")


def validate(body: dict) -> list[str]:
    """檢查 `/ingest` 請求本體。回傳問題描述的清單,空清單代表通過。

    純邏輯、無相依,可直接測試。刻意回傳清單而不是丟例外——一次把所有問題
    告訴呼叫端,比讓邊緣節點一個一個試錯有用。
    """
    problems = []

    for field in REQUIRED_FIELDS:
        if field not in body:
            problems.append(f"缺少必填欄位 {field!r}")

    duration = body.get("duration_s")
    if duration is not None:
        if not isinstance(duration, (int, float)) or isinstance(duration, bool):
            problems.append("duration_s 必須是數字")
        elif duration < 3.0:
            # 與 sensing/features.py 的下限一致
            problems.append(f"duration_s {duration} 小於 3 秒,特徵無法穩定估計")

    feats = body.get("features")
    if feats is None:
        return problems
    if not isinstance(feats, dict):
        problems.append("features 必須是物件")
        return problems

    for key in REQUIRED_FEATURE_KEYS:
        if key not in feats:
            problems.append(f"features 缺少 {key!r}")
        elif not isinstance(feats[key], (int, float)) or isinstance(feats[key], bool):
            problems.append(f"features[{key!r}] 必須是數字")

    for key in feats:
        if key not in REQUIRED_FEATURE_KEYS:
            problems.append(f"features 含未知鍵 {key!r}")

    return problems
