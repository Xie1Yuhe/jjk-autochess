# -*- coding: utf-8 -*-
r"""
check_ids.py —— 查「按 id 改数据」的脚本里，id 和注释里的角色名对不上

背景：这个项目里已经出过三次同类错误（乐岩寺、米格尔、东堂、里梅），
都是「凭印象填 id，结果改到了别的角色身上」。跑数据脚本前先跑这个。

做法：
  1. 扫 tools/apply_*.py，找出所有 6 位数字 id（字典键）
  2. 从 id 同一行或上一行的注释里抽出中文角色名
  3. 和 units.json 里的真实角色名比对，对不上就报

用法：
    python tools\check_ids.py
退出码 1 表示有问题。
"""
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNITS = os.path.join(ROOT, "data", "units.json")
TOOLS = os.path.join(ROOT, "tools")

ID_RE = re.compile(r'"(\d{6})"\s*:\s*\{')
CN_RE = re.compile(r'[\u4e00-\u9fa5]{2,6}')


def main():
    units = json.load(open(UNITS, encoding="utf-8"))
    by_id = {u["id"]: u for u in units}
    bases = sorted({u["baseCharacter"] for u in units}, key=len, reverse=True)

    files = sorted(f for f in os.listdir(TOOLS)
                   if f.startswith("apply_") and f.endswith(".py"))
    problems = []
    checked = 0

    for fn in files:
        path = os.path.join(TOOLS, fn)
        lines = open(path, encoding="utf-8").read().split("\n")
        for i, line in enumerate(lines):
            for m in ID_RE.finditer(line):
                uid = m.group(1)
                checked += 1
                u = by_id.get(uid)
                if not u:
                    problems.append((fn, i + 1, uid, "(units.json 里没有这个 id)", "id 不存在"))
                    continue
                # 注释：本行 id 之后的部分 + 上一行
                tail = line[m.end():]
                comment = ""
                if "#" in tail:
                    comment = tail.split("#", 1)[1]
                elif i > 0 and "#" in lines[i - 1]:
                    comment = lines[i - 1].split("#", 1)[1]
                if not comment:
                    continue
                # 注释里出现的角色名
                named = [b for b in bases if b in comment]
                if not named:
                    continue
                real = u["baseCharacter"]
                if real not in named:
                    problems.append((fn, i + 1, uid,
                                     "注释写的是 %s，实际是 %s" % ("/".join(named), real),
                                     "id 与注释不符"))

    # ---- 第二轮：状态名是不是真的出自原文 ----
    for u in units:
        sk = u.get("skill") or {}
        blob = ((sk.get("wikiDesc") or "") + (sk.get("stateWhy") or "")
                + ((u.get("ultimate") or {}).get("wikiDesc") or "")
                + ((u.get("passive") or {}).get("wikiDesc") or ""))
        es = sk.get("enterState")
        if es and es.get("name"):
            nm = es["name"]
            core = nm.split("・")[0].split("·")[0]
            if core not in blob:
                problems.append(("(数据)", 0, u["id"],
                                 "状态名「%s」在原文里找不到（%s）" % (nm, u["name"]),
                                 "状态名疑似编造"))
    # ---- 第三轮：面向玩家的文本里，不能拿「攻击」指代伤害属性 ----
    OK_ATTACK = ['攻击无效化', '吸引攻击', '次攻击', '近战攻击', '远程攻击', '受到攻击时', '攻击计数']
    for u in units:
        fields = []
        for key in ('skill', 'ult', 'passive'):
            d = u.get(key) or {}
            if d.get('desc'): fields.append((key, d['desc']))
        for key, txt in fields:
            t = txt
            for ok in OK_ATTACK:
                t = t.replace(ok, '')
            if '攻击' in t:
                problems.append(("(用词)", 0, u["id"],
                                 "%s 里用「攻击」指代伤害属性：…%s…" % (key, txt[:40]),
                                 "用词应改为体术/术式"))
    print("[check_ids] 扫描 %d 个 apply_*.py，检查 %d 个 id" % (len(files), checked))
    if not problems:
        print("[check_ids] 全部对得上 ✓")
        return 0

    print("[check_ids] 发现 %d 处问题：" % len(problems))
    for fn, ln, uid, msg, kind in problems:
        print("   %-22s L%-4d %s  %s" % (fn, ln, uid, msg))
    return 1


if __name__ == "__main__":
    sys.exit(main())
