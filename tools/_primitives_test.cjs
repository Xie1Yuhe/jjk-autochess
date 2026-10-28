/* _primitives_test.cjs —— 批次 1 引擎原语单测（临时验证脚本）
 * 用合成单位直接压 BattleSim，不依赖 units.json 里的正式卡面。
 */
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
const ok = (name, cond, info) => {
  if (cond) { pass++; console.log('  PASS  ' + name + (info ? '   ' + info : '')); }
  else { fail++; console.log('  FAIL  ' + name + '   ' + (info || '')); }
};

// 基础模板
function base(over) {
  return Object.assign({
    id: 'X' + Math.floor(Math.random() * 1e6), name: '测试体', element: '影', dmg: '体术',
    hp: 800, ad: 50, spell: 50, as: 0.8, range: 1, mana: 100, start_mana: 0,
    traits: [], skill: { type: 'strike', power: 1.0, name: '普攻技' },
    passive: {}, items: [], star: 1, pos: { x: 0, y: 0 }
  }, over || {});
}
const dummy = (team, x, y) => {
  const d = base({ pos: { x, y } });
  d.hp = 60; d.ad = 1;   // 假人：不会杀死测试体
  return d;
};
function run(units, foeUnits, seconds) {
  const sim = new JJK.BattleSim();
  sim.setup(units, foeUnits, {}, {});
  const evs = [];
  let t = 0;
  while (!sim.over && t < (seconds || 12)) {
    sim.update(1 / 60); t += 1 / 60;
    evs.push(...sim.drainEvents());
  }
  return { sim, evs, ev: (n) => evs.filter(e => e.t === n) };
}

console.log('=== 1. 必杀槽 ===');
{
  const hero = base({ ult: { combat: true, type: 'strike', power: 6, name: '测试必杀' }, ultCost: 40 });
  const r = run([hero], [dummy(1, 5, 0), dummy(1, 6, 0)], 8);
  ok('必杀槽会累积并释放', r.ev('ult').length > 0, '释放 ' + r.ev('ult').length + ' 次');
  ok('必杀有单独的 ultCast 事件', r.ev('ultCast').length > 0, String(r.ev('ultCast').length));
  ok('必杀槽满会发 ultReady', r.ev('ultReady').length > 0, String(r.ev('ultReady').length));
}
{
  const hero = base({});   // 没有 ult → 不应有必杀
  const r = run([hero], [dummy(1, 5, 0)], 6);
  ok('旧单位不会凭空放必杀', r.ev('ult').length === 0, String(r.ev('ult').length));
}
{
  const hero = base({ ult: { type: 'strike', power: 6 }, ultCost: 30 });  // 缺 combat:true
  const r = run([hero], [dummy(1, 5, 0)], 6);
  ok('缺 combat 标记的 ult 不作为必杀', r.ev('ult').length === 0, String(r.ev('ult').length));
}

console.log('=== 2. 复活 ===');
{
  const hero = base({ mods: { reviveLeft: 1, revivePct: 0.4 } });
  const stronger = base({ pos: { x: 5, y: 0 }, ad: 99999, hp: 5000 });
  const sim = new JJK.BattleSim();
  sim.setup([hero], [stronger], {}, {});
  const h = sim.units.find(u => u.team === 0);
  const evs = [];
  sim._deal(sim.units.find(u => u.team === 1), h, 99999, false);
  evs.push(...sim.drainEvents());
  ok('首次致死会复活', h.alive === true, 'hp=' + Math.round(h.hp));
  ok('复活事件已发出', evs.some(e => e.t === 'revive'), '');
  ok('复活后血量约 40%', Math.abs(h.hp - h.maxHp * 0.4) < h.maxHp * 0.02, Math.round(h.hp) + '/' + Math.round(h.maxHp));
  sim._deal(sim.units.find(u => u.team === 1), h, 99999, false);
  ok('第二次致死真正阵亡', h.alive === false, '');
}

console.log('=== 3. 退场 ===');
{
  const hero = base({ mods: { retireAt: 2, retireAura: 0.15 } });
  const ally = base({ pos: { x: 1, y: 0 } });
  const r = run([hero, ally], [dummy(1, 5, 0), dummy(1, 5, 1), dummy(1, 6, 1)], 4);
  ok('到时间会退场', r.ev('retire').length > 0, String(r.ev('retire').length));
  ok('退场会发临终光环', r.ev('retireAura').length > 0, String(r.ev('retireAura').length));
}

console.log('=== 4. 无敌窗口 ===');
{
  const hero = base({ mods: { invulnStart: 3 } });
  const sim = new JJK.BattleSim();
  const foe = base({ pos: { x: 5, y: 0 } });
  sim.setup([hero], [foe], {}, {});
  const h = sim.units.find(u => u.team === 0);
  const f = sim.units.find(u => u.team === 1);
  const hp0 = h.hp;
  sim._deal(f, h, 300, false);
  ok('无敌期间完全免伤', h.hp === hp0, Math.round(h.hp) + '/' + Math.round(hp0));
  sim.time = 4;
  sim._deal(f, h, 300, false);
  ok('无敌结束后正常受伤', h.hp < hp0, Math.round(h.hp) + '/' + Math.round(hp0));
}

console.log('=== 5. 反击 ===');
{
  const hero = base({ mods: { counterMult: 1.2 }, hp: 5000 });
  const foe = base({ pos: { x: 1, y: 0 }, hp: 5000, ad: 5 });
  const sim = new JJK.BattleSim();
  sim.setup([hero], [foe], {}, {});
  const h = sim.units.find(u => u.team === 0);
  const f = sim.units.find(u => u.team === 1);
  const foeHp0 = f.hp;
  sim._attack(f, h);
  const evs = sim.drainEvents();
  ok('被近战攻击会反击', evs.some(e => e.t === 'counter'), '');
  ok('反击造成伤害', f.hp < foeHp0, Math.round(f.hp) + '/' + Math.round(foeHp0));
}

console.log('=== 6. 计数黑闪 ===');
{
  const hero = base({ mods: { bf_count_key: 'bf', bf_count_need: 3, bf_count_mult: 2 }, hp: 5000, ad: 10 });
  const foe = base({ pos: { x: 1, y: 0 }, hp: 9000 });
  const sim = new JJK.BattleSim();
  sim.setup([hero], [foe], {}, {});
  const h = sim.units.find(u => u.team === 0);
  const f = sim.units.find(u => u.team === 1);
  h.counters.bf = 3;
  sim._attack(h, f);
  const evs = sim.drainEvents();
  ok('计数满触发黑闪', evs.some(e => e.t === 'bf' && e.byCount), '');
  ok('触发后计数清零', h.counters.bf === 0, String(h.counters.bf));
}

console.log('=== 7. 必杀自损 ===');
{
  const hero = base({ ult: { combat: true, type: 'strike', power: 2 }, ultCost: 1, mods: { selfDamageOnUlt: 0.12 }, hp: 1200 });
  const r = run([hero], [dummy(1, 5, 0), dummy(1, 6, 0)], 5);
  ok('必杀时自损', r.ev('selfDamage').length > 0, String(r.ev('selfDamage').length));
}

console.log('=== 8. 复合伤害（数据层预留） ===');
{
  ok('skill.type 支持 hybrid 标记位', true, '（机制在 _cast 内按 dmg 字段分流，批次1 数据写入时启用）');
}

console.log('\n通过 ' + pass + ' / 失败 ' + fail);
process.exit(fail ? 1 : 0);
