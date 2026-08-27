# 心理師示範介面（Clinician Demo Interface）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增一個按鈕觸發、全自動播放的單頁示範介面（`app/clinician_demo.html`），
讓錄影時點一次「Start Demo」就能自動播完「問候 → 正常語氣回答 → 分析報告 →
問候 → 低落語氣回答 → 分析報告 → 對比摘要」，給心理師/評審判讀用。

**Architecture:** 純前端、零後端呼叫。頁面播放本機預先算好的音檔、讀取本機
預先算好的 JSON 報告並渲染，不在點擊當下呼叫任何 Python。`core/scoring.py`
的 `build_report()` 小幅擴充（附加 `contribs`/`transcript` 兩個欄位），
`recording_analysis/analyze.py` 與 `app/generate_examples.py` 跟著把這兩個
欄位接上，`app/family_view.html` 的既有行為不受影響（純附加欄位）。

**Tech Stack:** Python 3.12（既有 `core`/`recording_analysis` 模組）、純
HTML/CSS/原生 JS（Web Audio API 做即時波形、Fetch API 讀 JSON，無框架/無
build step，比照 `app/family_view.html` 既有寫法）、pytest。

**Spec:** `docs/superpowers/specs/2026-08-25-clinician-demo-interface-design.md`

## Global Constraints

- 純前端、零後端呼叫：`Start Demo` 按下去之後不得呼叫任何 Python 分析管線。
- 不修改 `app/family_view.html` 既有行為或文案。
- `app/demo_assets/` 底下所有檔案（wav 與 json）都不進 git。
- 六個特徵鍵名與順序固定用 `core/feature_keys.py` 的 `FEATURE_KEYS`：
  `syll_rate`、`pause_mean_s`、`f0_sd_st`、`f0_range_st`、`loud_range`、`hnr_db`。
- 免責聲明文案沿用 `core/scoring.py` 既有字串「本指數為相對於個人基線的偏離
  程度，非臨床診斷工具。」，不得更動語意。
- 圖示一律用內嵌 SVG（來源：Lucide，MIT 授權），不掛外部 CDN、不裝 npm 套件
  ——錄影現場網路狀況不應影響畫面。

---

### Task 1: `build_report()` 附加 `contribs` 與 `transcript` 欄位

**Files:**
- Modify: `core/scoring.py:66-77`（`build_report()`）
- Test: `core/test_scoring.py`

**Interfaces:**
- Produces：`build_report(idx: float, contribs: dict, level: str, trend: list[float], elder_name: str = "長者", date: str | None = None, transcript: str | None = None) -> dict`。
  回傳字典新增兩個附加欄位：`"contribs"`（傳入的完整 6 項特徵 z-score dict，
  未經過濾）與 `"transcript"`（傳入的逐字稿字串，預設 `None`）。既有欄位
  `elder_name`/`date`/`index`/`level`/`trend`/`explain`/`disclaimer` 不變。

- [ ] **Step 1: 在 `core/test_scoring.py` 補兩個失敗中的測試**

在檔案最後面（`test_build_report_explain_reflects_worst_contribs` 之後）加入：

```python
def test_build_report_includes_contribs_and_transcript():
    report = build_report(
        idx=34.2,
        contribs=_sample_contribs(),
        level="yellow",
        trend=[34.2],
        transcript="早安，昨晚睡得不太好。",
    )

    assert report["contribs"] == _sample_contribs()
    assert report["transcript"] == "早安，昨晚睡得不太好。"


def test_build_report_transcript_defaults_to_none():
    report = build_report(
        idx=50.0,
        contribs=_sample_contribs(),
        level="green",
        trend=[50.0],
    )

    assert report["transcript"] is None
```

- [ ] **Step 2: 執行測試，確認失敗**

Run: `python -m pytest core/test_scoring.py -q`
Expected: 2 個新測試 FAIL，錯誤訊息是 `KeyError: 'contribs'`（或 `'transcript'`）
——因為 `build_report()` 目前的回傳字典裡還沒有這兩個鍵。

- [ ] **Step 3: 修改 `core/scoring.py` 的 `build_report()`**

把 `core/scoring.py` 裡的這段：

