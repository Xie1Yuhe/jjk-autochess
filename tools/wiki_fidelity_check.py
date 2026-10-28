# -*- coding: utf-8 -*-
r"""
wiki_fidelity_check.py —— 检查「技能倍率是否忠实于 wiki 百分比」

## 背景

build_units.py 里是这样从 wiki 提取倍率的：

    power = max_pct(desc)                    # 整段文字里最大的百分比
    power = round(clamp(power / 120, 1.0, 3.3), 2)

两个硬伤：
  1. max_pct 抓的是**全文最大**的百分比，很可能不是伤害倍率
     （比如「受到伤害提升 30%」「最大提升原本效果量的 600%」）
  2. clamp 到 3.3，2100% 的大招和 400% 的中招会被压成同一个值

本脚本做的是「体检」：把 wiki 原文里的**伤害倍率**按更严格的规则重新抽出来，
和当前 power×120 对比，看看偏差分布。

严格规则（优先级从高到低）：
  a) 「对…造成…X%的(体术|术式|复合)伤害」/「近战攻击的X%」/「远程攻击的X%」
  b) 「造成…X%…伤害」
  c) 「X%的伤害」
取**第一条命中**（原作技能通常是主伤害在前，附加效果在后）。

用法：
    python tools\wiki_fidelity_check.py
输出：
    WIKI_FIDELITY.md
"""
import json
import os
import re
import sys
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNITS = os.path.join(ROOT, "data", "units.json")
OUT = os.path.join(ROOT, "WIKI_FIDELITY.md")

K_SKILL = 120.0   # build_units.py：power = max_pct / 120
K_ULT = 150.0     # build_units.py：upow = max_pct / 150

# 优先级 a：明确的伤害倍率
PAT_A = [
    r"造成[^。%]{0,24}?([0-9]+(?:\.[0-9]+)?)%[^。%]{0,6}(?:的)?(?:体术|术式|复合|伤害)",
    r"(?:近战|远程|近身)攻击的[^。%]{0,12}?([0-9]+(?:\.[0-9]+)?)%",
    r"([0-9]+(?:\.[0-9]+)?)%\s*[的]?(?:体术|术式|复合)伤害",
]
PAT_B = [
    r"造成[^。%]{0,20}?([0-9]+(?:\.[0-9]+)?)%[^。]{0,10}伤害",
]
PAT_C = [
    r"([0-9]+(?:\.[0-9]+)?)%[^。]{0,8}伤害",
]


def first_hit(desc, pats):
    for p in pats:
        m = re.search(p, desc)
        if m:
            try:
                return float(m.group(1))
            except Exception:
                continue
    return None


def extract(desc):
    """返回 (百分比, 用的是哪一档规则)"""
    if not desc:
        return None, "-"
    v = first_hit(desc, PAT_A)
    if v is not None:
        return v, "A"
    v = first_hit(desc, PAT_B)
    if v is not None:
        return v, "B"
    v = first_hit(desc, PAT_C)
    if v is not None:
        return v, "C"
    return None, "-"


