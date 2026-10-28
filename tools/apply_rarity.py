# -*- coding: utf-8 -*-
r"""
apply_rarity.py —— Phase 7 第二步：品质（R/SR/SSR）+ 费用重算 + 可玩卡池扩充

背景（用户补充）：
  · 幻影夜行里 **大部分卡是 SSR**，少数 SR / R；
  · wiki 页面没有稀有度字段（见 DATA_GAP §2.2），所以按 **《咒术回战》原作设定** 裁定：
      特级 / 最强 / 主角高光  → SSR
      一级 / 准一级 / 主要配角 → SR
      三级以下 / 非术师 / 辅助 → R
  · 「特性」= 幻/影/夜/行（元素），「咒力」= 技能资源，「必杀充能」= 必杀技资源，
    「反转术式」= 治疗 —— 这些语义在 build_units.py 的转化规则里已经对齐。

本脚本只做三件事，且可重复执行（幂等）：
  1. 给每个棋子打 `rarity`（含按卡面的覆盖表）；
  2. 用「稀有度基准 + wiki 强度分位」重算 `cost`，并把 1–5 费压到健康分布；
  3. 按 `PLAYABLE_ADD` 扩充可玩卡池（含 3 组异格联动所需的卡）。

用法：python tools\apply_rarity.py
"""
import json
import os
import statistics
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNITS = os.path.join(ROOT, "data", "units.json")
REPORT = os.path.join(ROOT, "tools", "rarity_report.json")

# ---------------------------------------------------------------- 稀有度
# 依据原作：术师等级 + 战绩 + 剧情地位
RARITY_BASE = {
    # —— 特级 / 最强：SSR ——
    "五条悟": "SSR", "两面宿傩": "SSR", "夏油杰": "SSR", "乙骨忧太": "SSR",
    "伏黑甚尔": "SSR", "虎杖悠仁": "SSR", "伏黑惠": "SSR",
    "真人": "SSR", "漏瑚": "SSR", "花御": "SSR", "胀相": "SSR",
    "禅院直毘人": "SSR", "七海建人": "SSR",
    # —— 一级 / 准一级 / 主要配角：SR ——
    "钉崎野蔷薇": "SR", "狗卷棘": "SR", "熊猫": "SR", "禅院真希": "SR",
    "东堂葵": "SR", "加茂宪纪": "SR", "加茂宪伦": "SR", "日下部笃也": "SR",
    "冥冥": "SR", "家入硝子": "SR", "夜蛾正道": "SR", "乐岩寺嘉伸": "SR",
    "究极机械丸": "SR", "与幸吉": "SR", "陀艮": "SR", "里梅": "SR",
    "米格尔": "SR", "猪野琢真": "SR",
    # —— 三级以下 / 非术师 / 辅助：R ——
    "三轮霞": "R", "西宫桃": "R", "禅院真依": "R", "吉野顺平": "R",
    "伊地知洁高": "R", "结木海斗": "R", "灰原雄": "R", "漆英司": "R",
    "龙胆咲": "R",
}

# 同一角色的「觉醒 / 最终形态」可以额外升一档（卡面强度差异）
RARITY_BY_CARD = {
    "652057": "SSR",   # 禅院真希「破晓启程」——天与咒缚觉醒
    "607991": "SR",    # 禅院真希「天赐无才」
    "607988": "SR",    # 虎杖「宿傩的容器」——初始卡，SR 而非 SSR
    "607979": "SSR",   # 夏油杰「大义」已 SSR
    "721094": "SSR",   # 夏油杰「终焉之物」
    "606026": "SSR",   # 五条悟「最强」
    "607990": "R",     # 钉崎「为了保持自我」——早期卡
    "607993": "R",     # 熊猫「熊猫但不是熊猫」
    "607992": "R",     # 狗卷「诅咒的言灵」
    "607846": "R",     # 七海「不上班族术师」
    "607989": "R",     # 伏黑「不平等的救赎」——旧版页面
}

RARITY_COLOR = {"R": "#7f8ea3", "SR": "#4d9bff", "SSR": "#f0c34a"}
# 稀有度 → 费用基准（自走棋的经济档位）
COST_BASE = {"R": 1.65, "SR": 2.65, "SSR": 3.85}

# ------------------------------------------------------- 可玩卡池扩充
# 目的：① 让 3 组异格联动都凑得齐 ② 补足各费用档 ③ 收录人气异格
PLAYABLE_ADD = [
    "721094",  # 夏油杰「终焉之物」   —— 联动 L1
    "606026",  # 五条悟「最强」       —— 联动 L2
    "607988",  # 虎杖「宿傩的容器」   —— 联动 L3
    "652057",  # 禅院真希「破晓启程」
    "637822",  # 狗卷棘「破碎吧」
    "607839",  # 禅院真希「越是弱小越是聚集」
    "615301",  # 钉崎「相性极差」
    "620332",  # 熊猫「需要帮助吗」
    "632100",  # 七海「一级术师的实力」
    "607978",  # 乙骨「把力量借给我」
    "707237",  # 钉崎「出片常夏」
    "707238",  # 伏黑「清凉海风」
    "622642",  # 五条悟「苍之最强」
    "706232",  # 虎杖「苍穹扣杀」
]

TARGET_DIST = {1: 10, 2: 11, 3: 15, 4: 12, 5: 10}   # 合计 58