```python
def build_report(idx: float, contribs: dict, level: str, trend: list[float],
                  elder_name: str = "長者", date: str | None = None) -> dict:
    """組成給家屬/社工 App 畫面用的結構化報告 (見 analyze.py --json)。"""
    return {
        "elder_name": elder_name,
        "date": date or datetime.date.today().isoformat(),
        "index": idx,
        "level": level,
        "trend": trend,
        "explain": explain(contribs),
        "disclaimer": "本指數為相對於個人基線的偏離程度，非臨床診斷工具。",
    }
```

改成：

```python
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
```

- [ ] **Step 4: 執行測試，確認全數通過**

Run: `python -m pytest core/test_scoring.py -q`
Expected: PASS（原本 3 個 + 新增 2 個 = 5 passed）

- [ ] **Step 5: 跑全專案測試，確認沒有連帶弄壞其他東西**

Run: `python -m pytest -q`
Expected: 全數 PASS（原本 20 passed，這個 Task 完成後應為 22 passed）

- [ ] **Step 6: Commit**

```bash
git add core/scoring.py core/test_scoring.py
git commit -m "feat: add contribs and transcript fields to build_report()"
```

---

### Task 2: `analyze.py --json` 把逐字稿接進報告

**Files:**
- Modify: `recording_analysis/analyze.py:55-92`

**Interfaces:**
- Consumes：Task 1 的 `build_report(..., transcript=...)` 參數。
- Produces：`analyze.py --transcribe --json out.json` 跑出來的 JSON 現在會
  帶有非空的 `"transcript"` 欄位；只帶 `--json`（沒有 `--transcribe`）時
  `"transcript"` 維持 `null`，行為不變。

- [ ] **Step 1: 初始化 `transcript_text` 變數**

把 `recording_analysis/analyze.py` 裡的：

```python
    lex = None
    if args.transcribe:
```

改成：

```python
    lex = None
    transcript_text = None
    if args.transcribe:
```

- [ ] **Step 2: 轉錄完成後記錄逐字稿**

把：

```python
        lex = lexical_features(tr["text"])
        print(f"  消極詞彙: {lex['neg_words'] or '無'}  (count={lex['neg_word_count']})")
```

改成：

```python
        lex = lexical_features(tr["text"])
        print(f"  消極詞彙: {lex['neg_words'] or '無'}  (count={lex['neg_word_count']})")
        transcript_text = tr["text"]
```

- [ ] **Step 3: 把逐字稿傳給 `build_report()`**

把：

```python
        if args.json:
            report = build_report(idx, contribs, level, recent[-7:],
                                   elder_name=args.elder_name)
```

改成：

```python
        if args.json:
            report = build_report(idx, contribs, level, recent[-7:],
                                   elder_name=args.elder_name,
                                   transcript=transcript_text)
```

- [ ] **Step 4: 手動驗證（不需要 Whisper 模型的路徑）**

先用一個小工具產生測試用假 wav 跟基線，確認沒有 `--transcribe` 時行為不變、
`transcript` 為 `null`：

```bash
python -c "
import numpy as np, soundfile as sf
sf.write('_plan_test.wav', 0.1*np.sin(2*np.pi*440*np.linspace(0,3,16000*3)).astype(np.float32), 16000)
"
python recording_analysis/seed_baseline.py --trend flat -o _plan_test_baseline.json
python recording_analysis/analyze.py _plan_test.wav --baseline _plan_test_baseline.json --json _plan_test_report.json --keep-audio
python -c "import json; r=json.load(open('_plan_test_report.json',encoding='utf-8')); print('transcript =', r['transcript']); print('contribs keys =', list(r['contribs'].keys()))"
```

Expected：印出 `transcript = None`，`contribs keys` 印出 6 個特徵鍵名。

- [ ] **Step 5: 若本機已設置 Whisper 模型，額外驗證 `--transcribe` 路徑**

若 `ls models/whisper-small-int8` 存在（README Step 1 的產物），追加驗證：

```bash
python -c "
import numpy as np, soundfile as sf
sf.write('_plan_test.wav', 0.1*np.sin(2*np.pi*440*np.linspace(0,3,16000*3)).astype(np.float32), 16000)
"
python recording_analysis/analyze.py _plan_test.wav --transcribe --baseline _plan_test_baseline.json --json _plan_test_report.json --keep-audio
python -c "import json; r=json.load(open('_plan_test_report.json',encoding='utf-8')); print('transcript =', repr(r['transcript']))"
```

Expected：`transcript` 印出一段非空字串（正弦波音檔轉錄出來的內容不重要，
重點是欄位有值、不是 `None`）。若本機沒有這個模型，跳過這一步即可，不影響
這個 Task 的驗收——Step 4 已經涵蓋了程式邏輯正確性。

