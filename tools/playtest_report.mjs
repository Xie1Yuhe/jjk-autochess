/**
 * playtest_report.mjs —— 拟人化试玩，输出逐回合叙事日志
 *
 * 用法：
 *   node tools/playtest_report.mjs            # 简单/普通/困难各一局
 *   BAL_DECK=1 node tools/playtest_report.mjs # 用预设卡组开局
 */
import fs from 'fs';
import path from 'path';
import vm from 'vm';
import { fileURLToPath } from 'url';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const store = new Map();
const sandbox = {
  console, Math, Date, JSON, Promise, setTimeout, clearTimeout, performance,
  requestAnimationFrame: () => 0,
  localStorage: {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => store.set(k, v),
    removeItem: (k) => store.delete(k),
  },
  matchMedia: () => ({ matches: false }),
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
const ctx = vm.createContext(sandbox);
for (const f of ['js/core/util.js', 'data/game-data.js', 'js/core/data.js',
                 'js/core/battle.js', 'js/core/ai.js', 'js/core/game.js']) {
  vm.runInContext(fs.readFileSync(path.join(ROOT, f), 'utf8'), ctx, { filename: f });
}
const { JJK } = sandbox.window;
const D = JJK.data;

/* 拟人化打法：
   1. 前期存钱（留 10 金吃利息）
   2. 每回合买 1~2 张「能升星」或「新棋子」
   3. 4 人口后开始适度刷新
   4. 优先上阵高星 / 高费
*/
function playTurn(G) {
  const keep = G.round <= 3 ? 4 : (G.round <= 8 ? 8 : 0);
  const lvTarget = G.round <= 3 ? 3 : (G.round <= 8 ? 5 : 7);
  while (G.level < lvTarget && G.gold >= 14) {
    G.buyExp();
    if (G.level >= lvTarget) break;
  }
  let buys = 0;
  // 手里钱多就多买、多刷——模拟正常玩家的花钱节奏
  let cap = G.round <= 3 ? 2 : 3;
  if (G.gold > 30) cap = 6;
  if (G.gold > 50) cap = 9;
  for (let i = 0; i < 5 && buys < cap; i++) {
    const id = G.shop[i];
    if (!id) continue;
    const u = D.unitById[id];
    if (!u) continue;
    const canMerge = G._canMergeIntoExisting(id);
    const want = canMerge || G.benchUnits().length < 3 || u.cost >= 3;
    if (!want) continue;
    if (G.gold - u.cost < keep) continue;
    const r = G.buyFromShop(i);
    if (r && r.ok) buys += 1;
  }
  // 富余时刷新找可升星的棋子
  let rolls = G.gold > 50 ? 3 : (G.gold > 30 ? 2 : (G.gold > 20 && G.round >= 5 ? 1 : 0));
  for (let ri = 0; ri < rolls; ri++) {
    if (G.gold < 2) break;
    G.refreshShop();
    for (let i = 0; i < 5; i++) {
      const id = G.shop[i];
      if (!id) continue;
      const u = D.unitById[id];
      if (!u) continue;
      if (!G._canMergeIntoExisting(id) && G.benchUnits().length >= 4) continue;
      if (G.gold < u.cost) continue;
      const r = G.buyFromShop(i);
      if (r && r.ok) break;
    }
  }
  G.autoDeploy();
}

function traitsOnBoard(G) {
  const t = G.traitSummary ? G.traitSummary() : [];
  return (t || []).filter((x) => x.active)
    .map((x) => (D.traitById[x.id] ? D.traitById[x.id].name : x.id) + x.count)
    .slice(0, 4).join(' ');
}

function playOne(diff, deck) {
  const G = new JJK.Game();
  G.newGame(diff, true, deck);
  const log = [];
  let ultTotal = 0, battleSeconds = 0;

  for (let r = 0; r < 30; r++) {
    if (G.phase === 'gameover') break;
    const goldBefore = G.gold;
    playTurn(G);
    if (G.boardCount() === 0) {
      log.push({ round: G.round, note: '空场，轮空' });
      G.continueAfterResult();
      continue;
    }
    const comp = G.boardUnits().map((u) => {
      const d = D.unitById[u.id];
      return d.name.replace(/^\[[^\]]*\]\s*/, '') + (u.star > 1 ? u.star + '★' : '');
    }).join('、');
    const traits = traitsOnBoard(G);

    G.beginBattle();
    // 游戏内部每帧会抽走事件，这里先接管 drainEvents 计数
    let ults = 0;
    if (G.battle && G.battle.drainEvents && !G.battle.__patched) {
      const orig = G.battle.drainEvents.bind(G.battle);
      G.battle.__patched = true;
      G.battle.__ults = 0;
      G.battle.drainEvents = function () {
        const evs = orig();
        for (const e of evs) if (e.t === 'ult') this.__ults += 1;
        return evs;
      };
    }
    let steps = 0;
    while (G.phase === 'battle' && steps < 60 * 120) {
      G.tickBattle(1 / 30);
      steps += 1;
      // 事件由 battleview / 游戏内部消化，这里只读计数器
    }
    ults = (G.battle && G.battle.__ults) || 0;
    const secs = steps / 30;
    ultTotal += ults;
    battleSeconds += secs;
    const res = G.lastResult || {};
    log.push({
      round: G.round, kind: G.battleKind, enemy: res.enemyName || '',
      won: !!res.won, my: (res.myLeft || []).length, foe: (res.foeLeft || []).length,
      hp: G.hp, aiHp: G.ai.hp, level: G.level, gold: goldBefore,
      comp, traits, ults, secs: secs.toFixed(1),
      income: res.income ? res.income.total : 0,
    });
    if (G.phase === 'gameover') break;
    if (G.phase === 'result') G.continueAfterResult();
  }
  return { G, log, ultTotal, battleSeconds };
}

