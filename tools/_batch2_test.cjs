/* _batch2_test.cjs —— 批次 2 十四枚棋子的实机机制验证 */
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

const IDS = ['632100', '695641', '668491', '621266', '619763', '684667',
  '607872', '677690', '607873', '618983', '703204', '691924', '642790', '722687'];

console.log('=== 数据完整性 ===');
ok('14 枚都在可玩池', IDS.every(id => D.unitById[id]), IDS.filter(id => !D.unitById[id]).join(','));
ok('14 枚都有 combat 必杀', IDS.every(id => D.unitById[id].ult && D.unitById[id].ult.combat));
ok('必杀总数 = 111（全部实装）',
  D.units.filter(u => u.ult && u.ult.combat).length === 111,
  '实际 ' + D.units.filter(u => u.ult && u.ult.combat).length);
ok('冥冥已进入可玩池', D.unitById['722687'] && D.units.some(u => u.id === '722687'));

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

console.log('=== 新机制 ===');
// 即死（真人）
{
  const sim = new JJK.BattleSim();
  sim.setup([mk('619763', 0, 0, 0)], [mk('684163', 1, 1, 0)], {}, {});
  const me = sim.units.find(u => u.team === 0);
  const foe = sim.units.find(u => u.team === 1);
  foe.hp = foe.maxHp * 0.15;      // 压到 15% < 25% 阈值
  me.mana = me.manaMax;
  me.target = foe;
  sim._cast(me);
  const evs = sim.drainEvents();
  ok('真人 即死处决触发', evs.some(e => e.t === 'execute') && !foe.alive,
    'execute=' + evs.filter(e => e.t === 'execute').length + ' alive=' + foe.alive);
}
// 削弱（花御）
{
  // 确定性：直接让花御对目标施法，避免"还没放技能就死/对面先死"
  const sim1 = new JJK.BattleSim();
  const h = mk('607873', 0, 2, 1);
  const tanky1 = mk('633431', 1, 6, 1); tanky1.hp = tanky1.hp * 20; tanky1.ad = 1;
  sim1.setup([h, mk('606014', 0, 2, 2)], [tanky1], {}, {});
  const hu = sim1.units.find(u => u.team === 0 && u.def.id === '607873');
  const foe = sim1.units.find(u => u.team === 1);
  hu.target = foe; hu.mana = hu.manaMax;
  sim1._cast(hu);
  ok('花御 降低敌方伤害', foe && foe.mods.dmg_out > 0, 'dmg_out=' + (foe ? (foe.mods.dmg_out || 0).toFixed(2) : '?'));
}
// 不屈复活（七海 无言的压制）
{
  const r = battle([mk('695641', 0, 0, 0)], [mk('684163', 1, 5, 0), mk('644233', 1, 6, 0)], 30);
  ok('七海[无言的压制] 不屈复活', r.n('revive') > 0, String(r.n('revive')));
}
// 计数成长（冥冥）
{
  const sim = new JJK.BattleSim();
  sim.setup([mk('722687', 0, 0, 0)], [mk('633431', 1, 1, 0)], {}, {});
  const u = sim.units.find(x => x.team === 0);
  const ad0 = u.ad;
  sim.addCounter(u, 'kuro', 5);
  ok('冥冥 黑鸟操术提升攻击', u.ad > ad0, ad0.toFixed(1) + ' → ' + u.ad.toFixed(1));
}
// 易伤叠加（真人暴露的灵魂）
{
  const sim2 = new JJK.BattleSim();
  const me = mk('684667', 0, 2, 1);
  const tanky2 = mk('633431', 1, 6, 1); tanky2.hp = tanky2.hp * 20; tanky2.ad = 1;
  sim2.setup([me], [tanky2], {}, {});
  const ru = sim2.units.find(u => u.team === 0);
  const foe = sim2.units.find(u => u.team === 1);
  ru.target = foe; ru.mana = ru.manaMax;
  sim2._cast(ru);
  ok('真人[暴露的灵魂] 挂易伤', foe && (foe.mods.dmg_taken || 0) > 0, 'dmg_taken=' + (foe ? (foe.mods.dmg_taken || 0).toFixed(2) : '?'));
}

console.log('\n通过 ' + pass + ' / 失败 ' + fail);
process.exit(fail ? 1 : 0);
