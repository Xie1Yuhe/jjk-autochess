/* =========================================================================
 *  smoke.js —— 冒烟测试：从标题页点「开始对局」进入，抓运行期错误
 *  用法：把本文件注入 index.html 后无头跑，结果写在 document.title
 * ========================================================================= */
(function () {
  'use strict';
  var errors = [];
  window.addEventListener('error', function (e) {
    errors.push((e.message || 'error') + ' @' + (e.filename || '').split('/').pop() + ':' + e.lineno);
  });
  window.addEventListener('unhandledrejection', function (e) {
    errors.push('promise: ' + (e.reason && e.reason.message || e.reason));
  });
  var origErr = console.error;
  console.error = function () {
    try { errors.push('console: ' + Array.prototype.join.call(arguments, ' ')); } catch (e) { /* ignore */ }
    origErr.apply(console, arguments);
  };

  function finish() {
    var JJK = window.JJK;
    var g = JJK && JJK.App && JJK.App.game;
    document.title = 'SMOKE ' + JSON.stringify({
      errors: errors.slice(0, 8),
      errCount: errors.length,
      inGame: !!(JJK && JJK.App && JJK.App.inGame),
      screenActive: document.getElementById('screen-game').classList.contains('is-active'),
      round: g ? g.round : -1,
      gold: g ? g.gold : -1,
      shopCards: document.querySelectorAll('.shop-card').length,
      benchUnits: document.querySelectorAll('.bench-unit').length,
      hudGold: (document.getElementById('v-gold') || {}).textContent,
      bgTitle: (getComputedStyle(document.querySelector('.tc-logo')).fontFamily || '').slice(0, 28),
      cellVar: getComputedStyle(document.documentElement).getPropertyValue('--cell').trim(),
      cardW: (function () {
        var c = document.querySelector('.shop-card');
        return c ? Math.round(c.getBoundingClientRect().width) : 0;
      })(),
      imgsBroken: Array.prototype.filter.call(document.images, function (i) { return i.complete && i.naturalWidth === 0; })
        .map(function (i) { return (i.currentSrc || i.src || '').split('/').pop(); }).slice(0, 8)
    });
  }

  window.addEventListener('load', function () {
    setTimeout(function () {
      var btn = document.getElementById('btn-start-game');
      if (btn) btn.click();
      // 再点一张商店卡，确认购买链路
      setTimeout(function () {
        var card = document.querySelector('.shop-card:not(.is-empty)');
        if (card) card.click();
        setTimeout(finish, 500);
      }, 600);
    }, 500);
  });
})();
