# -*- coding: utf-8 -*-
r"""
apply_states2.py —— 第二批「状态是核心玩法」的角色

筛选标准（比第一批更严）：
  原文**给状态起了名字**，并且**状态会改变技能或数值**，而不是顺口提一句「状态」。

本批 10 张：
  640934 [zone] 虎杖            → 「zone」
  684667 [暴露的灵魂] 真人        → 「遍杀即灵体」
  672458 [履行哥哥的责任] 胀相     → 「赫鳞跃动・载」
  683430 [你这样就满足了吗？] 东堂  → 「亲友」
  717469 [不挠的瑞兽] 猪野        → 「麒麟」
  706232 [苍穹扣杀] 虎杖          → 「ZONE」
  680362 [诅咒的女王] 乙骨        → 「祈本里香」
  661932 [觉醒] 五条             → 「天上天下唯我独尊」
  614519 [寄宿于血中的决心] 加茂   → 「赤鳞跃动」
  675539 [唯快不破] 直毘人        → 「投射咒法」

用法：
    python tools\apply_states2.py && python tools\gen_text.py && python tools\build_data.py
"""
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNITS = os.path.join(ROOT, "data", "units.json")

S = {
    # 虎杖 zone：进入 zone 后技能变化、体术提升、追加行动
    "640934": ("zone", {"amp": 0.30, "bf": 0.30},
               {"name": "拳打・zone", "type": "barrage", "hits": 3, "sameTarget": True,
                "power": 1.05, "panel": "phys", "crit": 1.3},
               "原文：处于【zone】状态时技能变化、体术提升30%、追加行动"),
    # 真人：遍杀即灵体 = 体术/术式大幅提升
    "684667": ("遍杀即灵体", {"amp": 0.35, "guard": 0.15},
               {"name": "遍杀・无为转变", "type": "strike", "power": 4.2,
                "panel": "hybrid", "hybrid": True, "execute": 0.15},
               "原文：赋予自身「遍杀即灵体」状态、复合伤害并斩杀"),
    # 胀相：赫鳞跃动·载 = 体术/术式/造成伤害各 +50%
    "672458": ("赫鳞跃动・载", {"amp": 0.45},
               {"name": "穿血・载", "type": "strike", "power": 4.6,
                "panel": "hybrid", "hybrid": True, "applyTaken": 0.3},
               "原文：赫鳞跃动・载体术/术式/造成伤害各 +50%"),
    # 东堂：亲友状态 = 给亲友加体术、自己加暴击
    "683430": ("亲友", {"amp": 0.20, "bf": 0.20},
               {"name": "不义游戏・亲友", "type": "barrage", "hits": 4, "sameTarget": True,
                "power": 1.0, "panel": "phys"},
               "原文：亲友状态给友方体术提升、自身暴击提升"),
    # 猪野：麒麟状态 → 技能变化为「无痛的猛攻」
    "717469": ("麒麟", {"amp": 0.25},
               {"name": "无痛的猛攻", "type": "barrage", "hits": 2, "sameTarget": True,
                "power": 2.0, "panel": "hybrid", "hybrid": True, "applyTaken": 0.25},
               "原文：处于「麒麟」状态时技能变化为「无痛的猛攻」"),
    # 虎杖 苍穹扣杀：ZONE 体术提升
    "706232": ("ZONE", {"amp": 0.28, "bf": 0.25},
               {"name": "苍穹扣杀・ZONE", "type": "strike", "power": 5.2,
                "panel": "phys", "crit": 1.35},
               "原文：体术提升（ZONE 状态）"),
    # 乙骨：祈本里香 = 术式 +80%、必杀值回复
    "680362": ("祈本里香", {"amp": 0.40, "guard": 0.10},
               {"name": "里香・显现", "type": "barrage", "hits": 3, "sameTarget": True,
                "power": 2.2, "panel": "magic"},
               "原文：赋予自身「祈本里香」状态、术式 +80%"),
    # 五条 觉醒：天上天下唯我独尊
    "661932": ("天上天下唯我独尊", {"amp": 0.35},
               {"name": "赫・最大输出", "type": "slam", "radius": 99,
                "power": 2.6, "panel": "magic", "crit": 1.3},
               "原文：觉醒状态全能力提升、术式反转「赫」"),
    # 加茂：赤鳞跃动 = 技能变化
    "614519": ("赤鳞跃动", {"amp": 0.22},
               {"name": "虎爪・赤鳞", "type": "slam", "radius": 99,
                "power": 1.6, "panel": "magic", "applyTaken": 0.2},
               "原文：处于【赤鳞跃动】状态时技能发生变化，改为全体"),
    # 直毘人：投射咒法层数
    "675539": ("投射咒法", {"amp": 0.25},
               {"name": "最快的一击・壹", "type": "strike", "power": 4.0,
                "panel": "magic", "armNext": 1.2},
               "原文：投射咒法层数越多效果越大、破韧提升"),
}


def main():
    units = json.load(open(UNITS, encoding="utf-8"))
    by = {u["id"]: u for u in units}
    done = []
    for uid, (sname, buff, vskill, why) in S.items():
        u = by.get(uid)
        if not u:
            print("[states2] 找不到", uid)
            continue
        sk = dict(u.get("skill") or {})
        sk["enterState"] = {
            "name": sname, "dur": 20.0,
            "amp": buff.get("amp", 0),
            "guard": buff.get("guard", 0),
            "bf": buff.get("bf", 0),
            "skill": vskill,
        }
        sk["stateWhy"] = why
        u["skill"] = sk
        done.append((u["name"], sname, why))

    json.dump(units, open(UNITS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[states2] 接入 %d 张" % len(done))
    for n, s, w in done:
        print("   %-24s 「%s」" % (n, s))
        print("      %s" % w)


if __name__ == "__main__":
    main()
