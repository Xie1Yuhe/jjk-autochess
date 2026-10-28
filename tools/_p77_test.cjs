/* _p77_test.cjs —— P7-7 五项补齐的独立验证 */
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

console.log('=== P7-7 五项补齐 ===');

// 1) 免疫控制
{
  const r = battle([mk('684163', 0, 2, 1)], [mk('640936', 1, 5, 1)], 20);
  const s = r.sim.units.find(u => u.def.id === '684163');
  ok('宿傩[火力胜负] 免疫控制', s && s.mods.immuneControl === true && s.stun <= 0.001,
    'stun=' + (s ? s.stun.toFixed(2) : '?'));
}
// 2) 反转术式
{
  const ally = mk('606014', 0, 2, 2); ally.hp = Math.round(ally.hp * 0.3);
  const r = battle([mk('699088', 0, 2, 1), ally], [mk('633431', 1, 6, 1)], 14);
  ok('乙骨 反转术式治疗残血友军', r.n('reverseHeal') > 0, String(r.n('reverseHeal')) + ' 次');
}
// 3) 必杀后禁咒
{
  const r = battle([mk('640936', 0, 2, 1), mk('606014', 0, 2, 2)], [mk('633431', 1, 6, 1), mk('646160', 1, 6, 2)], 22);
  ok('五条[无下限] 必杀后咒力归零 + 禁咒', r.n('manaLock') > 0, String(r.n('manaLock')) + ' 次');
}
// 4) 低咒力回必杀值
{
  const sim = new JJK.BattleSim();
  sim.setup([mk('609120', 0, 0, 0)], [mk('633431', 1, 6, 0)], {}, {});
  const u = sim.units.find(x => x.team === 0);
  u.mana = 0;
  const u0 = u.ult;
  for (let i = 0; i < 60; i++) sim._tickSpecials(1 / 60);
  ok('伏黑 低咒力时必杀值自动增长', u.ult > u0, u0.toFixed(1) + ' → ' + u.ult.toFixed(1));
}
// 5a) 计数成长
{
  const sim = new JJK.BattleSim();
  sim.setup([mk('646160', 0, 0, 0)], [mk('633431', 1, 1, 0)], {}, {});
  const u = sim.units.find(x => x.team === 0);
  const ad0 = u.ad;
  sim.addCounter(u, 'bato', 3);
  ok('三轮霞 拔刀计数提升攻击', u.ad > ad0, ad0.toFixed(1) + ' → ' + u.ad.toFixed(1));
  sim.addCounter(u, 'bato', 20);
  ok('拔刀计数封顶 8 层', u.counters.bato === 8, String(u.counters.bato));
}
// 5b) 暴击回咒
{
  const sim = new JJK.BattleSim();
  sim.setup([mk('684163', 0, 0, 0)], [mk('633431', 1, 1, 0)], {}, {});
  const u = sim.units.find(x => x.team === 0);
  const f = sim.units.find(x => x.team === 1);
  u.mana = 0;
  u.mods.bf = 1;   // 必定黑闪
  sim._attack(u, f);
  ok('宿傩 暴击（黑闪）回咒', u.mana > 0, 'mana=' + Math.round(u.mana));
}

console.log('\n通过 ' + pass + ' / 失败 ' + fail);
process.exit(fail ? 1 : 0);
