/* =========================================================================
 *  balance.mjs —— 平衡性实验场（不参与交付运行，只用来调难度曲线）
 *  用法： node tools/balance.mjs
 *  用一个"会看羁绊/会留利息/会冲星"的机器人跑多局，统计每回合胜负与最终排名。
 * ========================================================================= */
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const files = ['js/core/util.js', 'data/game-data.js', 'js/core/data.js', 'js/core/battle.js', 'js/core/ai.js', 'js/core/game.js'];
const store = new Map();
const sandbox = {
  console, Math, Date, JSON, Promise, setTimeout, clearTimeout, requestAnimationFrame: () => 0,
  localStorage: { getItem: (k) => (store.has(k) ? store.get(k) : null), setItem: (k, v) => store.set(k, v), removeItem: (k) => store.delete(k) },
  matchMedia: () => ({ matches: false })
};
sandbox.window = sandbox; sandbox.globalThis = sandbox;
const ctx = vm.createContext(sandbox);
for (const f of files) vm.runInContext(fs.readFileSync(path.join(ROOT, f), 'utf8'), ctx, { filename: f });
const { JJK } = sandbox.window;
const D = JJK.data;

function boardTraitCount(G, traitId) {
  return G.boardUnits().filter((r) => (D.unitById[r.id].traits || []).includes(traitId)).length;
}

// 一个"像人"的玩家：按阶段冲等级、优先补同名冲星、按羁绊选牌、留一点利息
function playTurn(G) {
  // 1) 先买牌（保证场上有棋子），再拿余钱冲等级
  for (let guard = 0; guard < 30; guard++) {
    let best = -1, bestScore = -1;
    for (let i = 0; i < G.shop.length; i++) {
      const id = G.shop[i];
      if (!id) continue;
      const u = D.unitById[id];
      if (u.cost > G.gold) continue;
      const same = G.roster.filter((r) => r.id === id);
      let score = u.cost * 4;
      if (u.cost >= 4 && G.round <= 8) score -= 34;      // 前期别碰 4/5 费
      if (u.cost >= 5 && G.round <= 10) score -= 40;
      if (same.length === 2) score += 70;              // 立刻能 2 星
      else if (same.length === 1) score += 30;
      if (same.some((r) => r.star >= 2)) score += 20;  // 冲 3 星
      for (const t of u.traits) score += boardTraitCount(G, t) * 8;
      if (G.freeBench() < 0) score -= 10;
      if (G.roster.length < G.level) score += 40;      // 先把人凑满
      if (score > bestScore) { bestScore = score; best = i; }
    }
    if (best < 0) break;
    const res = G.buyFromShop(best);
    if (!res.ok) break;
  }

  // 2) 冲人口：留 8 金当本钱
  const wantLevel = G.round <= 3 ? 4 : (G.round <= 6 ? 5 : (G.round <= 9 ? 6 : (G.round <= 13 ? 7 : 8)));
  while (G.level < wantLevel && G.gold >= 8) G.buyExp();

  // 3) 找 2 星：手里有同名对子就多刷几次
  var pairs = 0;
  var seen = {};
  G.roster.forEach(function (r) { if (r.star === 1) seen[r.id] = (seen[r.id] || 0) + 1; });
  Object.keys(seen).forEach(function (k) { if (seen[k] === 2) pairs++; });
  var rolls = pairs > 0 ? 2 : 1;
  for (var ri = 0; ri < rolls; ri++) {
    if (G.gold > (pairs > 0 ? 12 : 22) && G.round > 3) G.refreshShop();
  }

  // 4) 摆位：先上已经 2 星的，再按费用
  G.autoDeploy();
  const bench = G.benchUnits().slice().sort((a, b) => {
    const da = D.unitById[a.id], db = D.unitById[b.id];
    return (db.star * 10 + db.cost) - (da.star * 10 + da.cost);
  });
  for (const inst of bench) {
    const weakest = G.boardUnits().slice().sort((a, b) => {
      const da = D.unitById[a.id], db = D.unitById[b.id];
      return (da.star * 10 + da.cost) - (db.star * 10 + db.cost);
    })[0];
    if (!weakest) break;
    const dw = D.unitById[weakest.id], dn = D.unitById[inst.id];
    if (dn.star * 10 + dn.cost > dw.star * 10 + dw.cost) {
      const oldPos = { x: weakest.pos.x, y: weakest.pos.y };
      G.placeUnit(inst.uid, { type: 'cell', x: oldPos.x, y: oldPos.y });
      const back = G.unitById(weakest.uid);
      if (back && back.pos.x >= 0) {
        // 被换下的回到备战席
        const b = G.freeBench();
        if (b >= 0) G.placeUnit(back.uid, { type: 'bench', index: b });
      }
    }
  }

  // 5) 咒具：全部装备到场上星级最高的棋子上（会触发组件合成）
  while (G.itemsBag.length) {
    const carriers = G.boardUnits().slice().sort((a, b) => {
      const da = D.unitById[a.id], db = D.unitById[b.id];
      return (db.star * 10 + db.cost) - (da.star * 10 + da.cost);
    });
    let done = false;
    for (const c of carriers) {
      if (c.items.length >= 3) continue;
      const id = G.itemsBag[0];
      const r = G.equipItem(c.uid, id);
      if (r.ok) { done = true; break; }
    }
    if (!done) break;
  }
}

