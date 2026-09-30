"""PulseCare — 從長者日常對話的聲音（不是內容）偵測活力狀態變化。

分層（相依方向一律由上往下，不可反向 import）：

    cli/         人用的入口
    server/      demo server：SSE 事件流、/run、/replay、/ingest
    lexical/     詞彙層（僅 server 端）
    inference/   OpenVINO 推論：Whisper / LLM / TTS（僅 server 端）
    scoring      個人基線、活力指數、燈號、可解釋性、報告組裝
    sensing/     邊緣節點能跑的一切（純 DSP，無 OpenVINO）
    contracts/   跨層資料契約，任何一層都可 import

隱私邊界見 CLAUDE.md；架構理由見
docs/superpowers/specs/2026-09-25-finals-demo-and-edge-split-design.md
"""