def main():
    units = json.load(open(UNITS, encoding="utf-8"))
    rows = []
    for u in units:
        sk = u.get("skill") or {}
        ul = u.get("ult") or {}
        sd = sk.get("wikiDesc") or ""
        ud = (u.get("ultimate") or {}).get("wikiDesc") or ""
        sv, sr = extract(sd)
        uv, ur = extract(ud)
        rows.append({
            "name": u["name"], "cost": u["cost"],
            "sk_pow": sk.get("power"), "sk_pct": sv, "sk_rule": sr,
            "ul_pow": ul.get("power"), "ul_pct": uv, "ul_rule": ur,
        })

    L = []
    A = L.append
    A("# WIKI_FIDELITY.md —— 技能倍率忠实度体检")
    A("")
    A("> 由 `python tools\\wiki_fidelity_check.py` 生成。")
    A("> 换算约定：`power = wiki百分比 / 120`（build_units.py 的口径）。")
    A("")

    # ---- 覆盖率
    ok_s = [r for r in rows if r["sk_pct"]]
    ok_u = [r for r in rows if r["ul_pct"]]
    A("## 1. 提取覆盖率")
    A("")
    A("| | 能抽到伤害倍率 | 抽不到 |")
    A("|---|---|---|")
    A("| 小技能 | %d / %d | %d |" % (len(ok_s), len(rows), len(rows) - len(ok_s)))
    A("| 必杀 | %d / %d | %d |" % (len(ok_u), len(rows), len(rows) - len(ok_u)))
    A("")

    # ---- 偏差
    def dev(r, key_pct, key_pow):
        if not r[key_pct] or not r[key_pow]:
            return None
        k = K_SKILL if key_pow == "sk_pow" else K_ULT
        want = max(1.0, r[key_pct] / k)
        return r[key_pow] / want

    for label, kp, kw in (("小技能", "sk_pct", "sk_pow"), ("必杀", "ul_pct", "ul_pow")):
        ds = [(dev(r, kp, kw), r) for r in rows]
        ds = [(d, r) for d, r in ds if d is not None]
        if not ds:
            continue
        ds.sort(key=lambda x: x[0])
        A("## 2.%s 倍率偏差" % ("小技能" if kp == "sk_pct" else "必杀"))
        A("")
        A("偏差 = 我们的 power ÷ (wiki% / 120)。1.00 表示完全忠实。")
        A("")
        A("| 区间 | 张数 |")
        A("|---|---|")
        buckets = defaultdict(int)
        for d, _ in ds:
            if d < 0.85:
                buckets["<0.85（偏低）"] += 1
            elif d <= 1.15:
                buckets["0.85~1.15（忠实）"] += 1
            else:
                buckets[">1.15（偏高）"] += 1
        for k in ("<0.85（偏低）", "0.85~1.15（忠实）", ">1.15（偏高）"):
            A("| %s | %d |" % (k, buckets.get(k, 0)))
        A("")
        A("偏差最大（偏低）5 张：")
        A("")
        A("| 棋子 | 费 | wiki% | 应为 power | 实际 power | 偏差 |")
        A("|---|---|---|---|---|---|")
        for d, r in ds[:5]:
            pct = r[kp]
            A("| %s | %d | %.0f%% | %.2f | %.2f | %.2f× |" % (
                r["name"], r["cost"], pct,
                max(1.0, pct / (K_SKILL if kw == "sk_pow" else K_ULT)), r[kw] or 0, d))
        A("")
        A("偏差最大（偏高）5 张：")
        A("")
        A("| 棋子 | 费 | wiki% | 应为 power | 实际 power | 偏差 |")
        A("|---|---|---|---|---|---|")
        for d, r in ds[-5:][::-1]:
            pct = r[kp]
            A("| %s | %d | %.0f%% | %.2f | %.2f | %.2f× |" % (
                r["name"], r["cost"], pct,
                max(1.0, pct / (K_SKILL if kw == "sk_pow" else K_ULT)), r[kw] or 0, d))
        A("")

    # ---- max_pct 是否抓到了非伤害数值
    PCT_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?)%")
    wrong_s = wrong_u = 0
    wrong_examples = []
    for u in units:
        sk = u.get("skill") or {}
        ul = u.get("ult") or {}
        for label, desc, key in (
            ("技", sk.get("wikiDesc") or "", "sk"),
            ("杀", (u.get("ultimate") or {}).get("wikiDesc") or "", "ul"),
        ):
            if not desc:
                continue
            nums = [float(x) for x in PCT_RE.findall(desc)]
            if not nums:
                continue
            mx = max(nums)
            dv, _ = extract(desc)
            if dv is None:
                continue
            if mx > dv * 1.25:
                if key == "sk":
                    wrong_s += 1
                else:
                    wrong_u += 1
                if len(wrong_examples) < 10:
                    wrong_examples.append((u["name"], label, dv, mx))

    A("## 2.9 max_pct 抓错数字的比例（真正的忠实度问题）")
    A("")
    A("`max_pct` 取的是**整段文字里最大的百分比**。"
      "当它明显大于真正的伤害倍率时，说明这一档 power 是被无关数值（暴击率/增伤/上限）带偏的。")
    A("")
    A("| 类别 | 被带偏的张数 |")
    A("|---|---|")
    A("| 小技能 | %d |" % wrong_s)
    A("| 必杀 | %d |" % wrong_u)
    A("")
    if wrong_examples:
        A("| 例子 | | 真实伤害% | max_pct 抓到 |")
        A("|---|---|---|---|")
        for n, lb, dv, mx in wrong_examples:
            A("| %s | %s | %.0f%% | **%.0f%%** |" % (n, lb, dv, mx))
        A("")

    # ---- 被上限 3.3 截断的
    capped = [r for r in rows if (r["sk_pow"] or 0) >= 3.29 or (r["ul_pow"] or 0) >= 3.29]
    A("## 3. 被 3.3 上限截断的卡（%d 张）" % len(capped))
    A("")
    A("| 棋子 | 小技能 wiki% | 必杀 wiki% | 现状 |")
    A("|---|---|---|---|")
    for r in capped[:20]:
        A("| %s | %s | %s | 已顶格 |" % (
            r["name"],
            ("%.0f%%" % r["sk_pct"]) if r["sk_pct"] else "—",
            ("%.0f%%" % r["ul_pct"]) if r["ul_pct"] else "—"))
    A("")

    open(OUT, "w", encoding="utf-8").write("\n".join(L))
    print("[fidelity] %s  %d 行" % (OUT, len(L)))
    print("[fidelity] 小技能可提取 %d/%d，必杀 %d/%d" % (
        len(ok_s), len(rows), len(ok_u), len(rows)))


if __name__ == "__main__":
    main()