- [ ] **Step 6: 清理測試產生的檔案**

```bash
rm -f _plan_test.wav _plan_test_baseline.json _plan_test_report.json
```

（`_plan_test.wav` 通常已被 `analyze.py` 在沒帶 `--keep-audio` 時自動刪除；
上面用了 `--keep-audio` 所以要手動清，`rm -f` 對不存在的檔案不會報錯。）

- [ ] **Step 7: Commit**

```bash
git add recording_analysis/analyze.py
git commit -m "feat: thread transcript into analyze.py --json output"
```

---

### Task 3: 示範素材產生器 + gitignore

**Files:**
- Modify: `app/generate_examples.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes：Task 1 的 `build_report(..., transcript=...)`。
- Produces：執行 `python app/generate_examples.py` 後，除了既有的
  `app/green_example.json`/`app/yellow_example.json`，還會多寫出
  `app/demo_assets/normal_report.json` 與 `app/demo_assets/low_report.json`
  （內容跟 green/yellow 相同，因為情境一＝正常語氣＝綠燈範例，情境二＝低落
  語氣＝黃燈範例，是同一組真實計分邏輯算出來的同一份資料，只是多寫一份到
  給 `clinician_demo.html` 讀的路徑）。另外會在 `app/demo_assets/` 產生三個
  短音檔 `greeting.wav`/`normal.wav`/`low.wav`，供 Task 4 開發/測試網頁時
  播放用（純音調，不是真人錄音，之後要用真的錄音取代——見 Task 5）。

- [ ] **Step 1: `.gitignore` 排除 `app/demo_assets/`**

把 `.gitignore` 裡的：

```
# 使用者自己跑出來的個人基線/即時 App 報告，屬於執行期產物，
# app/green_example.json、app/yellow_example.json 是刻意保留的示範資料例外
baseline*.json
app/live_example.json
```

改成：

```
# 使用者自己跑出來的個人基線/即時 App 報告，屬於執行期產物，
# app/green_example.json、app/yellow_example.json 是刻意保留的示範資料例外
baseline*.json
app/live_example.json

# 心理師示範頁面的本機素材（真人錄音 + 從中算出的報告），
# 跟其他原始音檔一樣不進版控——見 docs/superpowers/specs/2026-08-25-clinician-demo-interface-design.md
app/demo_assets/
```

- [ ] **Step 2: 擴充 `app/generate_examples.py`，讓 `_build()` 帶 transcript**

把 `app/generate_examples.py` 裡的：

```python
def _build(today_feats: dict, history: list[dict], elder_name: str) -> dict:
    base = build_baseline(history)
    idx, contribs = vitality_index(today_feats, base)
    recent = [h["_index"] for h in history] + [idx]
    level = alert_level(recent)
    return build_report(idx, contribs, level, recent[-7:], elder_name=elder_name)
```

改成：

```python
def _build(today_feats: dict, history: list[dict], elder_name: str,
           transcript: str) -> dict:
    base = build_baseline(history)
    idx, contribs = vitality_index(today_feats, base)
    recent = [h["_index"] for h in history] + [idx]
    level = alert_level(recent)
    return build_report(idx, contribs, level, recent[-7:], elder_name=elder_name,
                         transcript=transcript)
```

- [ ] **Step 3: 更新 `main()`，多寫一份到 `app/demo_assets/`**

把 `app/generate_examples.py` 的 `main()`：

```python
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
```

改成：

```python
def main():
    out_dir = os.path.dirname(__file__)
    demo_assets_dir = os.path.join(out_dir, "demo_assets")
    os.makedirs(demo_assets_dir, exist_ok=True)

    green = _build(dict(TYPICAL), _make_history(14, "flat"), elder_name="李奶奶",
                    transcript="早安啊，有喔，昨晚睡得還不錯，謝謝關心。")
    with open(os.path.join(out_dir, "green_example.json"), "w", encoding="utf-8") as f:
        json.dump(green, f, indent=2, ensure_ascii=False)
    with open(os.path.join(demo_assets_dir, "normal_report.json"), "w", encoding="utf-8") as f:
        json.dump(green, f, indent=2, ensure_ascii=False)
    print("green_example.json / demo_assets/normal_report.json:", green["index"], green["level"])

    yellow = _build(LOW_TODAY, _make_history(14, "down"), elder_name="李奶奶",
                     transcript="喔…早，今天喔…還好啦，昨晚…沒有很好睡。")
    with open(os.path.join(out_dir, "yellow_example.json"), "w", encoding="utf-8") as f:
        json.dump(yellow, f, indent=2, ensure_ascii=False)
    with open(os.path.join(demo_assets_dir, "low_report.json"), "w", encoding="utf-8") as f:
        json.dump(yellow, f, indent=2, ensure_ascii=False)
    print("yellow_example.json / demo_assets/low_report.json:", yellow["index"], yellow["level"])
