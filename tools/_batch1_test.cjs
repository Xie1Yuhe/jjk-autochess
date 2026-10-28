/* _batch1_test.cjs —— 批次 1 十五枚棋子的实机机制验证 */
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
  if (!d) throw new Error('缺单位 ' + id);
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

console.log('=== 数据完整性 ===');
const IDS = ['607988', '706232', '661932', '606026', '640936', '644233', '684163',
  '607979', '721094', '699088', '609120', '639110', '637822', '646160', '606014'];
ok('15 枚都在可玩池', IDS.every(id => D.unitById[id]));
ok('15 枚都有 combat 必杀', IDS.every(id => D.unitById[id].ult && D.unitById[id].ult.combat));
ok('15 枚都有必杀槽', IDS.every(id => D.unitById[id].ultCost > 0),
  IDS.map(id => D.unitById[id].ultCost).join(','));
ok('全部 112 张都有必杀',
  D.units.filter(u => u.ult && u.ult.combat).length === 112,
  '实际 ' + D.units.filter(u => u.ult && u.ult.combat).length);
ok('三面板：体术技能走 phys', D.unitById['706232'].skill.panel === 'phys');
ok('三面板：术式技能走 magic', D.unitById['640936'].ult.panel === 'magic');
ok('三面板：复合技能标了 hybrid', D.unitById['699088'].skill.hybrid === true);

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

{
  const mine = ['607979', '721094', '661932', '606026', '644233'].map((id, i) => mk(id, 0, i % 2, Math.floor(i / 2)));
  const theirs = ['633431', '646160', '606014', '639110', '637822'].map((id, i) => mk(id, 1, 5 + (i % 2), Math.floor(i / 2)));
  mine.concat(theirs).forEach(d => { d.hp = Math.round(d.hp * 2); });
  const r = battle(mine, theirs, 40);
  ok('整场 5v5 有必杀累积并释放', r.n('ult') > 0, r.n('ult') + ' 次 · ' + r.sim.time.toFixed(1) + 's');
}

console.log('=== 各机制事件 ===');
{
  // 复活：熊猫
  const r = battle([mk('606014', 0, 0, 0)], [mk('684163', 1, 5, 0), mk('644233', 1, 6, 0)], 30);
  ok('熊猫复活触发', r.n('revive') > 0, String(r.n('revive')));
}
{
  // 退场：五条最强 / 无下限
  const me = mk('606026', 0, 0, 0); me.hp = Math.round(me.hp * 4);
  const tanky = mk('633431', 1, 5, 0); tanky.hp = Math.round(tanky.hp * 4); tanky.ad = 1;
  const r = battle([me], [tanky, mk('646160', 1, 6, 0)], 16);
  ok('五条[最强] 到点退场', r.n('retire') > 0, String(r.n('retire')));
}
{
  // 无敌：五条觉醒
  const r = battle([mk('661932', 0, 0, 0)], [mk('633431', 1, 5, 0)], 10);
  ok('五条[觉醒] 开场无敌生效', r.n('invuln') > 0, String(r.n('invuln')));
}
{
  // 反击：三轮霞
  const r = battle([mk('646160', 0, 0, 0)], [mk('633431', 1, 1, 0)], 20);
  ok('三轮霞反击触发', r.n('counter') > 0, String(r.n('counter')));
}
{
  // 计数黑闪：虎杖苍穹
  const r = battle([mk('706232', 0, 0, 0)], [mk('644233', 1, 1, 0)], 25);
  ok('虎杖计数黑闪触发', r.evs.some(e => e.t === 'bf'), 'bf ' + r.n('bf'));
}
{
  // 自损：狗卷
  // 确定性：填满必杀槽直接放，不依赖 30 秒里能不能攒够
  const simS = new JJK.BattleSim();
  const me = mk('637822', 0, 0, 0); me.hp *= 5;
  const f1 = mk('633431', 1, 5, 0); f1.hp *= 10; f1.ad = 1;
  simS.setup([me], [f1], {}, {});
  const uu = simS.units.find(x => x.team === 0);
  const ff = simS.units.find(x => x.team === 1);
  uu.target = ff; uu.ult = uu.ultCost;
  const evs = [];
  simS.update(1 / 60);
  for (const e of simS.drainEvents()) evs.push(e.t);
  ok('狗卷必杀自损触发', evs.indexOf('selfDamage') >= 0, evs.join(','));
}
{
  // 击杀回咒：夏油杰大义
  const weak = mk('646160', 1, 1, 0); weak.hp = 30; weak.ad = 1;
  const r = battle([mk('607979', 0, 0, 0)], [weak], 30);
  ok('夏油杰击杀回咒触发', r.n('manaGain') > 0, String(r.n('manaGain')));
}
{
  // 受击回血：宿傩
  const r = battle([mk('644233', 0, 0, 0)], [mk('633431', 1, 1, 0), mk('646160', 1, 2, 0)], 30);
  ok('宿傩受击回血触发', r.n('heal') > 0, String(r.n('heal')));
}
{
  // 嘲讽：熊猫
  const r = battle([mk('606014', 0, 0, 0)], [mk('633431', 1, 5, 0)], 20);
  ok('熊猫嘲讽触发', r.n('taunt') > 0, String(r.n('taunt')));
}

console.log('\n通过 ' + pass + ' / 失败 ' + fail);
process.exit(fail ? 1 : 0);