const useDeck = process.env.BAL_DECK === '1' && D.raw.decks && D.raw.decks.decks.length
  ? { id: D.raw.decks.decks[0].id, name: D.raw.decks.decks[0].name, units: D.raw.decks.decks[0].units }
  : null;

for (const diff of [0, 1, 2]) {
  const { G, log, ultTotal, battleSeconds } = playOne(diff, useDeck);
  const label = ['简单', '普通', '困难'][diff];
  const wins = log.filter((x) => x.won).length;
  console.log('\n══════════ ' + label + ' ══════════');
  if (useDeck) console.log('卡组：' + useDeck.name);
  console.log('结果：' + (G.phase === 'gameover' && G.hp > 0 ? '通关 ✓' : '阵亡 ✗') +
    '  回合 ' + G.round + '  HP ' + Math.max(0, G.hp) + ' vs 对手 ' + Math.max(0, G.ai.hp));
  console.log('战斗：' + wins + ' 胜 / ' + (log.length - wins) + ' 负' +
    '  必杀合计 ' + ultTotal + ' 次  战斗总时长 ' + battleSeconds.toFixed(0) + 's');
  console.log('─'.repeat(96));
  for (const r of log) {
    if (r.note) { console.log(`R${String(r.round).padStart(2)}  ${r.note}`); continue; }
    const tag = r.kind === 'pve' ? 'PvE' : 'PvP';
    console.log(
      `R${String(r.round).padStart(2)} ${tag} ${r.won ? '胜' : '负'} ` +
      `HP${String(r.hp).padStart(3)}/敌${String(r.aiHp).padStart(3)} ` +
      `Lv${r.level} 金${String(r.gold).padStart(2)} ` +
      `必杀${String(r.ults).padStart(2)} ${String(r.secs).padStart(4)}s  ` +
      `败方剩${r.foe}`
    );
    console.log(`     阵容：${r.comp}`);
    if (r.traits) console.log(`     羁绊：${r.traits}`);
  }
}