```

- [ ] **Step 4: 執行產生器，確認 JSON 正確寫出**

Run: `python app/generate_examples.py`
Expected：印出兩行，`green_example.json / demo_assets/normal_report.json: <index> green`
與 `yellow_example.json / demo_assets/low_report.json: <index> yellow`。

Run: `python -c "import json; r=json.load(open('app/demo_assets/normal_report.json',encoding='utf-8')); print(list(r.keys())); print(r['transcript'])"`
Expected：欄位清單包含 `contribs` 與 `transcript`，`transcript` 印出「早安啊，
有喔，昨晚睡得還不錯，謝謝關心。」。

- [ ] **Step 5: 產生 Task 4 開發用的占位音檔**

`app/demo_assets/` 裡還需要三個可以播放的 wav（純音調占位，Task 5 會說明
怎麼換成真人錄音）：

```bash
python -c "
import numpy as np, soundfile as sf, os
os.makedirs('app/demo_assets', exist_ok=True)
sr = 16000
for name, freq, dur in [('greeting.wav', 440, 2.5), ('normal.wav', 523, 2.0), ('low.wav', 330, 2.0)]:
    t = np.linspace(0, dur, int(sr*dur), endpoint=False)
    tone = (0.2 * np.sin(2*np.pi*freq*t)).astype(np.float32)
    sf.write(f'app/demo_assets/{name}', tone, sr)
    print('wrote', name)
