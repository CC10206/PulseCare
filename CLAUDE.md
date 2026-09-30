# CLAUDE.md — PulseCare 開發約定

給 Claude Code 與後續協作者的工作約定。**硬性約束那一節違反了會真的出事**，
不是風格偏好。

---

## 開發方式

- **敏捷式開發，不走 TDD。** 先讓功能在真實資料上跑起來，再回頭補測試。
  不要求先寫失敗的測試再寫實作。
- 測試補在**純邏輯**上（計分、事件流、詞彙規則）。不為需要麥克風、
  真實模型或網路的路徑寫測試。
- 架構與範圍先討論定案再寫程式；範圍內的小改動直接動手，不用每步問。
- 遇到不確定的地方，先把不依賴那個答案的部分做完，再把問題一次問清楚。

## Git

- **commit 一定要手動同意。** 絕不自己 commit，**即使某個 skill 的流程說
  「把設計文件 commit 起來」也一樣**。把改動說明清楚，等明確同意那一次 commit。
- 同樣需要事前同意：`git add`、`git rm --cached`、`git push`、建分支、
  任何會改動 index 或歷史的操作。
- 唯讀的 git 指令（`status` / `log` / `diff` / `ls-files`）可自由使用。
- 不要在 `main` 上直接開發。

## 語言

- 文件、程式註解、對話說明用**繁體中文**。
- commit message 用英文（沿用既有慣例）。
- 程式碼識別字用英文。

---

## 硬性約束

### 環境

- Python **3.11 或 3.12**。3.13+ 部分套件輪子還不齊。
- **venv 的路徑不能含非 ASCII 字元。** `opensmile` 用 `ctypes` 把套件安裝路徑
  以純 ASCII 傳給 C library；venv 建在像 `D:\桌面\PulseCare\.venv` 這種路徑下，
  `opensmile.Smile(...)` 會直接丟 `UnicodeEncodeError`。而且**只 `import
  opensmile` 不會觸發，要實際建立 `Smile` 物件才炸**，很容易漏測。
  專案程式碼本身放中文路徑沒關係，**venv 要建在純 ASCII 路徑**。
- **OpenVINO 必須在專案中被使用**（技術棧約束）。但**不要求跑在邊緣裝置上**——
  邊緣節點只做純 DSP 特徵抽取，不需要 OpenVINO。

### 隱私不變量

這是專案的核心主張，不可妥協。

- 原始音訊在特徵抽取完成後立即 `os.remove`，**永不離開擷取裝置**。
  `--keep-audio` 只在除錯時用，正式流程一律銷毀。
- 逐字稿在詞彙指標抽取完成後立即銷毀，**比照音訊的紀律**。
- 跨網路只傳 6 個浮點數 + meta。**不傳音訊、不傳逐字稿。**
- 持久化的只有 6 個聲學數值 + 面向計數（整數）。

### 方法論不變量

- 指數是「相對於**個人**基線的偏離」，**不是跨人比較，不是診斷**。
- 基線用 **median/MAD**，不用 mean/std（對感冒、訪客、電視聲等離群值穩健）。
- **語速從聲學算（`loudnessPeaksPerSec`），不從逐字稿算字數/秒。**
  兩個理由：語言無關（台語、國語、客語都能算）、不受 ASR 準確率影響。
- **詞彙指標永遠不得影響活力指數。** 它受 ASR 品質限制（Whisper 對高齡者
  台灣國語/台語口音辨識差），是心理師專屬的低信賴度輔助資訊。
- 基線必須用「**與佈署時相同的裝置 + 相同麥克風**」採集。`hnr_db` 本質上
  在量噪音，換麥克風特徵會系統性偏移，舊基線立即失效。

### 誠實邊界

展示與旁白時：

- **不要用後製偽造 `low.wav`。** 實測過 `librosa.effects.time_stretch` 降速再
  壓縮動態，phase vocoder 的假影會讓 `loudnessPeaksPerSec` 和
  `loudness_pctlrange` 反而**上升**，指數不降反升。真的重錄比較快也比較誠實。
