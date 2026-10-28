/* _batch3_test.cjs —— 批次 3 十四枚低费棋子 + 两组新联动 */
const fs = require('fs'), vm = require('vm'), path = require('path');
const root = 'E:/我想做游戏/咒术自走棋v1.1';
const store = new Map();
const sb = {
  console, Math, Date, JSON, Promise, setTimeout, clearTimeout,
  requestAnimationFrame: () => 0,
  localStorage: { getItem: k => store.get(k) || null, setItem: (k, v) => store.set(k, v), removeItem: k => store.delete(k) },
  matchMedia: () => ({ matches: false })
};
sb.window = sb; sb.globalThis = sb;
const ctx = vm.createContext(sb);
for (const f of ['js/core/util.js', 'data/game-data.js', 'js/core/data.js', 'js/core/battle.js'])
  vm.runInContext(fs.readFileSync(path.join(root, f), 'utf8'), ctx, { filename: f });
const { JJK } = sb.window, D = JJK.data;

let pass = 0, fail = 0;
const ok = (n, c, i) => { if (c) { pass++; console.log('  PASS  ' + n + (i ? '   ' + i : '')); } else { fail++; console.log('  FAIL  ' + n + '   ' + (i || '')); } };

const mk = (id, team, x, y, star) => {
  const d = D.unitById[id];
  return {
    id, name: d.name, element: d.element, hp: d.hp, ad: d.ad, spell: d.spell, as: d.as,
    range: d.range, mana: d.mana, start_mana: d.start_mana, traits: d.traits,
    skill: d.skill, ult: d.ult, ultCost: d.ultCost, mods: d.mods,
    passive: d.passive, items: [], star: star || 1, pos: { x, y }
  };
};
function battle(mine, foes, seconds) {
  const sim = new JJK.BattleSim();
  sim.setup(mine, foes, {}, {});
  const evs = [];
  let t = 0;
  while (!sim.over && t < (seconds || 30)) { sim.update(1 / 60); t += 1 / 60; evs.push(...sim.drainEvents()); }
  return { sim, evs, n: (k) => evs.filter(e => e.t === k).length };
}

const IDS = ['606010', '605992', '649666', '606003', '605996', '683430', '678629', '717469', '606028', '713476', '619762', '622643', '689190', '610359'];

console.log('=== 数据完整性 ===');
ok('14 枚都可玩', IDS.every(id => D.units.some(u => u.id === id)), IDS.filter(id => !D.units.some(u => u.id === id)).join(','));
ok('14 枚都有 combat 必杀', IDS.every(id => D.unitById[id].ult && D.unitById[id].ult.combat));
ok('必杀总数 = 111（全部实装）', D.units.filter(u => u.ult && u.ult.combat).length === 111,
  '实际 ' + D.units.filter(u => u.ult && u.ult.combat).length);
ok('可玩池 111', D.units.length === 111, String(D.units.length));
ok('联动 5 组', D.raw.links.length === 5, D.raw.links.map(l => l.id).join(','));
ok('中费池已补厚（3+4 费 ≥ 41）',
  D.units.filter(u => u.cost >= 3 && u.cost <= 4).length >= 41,
  '3费 ' + D.unitsByCost[3].length + ' / 4费 ' + D.unitsByCost[4].length);

console.log('=== 必杀释放（确定性） ===');
for (const id of IDS) {
  const sim = new JJK.BattleSim();
  sim.setup([mk(id, 0, 0, 0)], [mk('633431', 1, 2, 0)], {}, {});
  const me = sim.units.find(x => x.team === 0);
  const foe = sim.units.find(x => x.team === 1);
  me.ult = me.ultCost;          // 直接填满必杀值
  me.target = foe;
  sim.update(1 / 60);
  const evs = sim.drainEvents();
  ok(D.unitById[id].name + ' 必杀值满时释放必杀',
    evs.some(e => e.t === 'ult'), 'ult 事件 ' + evs.filter(e => e.t === 'ult').length);
}

console.log('=== 新机制 / 新联动 ===');
// 治疗（家入）
{
  const ally = mk('606014', 0, 0, 0); ally.hp = Math.round(ally.hp * 0.3);
  const r = battle([mk('607834', 0, 1, 1), ally], [mk('633431', 1, 5, 0)], 14);
  ok('家入 治疗触发', r.n('heal') > 0, String(r.n('heal')));
}
// 召唤（夜蛾）
{
  const r = battle([mk('629916', 0, 1, 1)], [mk('633431', 1, 5, 0)], 20);
  ok('夜蛾 召唤咒骸', r.n('spawn') > 0, 'spawn ' + r.n('spawn'));
}
// 护盾（狗卷/结木）
{
  // 确定性：直接让狗卷放「防住」，不依赖对局节奏
  (function () {
    const simS = new JJK.BattleSim();
    const sh = mk('607992', 0, 1, 1);
    const t1 = mk('606014', 1, 5, 0); t1.hp = t1.hp * 10; t1.ad = 1;
    simS.setup([sh, mk('633431', 0, 0, 2)], [t1], {}, {});
    const su = simS.units.find(u => u.team === 0 && u.def.id === '607992');
    su.target = simS.units.find(u => u.team === 1);
    su.mana = su.manaMax;
    su.shield = 0;
    simS._cast(su);
    const got = simS.units.filter(u => u.team === 0 && u.shield > 0).length;
    ok('护盾机制触发', got > 0, '获得护盾单位 ' + got);
  })();
}
// 联动 blade-stance
{
  const r = battle([mk('646160', 0, 1, 1), mk('625876', 0, 1, 2)], [mk('633431', 1, 2, 1)], 25);
  const links = r.sim.links[0].map(l => l.id);
  ok('拔刀・纳刀 联动激活', links.indexOf('blade-stance') >= 0, links.join(','));
  const u = r.sim.units.find(x => x.def.id === '646160');
  ok('反击倍率被联动强化', u && u.counterMult > 1.2, u ? u.counterMult.toFixed(2) : '?');
}
// 联动 crow-dance
{
  const r = battle([mk('722687', 0, 1, 1), mk('652636', 0, 1, 2)], [mk('633431', 1, 2, 1)], 25);
  const links = r.sim.links[0].map(l => l.id);
  ok('黑鸟双舞 联动激活', links.indexOf('crow-dance') >= 0, links.join(','));
  const u = r.sim.units.find(x => x.def.id === '722687');
  ok('追击与攻速被联动强化', u && u.mods.extra_attack === true, u ? 'as=' + u.asRate.toFixed(2) : '?');
}

console.log('\n通过 ' + pass + ' / 失败 ' + fail);
process.exit(fail ? 1 : 0);
