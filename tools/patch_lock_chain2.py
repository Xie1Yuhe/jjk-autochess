# -*- coding: utf-8 -*-
r"""
patch_lock_chain2.py —— 用「显式链环」重做锁链与挂锁

上一版的两个问题：
  1. 🔒 依赖 emoji 字体，headless / 部分系统里渲染成方块
  2. SVG <pattern> 填充 stroke 在非等比缩放下不可靠，链环没画出来

这一版：
  · 挂锁改用 SVG 手绘（锁体 + 锁梁 + 钥匙孔），任何环境都能渲染
  · 锁链用**一个个椭圆链环**沿对角线排布，交替横竖，做出真链子的咬合感
  · 从中心向四角依次长出（每环带延迟）
"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = os.path.join(ROOT, "js", "ui", "shop.js")
s = io.open(p, encoding="utf-8").read()

start = "  // 锁定标记：中央大锁 + 四条锁链向四角蔓延"
end = "  function invalidate() { lastSig = ''; }"
i = s.index(start)
j = s.index(end)

block = '''  // 锁定标记：中央挂锁 + 四条链子向四角蔓延
  // 链环用显式椭圆绘制（不依赖 <pattern>），每环略微旋转，形成真链子的咬合感
  var NS_SVG = 'http://www.w3.org/2000/svg';
  function svgEl(tag, attrs) {
    var el = document.createElementNS(NS_SVG, tag);
    for (var k in attrs) if (attrs.hasOwnProperty(k)) el.setAttribute(k, attrs[k]);
    return el;
  }

  // 手绘挂锁（锁体 + 锁梁 + 钥匙孔）
  function padlockSVG() {
    var s2 = svgEl('svg', { viewBox: '0 0 40 46', 'class': 'sc-lock-body' });
    // 锁梁
    var shackle = svgEl('path', {
      d: 'M11 20 V13 a9 9 0 0 1 18 0 V20',
      fill: 'none', stroke: '#ffd97a', 'stroke-width': '5.2', 'stroke-linecap': 'round'
    });
    // 锁梁高光
    var shackleHi = svgEl('path', {
      d: 'M11 20 V13 a9 9 0 0 1 18 0 V20',
      fill: 'none', stroke: '#fff4cf', 'stroke-width': '1.8', 'stroke-linecap': 'round'
    });
    // 锁体
    var body = svgEl('rect', {
      x: '5', y: '19', width: '30', height: '23', rx: '5',
      fill: 'url(#lockgrad)' // 占位，下面替换为纯色
    });
    body.setAttribute('fill', '#f3c33f');
    body.setAttribute('stroke', '#8a6512');
    body.setAttribute('stroke-width', '1.6');
    // 钥匙孔
    var hole = svgEl('circle', { cx: '20', cy: '29', r: '3.1', fill: '#4a3407' });
    var slot = svgEl('rect', { x: '18.7', y: '30', width: '2.6', height: '6.4', rx: '1.1', fill: '#4a3407' });
    s2.appendChild(shackle);
    s2.appendChild(shackleHi);
    s2.appendChild(body);
    s2.appendChild(hole);
    s2.appendChild(slot);
    return s2;
  }

  function lockSVG() {
    var svg = svgEl('svg', {
      viewBox: '0 0 100 140',
      preserveAspectRatio: 'none',
      'class': 'sc-lock-svg'
    });

    // 卡片中心与四角
    var cx = 50, cy = 70;
    var corners = [[3, 3], [97, 3], [3, 137], [97, 137]];
    var linkIdx = 0;

    corners.forEach(function (c, ci) {
      var dx = c[0] - cx, dy = c[1] - cy;
      var len = Math.sqrt(dx * dx + dy * dy);
      var ux = dx / len, uy = dy / len;
      var pitch = 7.4;                       // 链环间距
      var n = Math.max(3, Math.floor(len / pitch));
      var ang = Math.atan2(dy, dx) * 180 / Math.PI;

      for (var k = 1; k <= n; k++) {
        var t = (k - 0.5) / n;
        var px = cx + dx * t;
        var py = cy + dy * t;
        // 交替：奇数环与链条同向（长轴沿链），偶数环横过来 -> 咬合感
        var along = (k % 2 === 1);
        var rx = along ? 3.5 : 2.1;
        var ry = along ? 2.0 : 3.4;
        var el = svgEl('ellipse', {
          cx: px.toFixed(2), cy: py.toFixed(2),
          rx: String(rx), ry: String(ry),
          transform: 'rotate(' + ang.toFixed(1) + ' ' + px.toFixed(2) + ' ' + py.toFixed(2) + ')',
          fill: 'none',
          stroke: along ? '#e8d79c' : '#9a8a55',
          'stroke-width': '1.7',
          'class': 'sc-chain-link'
        });
        // 由中心向外依次长出
        el.style.animationDelay = (ci * 0.045 + t * 0.22).toFixed(3) + 's';
        svg.appendChild(el);
        linkIdx += 1;
      }
    });
    return svg;
  }

  function syncLockBadge(card, on) {
    var badge = card.querySelector('.sc-lock');
    if (on && !badge) {
      badge = h('div', { class: 'sc-lock' });
      badge.appendChild(lockSVG());
      badge.appendChild(padlockSVG());
      card.appendChild(badge);
    } else if (!on && badge) {
      badge.parentNode.removeChild(badge);
    }
  }

'''
s = s[:i] + block + s[j:]
io.open(p, "w", encoding="utf-8").write(s)
print("[lock] 显式链环 + SVG 挂锁已写入")
