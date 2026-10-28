/* =========================================================================
 *  util.js —— 基础设施：DOM 助手 / 数学 / 随机 / 事件总线 / 帧循环 / 补间
 *  浏览器直接以 <script> 引入，挂在 window.JJK 命名空间下。
 * ========================================================================= */
(function (global) {
  'use strict';

  var JJK = global.JJK = global.JJK || {};

  /* ---------------------------------------------------------------- DOM */
  function h(tag, attrs, children) {
    var e = document.createElement(tag);
    if (attrs) {
      for (var k in attrs) {
        if (!attrs.hasOwnProperty(k)) continue;
        var v = attrs[k];
        if (v === null || v === undefined || v === false) continue;
        if (k === 'class' || k === 'className') e.className = v;
        else if (k === 'html') e.innerHTML = v;
        else if (k === 'text') e.textContent = v;
        else if (k === 'style' && typeof v === 'object') {
          // 注意：CSS 自定义属性（--x）不能用 el.style['--x'] = v 赋值，
          // 那样会被 CSSStyleDeclaration 静默丢弃，必须走 setProperty。
          for (var s in v) {
            if (s.slice(0, 2) === '--') e.style.setProperty(s, v[s]);
            else e.style[s] = v[s];
          }
        } else if (k === 'data' && typeof v === 'object') {
          for (var d in v) e.dataset[d] = v[d];
        } else if (k.slice(0, 2) === 'on' && typeof v === 'function') {
          e.addEventListener(k.slice(2).toLowerCase(), v);
        } else {
          e.setAttribute(k, v);
        }
      }
    }
    addChildren(e, children);
    return e;
  }

  function addChildren(e, children) {
    if (children === null || children === undefined) return;
    if (Array.isArray(children)) {
      for (var i = 0; i < children.length; i++) addChildren(e, children[i]);
      return;
    }
    if (children.nodeType) e.appendChild(children);
    else e.appendChild(document.createTextNode(String(children)));
  }

  function qs(sel, root) { return (root || document).querySelector(sel); }
  function qsa(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }
  function clear(e) { while (e && e.firstChild) e.removeChild(e.firstChild); return e; }
  function on(e, type, fn, opts) { if (e) e.addEventListener(type, fn, opts); return fn; }
  function off(e, type, fn, opts) { if (e) e.removeEventListener(type, fn, opts); }

  /* --------------------------------------------------------------- 数学 */
  function clamp(v, a, b) { return v < a ? a : (v > b ? b : v); }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function sign(v) { return v > 0 ? 1 : (v < 0 ? -1 : 0); }
  function round(v, d) { var p = Math.pow(10, d || 0); return Math.round(v * p) / p; }
  function easeOutCubic(t) { return 1 - Math.pow(1 - t, 3); }
  function easeOutQuint(t) { return 1 - Math.pow(1 - t, 5); }

  /* --------------------------------------------------------------- 随机 */
  function rand(a, b) { return a + Math.random() * (b - a); }
  function randInt(a, b) { return Math.floor(a + Math.random() * (b - a + 1)); }
  function pick(arr) { return arr[Math.floor(Math.random() * arr.length)]; }
  function chance(p) { return Math.random() < p; }
  function shuffle(arr) {
    for (var i = arr.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = arr[i]; arr[i] = arr[j]; arr[j] = t;
    }
    return arr;
  }

  /* ----------------------------------------------------------- 事件总线 */
  function Bus() { this.map = {}; }
  Bus.prototype.on = function (name, fn) {
    (this.map[name] = this.map[name] || []).push(fn);
    return fn;
  };
  Bus.prototype.off = function (name, fn) {
    var l = this.map[name];
    if (!l) return;
    var i = l.indexOf(fn);
    if (i >= 0) l.splice(i, 1);
  };
  Bus.prototype.emit = function (name, payload) {
    var l = this.map[name];
    if (!l) return;
    for (var i = 0; i < l.length; i++) {
      try { l[i](payload); } catch (err) { console.error('[bus]', name, err); }
    }
  };

  /* --------------------------------------------------------- 帧循环 */
  var subs = [];
  var lastT = 0;
  var started = false;

  function tick(now) {
    var dt = lastT ? (now - lastT) / 1000 : 0.016;
    lastT = now;
    if (dt > 0.1) dt = 0.1;                  // 切标签页回来不要瞬移
    for (var i = 0; i < subs.length; i++) {
      try { subs[i](dt, now / 1000); } catch (e) { console.error('[tick]', e); }
    }
    requestAnimationFrame(tick);
  }

  function addTicker(fn) {
    subs.push(fn);
    if (!started) { started = true; requestAnimationFrame(tick); }
    return fn;
  }
  function removeTicker(fn) {
    var i = subs.indexOf(fn);
    if (i >= 0) subs.splice(i, 1);
  }

  /* ------------------------------------------------------------- 补间 */
  // 数值补间：数值变化更有质感（金币、生命、经验）
  var tweens = [];
  function tweenNumber(from, to, dur, onUpdate, onDone) {
    var t = { from: from, to: to, t: 0, dur: Math.max(0.001, dur), onUpdate: onUpdate, onDone: onDone };
    tweens.push(t);
    return t;
  }
  addTicker(function (dt) {
    for (var i = tweens.length - 1; i >= 0; i--) {
      var t = tweens[i];
      t.t += dt;
      var k = clamp(t.t / t.dur, 0, 1);
      t.onUpdate(lerp(t.from, t.to, easeOutCubic(k)), k);
      if (k >= 1) {
        tweens.splice(i, 1);
        if (t.onDone) t.onDone();
      }
    }
  });

  /* ------------------------------------------------------------- 其它 */
  function pad2(n) { return n < 10 ? '0' + n : '' + n; }
  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
  function nextFrame() { return new Promise(function (r) { requestAnimationFrame(function () { r(); }); }); }

  // 判断是否在减少动效（无障碍 + 低性能机器）
  var reduceMotion = false;
  try {
    reduceMotion = global.matchMedia && global.matchMedia('(prefers-reduced-motion: reduce)').matches;
  } catch (e) { /* ignore */ }

  JJK.util = {
    h: h, qs: qs, qsa: qsa, clear: clear, on: on, off: off,
    clamp: clamp, lerp: lerp, sign: sign, round: round,
    easeOutCubic: easeOutCubic, easeOutQuint: easeOutQuint,
    rand: rand, randInt: randInt, pick: pick, chance: chance, shuffle: shuffle,
    Bus: Bus, addTicker: addTicker, removeTicker: removeTicker, tweenNumber: tweenNumber,
    pad2: pad2, sleep: sleep, nextFrame: nextFrame,
    reduceMotion: reduceMotion
  };
  JJK.bus = new Bus();

})(window);
