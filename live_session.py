"""
PulseCare — 即時對話迴路 (Phase 2)

對應 structure.png：「排程器 → TTS 問候 → 麥克風錄音(VAD) → 現有 pipeline
(聲學特徵 + Whisper 轉錄) → 小型 LLM 回應 → TTS」。

這裡的「排程器」不是真的 OS 層級排程——執行這支程式本身就代表
「排程觸發的那一刻」；真正的定時觸發交給部署環境的工作排程器負責，
不在這支程式的範圍內。

用法:
    python live_session.py --baseline baseline.json --json app/live_example.json
"""
import argparse
import json
import os
import time

from features import extract_features, lexical_features, FEATURE_KEYS
from scoring import build_baseline, vitality_index, explain, alert_level, build_report
import tts
import llm_reply
from listen import record_with_vad, save_wav

GREETING = "李奶奶早！今天陽光很好，昨晚睡得好嗎？"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", help="歷史特徵 json (list of dict)，給了才計分")
    ap.add_argument("--json", metavar="PATH",
                    help="額外輸出結構化報告 (給家屬/社工 App 畫面用)，需搭配 --baseline")
    ap.add_argument("--elder-name", default="長者")
    ap.add_argument("--keep-audio", action="store_true",
                    help="Demo/除錯用：保留錄到的音檔與合成語音。正式流程一律銷毀錄音")
    ap.add_argument("--max-record-s", type=float, default=20.0)
    ap.add_argument("--device", default="CPU", help="OpenVINO 推論裝置 CPU/GPU/NPU")
    args = ap.parse_args()

    if args.json and not args.baseline:
        ap.error("--json 需要搭配 --baseline 才能算出指數/燈號")

    print("⏰ [排程觸發] 開始今日問候\n")
    tts.speak(GREETING, out_path="_greeting.wav" if args.keep_audio else None,
              device=args.device, play=True)

    audio, sr = record_with_vad(max_total_s=args.max_record_s)
    wav_path = "_reply.wav"
    save_wav(audio, wav_path, sr)

    t0 = time.time()
    out = extract_features(wav_path)
    feats, meta = out["features"], out["meta"]
    t_feat = time.time() - t0

    print(f"\n=== 聲學特徵 (本地抽取) " + "=" * 30)
    print(f"音長 {meta['duration_s']}s   抽取耗時 {t_feat*1000:.0f} ms")
    for k in FEATURE_KEYS:
        print(f"  {k:<14} {feats[k]:>10.4f}")

    from transcribe import transcribe
    t1 = time.time()
    tr = transcribe(wav_path, device=args.device)
    t_asr = time.time() - t1
    print(f"\n=== 本地轉錄 (OpenVINO, {args.device}) " + "=" * 20)
    print(f"  耗時 {t_asr:.2f}s")
    print(f"  逐字稿: {tr['text']}")
    lex = lexical_features(tr["text"])
    print(f"  消極詞彙: {lex['neg_words'] or '無'}  (count={lex['neg_word_count']})")

    # 隱私邊界：特徵抽取 + 轉錄完成後，原始錄音即可銷毀
    if not args.keep_audio:
        os.remove(wav_path)
        print("\n  [privacy] 原始錄音已銷毀，僅保留上列數值特徵")

    if args.baseline:
        with open(args.baseline, encoding="utf-8") as f:
            history = json.load(f)
        base = build_baseline(history)
        idx, contribs = vitality_index(feats, base)
        recent = [h.get("_index", 50.0) for h in history] + [idx]
        level = alert_level(recent)

        print("\n=== 語音活力指數 " + "=" * 34)
        print(f"  指數 = {idx}   (50 = 本人常態)   燈號 = {level}")
        for line in explain(contribs):
            print(f"    - {line}")

        if args.json:
            report = build_report(idx, contribs, level, recent[-7:], elder_name=args.elder_name)
            with open(args.json, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"\n  [app] 家屬/社工 App 報告已寫出 → {args.json}")

    reply_text = llm_reply.generate_reply(tr["text"], device=args.device)
    print(f"\n🤖 [AI 回應] {reply_text}")
    tts.speak(reply_text, out_path="_reply_tts.wav" if args.keep_audio else None,
              device=args.device, play=True)

    print("\n✅ 對話結束\n")


if __name__ == "__main__":
    main()
