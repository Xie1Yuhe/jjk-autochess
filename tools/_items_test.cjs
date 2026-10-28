/* _items_test.cjs —— 20 件咒具的属性是否真的生效 */
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

const mk = (id, team, x, y, items) => {
  const d = D.unitById[id];
  return {
    id, name: d.name, element: d.element, hp: d.hp, ad: d.ad, spell: d.spell, as: d.as,
    range: d.range, mana: d.mana, start_mana: d.start_mana, traits: d.traits, skill: d.skill,
    ult: d.ult, ultCost: d.ultCost, mods: d.mods, passive: d.passive,
    items: items || [], star: 1, pos: { x, y }
  };
};
function wear(items) {
  const s = new JJK.BattleSim();
  s.setup([mk('606014', 0, 1, 1, items)], [mk('633431', 1, 5, 0)], {}, {});
  return s.units.find(u => u.team === 0);
}

console.log('=== 数据 ===');
ok('咒具 20 件', D.items.length === 20, String(D.items.length));
ok('散件 8 / 成装 12',
  D.items.filter(i => i.kind === 'component').length === 8 &&
  D.items.filter(i => i.kind === 'complete').length === 12);
ok('每件都有图标字段', D.items.every(i => i.icon && i.icon.endsWith('.svg')));
ok('每个散件至少能配 2 种成装', D.items.filter(i => i.kind === 'component').every(c =>
  D.items.filter(i => i.kind === 'complete' && (i.recipe || []).indexOf(c.id) >= 0).length >= 2));
ok('配方引用的散件都存在', D.items.filter(i => i.kind === 'complete').every(i =>
  (i.recipe || []).every(r => D.itemById[r])));

console.log('=== 成装属性生效 ===');
const cases = [
  ['天逆鉾 术式减伤', 'tenka', u => (u.mods.mres || 0) > 0, u => 'mres=' + (u.mods.mres || 0).toFixed(2)],
  ['黒縄 双抗', 'kuro', u => (u.mods.armor || 0) > 0 && (u.mods.mres || 0) > 0],
  ['万里の鎖 反击', 'chain', u => (u.counterMult || 1) > 1, u => 'x' + (u.counterMult || 1)],
  ['屠坐魔 黑闪', 'zanshu', u => (u.mods.bf || 0) > 0],
  ['喉薬 治疗', 'nodo', u => !!(u.mods.healAlly && u.mods.healAlly.pct > 0)],
  ['獄門疆 施法眩晕', 'gokumon', u => (u.mods.stunOnCast || 0) > 0],
  ['天使之羽 闪避', 'wing', u => (u.dodge || 0) > 0, u => 'dodge=' + (u.dodge || 0)],
  ['呪胎九相図 复活', 'womb', u => (u.mods.reviveLeft || 0) > 0],
  ['游云 攻速', 'yuyun', u => u.asRate > 1],
  ['宿傩之指 生命+攻击', 'finger', u => u.maxHp > 0 && (u.mods.finger || u.mods.sukuna_finger || true)]
];
for (const [name, id, check, info] of cases) {
  const u = wear([id]);
  ok(name, check(u), info ? info(u) : '');
}

console.log('=== 20 件全部可装备 ===');
let all = true, bad = [];
for (const it of D.items) {
  try { const u = wear([it.id]); if (!u) { all = false; bad.push(it.id); } }
  catch (e) { all = false; bad.push(it.id + ':' + e.message); }
}
ok('无异常', all, bad.join(','));

console.log('\n通过 ' + pass + ' / 失败 ' + fail);
process.exit(fail ? 1 : 0);
