# -*- coding: utf-8 -*-
r"""
patch_lock_chain3.py —— 锁与链条画在同一个 SVG 坐标系里

之前用两个绝对定位的 SVG 互相对齐，反复出现「锁跑到左边」的问题。
这一版彻底不管 CSS 定位：所有东西都画在 `viewBox="0 0 100 140"` 里，
锁的中心固定在 (50,70)，链条也从 (50,70) 向四角发射。
"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = os.path.join(ROOT, "js", "ui", "shop.js")
s = io.open(p, encoding="utf-8").read()

start = "  // 锁定标记：中央挂锁 + 四条链子向四角蔓延"
end = "  function invalidate() { lastSig = ''; }"
i = s.index(start)
j = s.index(end)

block = '''  // 锁定标记：锁与链条全部画在同一个 SVG 坐标系里（viewBox 100x140）
  var NS_SVG = 'http://www.w3.org/2000/svg';
  function svgEl(tag, attrs) {
    var el = document.createElementNS(NS_SVG, tag);
    for (var k in attrs) if (attrs.hasOwnProperty(k)) el.setAttribute(k, attrs[k]);
    return el;
  }

  function lockSVG() {
    var svg = svgEl('svg', {
      viewBox: '0 0 100 140',
      preserveAspectRatio: 'xMidYMid meet',
      'class': 'sc-lock-svg'
    });
    svg.style.cssText = 'position:absolute;left:0;top:0;width:100%;height:100%;overflow:visible;';

    var CX = 50, CY = 70;

    // ---------- 四条链子：从中心向四角 ----------
    var corners = [[2, 2], [98, 2], [2, 138], [98, 138]];
    corners.forEach(function (c, ci) {
      var dx = c[0] - CX, dy = c[1] - CY;
      var len = Math.sqrt(dx * dx + dy * dy);
      var pitch = 7.0;
      var n = Math.max(3, Math.floor(len / pitch));
      var ang = Math.atan2(dy, dx) * 180 / Math.PI;

      for (var k = 1; k <= n; k++) {
        var t = (k - 0.5) / n;
        var px = CX + dx * t;
        var py = CY + dy * t;
        var along = (k % 2 === 1);
        var el = svgEl('ellipse', {
          cx: px.toFixed(2), cy: py.toFixed(2),
          rx: along ? '3.9' : '2.4',
          ry: along ? '2.3' : '3.8',
          transform: 'rotate(' + ang.toFixed(1) + ' ' + px.toFixed(2) + ' ' + py.toFixed(2) + ')',
          fill: 'none',
          stroke: along ? '#ffeab0' : '#c8b271',
          'stroke-width': '2.1',
          'class': 'sc-chain-link'
        });
        el.style.animationDelay = (ci * 0.05 + t * 0.24).toFixed(3) + 's';
        svg.appendChild(el);
      }
    });

    // ---------- 中央挂锁（画在同一坐标系） ----------
    var g = svgEl('g', { 'class': 'sc-padlock' });
    // 锁梁
    g.appendChild(svgEl('path', {
      d: 'M42 74 V62 a8 8 0 0 1 16 0 V74',
      fill: 'none', stroke: '#8a6512', 'stroke-width': '6.4', 'stroke-linecap': 'round'
    }));
    g.appendChild(svgEl('path', {
      d: 'M42 74 V62 a8 8 0 0 1 16 0 V74',
      fill: 'none', stroke: '#ffd97a', 'stroke-width': '4.0', 'stroke-linecap': 'round'
    }));
    // 锁体
    g.appendChild(svgEl('rect', {
      x: '34', y: '72', width: '32', height: '26', rx: '5',
      fill: '#f3c33f', stroke: '#8a6512', 'stroke-width': '1.8'
    }));
    // 锁体高光
    g.appendChild(svgEl('rect', {
      x: '36.5', y: '74', width: '27', height: '7', rx: '3',
      fill: 'rgba(255,255,255,.35)'
    }));
    // 钥匙孔
    g.appendChild(svgEl('circle', { cx: '50', cy: '83', r: '3.2', fill: '#4a3407' }));
    g.appendChild(svgEl('rect', { x: '48.7', y: '84', width: '2.6', height: '6.6', rx: '1.1', fill: '#4a3407' }));
    svg.appendChild(g);

    return svg;
  }

  function syncLockBadge(card, on) {
    var badge = card.querySelector('.sc-lock');
    if (on && !badge) {
      badge = h('div', { class: 'sc-lock' });
      badge.style.cssText = 'position:absolute;left:0;top:0;width:100%;height:100%;' +
                            'pointer-events:none;z-index:9;overflow:visible;';
      badge.appendChild(lockSVG());
      card.appendChild(badge);
    } else if (!on && badge) {
      badge.parentNode.removeChild(badge);
    }
  }

'''
s = s[:i] + block + s[j:]
io.open(p, "w", encoding="utf-8").write(s)
print("[lock] 单 SVG 坐标系版本已写入")
