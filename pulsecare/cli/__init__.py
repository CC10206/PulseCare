"""人用的命令列入口。

    analyze.py        Phase 1：吃一支現成 wav,抽特徵 → 計分 → 報告
    seed_baseline.py  產生合成基線（Demo 用）,支援 --trend flat/down/up
    live_session.py   Phase 2：真的對著麥克風跑一輪完整對話

這一層只負責參數解析、流程串接與輸出,商業邏輯一律放在下層模組裡。
"""