- 合成基線要主動說是合成的。
- 預先算好的結果要說是預先算好的，不要講成即時。
- 六項特徵權重目前是**等權佔位值**，未經心理師校準——要講出來。
- 本系統**不是臨床診斷工具**，不應被解讀為憂鬱症篩檢結果。

---

## 測試

```bash
python -m pytest -q
```

測試檔與被測模組放**同一層資料夾**。只測不需要硬體/模型的純邏輯部分。

---

## 不要做的事

- **不要為了讓數字好看去調特徵權重。** 若 `low.wav` 沒有明顯低於 `normal.wav`，
  先看 `explain()` / 特徵貢獻，找出哪個特徵方向反了或沒動——通常是錄音表演
  差異不夠大，重錄比調參數有效。
- **不要動 `qwen_3_tts_helper.py`。** 外部 vendored 檔，不進版控，改了之後
  跟上游對不起來。
- **不要加 RAG、向量庫、嵌入模型。** 已評估並排除，理由見
  `docs/superpowers/specs/2026-09-25-finals-demo-and-edge-split-design.md` §8.4
  （沒有語料庫要檢索、臨床建議的法律風險、2GB 邊緣裝置裝不下）。
- 不要把 TTS 換模型排進決賽前的工作——已排除，是純風險。

---

## 目錄結構

```
pulsecare/
├── contracts/     跨層資料契約（特徵鍵名、SSE 事件階段、/ingest schema）
├── sensing/       邊緣節點能跑的一切——純 DSP，無 OpenVINO
├── scoring.py     個人基線、活力指數、燈號、可解釋性、報告組裝
├── inference/     OpenVINO 推論：Whisper / LLM / TTS（僅 server 端）
│   └── vendor/    外部 vendored 程式碼，不進版控、不要修改
├── lexical/       詞彙層（尚未實作）
├── server/        demo server：SSE 事件流（尚未實作）
└── cli/           命令列入口
web/               靜態頁面 + 示範資料
fixtures/          基線與錄音（不進版控）
docs/              詳細步驟、拍攝腳本、設計規格
models/            轉檔後的 OpenVINO IR（不進版控）
```

**相依方向一律由上往下**：`cli` → `server` → `lexical` / `inference` →
`scoring` → `sensing` → `contracts`。不可反向 import。

### 相依分層是可安裝的，不只是文件

`pyproject.toml` 用 extras 把分層變成真的：

```bash
pip install -e .[server,dev]     # 開發機 / 閘道器
pip install -e .[sensing] --extra-index-url https://download.pytorch.org/whl/cpu
                                 # 邊緣節點（KNEO Pi）
pip install -e .[convert]        # 只轉模型時（建議另一個 venv）
```

`[sensing]` 刻意**不含** OpenVINO、librosa、fastapi——不是靠自律，是靠裝不到。

`pulsecare/sensing/test_no_heavy_deps.py` 用靜態 AST 檢查把這條規則變成測試。
它目前是 `xfail`，因為 `features.py` 還 import 著 parselmouth 與 librosa；
等那兩項改掉會轉為 XPASS，屆時把 xfail 標記拿掉。

### 執行方式

所有入口都是模組，不要直接跑檔案路徑：

```bash
python -m pulsecare.cli.analyze sample.wav --baseline fixtures/baseline.json
python -m pulsecare.cli.seed_baseline --from-wav normal.wav -o fixtures/baseline.json
python -m pulsecare.cli.live_session --baseline fixtures/baseline.json
python -m pulsecare.cli.generate_examples
```

專案內部 import 的 `sys.path.insert(...)` 舊做法已全部移除，不要加回來。
唯一的例外是 `inference/tts.py` 裡用來定位外部 `Qwen3-TTS/` clone 的那一段——
那是外部原始碼樹，不是專案內的模組。

## 參考文件

- `docs/plan.md` — 環境建置、模型轉檔、六項特徵說明、驗收標準
- `docs/demo-steps.md` — 拍攝腳本、實測耗時、旁白要點、故障排除
- `docs/tts-setup.md` — Qwen3-TTS 可行性驗證與轉檔步驟
- `docs/superpowers/specs/` — 設計規格（**不進版控**）
