/* =========================================================================
 *  data.js —— 数据索引与展示元数据
 *  纯游戏数据在 data/game-data.js（自动生成）；这里放"怎么看"的信息。
 * ========================================================================= */
(function (global) {
  'use strict';

  var JJK = global.JJK = global.JJK || {};
  var RAW = global.JJK_DATA;

  if (!RAW) {
    console.error('[data] 未找到 window.JJK_DATA，请检查 data/game-data.js 是否被引入');
  }

  /* ------------------------------------------------------ 索引 ---------- */
  var unitById = {};
  var traitById = {};
  var itemById = {};
  var unitsByCost = { 1: [], 2: [], 3: [], 4: [], 5: [] };

  (RAW.units || []).forEach(function (u) {
    unitById[u.id] = u;
    (unitsByCost[u.cost] = unitsByCost[u.cost] || []).push(u);
  });
  (RAW.traits || []).forEach(function (t) { traitById[t.id] = t; });
  (RAW.items || []).forEach(function (i) { itemById[i.id] = i; });

  /* ------------------------------------------------------ 品质 ---------- */
  // B(1–2费) / A(3费) / S(4费) / SS(5费) —— 四档跨度必须一眼可辨
  var QUALITY = [
    { key: 'B', label: 'B', color: '#9aa3b2', glow: 'rgba(154,163,178,0.35)', rank: 0 },
    { key: 'A', label: 'A', color: '#4d9bff', glow: 'rgba(77,155,255,0.45)', rank: 1 },
    { key: 'S', label: 'S', color: '#b06bff', glow: 'rgba(176,107,255,0.55)', rank: 2 },
    { key: 'SS', label: 'SS', color: '#f0c34a', glow: 'rgba(240,195,74,0.65)', rank: 3 }
  ];

  function qualityOf(cost) {
    if (cost <= 2) return QUALITY[0];
    if (cost === 3) return QUALITY[1];
    if (cost === 4) return QUALITY[2];
    return QUALITY[3];
  }

  /* ------------------------------------------------------ 元素 ---------- */
  // 元素 = 阵营。情绪色：夜=萤绿 / 影=绀蓝 / 幻=绯红 / 行=琥珀
  var ELEMENTS = {
    '夜': { key: 'night', name: '夜行', color: '#35c994', deep: '#0d3b2e', glyph: '夜' },
    '影': { key: 'shadow', name: '影袭', color: '#5b9dff', deep: '#0e2445', glyph: '影' },
    '幻': { key: 'illusion', name: '幻术', color: '#ff5c7a', deep: '#3a0f1d', glyph: '幻' },
    '行': { key: 'motion', name: '行咒', color: '#f5b93c', deep: '#3b2a08', glyph: '行' }
  };

  /* ------------------------------------------------------ 羁绊色 --------- */
  // 原始 traits.json 的颜色偏暗，网页端统一提亮一档保证在深底上可读
  var TRAIT_COLORS = {
    '夜': '#35c994',
    '影': '#5b9dff',
    '幻': '#ff5c7a',
    '行': '#f5b93c',
    '体术': '#ff7d55',
    '术式': '#b18cff',
    '咒灵': '#e46a96',
    '特级': '#ffd166',
    '东京校': '#4bc6e8',
    '京都校': '#f59e5b'
  };

  function traitColor(id) {
    return TRAIT_COLORS[id] || (traitById[id] && traitById[id].color) || '#8b93a7';
  }

  /* ------------------------------------------------------ 技能 / 被动 --- */
  var SKILL_TYPES = {
    strike: { label: '单体突袭', glyph: '突', color: '#ff8a5c' },
    slam: { label: '范围重击', glyph: '震', color: '#ff6b47' },
    barrage: { label: '多段连击', glyph: '连', color: '#ffb04d' },
    beam: { label: '直线贯穿', glyph: '贯', color: '#5bd0ff' },
    dot: { label: '持续侵蚀', glyph: '蚀', color: '#c07bff' },
    drain: { label: '夺魂吸取', glyph: '吸', color: '#e05a8a' },
    stun: { label: '咒言眩晕', glyph: '缚', color: '#7fa8ff' },
    heal: { label: '治疗回复', glyph: '愈', color: '#5ce09a' },
    shield: { label: '护盾守护', glyph: '盾', color: '#ffd166' },
    buff: { label: '强化己方', glyph: '强', color: '#ffa94d' },
    domain: { label: '领域展开', glyph: '域', color: '#d94dff' },
    summon: { label: '召唤式神', glyph: '召', color: '#6ee7f0' }
  };

  /* 四特性（幻影夜行的「行 / 幻 / 夜 / 影」）—— 卡面右上角徽记用 */
  var ELEM_META = {
    '行': { color: '#f0a020', glyph: '行', glow: 'rgba(240,160,32,0.55)' },
    '幻': { color: '#e0483c', glyph: '幻', glow: 'rgba(224,72,60,0.55)' },
    '夜': { color: '#4fc06a', glyph: '夜', glow: 'rgba(79,192,106,0.55)' },
    '影': { color: '#2f5f9e', glyph: '影', glow: 'rgba(47,95,158,0.6)' }
  };
  function elemMeta(el) {
    return ELEM_META[el] || { color: '#8b95a7', glyph: el || '?', glow: 'rgba(139,149,167,0.4)' };
  }

  var PASSIVE_TYPES = {
    bf: { label: '黑闪', glyph: '閃', color: '#ff4d4d' },
    dodge: { label: '闪避', glyph: '避', color: '#7fd6ff' },
    taunt: { label: '守护', glyph: '守', color: '#ffd166' },
    mana_on_cast: { label: '咒力循环', glyph: '循', color: '#8ad2ff' },
    erode: { label: '侵蚀', glyph: '蚀', color: '#b06bff' },
    // ---- 批次重做后，被动一律由 mods 驱动，类型标签按主导效果取 ----
    retire: { label: '限时退场', glyph: '退', color: '#ff9f43' },
    retire_ult: { label: '必杀自毁', glyph: '毁', color: '#ff4d6d' },
    revive: { label: '复活', glyph: '活', color: '#7dffc8' },
    invuln: { label: '攻击无效化', glyph: '无', color: '#9ecbff' },
    counter: { label: '反击', glyph: '反', color: '#ffb020' },
    heal_ally: { label: '反转术式', glyph: '疗', color: '#7dffc8' },
    ult_start: { label: '必杀充能', glyph: '充', color: '#ffd166' },
    grow: { label: '计数成长', glyph: '计', color: '#c084fc' },
    aura: { label: '团队光环', glyph: '环', color: '#8ad2ff' },
    guard: { label: '减伤', glyph: '御', color: '#8b95a7' },
    extra: { label: '追击', glyph: '追', color: '#ff9f43' },
    mana_gain: { label: '回咒', glyph: '咒', color: '#8ad2ff' },
    mods: { label: '被动', glyph: '被', color: '#c084fc' },
    mana_steal: { label: '削咒', glyph: '削', color: '#7fa8ff' },
    lifesteal: { label: '吸血', glyph: '血', color: '#ff5c7a' },
    slow_on_hit: { label: '迟滞', glyph: '迟', color: '#8fa0c0' },
    regen_aura: { label: '再生光环', glyph: '生', color: '#5ce09a' },
    aura_haste: { label: '疾速光环', glyph: '疾', color: '#ffd166' },
    aura_power: { label: '增幅光环', glyph: '增', color: '#ffa94d' }
  };

  /* ------------------------------------------------------ 咒具 ---------- */
  // 咒具图标用汉字印章（不需要外部图标库，辨识度也够）
  var ITEM_META = {
    crystal: { glyph: '晶', color: '#7fb2ff' },
    scroll: { glyph: '卷', color: '#ffab6b' },
    charm: { glyph: '符', color: '#ffd166' },
    fang: { glyph: '牙', color: '#e8e2d2' },
    fragment: { glyph: '碎', color: '#b18cff' },
    ward: { glyph: '界', color: '#6ee7f0' },
    yuyun: { glyph: '云', color: '#ff7d55' },
    ao: { glyph: '苍', color: '#5bd0ff' },
    finger: { glyph: '指', color: '#ff5470' },
    domain_talisman: { glyph: '御', color: '#d94dff' }
  };

  function itemMeta(id) {
    return ITEM_META[id] || { glyph: '咒', color: '#9aa3b2' };
  }

  /* ------------------------------------------------------ 战斗数值 ------ */
  var STAR_MULT = [1, 1, 1.75, 3.0];

  function starMult(star) { return STAR_MULT[Math.max(1, Math.min(3, star || 1))]; }

  // 与 battle.js 的 _spawn 完全一致的星级换算，用于详情面板展示真实数值
  function statsAtStar(unit, star) {
    var m = starMult(star);
    return {
      hp: Math.round(unit.hp * m),
      ad: Math.round(unit.ad * (1 + 0.7 * (m - 1))),
      spell: Math.round(unit.spell * (1 + 0.7 * (m - 1))),
      as: unit.as,
      range: unit.range,
      mana: unit.mana,
      start_mana: unit.start_mana
    };
  }

  /* ------------------------------------------------------ 羁绊统计 ------ */
  function countTraits(unitIds) {
    var counts = {};
    for (var i = 0; i < unitIds.length; i++) {
      var u = unitById[unitIds[i]];
      if (!u) continue;
      var tr = u.traits || [];
      for (var j = 0; j < tr.length; j++) counts[tr[j]] = (counts[tr[j]] || 0) + 1;
    }
    return counts;
  }

  // 返回 { traitId: {count, level(0=未激活), tiers, info, color, next} }
  function traitStatus(counts) {
    var out = {};
    for (var tid in counts) {
      if (!counts.hasOwnProperty(tid)) continue;
      var info = traitById[tid];
      if (!info) continue;
      var c = counts[tid];
      var tiers = info.tiers || [];
      var lvl = 0, next = null;
      for (var i = 0; i < tiers.length; i++) {
        if (c >= tiers[i].count) lvl = i + 1;
        else { next = tiers[i]; break; }
      }
      out[tid] = {
        count: c, level: lvl, tiers: tiers, info: info,
        color: traitColor(tid), next: next
      };
    }
    return out;
  }

  function traitTiersFor(unitIds) {
    var st = traitStatus(countTraits(unitIds));
    var out = {};
    for (var tid in st) if (st.hasOwnProperty(tid)) out[tid] = st[tid].level;
    return out;
  }

  /* ------------------------------------------------------ 杂项 ---------- */
  function traitTypes() {
    // 元素优先，其次职业，最后阵营 —— 图鉴里分组用
    var order = { element: 0, class: 1, faction: 2 };
    return (RAW.traits || []).slice().sort(function (a, b) {
      return (order[a.type] || 9) - (order[b.type] || 9);
    });
  }

  // 同名异格：用于图鉴里把同一角色的不同形态并排展示
  function altForms() {
    var map = {};
    (RAW.units || []).forEach(function (u) {
      (map[u.name] = map[u.name] || []).push(u);
    });
    return map;
  }

  JJK.data = {
    raw: RAW,
    units: RAW.units || [],
    traits: RAW.traits || [],
    items: RAW.items || [],
    pve: RAW.pve || [],
    plans: RAW.plans || [],
    links: RAW.links || [],
    meta: RAW.meta || {},
    unitById: unitById,
    traitById: traitById,
    itemById: itemById,
    unitsByCost: unitsByCost,
    QUALITY: QUALITY,
    qualityOf: qualityOf,
    ELEMENTS: ELEMENTS,
    TRAIT_COLORS: TRAIT_COLORS,
    traitColor: traitColor,
    SKILL_TYPES: SKILL_TYPES,
    ELEM_META: ELEM_META,
    elemMeta: elemMeta,
    PASSIVE_TYPES: PASSIVE_TYPES,
    itemMeta: itemMeta,
    starMult: starMult,
    statsAtStar: statsAtStar,
    countTraits: countTraits,
    traitStatus: traitStatus,
    traitTiersFor: traitTiersFor,
    traitTypes: traitTypes,
    altForms: altForms
  };

})(window);
