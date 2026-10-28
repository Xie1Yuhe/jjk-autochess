# -*- coding: utf-8 -*-
"""修正 fidelity 检查的换算口径：小技能 /120，必杀 /150，并度量 max_pct 抓错率"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = os.path.join(ROOT, "tools", "wiki_fidelity_check.py")
s = io.open(p, encoding="utf-8").read()

s = s.replace('K = 120.0  # build_units.py 里用的换算系数',
              'K_SKILL = 120.0   # build_units.py：power = max_pct / 120\n'
              'K_ULT = 150.0     # build_units.py：upow = max_pct / 150')

# 偏差函数按类型取不同 K
s = s.replace(
    '''    def dev(r, key_pct, key_pow):
        if not r[key_pct] or not r[key_pow]:
            return None
        want = max(1.0, r[key_pct] / K)
        return r[key_pow] / want''',
    '''    def dev(r, key_pct, key_pow):
        if not r[key_pct] or not r[key_pow]:
            return None
        k = K_SKILL if key_pow == "sk_pow" else K_ULT
        want = max(1.0, r[key_pct] / k)
        return r[key_pow] / want''')

s = s.replace('                r["name"], r["cost"], pct, max(1.0, pct / K), r[kw] or 0, d))',
              '                r["name"], r["cost"], pct,\n'
              '                max(1.0, pct / (K_SKILL if kw == "sk_pow" else K_ULT)), r[kw] or 0, d))')

# 新增：max_pct 抓错率统计
anchor = '    # ---- 被上限 3.3 截断的'
add = '''    # ---- max_pct 是否抓到了非伤害数值
    PCT_RE = re.compile(r"([0-9]+(?:\\.[0-9]+)?)%")
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

''' + anchor
assert anchor in s
s = s.replace(anchor, add, 1)

io.open(p, "w", encoding="utf-8").write(s)
print("fidelity 检查已修正口径并加入 max_pct 抓错率")
