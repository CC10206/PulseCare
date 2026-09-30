"""SSE 事件流的階段契約。

demo server 的 `/run`（真實擷取）與 `/replay`（預錄素材）必須發出**完全相同
的階段序列**——這是 fallback 正確性的核心保證：台上任一環節失敗，切到
`/replay` 之後畫面流程一模一樣。`pulsecare/sensing/test_no_heavy_deps.py`
之外，這也是少數值得寫測試的純邏輯之一。

每個事件的外層形狀固定為：

    {"stage": <STAGES 之一>, "seq": <遞增整數>, "t_ms": <自起始毫秒>,
     "payload": {...}}
"""

#: 階段的正規順序。`/run` 與 `/replay` 都必須照這個順序發，
#: 唯一例外是 ERROR 可以在任何階段之後插入並終止該輪。
STAGES = (
    "greeting",          # payload: {text, audio_url}   播放預合成問候語
    "recording",         # payload: {max_s}             顯示錄音中 + 波形
    "vad_stop",          # payload: {duration_s, started}
    "audio_destroyed",   # payload: {path_removed}      隱私論述的視覺證據
    "features",          # payload: {features, meta}    逐項填入 6 個數值
    "scored",            # payload: {index, level, contribs, explain, trend}
    "done",              # payload: {}
)

#: 錯誤事件不在正規序列裡,可在任何階段後插入。
#: payload: {stage, message, recoverable}
ERROR = "error"
