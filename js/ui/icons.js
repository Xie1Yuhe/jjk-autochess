/* =========================================================================
 *  icons.js —— 羁绊/界面用的手绘 SVG 图标集
 *
 *  为什么不引第三方图标库：项目是零依赖、可离线双击运行的单页应用，
 *  任何 CDN 都会在断网时变成空白方块。这里用 24×24 的几何路径手绘，
 *  风格统一（粗笔画 + 圆角），并由 CSS 的 currentColor 着色。
 * ========================================================================= */
(function (global) {
  'use strict';

  var JJK = global.JJK = global.JJK || {};

  // 每个图标用 path 列表描述；stroke 表示只描边（fill:none）
  var SET = {
    /* ---------- 元素（特性）---------- */
    '夜': { d: ['M15.4 3.2a9 9 0 1 0 5.4 13.6A9.4 9.4 0 0 1 15.4 3.2z'], fill: true },
    '影': { d: ['M12 2.6l4.4 8.2-1.6 10.6h-5.6L7.6 10.8z', 'M9.2 11.4h5.6'], fill: true, second: 'stroke' },
    '幻': {
      d: ['M2.4 12S6 6.2 12 6.2 21.6 12 21.6 12 18 17.8 12 17.8 2.4 12 2.4 12z',
          'M12 8.6a3.4 3.4 0 1 1 0 6.8 3.4 3.4 0 0 1 0-6.8z',
          'M12 11a1 1 0 1 1 0 2 1 1 0 0 1 0-2z'],
      fill: false
    },
    '行': { d: ['M4.4 7.6h11.2', 'M4.4 12h15.2', 'M4.4 16.4h8.6', 'M16.4 7.6l3 2.2-3 2.2'], fill: false },

    /* ---------- 职业 ---------- */
    '体术': {
      d: ['M6.6 10.4V6.9a1.5 1.5 0 0 1 3 0v3.2', 'M9.6 9.8V5.6a1.5 1.5 0 0 1 3 0v4.2',
          'M12.6 10V6.9a1.5 1.5 0 0 1 3 0v3.4', 'M15.6 10.6V8.9a1.5 1.5 0 0 1 3 0v5.3c0 3.6-2.5 6.4-6 6.4s-6.1-2.6-6.1-6.3v-3.4a1.4 1.4 0 0 1 2.8 0'],
      fill: false
    },
    '术式': {
      d: ['M12 2.8l7.6 4.4v9.6L12 21.2 4.4 16.8V7.2z', 'M12 8.2a3.8 3.8 0 1 1 0 7.6 3.8 3.8 0 0 1 0-7.6z', 'M12 2.8v2.6M12 18.6v2.6'],
      fill: false
    },
    '咒灵': {
      d: ['M5.2 11.2c0-3.9 3-6.6 6.8-6.6s6.8 2.7 6.8 6.6c0 4.6-3 8.4-6.8 8.4s-6.8-3.8-6.8-8.4z',
          'M3.4 8.6c1.6-.9 2.9-.4 3.6.6', 'M20.6 8.6c-1.6-.9-2.9-.4-3.6.6'],
      fill: true, second: 'stroke'
    },
    '特级': {
      d: ['M3.6 8.4l4.2 3.1L12 4.6l4.2 6.9 4.2-3.1v9.4c0 .6-.5 1-1 1H4.6c-.6 0-1-.4-1-1z'],
      fill: true
    },

    /* ---------- 阵营 ---------- */
    '东京校': {
      d: ['M3.2 6.2h17.6', 'M5.6 6.2v13.4', 'M18.4 6.2v13.4', 'M7.4 10.2h9.2', 'M3.2 6.2c2.4-.8 5.4-1.2 8.8-1.2s6.4.4 8.8 1.2'],
      fill: false
    },
    '京都校': {
      d: ['M12 3.2l8.2 4.6H3.8z', 'M6.2 9.6h11.6', 'M7.4 13.6h9.2', 'M8.8 17.4h6.4', 'M4.6 20.8h14.8'],
      fill: false
    }
  };

  function svg(entry) {
    var NS = 'http://www.w3.org/2000/svg';
    var el = document.createElementNS(NS, 'svg');
    el.setAttribute('viewBox', '0 0 24 24');
    el.setAttribute('fill', 'none');
    el.setAttribute('aria-hidden', 'true');
    for (var i = 0; i < entry.d.length; i++) {
      var p = document.createElementNS(NS, 'path');
      p.setAttribute('d', entry.d[i]);
      var mode = (i === 0) ? (entry.fill ? 'fill' : 'stroke')
        : (entry.second === 'stroke' ? 'stroke' : (entry.fill ? 'fill' : 'stroke'));
      if (mode === 'fill') {
        p.setAttribute('fill', 'currentColor');
      } else {
        p.setAttribute('stroke', 'currentColor');
        p.setAttribute('stroke-width', '1.8');
        p.setAttribute('stroke-linecap', 'round');
        p.setAttribute('stroke-linejoin', 'round');
      }
      el.appendChild(p);
    }
    return el;
  }

  JJK.Icons = {
    trait: function (id) {
      return svg(SET[id] || SET['咒灵']);
    },
    has: function (id) { return !!SET[id]; },
    // 生成字符串形式（用于 innerHTML 场景）
    traitHTML: function (id) {
      var el = svg(SET[id] || SET['咒灵']);
      return el.outerHTML;
    }
  };

})(window);