function runGame(diff, verbose) {
  const G = new JJK.Game();
  // BAL_DECK=1 时用第一套预设卡组，验证卡组模式下的难度
  var _deck = null;
  if (process.env.BAL_DECK === '1' && JJK.data.raw.decks && JJK.data.raw.decks.decks.length) {
    var _d0 = JJK.data.raw.decks.decks[0];
    _deck = { id: _d0.id, name: _d0.name, units: _d0.units };
  }
  G.newGame(diff, true, _deck);
  const rounds = [];
  for (let r = 0; r < 30; r++) {
    if (G.phase === 'gameover') break;
    playTurn(G);
    if (G.boardCount() === 0) { G.continueAfterResult(); continue; }
    G.beginBattle();
    let steps = 0;
    while (G.phase === 'battle' && steps < 60 * 120) { G.tickBattle(1 / 30); steps++; }
    const res = G.lastResult;
    rounds.push({
      round: G.round, won: res ? res.won : null, my: res ? res.myLeft.length : 0,
      foe: res ? res.foeLeft.length : 0, hp: G.hp, aiHp: G.ai.hp, level: G.level,
      kind: G.battleKind, enemy: res ? res.enemyName : '',
      comp: G.boardUnits().map((u) => D.unitById[u.id].name + (u.star > 1 ? u.star + '★' : '')).join(' ')
    });
    if (G.phase === 'gameover') break;
    if (G.phase === 'result') G.continueAfterResult();
  }
  return { G, rounds };
}

for (const diff of [0, 1, 2]) {
  const N = Number(process.env.BAL_N || 80);   // BAL_N=300 可加大样本，降低噪声
  const deathAt = [];
  let wins = 0, totalRounds = 0, winRound = [], detail = null;
  for (let i = 0; i < N; i++) {
    const { G, rounds } = runGame(diff, false);
    if (G.phase === 'gameover' && G.hp > 0) wins++;
    if (!(G.phase === 'gameover' && G.hp > 0)) deathAt.push(G.round + ':' + Math.max(0, G.hp));
    totalRounds += rounds.length;
    winRound.push(rounds.filter((r) => r.won).length / Math.max(1, rounds.length));
    if (i === 0) detail = rounds;
  }
  console.log('\n=== 难度 ' + ['简单', '普通', '困难'][diff] + ' ===');
  const hist = {}; deathAt.forEach(function (k) { hist[k] = (hist[k]||0)+1; });
  console.log('  死因分布(回合:hp): ' + Object.entries(hist).sort((a,b)=>b[1]-a[1]).slice(0,5).map(function(e){return e[0]+'x'+e[1];}).join('  '));
  console.log('  胜率 ' + (wins / N * 100).toFixed(0) + '%  ·  平均坚持 ' + (totalRounds / N).toFixed(1) + ' 回合' +
    '  ·  单局胜率 ' + (winRound.reduce((a, b) => a + b, 0) / N * 100).toFixed(0) + '%');
  if (detail) {
    console.log('  首局逐回合：');
    for (const r of detail) {
      console.log('   R' + String(r.round).padStart(2) + (r.won ? ' 胜' : ' 负') +
        '  我' + r.my + ' 敌' + r.foe + '  HP' + String(r.hp).padStart(3) + '  AI' + String(r.aiHp).padStart(3) +
        '  Lv' + r.level + '  [' + r.kind + '] ' + r.comp);
    }
  }
}
