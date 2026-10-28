/* =========================================================================
 *  battle.js —— 自动战斗引擎（纯逻辑，不碰 DOM）
 *
 *  移植自 Godot 版 scripts/battle.gd，规则逐条对齐：
 *   · 8×4 棋盘，玩家 team=0 占第 0..3 列，敌方 team=1 占第 4..7 列
 *   · 按攻速出手；射程内打最近敌人，否则向最近敌人移动
 *   · 咒力满 → 放技能；命中/受击积攒咒力
 *   · 30 秒进入加时（每秒按最大生命百分比真伤递增），45 秒强制判定
 *   · 10 条羁绊 28 个档位、11 种被动全部有对应实现
 *   · 所有表现交给 events 队列，渲染层只消费事件
 * ========================================================================= */
(function (global) {
  'use strict';

  var JJK = global.JJK = global.JJK || {};
  var U = JJK.util;

  var GRID_W = 8;
  var GRID_H = 4;
  var MAX_TIME = 45.0;        // 硬性结束
  var OVERTIME_AT = 30.0;     // 进入加时
  var DOMAIN_TRIGGER = 8.0;   // 领域展开默认时间
  var DOMAIN_DURATION = 8.0;

  var STAR_MULT = [1, 1, 1.75, 3.0];

  function dist(a, b) {
    return Math.abs(a.x - b.x) + Math.abs(a.y - b.y);
  }

  /* ======================================================== 战斗单位 ==== */
  function BattleUnit() {
    this.id = 0;
    this.def = {};
    this.team = 0;
    this.pos = { x: 0, y: 0 };
    this.hp = 0;
    this.maxHp = 0;
    this.ad = 0;
    this.spell = 0;
    this.asRate = 0.85;
    this.atkRange = 1;
    this.mana = 0;
    this.manaMax = 100;
    this.startMana = 0;
    this.atkCd = 0;
    this.moveCd = 0;
    this.stun = 0;
    this.shield = 0;
    this.star = 1;
    this.alive = true;
    this.target = null;
    this.haste = 1;
    this.hasteTimer = 0;
    this.slow = 0;
    this.slowTimer = 0;
    this.dodge = 0;
    this.dodgeUntil = 0;
    this.untargetUntil = 0;
    this.mods = {};
    this.revived = false;
    this.hitsTaken = 0;
    this.castCount = 0;
    this.dotDps = 0;
    this.dotTime = 0;
    this.dmgMult = 1;
    this.isClone = false;
    this.isSummon = false;   // 是否召唤物（召唤物不能再召唤）
    this.gen = 0;            // 召唤代数
    this.cloneKind = '';   // 'shikigami'（伏黑式神） / 'shadow'（影袭分身）
    this.rec = { dealt: 0, taken: 0, heal: 0 };   // 战后统计
    this.stateUntil = 0;   // 状态切换（蒸升 / 全开速 / 猩猩模式…）到期时间
    this.stateSpec = null;
    this.buffUntil = 0;
    this.linkIds = [];
    this.linkStacks = 0;
    this.lastAttacker = null;
    this.linkDoubleUsed = false;
    /* —— 批次 1 原语 —— */
    this.ult = 0;                 // 必杀槽当前值
    this.ultCost = 100;           // 必杀槽上限（由必杀值换算）
    this.ultSpec = null;          // 必杀技规格（def.ult）
    this.invulnUntil = 0;         // 无敌到什么时候
    this.reviveLeft = 0;          // 剩余复活次数
    this.counters = {};           // 通用计数器（黑闪/拔刀…）
    this.debuffCount = 0;         // 身上减益数量（给「弱体特攻」用）
    this.retired = false;
  }

  /* ======================================================== 模拟器 ===== */
  function BattleSim() {
    this.units = [];
    this.events = [];
    this.time = 0;
    this.overtime = false;
    this.over = false;
    this.winner = -1;
    this.traitTiers = [{}, {}];
    this.domainActive = [false, false];
    this.domainTime = [-1, -1];
    this.domainDone = [false, false];
    this.manaLock = [false, false];
    this.links = [[], []];
    this._nextId = 1;
  }

  BattleSim.prototype.setup = function (playerUnits, enemyUnits, playerTraits, enemyTraits) {
    this.traitTiers = [playerTraits || {}, enemyTraits || {}];
    var i;
    for (i = 0; i < playerUnits.length; i++) this._spawn(playerUnits[i], 0);
    for (i = 0; i < enemyUnits.length; i++) this._spawn(enemyUnits[i], 1);
    for (i = 0; i < this.units.length; i++) this._applyStartMods(this.units[i]);
    this._applyLinks();
    this.time = 0;
    this.over = false;
    this.winner = -1;
    this._announceTier4();
    return this;
  };

  /* 羁绊最高档（4 人档）生效时广播一次，供 UI 播放专属特效 */
  var TIER4_STYLE = {
    '夜':  { color: '#4fc06a', title: '夜 行 · 月 下 领 域', text: '夜行单位首次阵亡时以 35% 生命复活' },
    '影':  { color: '#2f5f9e', title: '影 袭 · 影 分 身',     text: '阵亡后留下 50% 属性的分身继续战斗' },
    '幻':  { color: '#e0483c', title: '幻 术 · 无 限 幻 境',   text: '全场敌人攻速 -25%，每秒流失 6 咒力' },
    '行':  { color: '#f0a020', title: '行 咒 · 行 动 自 如',   text: '施法后立刻追加一次普攻' },
    '体术': { color: '#ff8f3c', title: '体 术 · 无 下 限',    text: '黑闪必定连击两次' },
    '术式': { color: '#8f7cff', title: '术 式 · 解 放',       text: '每场战斗首次施法只需一半咒力' },
    '咒灵': { color: '#9b5cff', title: '咒 灵 · 咒 胎',       text: '咒灵首次阵亡时以 40% 生命复活' },
    '特级': { color: '#ffd166', title: '特 级 · 领 域 覆 盖',  text: '开战 8 秒后自动展开领域' },
    '东京校': { color: '#5bb8ff', title: '东 京 校 · 全 校 集 结', text: '全体友军全属性 +12%' },
    '京都校': { color: '#ff6b8a', title: '京 都 校 · 全 校 集 结', text: '京都校单位获得群体反击' }
  };

  BattleSim.prototype._announceTier4 = function () {
    var self = this;
    for (var t = 0; t < 2; t++) {
      var tiers = this.traitTiers[t] || {};
      for (var k in tiers) {
        if (!tiers.hasOwnProperty(k)) continue;
        var lv = tiers[k];
        // 四属性 / 咒灵 / 体术 / 术式 / 东京校 / 京都校 的最高档都是 3（对应 4 人）
        if (lv < 3) continue;
        var meta = TIER4_STYLE[k];
        if (!meta) continue;
        self._emit({
          t: 'tier4', team: t, trait: k,
          title: meta.title, text: meta.text, color: meta.color
        });
      }
    }
  };

  BattleSim.prototype._spawn = function (spec, team) {
    var u = new BattleUnit();
    u.id = this._nextId++;
    u.def = spec;
    u.team = team;
    u.pos = { x: spec.pos.x, y: spec.pos.y };
    u.star = Math.max(1, Math.min(3, spec.star || 1));
    var m = STAR_MULT[u.star];
    u.maxHp = (spec.hp || 600) * m;
    u.hp = u.maxHp;
    u.ad = (spec.ad || 45) * (1 + 0.7 * (m - 1));
    u.spell = (spec.spell || 50) * (1 + 0.7 * (m - 1));
    u.asRate = spec.as !== undefined ? spec.as : 0.8;
    u.atkRange = spec.range !== undefined ? spec.range : 1;
    u.manaMax = spec.mana !== undefined ? spec.mana : 100;
    u.startMana = spec.start_mana !== undefined ? spec.start_mana : 40;
    // 开场多给半管咒力：让第一次技能在 3~4 秒内就能放出来
    u.startMana = Math.min(Math.round(u.manaMax * 0.8), u.startMana + 25);
    u.mana = u.startMana;
    this.units.push(u);
    return u;
  };

  BattleSim.prototype._applyItem = function (u, itemId) {
    var it = JJK.data.itemById[itemId];
    if (!it) return;
    var st = it.stat || {};
    if (st.hp !== undefined) { u.maxHp += st.hp; u.hp = u.maxHp; }
    if (st.ad !== undefined) u.ad += st.ad;
    if (st.spell !== undefined) u.spell += st.spell;
    if (st.as !== undefined) u.asRate *= (1 + st.as);
    if (st.start_mana !== undefined) { u.startMana += st.start_mana; u.mana = u.startMana; }
    if (st.armor !== undefined) u.mods.armor = (u.mods.armor || 0) + st.armor / 100;
    if (st.mres !== undefined) u.mods.mres = (u.mods.mres || 0) + st.mres / 100;
    if (st.bf !== undefined) u.mods.bf = (u.mods.bf || 0) + st.bf;
    if (st.dodge !== undefined) { u.dodge = Math.max(u.dodge, st.dodge); u.dodgeUntil = 99; }
    if (st.counter !== undefined) u.counterMult = (u.counterMult || 1) * st.counter;
    if (st.regen !== undefined) u.mods.regen = true;
    if (st.revive !== undefined) { u.mods.reviveLeft = (u.mods.reviveLeft || 0) + 1; u.mods.revivePct = st.revive; }
    if (st.heal_ally !== undefined) u.mods.healAlly = st.heal_ally;
    if (st.stun_on_cast !== undefined) u.mods.stunOnCast = st.stun_on_cast;
    if (st.domain_plus !== undefined) u.mods.domain_plus = st.domain_plus;
  };

  /* ---------------------------------------------------- 开局修正 ------- */
  BattleSim.prototype._applyStartMods = function (u) {
    var t = u.team === 0 ? 0 : 1;
    var traits = u.def.traits || [];
    var items = u.def.items || [];
    var i;

    for (i = 0; i < items.length; i++) this._applyItem(u, items[i]);

    var self = this;

    /* —— 元素羁绊 —— */
    if (traits.indexOf('夜') >= 0 && self._tier(t, '夜') >= 1) {
      u.dodge = 0.22; u.dodgeUntil = 3.0;                       // 夜行 Lv1 夜之隐
    }
    if (traits.indexOf('影') >= 0 && self._tier(t, '影') >= 1) {
      u.untargetUntil = 2.5;                                     // 影袭 Lv1 影中潜行
    }
    if (traits.indexOf('幻') >= 0 && self._tier(t, '幻') >= 2) {
      u.mods.immune = 0.22;                                      // 幻术 Lv2 虚像
    }
    if (traits.indexOf('行') >= 0 && self._tier(t, '行') >= 1) {
      u.mods.move_fast = true;                                   // 行咒 Lv1 疾行
    }
    if (traits.indexOf('行') >= 0 && self._tier(t, '行') >= 3) {
      u.mods.extra_attack = true;                                // 行咒 Lv3 行动自如
    }

    /* —— 职业羁绊 —— */
    if (traits.indexOf('体术') >= 0 && self._tier(t, '体术') >= 1) {
      u.mods.bf = Math.max(u.mods.bf || 0, 0.20);                // 体术 Lv1 格斗
    }
    if (traits.indexOf('体术') >= 0 && self._tier(t, '体术') >= 2) {
      u.mods.bf = 0.35; u.mods.bf_haste = true;                  // 体术 Lv2
    }
    if (traits.indexOf('体术') >= 0 && self._tier(t, '体术') >= 3) {
      u.mods.bf_double = true;                                   // 体术 Lv3 无下限
    }
    if (traits.indexOf('术式') >= 0 && self._tier(t, '术式') >= 1) {
      u.mods.mana_after_cast = (u.mods.mana_after_cast || 0) + 15;   // 术式 Lv1 咒力循环
    }
    if (traits.indexOf('术式') >= 0 && self._tier(t, '术式') >= 2) {
      u.dmgMult *= 1.25; u.mods.skill_burn = 15;                 // 术式 Lv2 术式强化
    }
    if (traits.indexOf('术式') >= 0 && self._tier(t, '术式') >= 3) {
      u.mods.free_first = true; u.mods.double_first = true;      // 术式 Lv3 术式解放
    }
    if (traits.indexOf('咒灵') >= 0 && self._tier(t, '咒灵') >= 1) {
      u.mods.erode = 0.02;                                       // 咒灵 Lv1 咒力侵蚀
    }
    if (traits.indexOf('咒灵') >= 0 && self._tier(t, '咒灵') >= 2) {
      u.mods.death_aoe = 180;                                    // 咒灵 Lv2 怨念
    }
    if (traits.indexOf('咒灵') >= 0 && self._tier(t, '咒灵') >= 3) {
      u.mods.revive = 0.40;                                      // 咒灵 Lv3 咒胎
    }
    if (traits.indexOf('特级') >= 0 && self._tier(t, '特级') >= 1) {
      u.mods.domain = true;
      u.mods.domain_owner = true;
    }

    /* —— 阵营羁绊 —— */
    if (traits.indexOf('东京校') >= 0 && self._tier(t, '东京校') >= 1) {
      u.shield += u.maxHp * 0.15;                                // 东京校 Lv1 同窗
    }
    if (self._tier(t, '东京校') >= 3) {
      u.dmgMult *= 1.12; u.ad *= 1.12; u.maxHp *= 1.12; u.hp = u.maxHp;  // Lv3 全校集结
    }
    if (traits.indexOf('京都校') >= 0 && self._tier(t, '京都校') >= 1) {
      u.mods.thorns = 0.15;                                      // 京都校 Lv1 反制
    }
    if (traits.indexOf('京都校') >= 0 && self._tier(t, '京都校') >= 2) {
      u.mods.counter = true;                                     // 京都校 Lv2 反击术式
    }

    /* —— 棋子被动 —— */
    var p = u.def.passive || {};
    var pv = p.value !== undefined ? p.value : 0;
    switch (p.type) {
      case 'bf':
        u.mods.bf = Math.max(u.mods.bf || 0, pv || 0.15); break;
      case 'dodge':
        u.dodge = Math.max(u.dodge, pv || 0.1); u.dodgeUntil = 99; break;
      case 'taunt':
        u.mods.taunt = true; u.mods.armor = (u.mods.armor || 0) + 0.18; break;
      case 'mana_on_cast':
        u.mods.mana_after_cast = (u.mods.mana_after_cast || 0) + (pv || 10); break;
      case 'erode':
        u.mods.erode = Math.max(u.mods.erode || 0, pv || 0.02); break;
      case 'mana_steal':
        u.mods.burn_on_hit = pv || 10; break;
      case 'lifesteal':
        u.mods.lifesteal = pv || 0.15; break;
      case 'slow_on_hit':
        u.mods.slow_on_hit = pv || 0.15; break;
      case 'regen_aura':
        u.mods.regen = true; break;
      default: break;   // aura_haste / aura_power 在下面的队伍光环里统一处理
    }

    /* —— 队伍光环（队内任意一人提供，作用于全队） —— */
    for (i = 0; i < this.units.length; i++) {
      var x = this.units[i];
      if (x.team !== u.team) continue;
      var xp = x.def.passive || {};
      if (xp.type === 'aura_power') { var _ap = 1 + (xp.value || 0.1); u.ad *= _ap; u.spell *= _ap; }
      else if (xp.type === 'aura_haste') u.asRate *= 1 + (xp.value || 0.1);
    }

    /* —— 批次 1：把 def.mods 里的通用原语配置合并进来 —— */
    var _cm = u.def.mods || {};
    for (var _ck in _cm) if (_cm.hasOwnProperty(_ck)) u.mods[_ck] = _cm[_ck];
    // mods.dodge 是「常驻闪避」的写法，落到真正被判定的 u.dodge 上
    if (u.mods.dodge) { u.dodge = Math.max(u.dodge, u.mods.dodge); u.dodgeUntil = 99; }
    // 只有带 combat:true 的 ult 才是真正的必杀技；旧数据里的 ult 只是详情展示字段
    if (u.def.ult && u.def.ult.combat) u.ultSpec = u.def.ult;
    if (u.def.ultCost) u.ultCost = u.def.ultCost;
    if (u.mods.reviveLeft) u.reviveLeft = u.mods.reviveLeft;
    if (u.mods.invulnStart) u.invulnUntil = Math.max(u.invulnUntil, u.mods.invulnStart);
    if (u.mods.ultStart) u.ult = Math.min(u.ultCost, u.mods.ultStart);   // 开场必杀值

    /* —— 敌方羁绊带来的开场减益 —— */
    var enemyT = 1 - t;
    if (self._tier(enemyT, '幻') >= 3) {                          // 幻术 Lv3 无限幻境
      u.asRate *= 0.75;
      u.mods.mana_drain = 6;
    }
  };

  /* -------------------------------------------------- 异格联动 ------- */
  // 同一角色的不同异格同时在场上时触发的隐藏协同（data/links.json）
  BattleSim.prototype._applyLinks = function () {
    var defs = (JJK.data.links) || [];
    for (var t = 0; t < 2; t++) {
      var present = {};
      for (var i = 0; i < this.units.length; i++) {
        if (this.units[i].team === t) present[this.units[i].def.id] = true;
      }
      for (var d = 0; d < defs.length; d++) {
        var def = defs[d];
        var all = true;
        for (var m = 0; m < def.members.length; m++) {
          if (!present[def.members[m]]) { all = false; break; }
        }
        if (!all) continue;
        this.links[t].push(def);
        this._emit({ t: 'linkActive', id: def.id, name: def.name, team: t, color: def.color });
        for (var k = 0; k < this.units.length; k++) {
          var u = this.units[k];
          if (u.team !== t || def.members.indexOf(u.def.id) < 0) continue;
          u.linkIds.push(def.id);
          this._applyLinkMods(u, def);
        }
      }
    }
  };

  BattleSim.prototype._applyLinkMods = function (u, def) {
    switch (def.id) {
      case 'twin-curse':
        // 咒灵操术・双生：施法回蓝 + 技能小范围溅射
        u.mods.mana_after_cast = (u.mods.mana_after_cast || 0) + 25;
        u.mods.skill_splash = 0.45;
        break;
      case 'strongest-two':
        // 最强的两人：不可侵 4 秒 + 必中 + 首次双发
        u.untargetUntil = Math.max(u.untargetUntil, 4.0);
        u.mods.sure_hit = true;
        u.mods.link_double_cast = 0.6;
        break;
      case 'blade-stance':
        // 拔刀・纳刀：反击更强 + 计数加速
        u.counterMult = (u.counterMult || u.mods.counterMult || 0) + 0.5;
        u.mods.counter_bonus = 2;
        break;
      case 'crow-dance':
        // 黑鸟双舞：追击 + 攻速
        u.mods.extra_attack = true;
        u.asRate *= 1.2;
        break;
      case 'vessel-king':
        // 容器与诅咒之王：虎杖受击叠层，宿傩击杀回复，虎杖阵亡则宿傩充能
        if (u.def.id === '607988') u.mods.link_stack = true;
        if (u.def.id === '644233') u.mods.link_heal_on_kill = 0.25;
        break;
      default: break;
    }
  };

  BattleSim.prototype._tier = function (team, traitId) {
    return this.traitTiers[team][traitId] || 0;
  };

  /* ---------------------------------------------------- 查询 ----------- */
  BattleSim.prototype.aliveUnits = function (team) {
    var out = [];
    for (var i = 0; i < this.units.length; i++) {
      var u = this.units[i];
      if (u.alive && (team === undefined || team < 0 || u.team === team)) out.push(u);
    }
    return out;
  };

  BattleSim.prototype.survivors = function (team) {
    return this.aliveUnits(team).length;
  };

  BattleSim.prototype.drainEvents = function () {
    var e = this.events;
    this.events = [];
    return e;
  };

  BattleSim.prototype._emit = function (ev) { this.events.push(ev); };

  /* ---------------------------------------------------- 主循环 --------- */
  BattleSim.prototype.update = function (dt) {
    if (this.over) return;
    this.time += dt;

    if (this.time > OVERTIME_AT && !this.overtime) {
      this.overtime = true;
      this._emit({ t: 'overtime' });
    }
    if (this.overtime) {
      var ramp = U.clamp((this.time - OVERTIME_AT) / 15, 0, 1);
      var pct = 0.030 + 0.070 * ramp;
      for (var i = 0; i < this.units.length; i++) {
        var u = this.units[i];
        if (u.alive) this._rawDamage(u, u.maxHp * pct * dt);
      }
    }

    this._tickDomains(dt);
    this._tickSpecials(dt);

    for (var j = 0; j < this.units.length; j++) {
      var v = this.units[j];
      if (v.alive) this._act(v, dt);
    }
    this._checkEnd();
  };

  /* ---------------------------------------------------- 领域 ----------- */
  BattleSim.prototype._tickDomains = function (dt) {
    for (var t = 0; t < 2; t++) {
      if (this._tier(t, '特级') < 1) continue;
      if (this.domainTime[t] < 0 && !this.domainDone[t]) {
        var trigger = DOMAIN_TRIGGER;
        for (var i = 0; i < this.units.length; i++) {
          var u = this.units[i];
          if (u.team === t && u.alive && u.mods.domain_plus) trigger -= u.mods.domain_plus;
        }
        if (this.time >= Math.max(2, trigger)) {
          this.domainDone[t] = true;
          this.domainTime[t] = 0;
          this.domainActive[t] = true;
          this._emit({ t: 'domain', team: t, name: '領域展開' });
          for (var k = 0; k < this.units.length; k++) {
            var a = this.units[k];
            if (a.team === t && a.alive) {
              a.ad *= 1.22; a.spell *= 1.22; a.maxHp *= 1.22; a.hp *= 1.22;
              a.mods.sure_hit = true;
              a.mods.domain_buffed = true;
            }
          }
          if (this._tier(t, '特级') >= 2) this.manaLock[1 - t] = true;   // Lv2 领域覆盖
        }
      } else if (this.domainTime[t] >= 0) {
        this.domainTime[t] += dt;
        if (this.domainTime[t] > DOMAIN_DURATION) {
          this.domainTime[t] = -1;
          this.domainActive[t] = false;
          this.manaLock[1 - t] = false;
          for (var m = 0; m < this.units.length; m++) {
            var b = this.units[m];
            if (b.mods.domain_buffed) {
              b.ad /= 1.22; b.spell /= 1.22; b.maxHp /= 1.22;
              b.hp = Math.min(b.hp / 1.22, b.maxHp);
              delete b.mods.sure_hit;
              delete b.mods.domain_buffed;
            }
          }
          this._emit({ t: 'domainEnd', team: t });
        }
      }
    }
  };

  /* ---------------------------------------------------- 单位行为 ------- */
  BattleSim.prototype._act = function (u, dt) {
    // 领域/技能带来的临时增伤到期回退
    if (u.mods.dmg_amp_until && this.time > u.mods.dmg_amp_until) {
      var _amp = u.mods.dmg_amp_amt || 0.25;
      u.ad /= 1 + _amp; u.spell /= 1 + _amp;
      delete u.mods.dmg_amp_until;
      delete u.mods.dmg_amp_amt;
    }
    // 强化（夜蛾正道）：6 秒后回退 —— 原版忘记回退，属实现 bug，这里修正
    if (u.buffUntil && this.time > u.buffUntil) {
      u.ad /= 1.25; u.buffUntil = 0;
    }
    if (u.stun > 0) { u.stun -= dt; return; }

    if (u.dotTime > 0) {
      u.dotTime -= dt;
      this._rawDamage(u, u.dotDps * dt * (1 - (u.mods.dotResist || 0)));
      if (!u.alive) return;
    }
    if (u.hasteTimer > 0) {
      u.hasteTimer -= dt;
      if (u.hasteTimer <= 0) u.haste = 1;
    }
    if (u.slowTimer > 0) {
      u.slowTimer -= dt;
      if (u.slowTimer <= 0) u.slow = 0;
    }
    if (u.mods.regen && u.hp < u.maxHp) {
      u.hp = Math.min(u.maxHp, u.hp + u.maxHp * 0.02 * dt);
    }
    if (u.mods.mana_drain) {
      u.mana = Math.max(0, u.mana - u.mods.mana_drain * dt);
    }

    if (!u.target || !u.target.alive || !this._targetable(u.target)) {
      u.target = this._acquire(u);
    }
    if (!u.target) return;

    // 必杀槽满 → 优先放必杀（不消耗法力）
    if (u.ultSpec && u.ult >= u.ultCost) { this._castUlt(u); return; }

    var d = dist(u.pos, u.target.pos);
    if (d <= u.atkRange) {
      u.atkCd -= dt;
      if (u.atkCd <= 0) {
        var spd = u.asRate * u.haste * (1 - u.slow);
        u.atkCd = 1 / Math.max(0.15, spd);
        this._attack(u, u.target);
      }
    } else {
      u.moveCd -= dt;
      if (u.moveCd <= 0) {
        u.moveCd = u.mods.move_fast ? 0.35 : 0.5;
        this._stepToward(u);
      }
    }
  };

  BattleSim.prototype._targetable = function (u) {
    if (!u.alive) return false;
    if (u.untargetUntil > this.time) return false;
    return true;
  };

  BattleSim.prototype._acquire = function (u) {
    var best = null, bestD = 999;
    for (var i = 0; i < this.units.length; i++) {
      var e = this.units[i];
      if (e.team === u.team || !e.alive) continue;
      if (!this._targetable(e)) continue;
      var d = dist(u.pos, e.pos);
      if (e.mods.taunt) d -= 1;      // 守护：优先被选
      if (d < bestD) { bestD = d; best = e; }
    }
    return best;
  };

  BattleSim.prototype._occupied = function (p, except) {
    for (var i = 0; i < this.units.length; i++) {
      var u = this.units[i];
      if (u.alive && u !== except && u.pos.x === p.x && u.pos.y === p.y) return true;
    }
    return false;
  };

  BattleSim.prototype._inBounds = function (p) {
    return p.x >= 0 && p.y >= 0 && p.x < GRID_W && p.y < GRID_H;
  };

  BattleSim.prototype._canMove = function (u, p) {
    if (!this._inBounds(p)) return false;
    if (this._occupied(p, u)) return false;
    return true;
  };

  BattleSim.prototype._stepToward = function (u) {
    var dx = 0, dy = 0;
    var d = { x: u.target.pos.x - u.pos.x, y: u.target.pos.y - u.pos.y };
    if (Math.abs(d.x) >= Math.abs(d.y)) {
      dx = U.sign(d.x);
      if (!this._canMove(u, { x: u.pos.x + dx, y: u.pos.y })) {
        dy = d.y !== 0 ? U.sign(d.y) : 1;
      }
    } else {
      dy = U.sign(d.y);
      if (!this._canMove(u, { x: u.pos.x, y: u.pos.y + dy })) {
        dx = d.x !== 0 ? U.sign(d.x) : 1;
      }
    }
    var np = { x: u.pos.x + dx, y: u.pos.y + dy };
    if (this._canMove(u, np)) { u.pos = np; return; }
    var cands = [{ x: 0, y: 1 }, { x: 0, y: -1 }, { x: 1, y: 0 }, { x: -1, y: 0 }];
    for (var i = 0; i < cands.length; i++) {
      var c = { x: u.pos.x + cands[i].x, y: u.pos.y + cands[i].y };
      if (this._canMove(u, c)) { u.pos = c; return; }
    }
  };

  /* ---------------------------------------------------- 普攻 ----------- */
  BattleSim.prototype._attack = function (src, dst) {
    var dmg = src.ad;
    var bfChance = src.mods.bf || 0;
    var blackFlash = false;

    this._emit({ t: 'attack', from: { x: src.pos.x, y: src.pos.y }, to: { x: dst.pos.x, y: dst.pos.y }, team: src.team, srcId: src.id });
    this._gainUlt(src, 5);          // 普攻积累必杀槽
    if (src.mods.bf_count_key) this.addCounter(src, src.mods.bf_count_key, 1);   // 攻击计数 +1

    // 黑闪计数：满阈值时本次攻击必定黑闪（虎杖「苍穹扣杀」）
    if (src.mods.bf_count_key && src.counters[src.mods.bf_count_key] >= (src.mods.bf_count_need || 5)) {
      src.counters[src.mods.bf_count_key] = 0;
      blackFlash = true;
      dmg *= (src.mods.bf_count_mult || 2.0);
      this._emit({ t: 'bf', pos: { x: dst.pos.x, y: dst.pos.y }, team: src.team, byCount: true });
    }

    if (bfChance > 0 && Math.random() < bfChance) {
      blackFlash = true;
      dmg *= 2.0;
      this._emit({ t: 'bf', pos: { x: dst.pos.x, y: dst.pos.y }, team: src.team });
      if (src.mods.bf_haste) { src.haste = 1.3; src.hasteTimer = 3.0; }
    }
    // 影袭 Lv2 背刺
    if (this._tier(src.team, '影') >= 2 && dst.hp < dst.maxHp * 0.4) {
      dmg *= 1.35;
      dst.mana = Math.max(0, dst.mana - 10);
    }
    // 夜行 Lv2 攻击附加侵蚀
    if (this._tier(src.team, '夜') >= 2 && (src.def.traits || []).indexOf('夜') >= 0) {
      dst.dotDps = Math.max(dst.dotDps, dst.maxHp * 0.02);
      dst.dotTime = Math.max(dst.dotTime, 4.0);
    }

    this._deal(src, dst, dmg, false);

    // 联动「容器与诅咒之王」：虎杖每被攻击一次叠一层宿傩之指（+5% 攻击，上限 8 层）
    if (dst.mods.link_stack && dst.alive && dst.linkStacks < 8) {
      dst.linkStacks += 1;
      dst.ad *= 1.05;
      this._emit({ t: 'linkStack', pos: { x: dst.pos.x, y: dst.pos.y }, team: dst.team, stacks: dst.linkStacks });
    }

    if (blackFlash && src.alive) {
      var _moc = src.mods.manaOnCrit || 0;
      if (_moc > 0) {
        src.mana = Math.min(src.manaMax, src.mana + _moc);
        this._emit({ t: 'manaGain', pos: { x: src.pos.x, y: src.pos.y }, team: src.team, amount: _moc, unitId: src.id });
      }
    }
    if (blackFlash && src.mods.bf_double && dst.alive) {
      this._deal(src, dst, dmg * 0.6, false);
    }

    // 反击：被近战攻击时反打（三轮霞「反击拔刀」/ 五条「无下限」）
    if (dst.alive && src.alive && (dst.mods.counterMult || 0) > 0 && dist(src.pos, dst.pos) <= 1.5) {
      this._deal(dst, src, dst.ad * dst.mods.counterMult, false);
      this._emit({ t: 'counter', from: { x: dst.pos.x, y: dst.pos.y }, to: { x: src.pos.x, y: src.pos.y }, team: dst.team });
      if (dst.mods.counter_counter) this.addCounter(dst, dst.mods.counter_counter, dst.mods.counter_bonus || 1);
    }

    var burn = src.mods.burn_on_hit || 0;
    if (burn > 0 && dst.alive) dst.mana = Math.max(0, dst.mana - burn);

    var slowv = src.mods.slow_on_hit || 0;
    if (slowv > 0 && dst.alive && !dst.mods.immuneControl) { dst.slow = Math.max(dst.slow, slowv); dst.slowTimer = 2.0; }

    var erode = src.mods.erode || 0;
    if (erode > 0 && dst.alive) {
      dst.dotDps = Math.max(dst.dotDps, dst.maxHp * erode);
      dst.dotTime = Math.max(dst.dotTime, 4.0);
    }

    // 攻击回蓝
    if (!this.manaLock[src.team] && this.time >= (src.manaLockedUntil || 0)) {
      src.mana = Math.min(src.manaMax, src.mana + 18);
    }

    if (dst.alive) {
      dst.hitsTaken += 1;
      if (dst.mods.thorns) this._deal(dst, src, dmg * dst.mods.thorns, false);
      if (dst.mods.counter && dst.hitsTaken % 3 === 0) {
        for (var i = 0; i < this.units.length; i++) {
          var e = this.units[i];
          if (e.alive && e.team !== dst.team && dist(e.pos, dst.pos) <= 1) {
            this._deal(dst, e, dst.ad * 0.8, false);
          }
        }
      }
    }

    var need = src.manaMax;
    if (src.mods.free_first && src.castCount === 0) need = src.manaMax * 0.5;
    if (src.mana >= need && src.alive) this._cast(src);
  };

  /* ---------------------------------------------------- 技能 ----------- */
  // overrideSkill：必杀技复用同一套机制（12 种），只是数值与标记不同
  BattleSim.prototype._cast = function (u, overrideSkill, isUlt) {
    // 状态切换：处于状态时，技能会被替换成「变化后」的版本（原作大量角色是这样）
    var _stateActive = u.stateUntil && this.time < u.stateUntil && u.stateSpec;
    if (!isUlt && _stateActive && u.stateSpec.skill) {
      this._emit({ t: 'stateSkill', pos: { x: u.pos.x, y: u.pos.y }, team: u.team, name: u.stateSpec.name });
      overrideSkill = u.stateSpec.skill;
    }
    // 交替技能：上一次放的是 A，这次换 B
    var _altNow = u._pendingAlt;
    u._pendingAlt = null;
    var sk = _altNow || overrideSkill || u.def.skill || {};
    if (!sk.type) { if (!isUlt) u.mana = 0; return; }

    if (!isUlt) {
      u.mana = 0;
      u.castCount += 1;
      this._gainUlt(u, 8);         // 施法积累必杀槽
    }
    var target = u.target;
    if (!target || !target.alive) target = this._acquire(u);

    this._emit({
      t: isUlt ? 'ultCast' : 'cast', pos: { x: u.pos.x, y: u.pos.y }, team: u.team,
      name: sk.name || (isUlt ? '必杀' : '技能'), skillType: sk.type, srcId: u.id
    });

    // 即死（真人）：对「当前血量」先判定，低于阈值直接处决（原作语义）
    if (sk.execute && target && target.alive && !target.def.boss &&
        target.hp <= target.maxHp * sk.execute) {
      this._emit({ t: 'execute', pos: { x: target.pos.x, y: target.pos.y }, team: target.team });
      this._kill(target);
    }

    var stype = sk.type;
    var power = sk.power !== undefined ? sk.power : 1.5;
    if (!isUlt && u.def.ult && u.star >= 2) power *= 1.6;   // 原版「有 ult 的棋子 2 星强化」（必杀自身不再叠加）

    /* ---- 三面板结算 ----------------------------------------------------
     * 体术技能 → 吃【体术面板】ad，受【护甲】减免
     * 术式技能 → 吃【术式面板】spell，受【魔抗】减免
     * 复合伤害 → 两者均值，护甲与魔抗各吃一半（对应原作「无视术体减伤」）
     * 判定优先级：技能自带 panel > hybrid 标记 > 角色伤害类型
     * ------------------------------------------------------------------ */
    var panel = sk.panel;
    if (!panel) {
      if (sk.hybrid) panel = 'hybrid';
      else panel = (u.def.dmg === '体术') ? 'phys' : 'magic';
    }
    var baseStat = panel === 'phys' ? u.ad
                 : panel === 'hybrid' ? (u.ad + u.spell) * 0.5
                 : u.spell;
    var dmg = baseStat * power * u.dmgMult;
    // 必定暴击（宿傩「开」）
    if (sk.crit) dmg *= sk.crit;

    // 破韧：上一次技能留存的「下一次技能伤害 +X%」（发动后解除）
    if (u.mods.nextCastAmp) {
      dmg *= 1 + u.mods.nextCastAmp;
      u.mods.nextCastAmp = 0;
      this._emit({ t: 'armConsumed', pos: { x: u.pos.x, y: u.pos.y }, team: u.team });
    }
    u._panel = panel;               // 供 _deal 选择护甲/魔抗
    var _sureSaved = !!u.mods.sure_hit;
    if (sk.sure) u.mods.sure_hit = true;    // 必中（本技能期间生效）
    // 弱体特攻（钉崎 / 狗卷）：目标身上减益越多，倍率越高
    if (sk.debuffBonus && target) {
      dmg *= 1 + Math.min(sk.debuffMax || 5, this._debuffsOn(target)) * sk.debuffBonus;
    }
    var i, e;

    switch (stype) {
      case 'strike':
        if (target) this._deal(u, target, dmg, true);
        break;

      case 'slam':
        if (target) {
          var _rad = sk.radius === undefined ? 1 : sk.radius;   // 99 = 敌方全体
          for (i = 0; i < this.units.length; i++) {
            e = this.units[i];
            if (e.alive && e.team !== u.team && (_rad >= 99 || dist(e.pos, target.pos) <= _rad)) {
              this._deal(u, e, dmg, true);
            }
          }
        }
        break;

      case 'barrage':
        // hits：段数（默认 3）；sameTarget：是否锁同一目标（虎杖三段拳 / 宿傩连击）
        var _hits = sk.hits || 3;
        for (i = 0; i < _hits; i++) {
          var t2 = (sk.sameTarget && target && target.alive) ? target : this._randomEnemy(u);
          if (!t2) continue;
          var _m = (sk.lastHitBf && i === _hits - 1) ? 2.0 : 1;   // 末段必黑闪
          this._deal(u, t2, dmg * _m, true);
          if (sk.lastHitBf && i === _hits - 1) {
            this._emit({ t: 'bf', pos: { x: t2.pos.x, y: t2.pos.y }, team: u.team, byLastHit: true });
          }
        }
        break;

      case 'beam':
        if (target) {
          var dir = U.sign(target.pos.x - u.pos.x);
          if (dir === 0) dir = u.team === 0 ? 1 : -1;
          var hit = [];
          for (i = 0; i < this.units.length; i++) {
            e = this.units[i];
            if (e.alive && e.team !== u.team && U.sign(e.pos.x - u.pos.x) === dir && e.pos.y === target.pos.y) hit.push(e);
          }
          if (!hit.length && target) hit = [target];
          for (i = 0; i < hit.length; i++) this._deal(u, hit[i], dmg, true);
        }
        break;

      case 'dot':
        if (target) {
          this._deal(u, target, dmg * 0.6, true);
          target.dotDps = Math.max(target.dotDps, target.maxHp * 0.04);
          target.dotTime = Math.max(target.dotTime, 5.0);
        }
        break;

      case 'drain':
        if (target) {
          this._deal(u, target, dmg, true);
          if (!target.mods.immuneControl) target.mana = Math.max(0, target.mana - 20);
        }
        break;

      case 'stun':
        if (target) {
          this._deal(u, target, dmg, true);
          if (!target.mods.immuneControl) target.stun = Math.max(target.stun, 1.5);
          else this._emit({ t: 'controlImmune', pos: { x: target.pos.x, y: target.pos.y }, team: target.team });
        }
        break;

      case 'empower':
        // 自身增伤 amp（0.6 = +60%），持续 dur 秒；可叠加刷新持续时间
        var _eamp = sk.amp === undefined ? 0.6 : sk.amp;
        var _edur = sk.dur === undefined ? 3.5 : sk.dur;
        if (u.mods.dmg_amp_until && this.time <= u.mods.dmg_amp_until) {
          u.mods.dmg_amp_until = Math.max(u.mods.dmg_amp_until, this.time + _edur);
        } else {
          u.ad *= 1 + _eamp; u.spell *= 1 + _eamp;
          u.mods.dmg_amp_until = this.time + _edur;
          u.mods.dmg_amp_amt = _eamp;
        }
        this._emit({ t: 'empower', pos: { x: u.pos.x, y: u.pos.y }, team: u.team, amp: _eamp });
        break;

      case 'heal':
        var ally = this._lowestAlly(u);
        if (ally) {
          // 必杀的治疗量自动比技能高一档（否则必杀就成了技能的下位替代）
          var amt = ally.maxHp * (sk.healPct || (isUlt ? 0.45 : 0.25));
          ally.hp = Math.min(ally.maxHp, ally.hp + amt);
        if (u.rec) u.rec.heal += amt;
        if (ally.rec) ally.rec.heal = ally.rec.heal;   // 目标不计，只记施法者
          this._emit({ t: 'heal', pos: { x: ally.pos.x, y: ally.pos.y }, amount: Math.round(amt), targetId: ally.id });
        }
        break;

      case 'shield':
        for (i = 0; i < this.units.length; i++) {
          var a = this.units[i];
          if (a.alive && a.team === u.team && dist(a.pos, u.pos) <= 1) {
            a.shield += a.maxHp * (sk.shieldPct || (isUlt ? 0.35 : 0.2));
            this._emit({ t: 'shield', pos: { x: a.pos.x, y: a.pos.y }, targetId: a.id });
          }
        }
        break;

      case 'buff':
        for (i = 0; i < this.units.length; i++) {
          var b = this.units[i];
          if (b.alive && b.team === u.team) {
            if (!b.buffUntil || this.time >= b.buffUntil) b.ad *= 1.25;
            b.buffUntil = this.time + 6.0;          // 修正：原版没有回退
            this._emit({ t: 'buff', pos: { x: b.pos.x, y: b.pos.y }, targetId: b.id });
          }
        }
        break;

      case 'domain':
        for (i = 0; i < this.units.length; i++) {
          e = this.units[i];
          if (e.alive && e.team !== u.team) this._deal(u, e, dmg * 0.5, true);
        }
        if (!u.mods.dmg_amp_until) {
          u.ad *= 1.25; u.spell *= 1.25;
          u.mods.dmg_amp_until = this.time + 8.0;    // 领域：自身增伤 8 秒且必中
        }
        u.mods.sure_hit = true;
        this._emit({ t: 'skillDomain', pos: { x: u.pos.x, y: u.pos.y }, team: u.team });
        break;

      case 'summon':
        if (target) {
          this._deal(u, target, dmg, true);
          this._summonFamiliar(u);
        }
        break;

      default:
        if (target) this._deal(u, target, dmg, true);
        break;
    }

    // 技能带 enterState：施放后进入一个持续状态，状态期间技能变招
    if (!isUlt && sk.enterState && u.alive) {
      var es = sk.enterState;
      var wasIn = u.stateUntil && this.time < u.stateUntil;
      u.stateSpec = es;
      u.stateUntil = this.time + (es.dur || 4);
      if (es.amp) { var _sa = 1 + es.amp; u.ad *= _sa; u.spell *= _sa; }
      if (es.guard) u.mods.armor = (u.mods.armor || 0) + es.guard;
      if (es.bf) u.mods.bf = Math.min(0.75, (u.mods.bf || 0) + es.bf);
      this._emit({ t: 'stateOn', pos: { x: u.pos.x, y: u.pos.y }, team: u.team,
                   name: es.name, dur: es.dur || 4, again: !!wasIn });
    }

    // 双技能交替（宿傩「解 / 捌」）：每放一次技能，下次换成另一套
    if (!isUlt && sk.altSkill && !overrideSkill) {
      u.altFlip = !u.altFlip;
      if (u.altFlip) {
        u._pendingAlt = sk.altSkill;
        this._emit({ t: 'altSkill', pos: { x: u.pos.x, y: u.pos.y }, team: u.team,
                     name: sk.altSkill.name });
      }
    }
    // 叠层引爆（里梅「冻结」）：层数攒满就炸
    if (!isUlt && sk.stackOnCast && u.alive) {
      var so = sk.stackOnCast;
      var key = so.key || 'stack';
      u.mods[key] = (u.mods[key] || 0) + 1;
      var cur = u.mods[key];
      this._emit({ t: 'stack', pos: { x: u.pos.x, y: u.pos.y }, team: u.team,
                   key: key, count: cur, max: so.max });
      if (cur >= (so.max || 3)) {
        u.mods[key] = 0;
        for (var _si = 0; _si < this.units.length; _si++) {
          var _sx = this.units[_si];
          if (_sx.alive && _sx.team !== u.team) {
            this._deal(u, _sx, (u.ad + u.spell) * 0.5 * (so.burst || 1.6), true);
            if (so.taken) _sx.mods.dmg_taken = (_sx.mods.dmg_taken || 0) + so.taken;
          }
        }
        this._emit({ t: 'stackBurst', pos: { x: u.pos.x, y: u.pos.y }, team: u.team, key: key });
      }
    }

    // 领域展开期间放技能：原作里宿傩/陀艮的领域是「每次技能都对全场再打一轮」
    if (u.domainUntil && this.time < u.domainUntil && u.domainSpec && !isUlt) {
      var dsp = u.domainSpec;
      if (dsp.skillAoe) {
        var pool = [];
        for (var _di = 0; _di < this.units.length; _di++) {
          var _e = this.units[_di];
          if (_e.alive && _e.team !== u.team) pool.push(_e);
        }
        for (var _dj = 0; _dj < pool.length; _dj++) {
          var _t = pool[_dj];
          // 领域追加伤害：按双面板均值 × 领域系数，独立于技能本身倍率
          var _dmg = (u.ad + u.spell) * 0.5 * dsp.skillAoe;
          this._deal(u, _t, _dmg, true);
        }
        this._emit({ t: 'domainHit', pos: { x: u.pos.x, y: u.pos.y }, team: u.team, name: u.domainName });
      }
      if (dsp.skillMana) {
        u.mana = Math.min(u.manaMax || 100, u.mana + dsp.skillMana);
        this._emit({ t: 'mana', pos: { x: u.pos.x, y: u.pos.y }, team: u.team, amount: dsp.skillMana });
      }
    }

    // 术式 Lv2：削减目标咒力
    if (u.mods.skill_burn && target && target.alive) {
      target.mana = Math.max(0, target.mana - u.mods.skill_burn);
    }
    // 术式 Lv3：首次施法后回一半咒力
    if (u.mods.double_first && u.castCount === 1) u.mana = u.manaMax * 0.5;
    // 施法后回咒力
    var back = u.mods.mana_after_cast || 0;
    if (back > 0) u.mana = Math.min(u.manaMax, u.mana + back);
    // 东京校 Lv2：同校友军跟着回蓝
    if (this._tier(u.team, '东京校') >= 2 && (u.def.traits || []).indexOf('东京校') >= 0) {
      for (i = 0; i < this.units.length; i++) {
        var fr = this.units[i];
        if (fr.alive && fr.team === u.team && fr !== u && (fr.def.traits || []).indexOf('东京校') >= 0) {
          fr.mana = Math.min(fr.manaMax, fr.mana + 12);
        }
      }
    }
    // 联动「咒灵操术・双生」：技能命中后对目标周围 1 格溅射
    if (u.mods.skill_splash && target && target.alive) {
      for (i = 0; i < this.units.length; i++) {
        e = this.units[i];
        if (e.alive && e.team !== u.team && e !== target && dist(e.pos, target.pos) <= 1) {
          this._deal(u, e, dmg * u.mods.skill_splash, true);
        }
      }
    }

    u._panel = null;
    if (sk.sure && !_sureSaved) u.mods.sure_hit = false;

    // 破韧：本技能结束后挂上「下一次技能 +armNext」
    if (sk.armNext) u.mods.nextCastAmp = sk.armNext;

    // 命中附加效果（眩晕 / 持续伤害 / 易伤），对"本次技能打到的第一个敌人"生效
    var _hit = (target && target.alive) ? target : null;
    if (_hit) {
      if (sk.stun) {
        if (!_hit.mods.immuneControl) _hit.stun = Math.max(_hit.stun, sk.stun);
        else this._emit({ t: 'controlImmune', pos: { x: _hit.pos.x, y: _hit.pos.y }, team: _hit.team });
      }
      // 咒具·獄門疆：每次施法都附带短眩晕
      if (u.mods.stunOnCast && !_hit.mods.immuneControl) {
        _hit.stun = Math.max(_hit.stun, u.mods.stunOnCast);
      }
      if (sk.dot) {
        _hit.dotDps = Math.max(_hit.dotDps, _hit.maxHp * sk.dot);
        _hit.dotTime = Math.max(_hit.dotTime, sk.dotDur || 5);
      }
      if (sk.applyTaken) {
        _hit.mods.dmg_taken = (_hit.mods.dmg_taken || 0) + sk.applyTaken;
      }
      // 削弱（花御「诅咒的种子」）：降低敌方造成的伤害
      if (sk.applyWeaken) {
        _hit.mods.dmg_out = Math.min(0.9, (_hit.mods.dmg_out || 0) + sk.applyWeaken);
      }
      // 即死（真人「变形攻击」）：目标血量低于阈值直接处决，对强敌无效
      if (sk.execute && _hit.alive && !_hit.def.boss && _hit.hp <= _hit.maxHp * sk.execute) {
        this._emit({ t: 'execute', pos: { x: _hit.pos.x, y: _hit.pos.y }, team: _hit.team });
        this._kill(_hit);
      }
    }
    // 嘲讽（熊猫）：自身短时间成为优先目标 + 减伤
    if (sk.taunt) {
      u.mods.taunt = true;
      u.mods.guardAmt = sk.guard || 0.5;
      u.mods.guardUntil = this.time + sk.taunt;
      this._emit({ t: 'taunt', pos: { x: u.pos.x, y: u.pos.y }, team: u.team, dur: sk.taunt });
    }

    // 行咒 Lv3：施法后追加一次普攻
    if (u.mods.extra_attack && target && target.alive) this._deal(u, target, u.ad * 0.6, false);

    // 联动「最强的两人」：每场第一次施法后立刻再放一次（60% 威力）
    if (u.mods.link_double_cast && !u.linkDoubleUsed && u.alive) {
      u.linkDoubleUsed = true;
      var savedSpell = u.spell;
      u.spell *= u.mods.link_double_cast;
      this._emit({ t: 'linkCast', id: 'strongest-two', pos: { x: u.pos.x, y: u.pos.y }, team: u.team });
      this._cast(u);                 // 递归一次；linkDoubleUsed 已置位，不会无限递归
      u.spell = savedSpell;
    }
  };

  /* ---------------------------------------------------- 属性克制 --- */
  // 四属性首尾相衔（仿五行）：行克幻 · 幻克夜 · 夜克影 · 影克行
  var ELEM_COUNTER = { '行': '幻', '幻': '夜', '夜': '影', '影': '行' };
  var ELEM_BONUS = 0.20;
  var ELEM_PENALTY = 0.10;

  // 返回攻击方对防守方的伤害倍率
  BattleSim.prototype._elemMult = function (src, dst) {
    if (!src || !dst || !src.def || !dst.def) return 1;
    var a = src.def.element, b = dst.def.element;
    if (!a || !b) return 1;
    var base = 1;
    if (ELEM_COUNTER[a] === b) base = 1 + ELEM_BONUS + (src.mods.elemHunter || 0);
    else if (ELEM_COUNTER[b] === a) base = 1 - ELEM_PENALTY;
    return base;
  };

  /* ---------------------------------------------------- 批次 1 原语 --- */

  // 必杀槽累积（普攻 +7 / 受击 +5 / 施法 +10 / 击杀 +15，见调用点）
  BattleSim.prototype._gainUlt = function (u, amount) {
    if (!u || !u.alive || !u.ultSpec) return;
    // 领域压制：必杀槽上升无效
    if (u.mods.ultBlockUntil && this.time < u.mods.ultBlockUntil) return;
    var rate = u.mods.ult_rate || 1;
    u.ult = Math.min(u.ultCost, u.ult + amount * rate);
    if (!u.ultFullEmitted && u.ult >= u.ultCost) {
      u.ultFullEmitted = true;
      this._emit({ t: 'ultReady', pos: { x: u.pos.x, y: u.pos.y }, team: u.team, unitId: u.id });
    } else if (u.ult < u.ultCost) {
      u.ultFullEmitted = false;
    }
  };

  // 通用计数器（黑闪计数 / 拔刀计数…）
  BattleSim.prototype.addCounter = function (u, key, n) {
    if (!u || !u.alive) return 0;
    var before = u.counters[key] || 0;
    u.counters[key] = before + (n === undefined ? 1 : n);
    var max = (u.mods['max_' + key]) || 0;
    if (max > 0) u.counters[key] = Math.min(max, u.counters[key]);
    // 计数成长（三轮霞「拔刀计数」每层 +3% 攻击）
    var grow = u.mods['grow_' + key];
    if (grow && u.counters[key] > before) {
      var steps = u.counters[key] - before;
      for (var _g = 0; _g < steps; _g++) u.ad *= 1 + grow;
    }
    return u.counters[key];
  };
  BattleSim.prototype.getCounter = function (u, key) {
    return (u && u.counters[key]) || 0;
  };

  // 目标身上当前生效的减益数量（给「弱体特攻」用）
  // 不额外维护计数，直接读实时状态，避免挂载/清理漏掉导致数值漂移
  BattleSim.prototype._debuffsOn = function (u) {
    if (!u) return 0;
    var n = 0;
    if (u.dotTime > 0) n++;                                  // 持续伤害
    if (u.stun > 0) n++;                                     // 眩晕
    if (u.slow > 0) n++;                                     // 减速
    if (u.mods && u.mods.armor_broken) n++;                  // 破甲
    if (u.mods && u.mods.dmg_taken > 0) n++;                 // 易伤
    return n;
  };

  // 释放必杀
  BattleSim.prototype._castUlt = function (u) {
    var spec = u.ultSpec;
    // 计数放大必杀（钉崎：钉子越多必杀越痛）
    if (spec && spec.scaleByCounter) {
      var _sc = u.mods[spec.scaleByCounter.key] || 0;
      var _k = 1 + Math.min(spec.scaleByCounter.max || 8, _sc) * (spec.scaleByCounter.per || 0.12);
      spec = Object.assign({}, spec, { power: (spec.power || 1) * _k });
    }
    if (!spec) return;
    u.ult = 0;
    u.ultFullEmitted = false;
    this._emit({ t: 'ult', pos: { x: u.pos.x, y: u.pos.y }, team: u.team, unitId: u.id, defId: u.def.id, unitName: u.def.name, name: spec.name || '必杀' });
    this._cast(u, spec, true);
    // 必杀代价②：领域结束后咒力归零并禁咒（五条「无下限的内侧」）
    var mp = u.mods.ultManaPenalty;
    if (mp) {
      u.mana = 0;
      u.manaLockedUntil = this.time + (mp.lock || 2);
      this._emit({ t: 'manaLock', pos: { x: u.pos.x, y: u.pos.y }, team: u.team, dur: mp.lock || 2 });
    }
    // 领域展开：原作里这是一个「持续状态」——期内自己必中/减伤、敌方被压制，
    // 而且每次放技能都会触发全场攻击（宿傩/陀艮的招牌），结束后咒力归零。
    if (spec.domain && u.alive) {
      var dm = spec.domain;
      var _i, _x;
      u.domainUntil = this.time + (dm.dur || 6);
      u.domainSpec = dm;
      u.domainName = spec.name;
      // 开域同时灌满一半咒力：否则咒力归零后 6 秒内根本放不出技能，
      // 「领域内每次技能追加全场攻击」这条就永远触发不了
      u.mana = Math.max(u.mana, (u.manaMax || 100) * 0.55);
      for (_i = 0; _i < this.units.length; _i++) {
        _x = this.units[_i];
        if (!_x.alive) continue;
        if (_x.team === u.team) {
          if (dm.allyAmp) { _x.ad *= 1 + dm.allyAmp; _x.spell *= 1 + dm.allyAmp; }
          if (dm.allyGuard) _x.mods.armor = (_x.mods.armor || 0) + dm.allyGuard;
        } else {
          if (dm.enemyTaken) _x.mods.dmg_taken = (_x.mods.dmg_taken || 0) + dm.enemyTaken;
          if (dm.enemyWeaken) _x.mods.dmg_out = Math.min(0.9, (_x.mods.dmg_out || 0) + dm.enemyWeaken);
          if (dm.enemyStun && !_x.mods.immuneControl) _x.stun = Math.max(_x.stun, dm.enemyStun);
          // 必杀槽上升无效：领域内敌人攒不出必杀
          if (dm.ultBlock) _x.mods.ultBlockUntil = this.time + (dm.dur || 6);
          if (dm.enemyDot) {
            _x.dotDps = Math.max(_x.dotDps, _x.maxHp * dm.enemyDot);
            _x.dotTime = Math.max(_x.dotTime, dm.dur || 6);
          }
          if (dm.enemyMaxHpPct) this._deal(u, _x, _x.maxHp * dm.enemyMaxHpPct, true);
        }
      }
      // 自身守护（领域内持续减免）
      if (dm.selfGuard) {
        u.domainGuard = dm.selfGuard;
        u.mods.armor = (u.mods.armor || 0) + dm.selfGuard;
      }
      // 开域瞬间先打一轮全场（原作：宿傩开域即斩、陀艮开域即式神海）
      if (dm.skillAoe) {
        for (_i = 0; _i < this.units.length; _i++) {
          _x = this.units[_i];
          if (_x.alive && _x.team !== u.team) {
            this._deal(u, _x, (u.ad + u.spell) * 0.5 * dm.skillAoe, true);
          }
        }
        this._emit({ t: 'domainHit', pos: { x: u.pos.x, y: u.pos.y }, team: u.team, name: spec.name });
      }
      this._emit({ t: 'domain', pos: { x: u.pos.x, y: u.pos.y }, team: u.team,
                   name: spec.name, dur: dm.dur || 6 });
    }

    // 必杀一次性代价（咒言反噬等）
    var self = u.mods.selfDamageOnUlt || 0;
    if (self > 0 && u.alive) {
      var loss = u.maxHp * self;
      u.hp = Math.max(1, u.hp - loss);
      this._emit({ t: 'selfDamage', pos: { x: u.pos.x, y: u.pos.y }, team: u.team, amount: Math.round(loss) });
    }
    // 必杀后自毁（五条「虚式茈」/「0.2秒的领域展开」）：一换一式的核弹
    if (u.mods.retireOnUlt && u.alive) this._retire(u);
  };

  // 定时退场 + 临终光环（五条「有急事」）
  BattleSim.prototype._retire = function (u) {
    if (!u.alive) return;
    u.alive = false;
    u.hp = 0;
    u.retired = true;
    this._emit({ t: 'retire', pos: { x: u.pos.x, y: u.pos.y }, team: u.team, unitId: u.id });
    var amp = u.mods.retireAura || 0;
    if (amp > 0) {
      for (var i = 0; i < this.units.length; i++) {
        var a = this.units[i];
        if (a.alive && a.team === u.team) { a.spell *= 1 + amp; a.ad *= 1 + amp; }
      }
      this._emit({ t: 'retireAura', team: u.team, amount: amp });
    }
  };

  // 每帧：退场计时 / 低血无敌
  BattleSim.prototype._tickSpecials = function (dt) {
    for (var i = 0; i < this.units.length; i++) {
      var u = this.units[i];
      if (!u.alive) continue;
      if (u.mods.retireAt && !u.retired && this.time >= u.mods.retireAt) {
        this._retire(u);
        continue;
      }
      // 状态到期：解除时把当时的增益回退
      if (u.stateUntil && this.time >= u.stateUntil) {
        var _se = u.stateSpec || {};
        if (_se.amp) { var _sb = 1 + _se.amp; u.ad /= _sb; u.spell /= _sb; }
        if (_se.guard) u.mods.armor = Math.max(0, (u.mods.armor || 0) - _se.guard);
        u.stateUntil = 0;
        u.stateSpec = null;
        this._emit({ t: 'stateOff', pos: { x: u.pos.x, y: u.pos.y }, team: u.team });
      }
      // 被动自带嘲讽的单位，开战报一次（原来只有主动技能才发事件）
      if (u.mods.taunt && !u._tauntShown) {
        u._tauntShown = true;
        this._emit({ t: 'taunt', pos: { x: u.pos.x, y: u.pos.y }, team: u.team, srcId: u.id });
      }
      // 必杀基础充能：光靠普攻太慢（一局只有 20 秒），给一条稳定涓流
      if (u.ultSpec && u.ult < u.ultCost && !(u.mods.ultBlockUntil && this.time < u.mods.ultBlockUntil)) {
        u.ult = Math.min(u.ultCost, u.ult + 1.6 * dt);
      }
      // 领域结束：解除自身增益，咒力归零
      if (u.domainUntil && this.time >= u.domainUntil) {
        var ds = u.domainSpec || {};
        u.domainUntil = 0;
        u.domainSpec = null;
        if (u.domainGuard) { u.mods.armor = Math.max(0, (u.mods.armor || 0) - u.domainGuard); u.domainGuard = 0; }
        if (ds.endMana !== false) u.mana = 0;
        this._emit({ t: 'domainEnd', pos: { x: u.pos.x, y: u.pos.y }, team: u.team });
      }
      // 低咒力时持续回复必杀值（伏黑「马上就超越你」）
      var uw = u.mods.ultWhenLowMana;
      if (uw && u.mana < (uw.below || 15)) {
        this._gainUlt(u, (uw.perSec || 40) * dt);
      }
      // 反转术式：消耗咒力治疗残血友军（乙骨）
      var ha = u.mods.healAlly;
      if (ha && this.time >= (u.nextHealAt || 0) && u.mana >= (ha.cost || 15)) {
        var low = null, lowPct = 1;
        for (var j = 0; j < this.units.length; j++) {
          var al = this.units[j];
          if (!al.alive || al.team !== u.team) continue;
          var pc = al.hp / al.maxHp;
          if (pc < (ha.maxHpPct || 0.6) && pc < lowPct) { lowPct = pc; low = al; }
        }
        if (low) {
          var hl = low.maxHp * (ha.pct || 0.10);
          low.hp = Math.min(low.maxHp, low.hp + hl);
          u.mana -= (ha.cost || 15);
          u.nextHealAt = this.time + (ha.interval || 4);
          this._emit({ t: 'heal', pos: { x: low.pos.x, y: low.pos.y }, amount: Math.round(hl), targetId: low.id });
          this._emit({ t: 'reverseHeal', pos: { x: u.pos.x, y: u.pos.y }, team: u.team, unitId: u.id });
        }
      }
      if (u.mods.invulnLowHp && !u.invulnLowUsed && u.hp <= u.maxHp * 0.5) {
        u.invulnLowUsed = true;
        u.invulnUntil = Math.max(u.invulnUntil, this.time + u.mods.invulnLowHp);
        this._emit({ t: 'invuln', pos: { x: u.pos.x, y: u.pos.y }, team: u.team, unitId: u.id });
      }
    }
  };

  BattleSim.prototype._summonFamiliar = function (u) {
    // 彩蛋角色允许链式召唤（式神可以继续召唤），普通角色不允许
    var chain = !!(u.def && u.def.skill && u.def.skill.chain);

    // ① 同队场上式神数量上限：防止反复施法把场子堆满
    var live = 0;
    for (var k = 0; k < this.units.length; k++) {
      var o = this.units[k];
      if (o.alive && o.team === u.team && o.cloneKind === 'shikigami') live++;
    }
    if (live >= (chain ? 30 : 3)) return;

    var clone = new BattleUnit();
    clone.id = this._nextId++;
    // ② 召唤物不能再召唤：复制 def 但剥掉 skill / ult
    //    （之前直接 clone.def = u.def，导致式神继承了「召唤」技能，无限链式召唤）
    var stripped = {};
    for (var kk in u.def) {
      if (Object.prototype.hasOwnProperty.call(u.def, kk)) stripped[kk] = u.def[kk];
    }
    stripped.ult = null;
    if (!chain) stripped.skill = null;
    clone.def = stripped;
    clone.isSummon = true;
    clone.gen = (u.gen || 0) + 1;
    clone.team = u.team;
    clone.star = 1;
    clone.isClone = true;
    clone.cloneKind = 'shikigami';
    clone.maxHp = u.maxHp * 0.3;
    clone.hp = clone.maxHp;
    clone.ad = u.ad * 0.35;
    clone.spell = u.spell * 0.35;
    clone.asRate = u.asRate;
    clone.atkRange = 1;
    clone.manaMax = 100;
    var spot = this._freeCellNear(u.pos);
    if (spot.x < 0) return;
    clone.pos = spot;
    this.units.push(clone);
    this._emit({ t: 'spawn', pos: { x: spot.x, y: spot.y }, team: u.team, unitId: clone.id, cloneKind: clone.cloneKind });
  };

  BattleSim.prototype._freeCellNear = function (p) {
    for (var dy = -1; dy <= 1; dy++) {
      for (var dx = -1; dx <= 1; dx++) {
        var c = { x: p.x + dx, y: p.y + dy };
        if (this._inBounds(c) && !this._occupied(c, null)) return c;
      }
    }
    return { x: -1, y: -1 };
  };

  BattleSim.prototype._randomEnemy = function (u) {
    var list = this.aliveUnits(1 - u.team);
    if (!list.length) return null;
    return list[Math.floor(Math.random() * list.length)];
  };

  BattleSim.prototype._randomOtherEnemy = function (u, exclude) {
    var list = [];
    for (var i = 0; i < this.units.length; i++) {
      var e = this.units[i];
      if (e.alive && e.team !== u.team && e !== exclude) list.push(e);
    }
    if (!list.length) return null;
    return list[Math.floor(Math.random() * list.length)];
  };

  BattleSim.prototype._lowestAlly = function (u) {
    var best = null, ratio = 2.0;
    for (var i = 0; i < this.units.length; i++) {
      var a = this.units[i];
      if (a.alive && a.team === u.team) {
        var r = a.hp / Math.max(1, a.maxHp);
        if (r < ratio) { ratio = r; best = a; }
      }
    }
    return best;
  };

  /* ---------------------------------------------------- 伤害 ----------- */
  BattleSim.prototype._deal = function (src, dst, amount, isSkill) {
    if (!dst || !dst.alive) return;
    if (src) dst.lastAttacker = src;

    // 攻击无效化（五条「无下限」）：完全免疫，但**不吃必杀槽**
    if (dst.invulnUntil && this.time < dst.invulnUntil) {
      this._emit({ t: 'invuln', pos: { x: dst.pos.x, y: dst.pos.y }, team: dst.team, targetId: dst.id });
      return;
    }
    var sure = !!(src && src.mods.sure_hit);

    // 闪避（必中无视）
    if (!sure && dst.dodge > 0 && this.time <= dst.dodgeUntil && Math.random() < dst.dodge) {
      this._emit({ t: 'dodge', pos: { x: dst.pos.x, y: dst.pos.y }, targetId: dst.id });
      return;
    }
    // 幻术 Lv2 虚像
    if (!sure && dst.mods.immune && Math.random() < dst.mods.immune) {
      dst.mana = Math.min(dst.manaMax, dst.mana + 20);
      this._emit({ t: 'immune', pos: { x: dst.pos.x, y: dst.pos.y }, targetId: dst.id });
      return;
    }

    // 护甲 / 魔抗分离：体术吃护甲，术式吃魔抗，复合各一半
    // （未单独配置 mres 的单位默认沿用 armor，保证旧卡行为不变）
    var _k = (isSkill && src && src._panel) ? src._panel : 'phys';
    var _ar = dst.mods.armor || 0;
    var _mr = (dst.mods.mres !== undefined && dst.mods.mres !== null) ? dst.mods.mres : _ar;
    var _mit = _k === 'magic' ? _mr : (_k === 'hybrid' ? (_ar + _mr) / 2 : _ar);
    if (dst.mods.guardUntil && this.time < dst.mods.guardUntil) {
      _mit = 1 - (1 - _mit) * (1 - (dst.mods.guardAmt || 0));   // 减免按乘法叠加
    }
    var dmg = amount * (1 - _mit);
    if (src && src.mods.dmg_out) dmg *= Math.max(0.1, 1 - src.mods.dmg_out);   // 被削弱（花御）
    // 属性克制：行→幻→夜→影→行
    var _em = src ? this._elemMult(src, dst) : 1;
    if (_em !== 1) {
      dmg *= _em;
      if (_em > 1) {
        this._emit({ t: 'elemCounter', pos: { x: dst.pos.x, y: dst.pos.y },
                     team: src.team, from: src.def.element, to: dst.def.element });
      }
    }

    // 幻惑：幻术 Lv1 —— 普攻有 18% 打偏到另一个随机敌人
    if (!isSkill && src && this._tier(dst.team, '幻') >= 1 && Math.random() < 0.18) {
      var other = this._randomOtherEnemy(src, dst);
      if (other) {
        dst = other;
        this._emit({ t: 'miss', pos: { x: dst.pos.x, y: dst.pos.y }, targetId: dst.id });
      }
    }

    this._rawDamage(dst, dmg, src);
    this._gainUlt(dst, 3);          // 受击积累必杀槽
    if (dst.mods.bf_count_key) this.addCounter(dst, dst.mods.bf_count_key, 1);   // 受击计数 +1

    // 受击计数回血（宿傩「反转术式」：每挨 N 次回 X% 最大生命）
    if (dst.alive && dst.mods.healHitsEvery) {
      var _hc = this.addCounter(dst, '_hitsTaken', 1);
      if (_hc % dst.mods.healHitsEvery === 0) {
        var _hl = dst.maxHp * (dst.mods.healHitsPct || 0.08);
        dst.hp = Math.min(dst.maxHp, dst.hp + _hl);
        if (dst.rec) dst.rec.heal += _hl;
        this._emit({ t: 'heal', pos: { x: dst.pos.x, y: dst.pos.y }, amount: Math.round(_hl), targetId: dst.id });
      }
    }

    if (src && src.mods.lifesteal && src.alive) {
      src.hp = Math.min(src.maxHp, src.hp + dmg * src.mods.lifesteal);
    }

    this._emit({
      t: 'dmg', pos: { x: dst.pos.x, y: dst.pos.y }, amount: Math.round(dmg),
      skill: !!isSkill, team: src ? src.team : -1,
      from: src ? { x: src.pos.x, y: src.pos.y } : { x: dst.pos.x, y: dst.pos.y },
      targetId: dst.id, srcId: src ? src.id : -1
    });
  };

  BattleSim.prototype._rawDamage = function (u, dmg, src) {
    if (!u.alive) return;
    dmg *= (1 + (u.mods.dmg_taken || 0));   // 易伤：目标受到伤害「增加」
    if (u.shield > 0) {
      var absorbed = Math.min(u.shield, dmg);
      u.shield -= absorbed;
      dmg -= absorbed;
      if (u.rec) u.rec.taken += absorbed;   // 護盾吸收也算承伤
    }
    var real = Math.min(dmg, Math.max(0, u.hp));
    if (u.rec) u.rec.taken += real;
    if (src && src.rec) src.rec.dealt += real;
    u.hp -= dmg;
    if (u.hp <= 0) this._kill(u);
  };

  /* ---------------------------------------------------- 战后统计 ------ */
  // 返回 [{id, name, team, cost, star, dealt, taken, heal, alive}]
  BattleSim.prototype.stats = function () {
    var out = [];
    for (var i = 0; i < this.units.length; i++) {
      var u = this.units[i];
      var r = u.rec || { dealt: 0, taken: 0, heal: 0 };
      out.push({
        id: u.id, name: (u.def && u.def.name) || '咒灵', team: u.team,
        cost: (u.def && u.def.cost) || 0, star: u.star || 1,
        dealt: Math.round(r.dealt), taken: Math.round(r.taken),
        heal: Math.round(r.heal), alive: !!u.alive
      });
    }
    return out;
  };

  BattleSim.prototype._kill = function (u) {
    // 复活（熊猫「核转换」）：以 N% 生命站起来，眩晕 0.6s
    if (u.reviveLeft > 0) {
      u.reviveLeft -= 1;
      u.alive = true;
      u.hp = u.maxHp * (u.mods.revivePct || 0.4);
      u.stun = Math.max(u.stun, 0.6);
      u.mana = 0;
      u.dotTime = 0;
      this._emit({ t: 'revive', pos: { x: u.pos.x, y: u.pos.y }, team: u.team, unitId: u.id });
      return;
    }
    u.alive = false;
    u.hp = 0;
    this._emit({ t: 'death', pos: { x: u.pos.x, y: u.pos.y }, team: u.team, unitId: u.id });
    var i, e;
    if (u.lastAttacker) {
      this._gainUlt(u.lastAttacker, 10);                     // 击杀积累必杀槽
      var _mok = u.lastAttacker.mods.manaOnKill || 0;        // 击杀回咒（夏油杰「吸收」）
      if (_mok > 0 && u.lastAttacker.alive) {
        u.lastAttacker.mana = Math.min(u.lastAttacker.manaMax, u.lastAttacker.mana + _mok);
        this._emit({ t: 'manaGain', pos: { x: u.lastAttacker.pos.x, y: u.lastAttacker.pos.y },
                     team: u.lastAttacker.team, amount: _mok, unitId: u.lastAttacker.id });
      }
    }

    // 联动「容器与诅咒之王」①：宿傩击杀回复
    if (u.lastAttacker && u.lastAttacker.alive && u.lastAttacker.mods.link_heal_on_kill) {
      var heal = u.lastAttacker.maxHp * u.lastAttacker.mods.link_heal_on_kill;
      u.lastAttacker.hp = Math.min(u.lastAttacker.maxHp, u.lastAttacker.hp + heal);
      this._emit({ t: 'heal', pos: { x: u.lastAttacker.pos.x, y: u.lastAttacker.pos.y },
                   amount: Math.round(heal), targetId: u.lastAttacker.id });
    }
    // 联动「容器与诅咒之王」②：容器阵亡 → 同队同联动的另一位立刻充满咒力
    if (u.linkIds && u.linkIds.indexOf('vessel-king') >= 0) {
      for (i = 0; i < this.units.length; i++) {
        e = this.units[i];
        if (e.alive && e.team === u.team && e !== u && e.linkIds.indexOf('vessel-king') >= 0) {
          e.mana = e.manaMax;
          this._emit({ t: 'linkCharge', pos: { x: e.pos.x, y: e.pos.y }, team: e.team, unitId: e.id });
        }
      }
    }

    // 咒灵 Lv2 怨念：阵亡爆炸
    if (u.mods.death_aoe) {
      for (i = 0; i < this.units.length; i++) {
        e = this.units[i];
        if (e.alive && e.team !== u.team && dist(e.pos, u.pos) <= 1) {
          this._rawDamage(e, u.mods.death_aoe);
          this._emit({
            t: 'dmg', pos: { x: e.pos.x, y: e.pos.y }, amount: u.mods.death_aoe,
            skill: true, team: u.team, from: { x: u.pos.x, y: u.pos.y }, targetId: e.id
          });
        }
      }
    }
    // 咒灵 Lv3 咒胎 / 夜行 Lv3 月下领域：复活一次
    if (u.mods.revive && !u.revived) {
      u.revived = true; u.alive = true; u.hp = u.maxHp * u.mods.revive; u.dotTime = 0;
      this._emit({ t: 'revive', pos: { x: u.pos.x, y: u.pos.y }, team: u.team, unitId: u.id });
      return;
    }
    if (!u.mods.revive && this._tier(u.team, '夜') >= 3 && !u.revived && (u.def.traits || []).indexOf('夜') >= 0) {
      u.revived = true; u.alive = true; u.hp = u.maxHp * 0.35;
      this._emit({ t: 'revive', pos: { x: u.pos.x, y: u.pos.y }, team: u.team, unitId: u.id });
      return;
    }
    // 影袭 Lv3 影分身
    if (this._tier(u.team, '影') >= 3 && (u.def.traits || []).indexOf('影') >= 0 && !u.isClone && !u.revived) {
      this._summonClone(u);
      u.revived = true;
    }
    // 东京校 Lv3：阵亡给相邻友军护盾
    if (this._tier(u.team, '东京校') >= 3 && (u.def.traits || []).indexOf('东京校') >= 0) {
      for (i = 0; i < this.units.length; i++) {
        var a = this.units[i];
        if (a.alive && a.team === u.team && dist(a.pos, u.pos) <= 1) a.shield += a.maxHp * 0.12;
      }
    }
    // 行咒 Lv2 连环：击杀方队伍回 35 咒力
    if (this._tier(1 - u.team, '行') >= 2) {
      for (i = 0; i < this.units.length; i++) {
        e = this.units[i];
        if (e.alive && e.team !== u.team && (e.def.traits || []).indexOf('行') >= 0) {
          e.mana = Math.min(e.manaMax, e.mana + 35);
        }
      }
    }
  };

  BattleSim.prototype._summonClone = function (u) {
    var clone = new BattleUnit();
    clone.id = this._nextId++;
    clone.def = u.def;
    clone.team = u.team;
    clone.star = 1;
    clone.isClone = true;
    clone.cloneKind = 'shadow';
    clone.maxHp = u.maxHp * 0.5;
    clone.hp = clone.maxHp;
    clone.ad = u.ad * 0.5;
    clone.spell = u.spell * 0.5;
    clone.asRate = u.asRate;
    clone.atkRange = u.atkRange;
    var spot = this._freeCellNear(u.pos);
    if (spot.x < 0) return;
    clone.pos = spot;
    this.units.push(clone);
    this._emit({ t: 'spawn', pos: { x: spot.x, y: spot.y }, team: u.team, unitId: clone.id, cloneKind: clone.cloneKind });
  };

  /* ---------------------------------------------------- 结束判定 ------- */
  BattleSim.prototype._checkEnd = function () {
    if (this.over) return;
    var p = this.aliveUnits(0).length;
    var e = this.aliveUnits(1).length;
    if (p === 0 && e === 0) { this.over = true; this.winner = 1; }
    else if (p === 0) { this.over = true; this.winner = 1; }
    else if (e === 0) { this.over = true; this.winner = 0; }
    else if (this.time >= MAX_TIME) { this.over = true; this.winner = p >= e ? 0 : 1; }
  };

  /* ---------------------------------------------------- 导出 ----------- */
  JJK.BattleSim = BattleSim;
  JJK.BATTLE = { GRID_W: GRID_W, GRID_H: GRID_H, MAX_TIME: MAX_TIME, OVERTIME_AT: OVERTIME_AT };

})(window);
