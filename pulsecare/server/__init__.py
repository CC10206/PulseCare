"""Demo server——單一行程,同時 serve 靜態頁與事件流。（尚未實作）

規劃：`app.py`（FastAPI：`/`、`/events`、`/run`、`/replay`、`/ingest`、
`/seed_baseline`）、`pipeline.py`（階段編排,發 SSE 事件）。

**設計要點：** `/run`（真實擷取）與 `/replay`（預錄素材）走**同一條事件流**,
所以 fallback 不是另一個 demo,而是同一個 demo 換資料來源——可反覆排練,
且保證台上看起來一樣。階段契約見 `pulsecare/contracts/events.py`。

單一行程的理由：現行做法要另開 `python -m http.server` 再跑 CLI,
台上兩個行程就是兩倍出錯機會。

相依對應 `pyproject.toml` 的 `[server]` extra。設計見 spec §5.1。
"""
