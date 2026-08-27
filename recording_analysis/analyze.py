"""
PulseCare Phase 1 CLI

用法:
    python recording_analysis/analyze.py sample.wav                    # 只跑聲學特徵 (不需模型)
    python recording_analysis/analyze.py sample.wav --transcribe       # 加上本地 Whisper 轉錄
    python recording_analysis/analyze.py sample.wav --baseline base.json
    python recording_analysis/analyze.py sample.wav --baseline base.json --json out.json --elder-name 李奶奶

Phase 1 的驗收標準：這支程式能印出 6 個特徵 + 一個活力指數。
--json 額外輸出一份給家屬/社工 App 畫面用的結構化報告 (見 app/family_view.html)。
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))

from features import extract_features, lexical_features, FEATURE_KEYS
from scoring import build_baseline, vitality_index, explain, alert_level, build_report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wav")
    ap.add_argument("--transcribe", action="store_true", help="啟用本地 Whisper")
    ap.add_argument("--model-dir", default="models/whisper-small-int8")
    ap.add_argument("--device", default="CPU", help="CPU / GPU / NPU")
    ap.add_argument("--baseline", help="歷史特徵 json (list of dict)")
    ap.add_argument("--keep-audio", action="store_true",
                    help="Demo 用：保留音檔。正式流程一律銷毀")
    ap.add_argument("--json", metavar="PATH",
                    help="額外輸出一份結構化報告 (給家屬/社工 App 畫面用)，"
                         "需搭配 --baseline")
    ap.add_argument("--elder-name", default="長者",
                    help="--json 報告裡顯示的稱呼")
    args = ap.parse_args()

    if args.json and not args.baseline:
        ap.error("--json 需要搭配 --baseline 才能算出指數/燈號")

    t0 = time.time()
    out = extract_features(args.wav)
    feats, meta = out["features"], out["meta"]
    t_feat = time.time() - t0

    print("\n=== 聲學特徵 (本地抽取) " + "=" * 30)
    print(f"音長 {meta['duration_s']}s   抽取耗時 {t_feat*1000:.0f} ms")
    for k in FEATURE_KEYS:
        print(f"  {k:<14} {feats[k]:>10.4f}")

    lex = None
    transcript_text = None
    if args.transcribe:
        from transcribe import transcribe
        t1 = time.time()
        tr = transcribe(args.wav, args.model_dir, args.device)
        t_asr = time.time() - t1
        print(f"\n=== 本地轉錄 (OpenVINO, {args.device}) " + "=" * 20)
        print(f"  耗時 {t_asr:.2f}s")
        print(f"  逐字稿: {tr['text']}")
        lex = lexical_features(tr["text"])
        print(f"  消極詞彙: {lex['neg_words'] or '無'}  (count={lex['neg_word_count']})")
        transcript_text = tr["text"]

    # 隱私邊界：特徵抽取完成後，原始音檔即可銷毀
    if not args.keep_audio:
        os.remove(args.wav)
        print("\n  [privacy] 原始音檔已銷毀，僅保留上列數值特徵")

    if args.baseline:
        with open(args.baseline, encoding="utf-8") as f:
            history = json.load(f)
        base = build_baseline(history)
        idx, contribs = vitality_index(feats, base)
        recent = [h.get("_index", 50.0) for h in history] + [idx]
        level = alert_level(recent)

        print("\n=== 語音活力指數 " + "=" * 34)
        print(f"  指數 = {idx}   (50 = 本人常態)   燈號 = {level}")
        print(f"  特徵貢獻: {contribs}")
        for line in explain(contribs):
            print(f"    - {line}")
        print("\n  ※ 本指數為相對於個人基線的偏離程度，非臨床診斷工具。")

        if args.json:
            report = build_report(idx, contribs, level, recent[-7:],
                                   elder_name=args.elder_name,
                                   transcript=transcript_text)
            with open(args.json, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"\n  [app] 家屬/社工 App 報告已寫出 → {args.json}")

    print()


if __name__ == "__main__":
    main()