def pctile(sorted_vals, v):
    return sum(1 for x in sorted_vals if x < v) / max(1, len(sorted_vals))


def num(s):
    try:
        return int(float(str(s).replace(",", "")))
    except Exception:
        return 0


def main():
    units = json.load(open(UNITS, encoding="utf-8"))
    if units and "tier" in units[0]:
        print("[warn] 检测到强度榜数据：本脚本写的 rarity 会被 apply_tierlist.py 覆盖。")
        print("[warn] 正确顺序：build_units → apply_rarity → apply_tierlist → build_data")

    mains = sorted(max(num(u["wikiStats"].get("体术")), num(u["wikiStats"].get("术式"))) for u in units)

    # 1) 打稀有度
    for u in units:
        base = u["baseCharacter"]
        r = RARITY_BY_CARD.get(u["id"]) or RARITY_BASE.get(base) or "SR"
        u["rarity"] = r
        u["rarityColor"] = RARITY_COLOR[r]
        u["raritySource"] = "canon" if base in RARITY_BASE else "fallback"

    # 2) 重算费用：稀有度基准 + 强度分位
    for u in units:
        main = max(num(u["wikiStats"].get("体术")), num(u["wikiStats"].get("术式")))
        p = pctile(mains, main)
        raw = COST_BASE[u["rarity"]] + (p - 0.5) * 2.1
        u["cost"] = int(max(1, min(5, round(raw))))
        u["costFromRarity"] = True

    # 已实装的 44 名如果费用被改得过大，保留原值以保护手感（只允许 ±1）
    # —— 这里先不强制，交给下面的分布校正统一处理

    # 3) 可玩卡池（幂等：以首次标记的底座为准，重复执行不会滚雪球）
    if "_basePlayable" not in units[0]:
        base_ids = [u["id"] for u in units if u["playable"]]
        for u in units:
            u["_basePlayable"] = u["playable"]
    for u in units:
        u["playable"] = bool(u["_basePlayable"]) or (u["id"] in PLAYABLE_ADD)

    # 4) 费用分档：按「强度分」全局排序后按分位切档，再受稀有度上下限约束
    #    这样不会出现"逐个档位搬人"导致的级联（上一版把两面宿傩搬到了 3 费）。
    playable = [u for u in units if u["playable"]]
    print("校正前分布:", {c: sum(1 for u in playable if u["cost"] == c) for c in range(1, 6)},
          "可玩", len(playable))

    def score(u):
        main = max(num(u["wikiStats"].get("体术")), num(u["wikiStats"].get("术式")))
        return COST_BASE[u["rarity"]] + (pctile(mains, main) - 0.5) * 2.1

    # 稀有度硬约束：SSR 不进 1 费；R 不进 5 费；SSR 最高优先占 5 费
    def clamp_cost(u, c):
        if u["rarity"] == "SSR":
            c = max(c, 3)
        if u["rarity"] == "R":
            c = min(c, 2)
        return max(1, min(5, c))

    playable.sort(key=score)
    n = max(1, len(playable))
    for i, u in enumerate(playable):
        frac = i / max(1, n - 1)
        c = 1 + int(frac * 4.999)
        u["cost"] = clamp_cost(u, c)

    # 微调：把分布往目标拉，但只在「不违反稀有度约束」的前提下交换
    def bump_toward_target():
        for _ in range(200):
            dist = {c: sum(1 for u in playable if u["cost"] == c) for c in range(1, 6)}
            worst = max(range(1, 6), key=lambda c: TARGET_DIST[c] - dist[c])
            if TARGET_DIST[worst] - dist[worst] <= 1:
                break
            # 从最近的盈余档里找一个能搬的
            donors = sorted(range(1, 6), key=lambda c: dist[c] - TARGET_DIST[c], reverse=True)
            moved = False
            for d in donors:
                if d == worst or dist[d] <= TARGET_DIST[d]:
                    continue
                step = 1 if d < worst else -1
                cands = [u for u in playable if u["cost"] == d]
                # 搬动方向：往高价搬挑最弱的，往低价搬挑最强的
                cands.sort(key=score, reverse=(step < 0))
                for u in cands:
                    if clamp_cost(u, d + step) == d + step:
                        u["cost"] = d + step
                        moved = True
                        break
                if moved:
                    break
            if not moved:
                break
    bump_toward_target()

    playable = [u for u in units if u["playable"]]
    dist = {c: sum(1 for u in playable if u["cost"] == c) for c in range(1, 6)}
    rarity_dist = {r: sum(1 for u in playable if u["rarity"] == r) for r in ("R", "SR", "SSR")}
    all_rarity = {r: sum(1 for u in units if u["rarity"] == r) for r in ("R", "SR", "SSR")}

    json.dump(units, open(UNITS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    rep = {
        "playable": len(playable),
        "total": len(units),
        "costDist": dist,
        "rarityDistPlayable": rarity_dist,
        "rarityDistAll": all_rarity,
        "added": PLAYABLE_ADD,
    }
    json.dump(rep, open(REPORT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("校正后分布:", dist, "可玩", len(playable))
    print("稀有度（可玩）:", rarity_dist)
    print("稀有度（全部）:", all_rarity)
    for c in range(1, 6):
        names = [u["name"] for u in playable if u["cost"] == c]
        print("  %d费(%d): %s" % (c, len(names), "、".join(names)))


if __name__ == "__main__":
    main()