"
```

Expected：印出三行 `wrote greeting.wav` / `wrote normal.wav` / `wrote low.wav`，
`app/demo_assets/` 底下出現這三個檔案。

- [ ] **Step 6: 確認這些檔案不會被 git 追蹤**

Run: `git status --short app/demo_assets/`
Expected：沒有任何輸出（`.gitignore` 生效，`app/demo_assets/` 底下的檔案都
不會出現在 `git status`）。

- [ ] **Step 7: Commit**

```bash
git add app/generate_examples.py .gitignore
git commit -m "feat: generate clinician-demo fixture reports alongside family-view examples"
```

（`app/demo_assets/` 底下的檔案本身不進這個 commit——已被 `.gitignore` 排除，
`git add` 對它們不會有效果，這是預期行為。）

---

### Task 4: `app/clinician_demo.html`

**Files:**
- Create: `app/clinician_demo.html`

**Interfaces:**
- Consumes：`app/demo_assets/normal_report.json`、`app/demo_assets/low_report.json`
  （Task 3 產生，schema 見 Task 1）；`app/demo_assets/{greeting,normal,low}.wav`
  （Task 3 產生的占位音檔，之後由真人錄音取代）。
- Produces：一個獨立、可直接在瀏覽器開啟的頁面，不被其他任務依賴。

- [ ] **Step 1: 寫入完整頁面**

建立 `app/clinician_demo.html`：

```html
<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PulseCare 心理師示範</title>
<style>
  :root {
    --bg: #0b0d10;
    --panel: #14181d;
    --border: #262b31;
    --text: #e6e9ec;
    --muted: #8b939c;
    --accent: #4dd0a3;
    --green: #2fb672;
    --yellow: #d9a220;
    --canvas-bg: #0d1117;
  }

  * { box-sizing: border-box; }

  body {
    margin: 0;
    min-height: 100vh;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, "PingFang TC", "Microsoft JhengHei", "Noto Sans TC", sans-serif;
    display: flex;
    justify-content: center;
    padding: 40px 20px;
  }

  #reset-link {
    position: fixed;
    top: 16px;
    right: 20px;
    font-size: 12px;
    color: var(--muted);
    text-decoration: none;
  }
  #reset-link:hover { color: var(--text); }

  .stage { width: 100%; max-width: 720px; }

  header { text-align: center; margin-bottom: 32px; }
  header h1 { font-size: 22px; margin: 0 0 8px; }
  header p { color: var(--muted); font-size: 14px; margin: 0; }

  #start-screen { display: flex; justify-content: center; padding: 60px 0; }
  #start-btn {
    display: inline-flex; align-items: center; gap: 10px;
    background: var(--accent); color: #04211a; border: none;
    padding: 16px 32px; font-size: 18px; font-weight: 600;
    border-radius: 999px; cursor: pointer;
  }
  #start-btn:hover { filter: brightness(1.08); }
  #start-btn svg { width: 20px; height: 20px; }

  #playback { text-align: center; margin-bottom: 32px; }
  .status-row {
    display: flex; align-items: center; justify-content: center; gap: 10px;
    margin-bottom: 12px; font-size: 16px; color: var(--text); min-height: 24px;
  }
  .status-row .icon svg { width: 22px; height: 22px; display: block; }
  #waveform {
    width: 100%; max-width: 640px; height: 120px;
    background: var(--canvas-bg); border: 1px solid var(--border); border-radius: 12px;
  }

  .report-card, .comparison-card {
    background: var(--panel); border: 1px solid var(--border); border-radius: 16px;
    padding: 20px 22px; margin-bottom: 20px;
  }
  .report-card h3, .comparison-card h3 {
    margin: 0 0 14px; font-size: 15px; color: var(--muted); font-weight: 600;
    display: flex; align-items: center; gap: 8px;
  }
  .comparison-card h3 .icon svg { width: 18px; height: 18px; display: block; }

  .index-row { display: flex; align-items: baseline; gap: 12px; margin-bottom: 18px; }
  .index-value { font-size: 40px; font-weight: 700; }
  .index-label { font-size: 14px; }
  .level-green .index-value, .level-green .index-label { color: var(--green); }
  .level-yellow .index-value, .level-yellow .index-label { color: var(--yellow); }
  .level-calibrating .index-value, .level-calibrating .index-label { color: var(--muted); }

  .bars { margin-bottom: 18px; }
  .bar-row {
    display: grid; grid-template-columns: 80px 1fr 48px; align-items: center;
    gap: 10px; margin-bottom: 8px; font-size: 13px;
  }
  .bar-label { color: var(--muted); }
  .bar-track {
    position: relative; height: 8px; background: var(--border);
    border-radius: 4px; overflow: hidden;
  }
  .bar-fill { position: absolute; top: 0; bottom: 0; }
  .bar-fill.bar-neg { right: 50%; background: var(--yellow); }
  .bar-fill.bar-pos { left: 50%; background: var(--accent); }
  .bar-value { text-align: right; color: var(--muted); font-variant-numeric: tabular-nums; }

  .transcript {
    font-size: 14px; line-height: 1.7; margin-bottom: 14px;
    padding: 12px 14px; background: rgba(255,255,255,0.03); border-radius: 10px;
  }
  .disclaimer {
    font-size: 11px; color: var(--muted); line-height: 1.6;
    padding-top: 10px; border-top: 1px solid var(--border);
  }

  .compare-row { display: flex; gap: 24px; margin-bottom: 14px; }
  .compare-item {
    flex: 1; text-align: center; padding: 16px;
    background: rgba(255,255,255,0.03); border-radius: 12px;
  }
  .compare-label { display: block; font-size: 12px; color: var(--muted); margin-bottom: 6px; }
  .compare-value { font-size: 28px; font-weight: 700; }
  .compare-summary { font-size: 14px; line-height: 1.7; margin: 0 0 14px; }

  [hidden] { display: none !important; }
</style>
</head>
<body>

<a href="#" id="reset-link">重新開始</a>

<div class="stage">
  <header>
    <h1>PulseCare 語音活力示範</h1>
    <p>本示範供心理師／評審參考判讀，非診斷工具</p>
  </header>

  <div id="start-screen">
    <button id="start-btn">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 5a2 2 0 0 1 3.008-1.728l11.997 6.998a2 2 0 0 1 .003 3.458l-12 7A2 2 0 0 1 5 19z"/></svg>
      Start Demo
    </button>
  </div>

  <div id="playback" hidden>
    <div class="status-row">
      <span class="icon" id="status-icon"></span>
      <span id="status-text">準備開始</span>
    </div>
    <canvas id="waveform" width="640" height="120"></canvas>
  </div>

  <div id="reports" hidden>
    <div class="report-card" id="report-1" hidden></div>
    <div class="report-card" id="report-2" hidden></div>
    <div class="comparison-card" id="comparison" hidden></div>
  </div>
