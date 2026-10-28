# -*- coding: utf-8 -*-
r"""
gen_text.py —— 从**实际数据字段**生成所有面向玩家的描述文本

为什么需要它：
  批次重写只改了 skill.type / power / ult / mods，但 skill.desc 和 passive.desc
  还是 Phase 7 之前规则引擎生成的旧文本 —— 于是出现「数据是全体 AoE、描述写 1 格」、
  「被动写侵蚀、实际是开场必杀值 + 必杀后自毁」这种对不上的情况。

  修法：描述**不再手写、不再遗留**，一律由字段生成。改数据 = 自动改文本。

生成：
  skill.desc   ← type / panel / power / hits / radius / 各类附加效果
  ult.desc     ← 同上 + 必杀值
  passive.desc ← mods 的每一项

用法（排在所有 apply_* 之后、build_data 之前）：
    python tools\gen_text.py
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

TYPE_LABEL = {
    "strike": "单体突袭", "slam": "范围重击", "barrage": "多段连击", "beam": "直线贯穿",
    "dot": "持续侵蚀", "drain": "削咒打击", "stun": "眩晕控制", "heal": "治疗回复",
    "shield": "护盾守护", "buff": "全队增益", "empower": "自我强化", "summon": "召唤式神",
    "taunt": "嘲讽",
}
PANEL_LABEL = {"phys": "体术", "magic": "术式", "hybrid": "复合"}


def pct(x, digits=0):
    return ("%." + str(digits) + "f%%") % (x * 100)


def panel_of(sk, u):
    p = sk.get("panel")
    if p:
        return p
    if sk.get("hybrid"):
        return "hybrid"
    return "phys" if u.get("dmg") == "体术" else "magic"


def _suffix_of(sk):
    """状态 / 领域 的追加说明（所有技能类型都要带）"""
    bits = []
    es = sk.get("enterState")
    if es:
        b = ["施放后进入「%s」%.0f 秒" % (es.get("name"), es.get("dur", 20))]
        if es.get("amp"): b.append("期间体术/术式 +%s" % pct(es["amp"]))
        if es.get("guard"): b.append("减伤 %s" % pct(es["guard"]))
        if es.get("bf"): b.append("黑闪 +%s" % pct(es["bf"]))
        if es.get("skill"): b.append("状态中技能变化为「%s」" % es["skill"].get("name"))
        bits.append("【状态】" + "，".join(b))
    d = sk.get("domain")
    if d:
        b = []
        if d.get("allyAmp"): b.append("己方体术/术式 +%s" % pct(d["allyAmp"]))
        if d.get("allyGuard"): b.append("己方减伤 %s" % pct(d["allyGuard"]))
        if d.get("enemyTaken"): b.append("敌方受到伤害 +%s" % pct(d["enemyTaken"]))
        if d.get("enemyWeaken"): b.append("敌方造成伤害 -%s" % pct(d["enemyWeaken"]))
        if d.get("enemyStun"): b.append("开域瞬间全体眩晕 %.1f 秒" % d["enemyStun"])
        if d.get("selfGuard"): b.append("自身减伤 %s" % pct(d["selfGuard"]))
        if d.get("enemyDot"): b.append("敌方每秒 %s 最大生命" % pct(d["enemyDot"]))
        if d.get("enemyMaxHpPct"): b.append("立刻削掉敌方 %s 最大生命" % pct(d["enemyMaxHpPct"]))
        if d.get("ultBlock"): b.append("敌方必杀槽上升无效")
        if d.get("skillAoe"): b.append("领域内每次技能追加全场 %.0f%% 双面板伤害" % (d["skillAoe"] * 100))
        if d.get("skillMana"): b.append("每次技能回 %d 咒力" % d["skillMana"])
        if d.get("endMana"): b.append("%s 秒后领域结束、咒力归零" % d.get("dur", 6))
        bits.append("【领域】" + "，".join(b))
    sk2 = sk.get("altSkill")
    if sk2:
        bits.append("【双技能】与「%s」交替使用" % sk2.get("name"))
    so = sk.get("stackOnCast")
    if so:
        bits.append("【叠层】每次施法 +1 层，满 %d 层引爆全场" % so.get("max", 3))
    return ("，" + "，".join(bits)) if bits else ""


def skill_text(u, sk, is_ult=False):
    base = _skill_core(u, sk, is_ult)
    suf = _suffix_of(sk)
    if not suf:
        return base
    # 避免重复（伤害类技能内部已追加过）
    if "【状态】" in base or "【领域】" in base:
        return base
    return base + suf


def _skill_core(u, sk, is_ult=False):
    """从字段生出一句人话。"""
    if not sk:
        return ""
    t = sk.get("type")

    # 非伤害类技能：不谈面板与倍率，只描述效果
    if t in ("heal", "shield", "buff", "empower", "taunt", "summon"):
        if t == "heal":
            return "治疗血量最低的友军 %s 最大生命" % pct(
                sk.get("healPct") or (0.45 if is_ult else 0.25))
        if t == "shield":
            return "为自身与相邻友军提供 %s 最大生命护盾" % pct(
                sk.get("shieldPct") or (0.35 if is_ult else 0.20))
        if t == "buff":
            return "全队体术 / 术式 +25%"
        if t == "summon":
            return "召唤属性 30% 的式神助战"
        if t == "taunt":
            s = "嘲讽 %.1f 秒" % sk.get("taunt", 2)
            if sk.get("guard"):
                s += "，期间减伤 %s" % pct(sk["guard"])
            return s
        # empower
        s = "自身体术 / 术式 +%s（%s 秒）" % (pct(sk.get("amp", 0.6)), sk.get("dur", 3.5))
        if sk.get("taunt"):
            s += "，同时嘲讽 %.1f 秒" % sk["taunt"]
        if sk.get("guard"):
            s += "、减伤 %s" % pct(sk["guard"])
        return s

    lab = TYPE_LABEL.get(t, "技能")
    panel = PANEL_LABEL.get(panel_of(sk, u), "术式")
    parts = []

    # 主体
    pw = sk.get("power")
    pw_txt = (" ×%s" % (("%.2f" % pw).rstrip("0").rstrip("."))) if pw else ""
    parts.append("%s（%s）%s" % (lab, panel, pw_txt))

    # 段数 / 目标
    if sk.get("hits"):
        parts.append("%d 段" % sk["hits"])
    if sk.get("sameTarget"):
        parts.append("锁定同一目标")
    rad = sk.get("radius")
    if rad is not None:
        parts.append("对敌方全体" if rad >= 99 else "半径 %s 格" % rad)

    # 控制 / 削弱 / 增益
    if sk.get("stun"):
        parts.append("眩晕 %.1f 秒" % sk["stun"])
    if sk.get("applyTaken"):
        parts.append("施加易伤 %s" % pct(sk["applyTaken"]))
    if sk.get("applyWeaken"):
        parts.append("削弱敌方 %s 造成伤害" % pct(sk["applyWeaken"]))
    if sk.get("dot"):
        parts.append("附加持续伤害 %s/秒（%s 秒）" % (pct(sk["dot"], 1), sk.get("dotDur", 5)))
    if sk.get("execute"):
        parts.append("血量低于 %s 时直接处决" % pct(sk["execute"]))
    if sk.get("taunt"):
        parts.append("嘲讽 %.1f 秒" % sk["taunt"])
    if sk.get("guard"):
        parts.append("期间减伤 %s" % pct(sk["guard"]))
    if sk.get("armNext"):
        parts.append("破韧：下一次技能 +%s" % pct(sk["armNext"]))
    if sk.get("amp"):
        parts.append("自身增伤 %s（%s 秒）" % (pct(sk["amp"]), sk.get("dur", 3.5)))
    if sk.get("crit"):
        parts.append("必定暴击（×%.1f）" % sk["crit"])
    if sk.get("sure"):
        parts.append("必中")
    if sk.get("lastHitBf"):
        parts.append("末段必定黑闪")
    es = sk.get("enterState")
    if es:
        bits = ["施放后进入「%s」%.0f 秒" % (es.get("name"), es.get("dur", 10))]
        if es.get("amp"): bits.append("期间体术/术式 +%s" % pct(es["amp"]))
        if es.get("guard"): bits.append("减伤 %s" % pct(es["guard"]))
        if es.get("bf"): bits.append("黑闪 +%s" % pct(es["bf"]))
        if es.get("skill"): bits.append("状态中技能变化为「%s」" % es["skill"].get("name"))
        parts.append("【状态】" + "，".join(bits))
    d = sk.get("domain")
    if d:
        bits = []
        if d.get("allyAmp"): bits.append("己方体术/术式 +%s" % pct(d["allyAmp"]))
        if d.get("allyGuard"): bits.append("己方减伤 %s" % pct(d["allyGuard"]))
        if d.get("enemyTaken"): bits.append("敌方受到伤害 +%s" % pct(d["enemyTaken"]))
        if d.get("enemyWeaken"): bits.append("敌方造成伤害 -%s" % pct(d["enemyWeaken"]))
        if d.get("enemyStun"): bits.append("开域瞬间全体眩晕 %.1f 秒" % d["enemyStun"])
        if d.get("selfGuard"): bits.append("自身减伤 %s" % pct(d["selfGuard"]))
        if d.get("enemyDot"): bits.append("敌方每秒 %s 最大生命" % pct(d["enemyDot"]))
        if d.get("enemyMaxHpPct"): bits.append("立刻削掉敌方 %s 最大生命" % pct(d["enemyMaxHpPct"]))
        if d.get("ultBlock"): bits.append("敌方必杀槽上升无效")
        if d.get("skillAoe"): bits.append("领域内每次技能追加全场 %.0f%% 双面板伤害" % (d["skillAoe"] * 100))
        if d.get("skillMana"): bits.append("每次技能回 %d 咒力" % d["skillMana"])
        if d.get("endMana"): bits.append("%s 秒后领域结束、咒力归零" % d.get("dur", 6))
        parts.append("【领域】" + "，".join(bits))
    if sk.get("debuffBonus"):
        parts.append("目标每层减益再 +%s 伤害（上限 %d 层）"
                     % (pct(sk["debuffBonus"]), sk.get("debuffMax", 5)))

    return "，".join(parts)


# mods 每一项 → 一句说明
def passive_text(mods):
    if not mods:
        return "无被动（纯数值卡）"
    out = []
    for k, v in mods.items():
        if k.startswith("grow_"):
            out.append("计数每层 +%s 体术 / 术式" % pct(v))
        elif k.startswith("max_"):
            continue
        elif k == "bf":
            out.append("黑闪率 %s" % pct(v))
        elif k == "dodge":
            out.append("闪避 %s" % pct(v))
        elif k == "armor":
            out.append("减伤 %s" % pct(v))
        elif k == "mres":
            out.append("术式减伤 %s" % pct(v))
        elif k == "regen":
            out.append("每秒再生 2% 生命")
        elif k == "reviveLeft":
            out.append("阵亡时以 %s 生命复活一次" % pct(mods.get("revivePct", 0.4)))
        elif k == "revivePct":
            continue
        elif k == "retireAt":
            out.append("%.0f 秒后强制退场" % v)
        elif k == "retireOnUlt":
            out.append("释放必杀后自毁")
        elif k == "retireAura":
            out.append("退场时全队体术/术式 +%s" % pct(v))
        elif k == "invulnStart":
            out.append("开场 %.0f 秒攻击无效化" % v)
        elif k == "invulnLowHp":
            out.append("生命首次 ≤50%% 时再获 %.0f 秒无敌" % v)
        elif k == "counterMult":
            out.append("受近战攻击时反击 %.1f 倍体术" % v)
        elif k == "counter_counter":
            out.append("反击时累积计数")
        elif k == "counter_bonus":
            continue
        elif k == "manaOnKill":
            out.append("击杀回复 %d 咒力" % v)
        elif k == "manaOnCrit":
            out.append("暴击/黑闪回复 %d 咒力" % v)
        elif k == "mana_on_cast":
            out.append("施法后额外回复 %d 咒力" % v)
        elif k == "healAlly":
            out.append("每 %s 秒消耗 %d 咒力治疗残血友军 %s 生命"
                       % (v.get("interval", 4), v.get("cost", 15), pct(v.get("pct", 0.1))))
        elif k == "healHitsEvery":
            out.append("每受 %d 次击回复 %s 生命" % (v, pct(mods.get("healHitsPct", 0.08))))
        elif k == "healHitsPct":
            continue
        elif k == "aura_power":
            out.append("全队体术 / 术式 +%s" % pct(v))
        elif k == "aura_haste":
            out.append("全队攻速 +%s" % pct(v))
        elif k == "ultStart":
            out.append("开场必杀值 %s" % v)
        elif k == "selfDamageOnUlt":
            out.append("必杀时自损 %s 生命" % pct(v))
        elif k == "ultManaPenalty":
            out.append("必杀后咒力归零并禁咒 %s 秒" % v.get("lock", 2))
        elif k == "ultWhenLowMana":
            out.append("咒力低于 %d 时每秒回 %d 必杀值"
                       % (v.get("below", 15), v.get("perSec", 40)))
        elif k == "immuneControl":
            out.append("免疫控制")
        elif k == "elemHunter":
            out.append("属性克制时额外 +%s" % pct(v))
        elif k == "extra_attack":
            out.append("行动后追加一次普攻")
        elif k == "dotResist":
            out.append("持续伤害减免 %s" % pct(v))
        elif k == "bf_count_key":
            out.append("每累计 %d 次攻击必定黑闪" % mods.get("bf_count_need", 5))
        elif k in ("bf_count_need", "bf_count_mult"):
            continue
        elif k == "bf_double":
            out.append("黑闪追加一次伤害")
        elif k == "sure_hit":
            out.append("体术/术式必中")
        elif k == "skill_splash":
            out.append("技能附加 %s 溅射" % pct(v))
        elif k == "mana_on_cast":
            out.append("施法回咒")
        elif k == "lifesteal":
            out.append("吸血 %s" % pct(v))
        elif k == "erode":
            out.append("普攻附带 %s 最大生命伤害" % pct(v))
        elif k == "slow_on_hit":
            out.append("普攻减速 %s" % pct(v))
        elif k == "taunt":
            out.append("优先吸引攻击")
        elif k == "link_stack" or k == "link_heal_on_kill" or k == "link_double_cast":
            continue   # 联动效果在联动条目里说明
        else:
            out.append(k)
    return "；".join(out) if out else "无被动（纯数值卡）"


def passive_kind(mods):
    """按主导效果给被动分类（决定 tooltip 上的小标签）"""
    if not mods:
        return "mods"
    order = [
        ("retireOnUlt", "retire_ult"), ("retireAt", "retire"), ("reviveLeft", "revive"),
        ("invulnStart", "invuln"), ("invulnLowHp", "invuln"), ("counterMult", "counter"),
        ("healAlly", "heal_ally"), ("extra_attack", "extra"), ("ultStart", "ult_start"),
        ("aura_power", "aura"), ("aura_haste", "aura"), ("manaOnKill", "mana_gain"),
        ("manaOnCrit", "mana_gain"), ("mana_on_cast", "mana_gain"), ("bf", "bf"),
        ("dodge", "dodge"), ("armor", "guard"), ("mres", "guard"), ("taunt", "taunt"),
        ("erode", "erode"), ("lifesteal", "erode"), ("slow_on_hit", "erode"),
    ]
    for key, kind in order:
        if key in mods:
            return kind
    for k in mods:
        if k.startswith("grow_"):
            return "grow"
    return "mods"


def main():
    units = json.load(open(UNITS, encoding="utf-8"))
    changed = 0
    for u in units:
        sk = u.get("skill") or {}
        old_desc = sk.get("desc")
        new_desc = skill_text(u, sk, is_ult=False)
        if old_desc != new_desc:
            changed += 1
        sk["desc"] = new_desc
        sk["effect"] = new_desc
        u["skill"] = sk

        ult = u.get("ult") or {}
        if ult.get("combat"):
            ult["desc"] = skill_text(u, ult, is_ult=True)
            u["ult"] = ult

        pv = u.get("passive") or {}
        pv["desc"] = passive_text(u.get("mods") or {})
        pv["kind"] = passive_kind(u.get("mods") or {})   # 仅用于显示，不能覆盖 type（引擎在读）
        u["passive"] = pv

    json.dump(units, open(UNITS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[text] 重新生成描述：技能改动 %d 张 / 共 %d 张" % (changed, len(units)))
    s = units[0]
    print("[text] 示例 %s" % s["name"])
    print("        技: " + s["skill"]["desc"])
    if (s.get("ult") or {}).get("desc"):
        print("        杀: " + s["ult"]["desc"])
    print("        被: " + s["passive"]["desc"])


if __name__ == "__main__":
    main()
