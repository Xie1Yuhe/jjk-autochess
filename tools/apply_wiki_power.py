# -*- coding: utf-8 -*-
r"""
apply_wiki_power.py —— 把技能/必杀倍率改成「忠实于 wiki」的映射

## 现状问题（见 FIDELITY_ROUND2.md）

    power = clamp(max_pct/120, 1.0, 3.3)
    upow  = clamp(max_pct/150, 1.4, 4.0)

  · max_pct 取全文最大百分比 → 24/84 技能、30/106 必杀抓错数字
  · clamp 把 wiki 的 13.5× / 21× 跨度压成 3.3× / 4.0×，低倍率卡被抬到下限

## 本脚本的做法

  1. 用严格规则抽取**伤害倍率**（优先「造成…X%的体术/术式伤害」这类句式）
  2. 映射：power = (pct / K) ** COMPRESS
     · COMPRESS = 1.0 → 完全线性（最忠实，但 5 费大招会秒杀）
     · COMPRESS = 0.75 → 幂压缩（保序、压缩差距）← 默认
  3. K 自动求解，使**映射后的中位数 = 改造前的中位数**，
     这样整体伤害量级不变，只有「相对关系」变得更忠实
  4. 只改伤害类技能（strike/slam/barrage/beam/dot/drain），
     治疗/护盾/增益类跳过，避免把 wiki 的伤害数字套到辅助技上

用法：
    python tools\apply_wiki_power.py                 # 预览
    python tools\apply_wiki_power.py --apply         # 写回
    python tools\apply_wiki_power.py --linear        # 改完线性模式再预览
"""
import json
import os
import re
import statistics
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNITS = os.path.join(ROOT, "data", "units.json")
REPORT = os.path.join(ROOT, "WIKI_POWER_MAP.md")

COMPRESS = 0.75
DAMAGE_TYPES = {"strike", "slam", "barrage", "beam", "dot", "drain"}

PAT_A = [
    r"造成[^。%]{0,24}?([0-9]+(?:\.[0-9]+)?)%[^。%]{0,6}(?:的)?(?:体术|术式|复合|伤害)",
    r"(?:近战|远程|近身)攻击的[^。%]{0,12}?([0-9]+(?:\.[0-9]+)?)%",
    r"([0-9]+(?:\.[0-9]+)?)%\s*[的]?(?:体术|术式|复合)伤害",
]
PAT_B = [r"造成[^。%]{0,20}?([0-9]+(?:\.[0-9]+)?)%[^。]{0,10}伤害"]
PAT_C = [r"([0-9]+(?:\.[0-9]+)?)%[^。]{0,8}伤害"]


def extract(desc, floor):
    if not desc:
        return None
    for group in (PAT_A, PAT_B, PAT_C):
        for p in group:
            m = re.search(p, desc)
            if m:
                try:
                    v = float(m.group(1))
                except Exception:
                    continue
                if v >= floor:
                    return v
    return None


def solve_k(pcts, target_median):
    """求 K 使 (pct/K)**C 的中位数 == target_median"""
    base = statistics.median(pcts)
    # (base/K)**C = target  →  K = base / target**(1/C)
    return base / (target_median ** (1.0 / COMPRESS))


def main():
    apply = "--apply" in sys.argv
    units = json.load(open(UNITS, encoding="utf-8"))

    sk_rows, ul_rows = [], []
    for u in units:
        sk = u.get("skill") or {}
        ul = u.get("ult") or {}
        if sk.get("type") in DAMAGE_TYPES and sk.get("power"):
            pct = extract(sk.get("wikiDesc") or "", 60)
            if pct:
                sk_rows.append((u, sk, pct, sk["power"]))
        if ul.get("power"):
            pct = extract((u.get("ultimate") or {}).get("wikiDesc") or "", 100)
            if pct:
                ul_rows.append((u, ul, pct, ul["power"]))

    if not sk_rows and not ul_rows:
        print("[powermap] 没抽到任何倍率，退出")
        return

    K_S = solve_k([r[2] for r in sk_rows], statistics.median([r[3] for r in sk_rows])) if sk_rows else 1
    K_U = solve_k([r[2] for r in ul_rows], statistics.median([r[3] for r in ul_rows])) if ul_rows else 1

    def conv(pct, K):
        return round(max(0.25, min(9.0, (pct / K) ** COMPRESS)), 2)

    L = []
    A = L.append
    A("# WIKI_POWER_MAP.md —— 倍率重映射对照表")
    A("")
    A("> `python tools\\apply_wiki_power.py` 生成。")
    A("> 映射公式：power = (wiki% / K) 的 " + str(COMPRESS) + " 次方；K 使映射后中位数与原值持平。")
    A("")
    A("| 类别 | 张数 | K | 映射前范围 | 映射后范围 |")
    A("|---|---|---|---|---|")
    for label, rows, K in (("小技能", sk_rows, K_S), ("必杀", ul_rows, K_U)):
        if not rows:
            continue
        old = [r[3] for r in rows]
        new = [conv(r[2], K) for r in rows]
        A("| %s | %d | %.0f | %.2f~%.2f | %.2f~%.2f |" % (
            label, len(rows), K, min(old), max(old), min(new), max(new)))
    A("")

    for label, rows, K in (("小技能", sk_rows, K_S), ("必杀", ul_rows, K_U)):
        A("## %s 对照（按 wiki%% 降序）" % label)
        A("")
        A("| 棋子 | wiki% | 旧 power | 新 power | 变化 |")
        A("|---|---|---|---|---|")
        for u, obj, pct, old in sorted(rows, key=lambda r: -r[2]):
            new = conv(pct, K)
            delta = new - old
            A("| %s | %.0f%% | %.2f | **%.2f** | %+.2f |" % (u["name"], pct, old, new, delta))
            if apply:
                obj["power"] = new
        A("")

    open(REPORT, "w", encoding="utf-8").write("\n".join(L))

    print("[powermap] COMPRESS=%.2f  K_skill=%.0f  K_ult=%.0f" % (COMPRESS, K_S, K_U))
    for label, rows, K in (("小技能", sk_rows, K_S), ("必杀", ul_rows, K_U)):
        if not rows:
            continue
        old = [r[3] for r in rows]
        new = [conv(r[2], K) for r in rows]
        print("   %s n=%d  旧 %.2f~%.2f  新 %.2f~%.2f" % (
            label, len(rows), min(old), max(old), min(new), max(new)))

    if apply:
        json.dump(units, open(UNITS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("[powermap] 已写回 units.json，并输出 %s" % REPORT)
    else:
        print("[powermap] 预览模式（加 --apply 应用），报告已写到 %s" % REPORT)


if __name__ == "__main__":
    main()
