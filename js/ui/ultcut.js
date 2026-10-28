/**
 *  ultcut.js —— 必杀「奥义图」切入 + 黑闪雷击演出
 *
 *  两个演出都放在这里，因为它们都要全屏层：
 *    · ultCutIn()   —— 横贯屏幕的必杀切入（角色立绘 + 必杀名）
 *    · boltStorm()  —— 黑闪触发的黑色闪电
 *
 *  立绘优先用 assets/art/<id>.webp（wiki 下载的全图，放进去就会自动生效），
 *  没有的话退回卡面 assets/cards/<id>.webp，用渐变遮罩让放大后不露怯。
 */
(function (window) {
  'use strict';

  var layer = null;
  var busy = false;

  function ensureLayer() {
    if (layer && document.body.contains(layer)) return layer;
    layer = document.getElementById('cut-layer');
    if (!layer) {
      layer = document.createElement('div');
      layer.id = 'cut-layer';
      layer.className = 'cut-layer';
      document.body.appendChild(layer);
    }
    return layer;
  }

  function artOf(u) {
    if (!u) return '';
    return 'assets/art/' + u.id + '.webp';
  }

  /**
   * 必杀奥义图
   * @param {object} u  棋子定义（需 id / name / card / element / rarityColor）
   * @param {string} name 必杀名
   * @param {number} team 0=我方 1=敌方
   */
  function ultCutIn(u, name, team) {
    if (!u) return;
    // 设置里可以关掉（加快节奏 / 刷局时不想看）
    try { if (localStorage.getItem('jjk_ultcut') === '0') return; } catch (e) {}
    // 同一时刻只放一张，避免多卡同时开必杀时糊成一片
    if (busy) return;
    var host = ensureLayer();
    var foe = team === 1;
    var el = document.createElement('div');
    el.className = 'ult-cut' + (foe ? ' is-foe' : ' is-mine');

    var art = document.createElement('div');
    art.className = 'uc-art';
    // 优先全图，加载失败退回卡面
    var img = document.createElement('img');
    img.src = artOf(u);
    img.alt = u.name || '';
    img.draggable = false;
    img.onerror = function () { img.onerror = null; img.src = u.card || ''; };
    art.appendChild(img);

    var band = document.createElement('div');
    band.className = 'uc-band';

    var glow = document.createElement('div');
    glow.className = 'uc-glow';

    var text = document.createElement('div');
    text.className = 'uc-text';
    // 侧边阵营大字：最能一眼看出是哪边在放
    var side = document.createElement('div');
    side.className = 'uc-side';
    side.innerHTML = '<b>' + (foe ? '敵' : '我') + '</b><span>' + (foe ? '方' : '方') + '</span>' +
                     '<i>' + (foe ? 'ENEMY' : 'ALLY') + '</i>';

    var k = document.createElement('div');
    k.className = 'uc-kicker';
    k.textContent = foe ? '敌方 · 必 杀' : '我方 · 必 杀';
    var t = document.createElement('div');
    t.className = 'uc-title';
    t.textContent = name || '必杀';
    var n = document.createElement('div');
    n.className = 'uc-name';
    n.textContent = u.name || '';
    text.appendChild(k); text.appendChild(t); text.appendChild(n);

    el.appendChild(band);
    el.appendChild(art);
    el.appendChild(glow);
    el.appendChild(side);
    el.appendChild(text);
    // 边框色条：我方金色在左，敌方血红在右
    var edge = document.createElement('div');
    edge.className = 'uc-edge';
    el.appendChild(edge);

    if (u.rarityColor) el.style.setProperty('--uc', u.rarityColor);
    host.appendChild(el);
    busy = true;

    // 演出结束清理（用 animationend 更可靠，setTimeout 兜底）
    var done = false;
    function finish() {
      if (done) return;
      done = true;
      busy = false;
      if (el.parentNode) el.parentNode.removeChild(el);
    }
    el.addEventListener('animationend', function (e) {
      if (e.target === el) finish();
    });
    setTimeout(finish, 1500);
  }

  /** 黑闪：从命中点向外劈出数道黑色锯齿闪电 */
  function boltStorm(px, py, opts) {
    opts = opts || {};
    var host = ensureLayer();
    var n = opts.count || 5;
    var wrap = document.createElement('div');
    wrap.className = 'bf-storm';
    wrap.style.left = px + 'px';
    wrap.style.top = py + 'px';

    var core = document.createElement('div');
    core.className = 'bf-core';
    wrap.appendChild(core);

    for (var i = 0; i < n; i++) {
      var ang = (Math.PI * 2 / n) * i + Math.random() * 0.7;
      var len = 110 + Math.random() * 120;
      var seg = 4 + Math.floor(Math.random() * 3);
      var d = 'M 0 0';
      for (var s = 1; s <= seg; s++) {
        var r = len * (s / seg);
        var jitter = (s === seg ? 0 : (Math.random() - 0.5) * 42);
        var x = Math.cos(ang) * r + Math.cos(ang + Math.PI / 2) * jitter;
        var y = Math.sin(ang) * r + Math.sin(ang + Math.PI / 2) * jitter;
        d += ' L ' + x.toFixed(1) + ' ' + y.toFixed(1);
      }
      var svgNS = 'http://www.w3.org/2000/svg';
      var svg = document.createElementNS(svgNS, 'svg');
      svg.setAttribute('class', 'bf-bolt');
      svg.setAttribute('width', '320');
      svg.setAttribute('height', '320');
      svg.setAttribute('viewBox', '-160 -160 320 320');
      svg.style.animationDelay = (i * 22) + 'ms';
      var path = document.createElementNS(svgNS, 'path');
      path.setAttribute('d', d);
      path.setAttribute('class', 'bf-line');
      path.setAttribute('fill', 'none');
      path.setAttribute('stroke-linecap', 'round');
      path.setAttribute('stroke-linejoin', 'round');
      svg.appendChild(path);
      // 白热芯：叠一条细的，制造「黑雷外面裹着白光」的层次
      var coreLine = document.createElementNS(svgNS, 'path');
      coreLine.setAttribute('d', d);
      coreLine.setAttribute('class', 'bf-line-core');
      coreLine.setAttribute('fill', 'none');
      coreLine.setAttribute('stroke-linecap', 'round');
      coreLine.setAttribute('stroke-linejoin', 'round');
      svg.appendChild(coreLine);
      wrap.appendChild(svg);
    }

    host.appendChild(wrap);
    setTimeout(function () {
      if (wrap.parentNode) wrap.parentNode.removeChild(wrap);
    }, 620);
  }

  window.JJK = window.JJK || {};
  window.JJK.Cut = { ultCutIn: ultCutIn, boltStorm: boltStorm, isBusy: function () { return busy; } };
})(window);
