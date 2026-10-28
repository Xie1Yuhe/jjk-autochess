# -*- coding: utf-8 -*-
r"""
fix_display_text.py —— 修咒具/技能描述里的显示问题

1. 字段名泄漏：desc 里混进了 `debuffBonus；` 这类代码字段名
2. 术语残留：「全队攻击提升」应为「全队伤害提升」（本作不用「攻击」这个说法）

改的是 data/units.json（game-data.js 的源头），改完需要跑 build_data.py。
"""
import io
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = os.path.join(ROOT, "data", "units.json")
d = json.load(io.open(p, encoding="utf-8"))
units = d["units"] if isinstance(d, dict) and "units" in d else d

# 字段名 → 人话
FIELD_MAP = {
    "debuffBonus": "受到减益增伤",
    "applyTaken": "受到伤害提升",
    "enterState": "进入状态",
    "altSkill": "交替技能",
    "stackOnCast": "施法叠层",
    "scaleByCounter": "按计数成长",
    "sureHit": "必中",
    "armNext": "护甲",
    "lastHitBf": "斩杀加成",
}

changed = 0


def clean_text(t):
    """去掉描述里裸露的字段名与残留标记"""
    if not isinstance(t, str):
        return t, False
    orig = t
    # ① 「字段名；」或「字段名,」开头/夹在中间的残留
    for k, v in FIELD_MAP.items():
        t = re.sub(r"(^|[；;，,\s])" + k + r"\s*[；;，,、]\s*", r"\1" + v + "；", t)
        t = re.sub(r"(^|[；;，,、\s])" + k + r"(?=[；;，,、\s]|$)", r"\1" + v, t)
    # ② 「攻击提升」→「伤害提升」（本作没有「攻击」这个属性名）
    t = t.replace("全队攻击提升", "全队伤害提升")
    t = t.replace("攻击提升", "伤害提升")
    return t, (t != orig)


def walk(obj, path=""):
    global changed
    if isinstance(obj, dict):
        for k in list(obj.keys()):
            v = obj[k]
            if isinstance(v, str):
                nv, ch = clean_text(v)
                if ch:
                    obj[k] = nv
                    changed += 1
                    print("  修正 %s.%s: %s" % (path, k, nv[:70]))
            elif isinstance(v, (dict, list)):
                walk(v, path + "." + k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, str):
                nv, ch = clean_text(v)
                if ch:
                    obj[i] = nv
                    changed += 1
            else:
                walk(v, path + "[%d]" % i)


walk(units, "units")

# 兜底：全局再扫一遍字段名残留
raw = json.dumps(d, ensure_ascii=False)
leftover = [k for k in FIELD_MAP if re.search(r"[；;，,]\s*" + k + r"\s*[；;，,]", raw)]
print("[fix] 共修正 %d 处；剩余疑似字段名：%s" % (changed, leftover or "无"))

json.dump(d, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("[fix] units.json 已保存，请运行 build_data.py")
