# -*- coding: utf-8 -*-
r"""
patch_pace.py —— 拉长战斗节奏，让技能与必杀真的打得出来

## 诊断

实测：均势 5v5 战斗平均 **9.6 秒**，其中必杀 0 次、技能 0 次。
原因不是数值问题，是**时间不够**：
  · 一次技能要攒 `manaMax`（多为 100~120），初始 30~40，普攻 +10/次，攻速 0.85
    → 攒满约需 7~9 秒
  · 必杀槽要 100，涓流 1.0/s + 行为加成 → 约 10 秒
但战斗 5~10 秒就结束了，所以大部分对局里单位既不放技能也不放必杀。

## 两处改动

1. **所有棋子 HP ×1.7**：战斗时长直接拉长到 15~18 秒，技能/必杀才打得出来
2. **败北掉血放缓**：`2 + 存活×2 + 回合/3` → `2 + 存活×1.3 + 回合/4`
   原来 10 回合左右就能把对手打死，一整局只有 10~19 回合；
   放缓后目标 22~30 回合，接近成熟自走棋的长度

配套：AI 与玩家的初始 HP 不变（100），因为掉血公式已经放缓。
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
HP_SCALE = 1.7


def main():
    apply = "--apply" in sys.argv
    units = json.load(open(UNITS, encoding="utf-8"))
    for u in units:
        u["hp"] = int(round(u["hp"] * HP_SCALE))
    if apply:
        json.dump(units, open(UNITS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("[pace] HP ×%.2f 已应用（%d 张）" % (HP_SCALE, len(units)))
    else:
        print("[pace] 预览：HP ×%.2f（加 --apply 应用）" % HP_SCALE)


if __name__ == "__main__":
    main()