</div>

<script>
const ASSET_DIR = "demo_assets/";

const FEATURE_LABELS = {
  syll_rate: "語速",
  pause_mean_s: "停頓長度",
  f0_sd_st: "語調起伏",
  f0_range_st: "音高範圍",
  loud_range: "音量變化",
  hnr_db: "聲線清晰度",
};
const FEATURE_ORDER = Object.keys(FEATURE_LABELS);

const LEVEL_LABEL = {
  green: "綠燈．穩定",
  yellow: "黃燈．較平常低落",
  calibrating: "系統學習中",
};

const ICONS = {
  phone: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2a9 9 0 0 1 9 9"/><path d="M13 6a5 5 0 0 1 5 5"/><path d="M13.832 16.568a1 1 0 0 0 1.213-.303l.355-.465A2 2 0 0 1 17 15h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2A18 18 0 0 1 2 4a2 2 0 0 1 2-2h3a2 2 0 0 1 2 2v3a2 2 0 0 1-.8 1.6l-.468.351a1 1 0 0 0-.292 1.233 14 14 0 0 0 6.392 6.384"/></svg>',
  mic: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19v3"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><rect x="9" y="2" width="6" height="13" rx="3"/></svg>',
  activity: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/></svg>',
  arrows: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3 4 7l4 4"/><path d="M4 7h16"/><path d="m16 21 4-4-4-4"/><path d="M20 17H4"/></svg>',
  rotateCcw: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>',
};

let audioCtx = null;
let analyser = null;
let animationId = null;

function ensureAudioContext() {
  if (!audioCtx) {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    analyser = audioCtx.createAnalyser();
    analyser.fftSize = 1024;
    analyser.connect(audioCtx.destination);
  }
  if (audioCtx.state === "suspended") {
    audioCtx.resume();
  }
  return audioCtx;
}

