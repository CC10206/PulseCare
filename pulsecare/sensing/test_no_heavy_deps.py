"""把關測試：`pulsecare/sensing/` 不得 import 邊緣裝置裝不起來的東西。

這是唯一能防止有人哪天在 sensing 層加一行 `import librosa`、就把 KNEO Pi
部署靜靜弄壞的機制——那種壞法不會有任何測試變紅，只會在板子上 pip install
失敗，而那通常是展示前一天才發現。

用靜態 AST 檢查而不是在子行程 import 後看 `sys.modules`，理由有二：
1. 不需要真的裝好 opensmile / parselmouth 就能跑，任何環境都能驗
2. `sensing/features.py` 在 import 時就會建立 `opensmile.Smile(...)` 物件，
   而那個動作在非 ASCII 路徑的 venv 下會丟 UnicodeEncodeError（見 CLAUDE.md），
   讓執行期檢查在某些機器上根本跑不起來

代價是抓不到間接洩漏（import 了某個自己會拉 librosa 的東西）。對「防止有人
手動加重量級 import」這個目的來說，靜態檢查夠用而且更穩。
"""
import ast
import pathlib

import pytest

#: 這些 top-level 模組不得出現在 sensing 層的任何 import 裡。
#: openvino/librosa/parselmouth/transformers 是重量級或沒有 aarch64 wheel；
#: fastapi/opencc/jieba 屬於上層，出現在這裡代表分層被打破。
FORBIDDEN = {
    "openvino",
    "openvino_genai",
    "librosa",
    "parselmouth",
    "transformers",
    "fastapi",
    "uvicorn",
    "opencc",
    "jieba",
}

SENSING_DIR = pathlib.Path(__file__).resolve().parent


def _imported_roots(path: pathlib.Path) -> set[str]:
    """回傳這支檔案 import 到的所有 top-level 模組名（含函式內的延遲 import）。"""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            # level > 0 是相對 import（同一個 package 內），不是外部相依
            if node.level == 0 and node.module:
                roots.add(node.module.split(".")[0])
    return roots


def _sensing_modules() -> list[pathlib.Path]:
    return sorted(p for p in SENSING_DIR.glob("*.py") if not p.name.startswith("test_"))


def test_sensing_modules_exist():
    """先確認掃描範圍不是空的——否則下面那條測試會空轉通過。"""
    assert _sensing_modules(), "找不到任何 sensing 模組，掃描路徑可能錯了"


@pytest.mark.xfail(
    reason="features.py 仍 import parselmouth（無 aarch64 wheel）與 librosa。"
           "待 f0_sd_st 改由 eGeMAPS 推導、librosa.load 換成 soundfile.info 後，"
           "這條會轉為 XPASS，屆時把 xfail 標記拿掉（spec §5.3 / §5.4）",
)
def test_sensing_layer_has_no_heavy_deps():
    offenders = {}
    for path in _sensing_modules():
        bad = _imported_roots(path) & FORBIDDEN
        if bad:
            offenders[path.name] = sorted(bad)
    assert not offenders, f"sensing 層不得 import 這些模組：{offenders}"
