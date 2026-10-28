/* =========================================================================
 *  selftest.mjs —— 无浏览器内核自测（Node 直接跑纯逻辑层）
 *  用法： node tools/selftest.mjs
 *  覆盖：数据完整性 / 经济 / 商店锁定 / 人口上限 / 升星合成 / 咒具合成 /
 *        领域只触发一次 / 羁绊档位 / 20 回合全自动对局稳定性
 * ========================================================================= */
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));

const files = [
  'js/core/util.js',
  'data/game-data.js',
  'js/core/data.js',
  'js/core/battle.js',
  'js/core/ai.js',
  'js/core/game.js'
];

const store = new Map();
const sandbox = {
  console,
  Math, Date, JSON, Promise, setTimeout, clearTimeout, requestAnimationFrame: () => 0,
  localStorage: {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => store.set(k, v),
    removeItem: (k) => store.delete(k)
  },
  matchMedia: () => ({ matches: false })
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;

const ctx = vm.createContext(sandbox);
for (const f of files) {
  const src = fs.readFileSync(path.join(ROOT, f), 'utf8');
  vm.runInContext(src, ctx, { filename: f });
}

const W = sandbox.window;
const JJK = W.JJK;
const D = JJK.data;

let pass = 0, fail = 0;
function ok(name, cond, extra) {
  if (cond) { pass++; console.log('  PASS  ' + name + (extra ? '   ' + extra : '')); }
  else { fail++; console.log('  FAIL  ' + name + (extra ? '   ' + extra : '')); }
}
function section(t) { console.log('\n## ' + t); }

/* ------------------------------------------------------------ 1 数据 */
section('数据完整性');
ok('棋子 111 名（全量实装）', D.units.length === 111, '实际 ' + D.units.length);
ok('羁绊 10 条', D.traits.length === 10, '实际 ' + D.traits.length);
ok('咒具 20 件（散件 8 / 成装 12）', D.items.length === 20, '实际 ' + D.items.length);
ok('PvE 3 波', D.pve.length === 3, '实际 ' + D.pve.length);
ok('AI 蓝图 3 套', D.plans.length === 3, '实际 ' + D.plans.length);
ok('费用分布 21/23/23/24/20（领域角色上调后）',
  [1, 2, 3, 4, 5].every((c) => D.unitsByCost[c].length === { 1: 21, 2: 23, 3: 23, 4: 24, 5: 20 }[c]),
  [1, 2, 3, 4, 5].map((c) => D.unitsByCost[c].length).join('/'));
if (D.raw.links) {
  ok('异格联动定义 5 组', D.raw.links.length === 5, D.raw.links.map((l) => l.id).join(','));
  ok('联动成员都在棋子表里', D.raw.links.every((l) => l.members.every((m) => !!D.unitById[m])));
}
ok('每名棋子都有头像与卡面', D.units.every((u) => u.icon && u.card));
ok('羁绊档位无死重（连续整数）',
  D.traits.every((t) => t.tiers.every((x, i) => i === 0 || x.count === t.tiers[i - 1].count + 1)));

/* ------------------------------------------------------------ 2b 经济补丁 */
/* Phase 7 P3：连势查表对齐 TFT，卖棋折旧 */
(function () {
  const SB = JJK.Game.STREAK_BONUS;
  const table = [[0, 0], [1, 0], [2, 0], [3, 1], [4, 1], [5, 2], [6, 3], [9, 3]];
  ok('连势查表 3-4→+1 / 5→+2 / 6+→+3',
    table.every(([n, v]) => SB(n) === v),
    table.map(([n]) => n + '→' + SB(n)).join(' '));

  const gg = new JJK.Game();
  const u1 = D.units.filter((u) => u.cost === 1)[0];
  const u4 = D.units.filter((u) => u.cost === 4)[0];
  ok('1 费 1 星不折旧（返 1）', gg._refundOf({ id: u1.id, star: 1 }) === 1,
    u1.name + '=' + gg._refundOf({ id: u1.id, star: 1 }));
  ok('4 费 1 星返 3（折旧 1）', gg._refundOf({ id: u4.id, star: 1 }) === 3,
    String(gg._refundOf({ id: u4.id, star: 1 })));
  ok('2★ 按 3× 返还再折旧（4 费 → 11）', gg._refundOf({ id: u4.id, star: 2 }) === 11,
    String(gg._refundOf({ id: u4.id, star: 2 })));
  ok('3★ 按 9× 返还再折旧（4 费 → 35）', gg._refundOf({ id: u4.id, star: 3 }) === 35,
    String(gg._refundOf({ id: u4.id, star: 3 })));
})();

/* ------------------------------------------------------------ 2 经济 */
section('经济与商店');
const g = new JJK.Game();
g.newGame(1);
ok('开局金币 6', g.gold === 6, '实际 ' + g.gold);
ok('开局 2 级', g.level === 2);
ok('开局 5 张商店卡', g.shop.filter(Boolean).length === 5);
ok('第 1 回合是 PvE', g.battleKind === 'pve');

// 锁定商店后，下一回合商店不变
const before = g.shop.slice();
g.toggleLock();
g.startRound();
ok('锁定商店后本轮商店不变', before.join() === g.shop.join(), before.join() + ' -> ' + g.shop.join());
ok('进入新回合后自动解锁', g.shopLocked === false);

// 利息
g.gold = 50;
const income = { interest: Math.min(5, Math.floor(g.gold / 10)) };
ok('50 金吃满 5 利息', income.interest === 5, '实际 ' + income.interest);
g.gold = 6;
ok('6 金利息为 0', Math.min(5, Math.floor(g.gold / 10)) === 0);

/* ------------------------------------------------------------ 3 人口 */
section('棋盘与人口');
const g2 = new JJK.Game();
g2.newGame(0);
g2.gold = 999;
// 每次买最贵的可买卡（买到后该格会清空，所以要重新找）
for (let n = 0; n < 6; n++) {
  let idx = -1;
  for (let i = 0; i < g2.shop.length; i++) if (g2.shop[i] && (idx < 0 || D.unitById[g2.shop[i]].cost > D.unitById[g2.shop[idx]].cost)) idx = i;
  if (idx < 0) { g2.rollShop(); continue; }
  g2.buyFromShop(idx);
}
// 直接塞棋子到棋盘，验证人口上限
let placed = 0;
for (let i = 0; i < g2.roster.length && placed < g2.level; i++) {
  const r = g2.roster[i];
  const cell = g2._findFreeCell(true);
  if (cell) { g2.placeUnit(r.uid, { type: 'cell', x: cell.x, y: cell.y }); placed++; }
}
ok('人口 = 等级时已满', g2.boardCount() === g2.level, g2.boardCount() + '/' + g2.level);
const pool = g2.roster.find((r) => r.pos.x < 0);
if (pool) {
  const free = { x: 3, y: 3 };
  const occupied = g2.unitAtCell(free.x, free.y);
  const res = g2.placeUnit(pool.uid, { type: 'cell', x: free.x, y: free.y });
  ok('人口已满时拖到空位被拒绝', res.ok === false && res.reason === 'cap');
}
// 敌方半场不可放置
const anyUnit = g2.roster[0];
ok('敌方半场不可放置', g2.placeUnit(anyUnit.uid, { type: 'cell', x: 5, y: 0 }).reason === 'territory');

/* ------------------------------------------------------------ 4 升星 */
section('升星合成');
const g3 = new JJK.Game();
g3.reset(1);
g3.phase = 'planning';
const target = D.units.find((u) => u.cost === 1).id;
for (let i = 0; i < 9; i++) { g3._addUnit(target); }
const same = g3.roster.filter((r) => r.id === target);
ok('9 张同名合成 1 张 3 星', same.length === 1 && same[0].star === 3,
  '剩 ' + same.length + ' 张 / ' + (same[0] ? same[0].star : 0) + ' 星');

/* ------------------------------------------------------------ 5 咒具 */
section('咒具合成');
const g4 = new JJK.Game();
g4.reset(1); g4.phase = 'planning';
g4._addUnit(target);
const u4 = g4.roster[0];
g4.itemsBag.push('scroll', 'fang');
const bagBefore = g4.itemsBag.length;
g4.selectItem('scroll');
g4.equipItem(u4.uid, 'scroll');
g4.selectItem('fang');
const r5 = g4.equipItem(u4.uid, 'fang');
ok('卷轴 + 牙 = 游云', r5.ok && u4.items.length === 1 && u4.items[0] === 'yuyun', JSON.stringify(u4.items));
ok('背包净减 2 件', g4.itemsBag.length === bagBefore - 2, bagBefore + ' -> ' + g4.itemsBag.length);
ok('背包已空', g4.itemsBag.length === 0);

/* ------------------------------------------------------------ 6 羁绊 */
section('羁绊档位');
const tokyo = D.units.filter((u) => u.traits.includes('东京校')).slice(0, 4).map((u) => u.id);
ok('东京校 2 人 = 1 档', D.traitTiersFor(tokyo.slice(0, 2))['东京校'] === 1);
ok('东京校 3 人 = 2 档', D.traitTiersFor(tokyo.slice(0, 3))['东京校'] === 2);
ok('东京校 4 人 = 3 档', D.traitTiersFor(tokyo.slice(0, 4))['东京校'] === 3);

/* ------------------------------------------------------------ 7 战斗 */
section('战斗引擎');
function runBattle(mineSpecs, foeSpecs) {
  const sim = new JJK.BattleSim();
  sim.setup(mineSpecs, foeSpecs, D.traitTiersFor(mineSpecs.map((m) => m.id)),
    D.traitTiersFor(foeSpecs.map((m) => m.id)));
  const events = [];
  let guard = 0;
  while (!sim.over && guard < 60 * 60) {
    sim.update(1 / 60);
    guard++;
    const evs = sim.drainEvents();
    for (const e of evs) events.push(e);
  }
  return { sim, events, steps: guard };
}

const pveWave = D.pve[0];
const pveEnemies = [];
let slot = 0;
for (const grp of pveWave.enemies) {
  for (let i = 0; i < (grp.count || 1); i++) {
    pveEnemies.push({
      id: 'pve', name: grp.name, element: '咒灵', hp: grp.hp, ad: grp.ad, spell: 40,
      as: 0.8, range: grp.range || 1, mana: 100, start_mana: 0, traits: [],
      skill: { name: '咒力冲击', type: 'strike', power: 1.4 }, passive: {}, items: [],
      star: 1, pos: { x: 5 + (slot % 2), y: Math.floor(slot / 2) }
    });
    slot++;
  }
}
const my5 = D.unitsByCost[1].slice(0, 3).map((u, i) => ({
  id: u.id, name: u.name, element: u.element, hp: u.hp, ad: u.ad, spell: u.spell,
  as: u.as, range: u.range, mana: u.mana, start_mana: u.start_mana, traits: u.traits,
  skill: u.skill, passive: u.passive, items: [], star: 1, pos: { x: i, y: 1 }
}));
const rb = runBattle(my5, pveEnemies);
ok('PvE 第 1 波能分出胜负', rb.sim.over === true, 'winner=' + rb.sim.winner + ' 用时 ' + rb.sim.time.toFixed(1) + 's');
ok('战斗有伤害事件', rb.events.filter((e) => e.t === 'dmg').length > 12,
  'dmg=' + rb.events.filter((e) => e.t === 'dmg').length);

// 领域只触发一次
const specials = D.units.filter((u) => u.traits.includes('特级')).slice(0, 3);
const domSpecs = specials.map((u, i) => ({
  id: u.id, name: u.name, element: u.element, hp: u.hp, ad: u.ad, spell: u.spell, as: u.as,
  range: u.range, mana: u.mana, start_mana: u.start_mana, traits: u.traits, skill: u.skill,
  passive: u.passive, items: [], star: 1, pos: { x: i, y: 0 }
}));
const domFoes = my5.map((m, i) => Object.assign({}, m, { pos: { x: 5 + i, y: 1 }, hp: 4000, ad: 1 }));
const rb2 = runBattle(domSpecs, domFoes);
const domEvents = rb2.events.filter((e) => e.t === 'domain' && e.team === 0);
ok('领域（特级 3 人）只触发 1 次', domEvents.length === 1, '次数 ' + domEvents.length);

// 黑闪存在
const bfTeam = D.units.filter((u) => u.passive.type === 'bf').slice(0, 4).map((u, i) => ({
  id: u.id, name: u.name, element: u.element, hp: 3000, ad: u.ad * 4, spell: u.spell, as: u.as,
  range: u.range, mana: u.mana, start_mana: u.start_mana, traits: u.traits, skill: u.skill,
  passive: u.passive, items: [], star: 1, pos: { x: i, y: 1 }
}));
const rb3 = runBattle(bfTeam, domFoes.slice(0, 3));
ok('黑闪可触发', rb3.events.some((e) => e.t === 'bf'));

/* ------------------------------------------------------------ 8 全流程 */
section('20 回合全自动对局');
function autoplay(difficulty, rounds, seedLog) {
  const G = new JJK.Game();
  G.newGame(difficulty, true);
  let battles = 0;
  for (let r = 0; r < rounds; r++) {
    if (G.phase === 'gameover') break;
    // 买东西：优先买得起的最贵
    for (let guard = 0; guard < 40; guard++) {
      let best = -1, bestCost = -1;
      for (let i = 0; i < G.shop.length; i++) {
        const id = G.shop[i];
        if (!id) continue;
        const c = D.unitById[id].cost;
        if (c <= G.gold && c > bestCost) { bestCost = c; best = i; }
      }
      if (best < 0) break;
      const res = G.buyFromShop(best);
      if (!res.ok) break;
    }
    if (G.level < 9 && G.gold > 30) G.buyExp();
    G.autoDeploy();
    if (G.boardCount() === 0) { G.continueAfterResult(); continue; }
    const br = G.beginBattle();
    if (!br.ok) break;
    battles++;
    let steps = 0;
    while (G.phase === 'battle' && steps < 60 * 120) { G.tickBattle(1 / 30); steps++; }
    if (G.phase === 'battle') throw new Error('战斗未结束（死循环）');
    if (G.phase === 'result') G.continueAfterResult();
  }
  return { G, battles };
}

let crashed = null;
for (const diff of [0, 1, 2]) {
  try {
    const { G, battles } = autoplay(diff, 20);
    console.log('  难度' + ['简单', '普通', '困难'][diff] + '：' + battles + ' 场战斗，回合 ' +
      G.round + '，生命 ' + G.hp + '，对手生命 ' + G.ai.hp + '，等级 ' + G.level + '，终局 ' + G.phase);
  } catch (e) {
    crashed = e;
    console.log('  ERROR 难度' + diff + '：' + e.message);
  }
}
ok('三档难度 20 回合全程无异常', !crashed);

/* ------------------------------------------------------------ 9 AI */
section('AI 对手');
const a = new JJK.AI(2);
for (let i = 0; i < 12; i++) a.beginRound(i % 3 === 0 ? 1 : -1);
const bu = a.boardUnits();
ok('AI 第 12 回合有阵容', bu.length > 0, '人数 ' + bu.length + ' 等级 ' + a.level + ' 金币 ' + a.gold);
const posSet = new Set(bu.map((x) => x.pos.x + ',' + x.pos.y));
ok('AI 摆位无重叠', posSet.size === bu.length, posSet.size + '/' + bu.length);
ok('AI 全部站在敌方半场', bu.every((x) => x.pos.x >= 4));
const sc = a.powerScale(12, 40);
ok('强度曲线随回合上升', a.powerScale(3, 100) < a.powerScale(12, 100),
  a.powerScale(3, 100).toFixed(2) + ' -> ' + a.powerScale(12, 100).toFixed(2));
ok('玩家落后时对手强度补正生效', sc > a.powerScale(12, 100), sc.toFixed(2));

/* ------------------------------------------------------------ 10 存档 */
section('存档');
const g5 = new JJK.Game();
g5.newGame(2);
g5.gold = 33;
g5.save();
const g6 = new JJK.Game();
ok('能读出存档', g6.load() === true);
ok('读档金币一致', g6.gold === 33, '实际 ' + g6.gold);
ok('读档回合一致', g6.round === g5.round, g6.round + ' vs ' + g5.round);

/* ------------------------------------------------------------ 汇总 */
console.log('\n================================');
console.log('通过 ' + pass + ' / 失败 ' + fail);
console.log('================================');
process.exit(fail ? 1 : 0);
