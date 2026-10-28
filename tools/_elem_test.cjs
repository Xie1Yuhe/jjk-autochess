/* _elem_test.cjs —— 四属性首尾相衔（行→幻→夜→影→行）验证 */
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

// 造一个指定属性的单位
const mkE = (elem, team, x, y) => ({
  id: 'E' + elem + team, name: elem, element: elem, dmg: '体术',
  hp: 5000, ad: 100, spell: 100, as: 0.7, range: 1, mana: 100, start_mana: 0,
  traits: [], skill: { type: 'strike', power: 1 }, passive: {}, mods: {},
  items: [], star: 1, pos: { x, y }
});
function dmgOnce(srcElem, dstElem) {
  const sim = new JJK.BattleSim();
  sim.setup([mkE(srcElem, 0, 0, 0)], [mkE(dstElem, 1, 1, 0)], {}, {});
  const s = sim.units.find(u => u.team === 0);
  const d = sim.units.find(u => u.team === 1);
  const hp0 = d.hp;
  sim._deal(s, d, 1000, false);
  return hp0 - d.hp;
}

console.log('=== 克制表 ===');
ok('数据里有 elements', !!D.raw.elements, D.raw.elements ? D.raw.elements.order.join('→') : '缺失');
const base = dmgOnce('行', '行');   // 同属性 = 无加成
console.log('  基准伤害 ' + base.toFixed(1));

const beats = [['行', '幻'], ['幻', '夜'], ['夜', '影'], ['影', '行']];
for (const [a, b] of beats) {
  const v = dmgOnce(a, b);
  ok(a + ' 克 ' + b, v > base * 1.15, v.toFixed(1) + ' (>' + (base * 1.15).toFixed(1) + ')');
}
const loses = [['幻', '行'], ['夜', '幻'], ['影', '夜'], ['行', '影']];
for (const [a, b] of loses) {
  const v = dmgOnce(a, b);
  ok(a + ' 被 ' + b + ' 克', v < base * 0.95, v.toFixed(1) + ' (<' + (base * 0.95).toFixed(1) + ')');
}
const neutral = [['行', '夜'], ['影', '幻']];
for (const [a, b] of neutral) {
  const v = dmgOnce(a, b);
  ok(a + ' vs ' + b + ' 无克制关系', Math.abs(v - base) < 0.5, v.toFixed(1));
}

console.log('=== 弱点攻击（七海/真人） ===');
{
  const sim = new JJK.BattleSim();
  const hunter = mkE('行', 0, 0, 0);
  hunter.mods = { elemHunter: 0.15 };
  sim.setup([hunter], [mkE('幻', 1, 1, 0)], {}, {});
  const s = sim.units.find(u => u.team === 0);
  const d = sim.units.find(u => u.team === 1);
  const hp0 = d.hp;
  sim._deal(s, d, 1000, false);
  const v = hp0 - d.hp;
  ok('elemHunter 放大克制收益', v > base * 1.3, v.toFixed(1) + ' (>' + (base * 1.3).toFixed(1) + ')');
}

console.log('\n通过 ' + pass + ' / 失败 ' + fail);
process.exit(fail ? 1 : 0);