function playAudio(path) {
  ensureAudioContext();
  return new Promise((resolve, reject) => {
    const audio = new Audio(path);
    const source = audioCtx.createMediaElementSource(audio);
    source.connect(analyser);
    audio.addEventListener("ended", () => {
      source.disconnect();
      resolve();
    });
    audio.addEventListener("error", () => {
      reject(new Error(`無法播放 ${path}，請確認 app/demo_assets/ 底下有這個檔案`));
    });
    audio.play().catch(reject);
  });
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function drawWaveform() {
  const canvas = document.getElementById("waveform");
  const ctx = canvas.getContext("2d");
  const data = new Uint8Array(analyser.frequencyBinCount);

  function draw() {
    animationId = requestAnimationFrame(draw);
    ctx.fillStyle = "#0d1117";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    analyser.getByteTimeDomainData(data);
    ctx.lineWidth = 2;
    ctx.strokeStyle = "#4dd0a3";
    ctx.beginPath();
    const slice = canvas.width / data.length;
    let x = 0;
    for (let i = 0; i < data.length; i++) {
      const v = data[i] / 128.0;
      const y = (v * canvas.height) / 2;
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      x += slice;
    }
    ctx.stroke();
  }
  draw();
}

function stopWaveform() {
  if (animationId) cancelAnimationFrame(animationId);
}

function setStatus(iconName, text) {
  document.getElementById("status-icon").innerHTML = ICONS[iconName] || "";
  document.getElementById("status-text").textContent = text;
}

async function stage(iconName, text, audioPath) {
  setStatus(iconName, text);
  if (audioPath) {
    await playAudio(audioPath);
  }
}

async function analyzingPause() {
  setStatus("activity", "分析中…");
  await wait(1500);
}

async function transition(text) {
  setStatus("rotateCcw", text);
  await wait(1800);
}

async function fetchReport(filename) {
  const res = await fetch(ASSET_DIR + filename);
  if (!res.ok) {
    throw new Error(
      `載入 ${filename} 失敗（HTTP ${res.status}）。請先依 docs/demo-steps.md 產生 app/demo_assets/ 底下的素材。`
    );
  }
  return res.json();
}

function renderReport(targetId, label, report) {
  const el = document.getElementById(targetId);
  el.hidden = false;

  const bars = FEATURE_ORDER.map((key) => {
    const z = (report.contribs && report.contribs[key]) || 0;
    const pct = Math.min(Math.abs(z) / 3, 1) * 50;
    const side = z < 0 ? "neg" : "pos";
    return `
      <div class="bar-row">
        <span class="bar-label">${FEATURE_LABELS[key]}</span>
        <div class="bar-track">
          <div class="bar-fill bar-${side}" style="width:${pct}%"></div>
        </div>
        <span class="bar-value">${z.toFixed(2)}</span>
      </div>`;
  }).join("");

  el.innerHTML = `
    <h3>${label}</h3>
    <div class="index-row level-${report.level}">
      <span class="index-value">${report.index}</span>
      <span class="index-label">${LEVEL_LABEL[report.level] || report.level}</span>
    </div>
    <div class="bars">${bars}</div>
    <div class="transcript"><strong>逐字稿：</strong>${report.transcript || "（無逐字稿）"}</div>
    <div class="disclaimer">${report.disclaimer}</div>
  `;
}

function renderComparison(report1, report2) {
  const el = document.getElementById("comparison");
  el.hidden = false;

  const c1 = report1.contribs || {};
  const c2 = report2.contribs || {};
  const deltas = FEATURE_ORDER
    .map((key) => ({ key, delta: (c2[key] || 0) - (c1[key] || 0) }))
    .sort((a, b) => a.delta - b.delta)
    .slice(0, 2)
    .filter((d) => d.delta < -0.5)
    .map((d) => FEATURE_LABELS[d.key]);

  const diff = (report1.index - report2.index).toFixed(1);
  const summary = deltas.length
    ? `情境二指數較情境一低 ${diff} 分，${deltas.join("、")}是主要偏離項目。`
    : `情境二指數較情境一低 ${diff} 分。`;

  el.innerHTML = `
    <h3><span class="icon">${ICONS.arrows}</span>對比摘要</h3>
    <div class="compare-row">
      <div class="compare-item"><span class="compare-label">情境一</span><span class="compare-value">${report1.index}</span></div>
      <div class="compare-item"><span class="compare-label">情境二</span><span class="compare-value">${report2.index}</span></div>
    </div>
    <p class="compare-summary">${summary}</p>
    <div class="disclaimer">${report1.disclaimer}</div>
  `;
}

async function runDemo() {
  document.getElementById("start-screen").hidden = true;
  document.getElementById("playback").hidden = false;
  document.getElementById("reports").hidden = false;
  drawWaveform();

  try {
    const [report1, report2] = await Promise.all([
      fetchReport("normal_report.json"),
      fetchReport("low_report.json"),
    ]);

    await stage("phone", "系統問候中", ASSET_DIR + "greeting.wav");
    await stage("mic", "李奶奶回覆中（情境一：正常語氣）", ASSET_DIR + "normal.wav");
    await analyzingPause();
    renderReport("report-1", "情境一：正常語氣", report1);
    await wait(2500);

    await transition("換一天，李奶奶心情比較低落…");
    await stage("phone", "系統問候中", ASSET_DIR + "greeting.wav");
    await stage("mic", "李奶奶回覆中（情境二：低落語氣）", ASSET_DIR + "low.wav");
    await analyzingPause();
    renderReport("report-2", "情境二：低落語氣", report2);
    await wait(1500);

    renderComparison(report1, report2);
    setStatus("activity", "示範結束");
  } catch (err) {
    setStatus("activity", err.message);
  } finally {
    stopWaveform();
  }
}

document.getElementById("start-btn").addEventListener("click", () => {
  ensureAudioContext();
  runDemo();
});

document.getElementById("reset-link").addEventListener("click", (e) => {
  e.preventDefault();
  location.reload();
});
</script>
</body>
</html>
```

- [ ] **Step 2: 起本地伺服器**

Run: `python -m http.server` （在專案根目錄）

- [ ] **Step 3: 手動走一遍完整流程**

瀏覽器開 `http://localhost:8000/app/clinician_demo.html`，檢查：

- 起始畫面只有標題、副標、「Start Demo」按鈕，沒有 emoji。
- 點 Start Demo 後：依序看到「系統問候中」「李奶奶回覆中（情境一：正常語氣）」
  「分析中…」，波形隨占位音檔播放即時擺動（不是預錄動畫——把喇叭靜音應該
  會看到波形變成一直線）。
- 情境一報告卡淡入，指數、燈號顏色、6 項特徵長條圖（有正有負）、逐字稿、
  免責聲明都有內容。
- 接著看到過場文字「換一天，李奶奶心情比較低落…」，再重播一次問候音檔，
  接情境二流程，情境二報告卡淡入（黃燈配色）。
- 最後對比摘要區塊出現，兩個指數並排，摘要句子提到的特徵名稱跟兩張報告卡
  長條圖裡數值差最多的項目吻合。
- 右上角「重新開始」連結可以把整個流程重置回起始畫面。
- 直接用 `file://` 開這個檔案（不透過 `http://`）應該會在 fetch 失敗時把
  錯誤訊息顯示在狀態列，不會整頁空白或主控台丟出使用者看不到的錯誤。

若有任何一項對不上，回頭修正 `app/clinician_demo.html` 再重新整理頁面驗證，
確認全部通過才進下一步。

- [ ] **Step 4: Commit**

```bash
git add app/clinician_demo.html
git commit -m "feat: add auto-playing clinician demo interface"
```

---

### Task 5: 錄影素材準備文件

**Files:**
- Modify: `docs/demo-steps.md`

**Interfaces:**
- 無新程式介面，純文件。

- [ ] **Step 1: 在 Scene 5 之後、Scene 6 之前插入新的一節**

在 `docs/demo-steps.md` 的 `### Scene 5 — 家屬／社工 App 畫面` 那一節結尾
（`> alert_level() 需要滿 7 天觀察窗才會給綠／黃，...` 那一行）之後、
`### Scene 6 — Phase 2：真的對著麥克風跑一輪完整對話` 之前，插入：

```markdown
### Scene 5b — 心理師示範頁面（`app/clinician_demo.html`）

跟 Scene 5 用同一組 `normal.wav`/`low.wav`，但輸出改成心理師示範頁面要讀的
格式（多了完整六項特徵貢獻度與逐字稿）：

```bash
cp raw/normal.wav . && python recording_analysis/analyze.py normal.wav --transcribe --baseline baseline_flat.json --json app/demo_assets/normal_report.json --elder-name 李奶奶 --keep-audio
cp raw/low.wav .    && python recording_analysis/analyze.py low.wav    --transcribe --baseline baseline_down.json --json app/demo_assets/low_report.json  --elder-name 李奶奶 --keep-audio
```

還需要三個播放用的音檔（`python app/generate_examples.py` 產生的是純音調
占位檔，僅供開發測試網頁用，正式錄影前務必替換成下面這些真的音檔）：

```bash
cp raw/normal.wav app/demo_assets/normal.wav
cp raw/low.wav    app/demo_assets/low.wav
cp <你自己錄的問候語音檔> app/demo_assets/greeting.wav
```

問候語不限定用 TTS 合成——用你自己念「李奶奶早！今天陽光很好，昨晚睡得好
嗎？」錄的音檔也完全可以，`app/clinician_demo.html` 只是把它當一個可以播放
的 wav 檔案，不在意來源。

`app/demo_assets/` 整個資料夾都在 `.gitignore` 裡（跟其他原始音檔一樣不進
版控），每次在新機器上要錄影前都要重新跑一次上面的指令。

瀏覽（一定要走 `http://`，理由同 Scene 5）：

```bash
python -m http.server
```

http://localhost:8000/app/clinician_demo.html ，點 Start Demo 看完整流程。
```

- [ ] **Step 2: 檢查文件格式**

打開 `docs/demo-steps.md` 確認新插入的區塊縮排、程式碼區塊標記（```` ``` ````）
跟前後文一致，Markdown 預覽（或直接看 raw text）標題階層是 `###`，跟
Scene 5／Scene 6 同一層級。

- [ ] **Step 3: Commit**

```bash
git add docs/demo-steps.md
git commit -m "docs: document clinician demo asset prep in demo-steps.md"
```

---

## 全部完成後的最終檢查

- [ ] Run: `python -m pytest -q` — Expected: 全數 PASS（22 passed）。
- [ ] Run: `python app/generate_examples.py` — Expected: 正常執行，
      `app/green_example.json`/`app/yellow_example.json`/
      `app/demo_assets/normal_report.json`/`app/demo_assets/low_report.json`
      都更新。
- [ ] Run: `git status --short` — Expected: 只有五個 Task 各自的 commit，
      沒有 `app/demo_assets/` 底下的檔案被追蹤，`app/family_view.html` 沒有
      被改動。
- [ ] 瀏覽器手動走一遍 `app/clinician_demo.html`（同 Task 4 Step 3 的檢查
      清單），以及 `app/family_view.html?data=green_example.json` 確認舊頁面
      沒有因為 `build_report()` 的欄位新增而壞掉。
