# -*- coding: utf-8 -*-
r"""
patch_lock_chain.py —— 把锁定标记换成「中央大锁 + 四角真实锁链」

需求：
  · 🔒 位于卡片正中央，尺寸更大
  · 锁链从中央锁向**四个角**蔓延，动态生长
  · 锁链要有「真实链环」的质感，不是发光虚线

做法：用 SVG 的 `<pattern>` 定义链环（两个交错的椭圆），
四条 path 从中心连到四角，stroke 用链环图案填充；
再用 `pathLength=100` + `stroke-dasharray/offset` 做「从中心长出」的动画。
"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = os.path.join(ROOT, "js", "ui", "shop.js")
s = io.open(p, encoding="utf-8").read()

old_start = "  // 锁定标记：卡上方一个 🔒 + 两条垂下来的锁链"
old_end = "  function invalidate() { lastSig = ''; }"
i = s.index(old_start)
j = s.index(old_end)
new_block = '''  // 锁定标记：中央大锁 + 四条锁链向四角蔓延
  // 链环用 SVG <pattern> 画（两个交错的椭圆），不是虚线
  var chainSeq = 0;
  function lockSVG() {
    chainSeq += 1;
    var pid = 'chainpat' + chainSeq;
    var NS = 'http://www.w3.org/2000/svg';
    var svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', '0 0 100 140');
    svg.setAttribute('preserveAspectRatio', 'none');
    svg.setAttribute('class', 'sc-lock-svg');

    var defs = document.createElementNS(NS, 'defs');
    var pat = document.createElementNS(NS, 'pattern');
    pat.setAttribute('id', pid);
    pat.setAttribute('width', '9');
    pat.setAttribute('height', '9');
    pat.setAttribute('patternUnits', 'userSpaceOnUse');
    // 链环：暗色底环 + 亮色高光，交错排布形成「一环扣一环」
    var link1 = document.createElementNS(NS, 'ellipse');
    link1.setAttribute('cx', '4.5'); link1.setAttribute('cy', '3');
    link1.setAttribute('rx', '3.1'); link1.setAttribute('ry', '2.2');
    link1.setAttribute('fill', 'none');
    link1.setAttribute('stroke', '#8a7b4c');
    link1.setAttribute('stroke-width', '2.0');
    var link2 = document.createElementNS(NS, 'ellipse');
    link2.setAttribute('cx', '4.5'); link2.setAttribute('cy', '7.5');
    link2.setAttribute('rx', '3.1'); link2.setAttribute('ry', '2.2');
    link2.setAttribute('fill', 'none');
    link2.setAttribute('stroke', '#e2d19a');
    link2.setAttribute('stroke-width', '2.0');
    var patBg = document.createElementNS(NS, 'rect');
    patBg.setAttribute('width', '9'); patBg.setAttribute('height', '9');
    patBg.setAttribute('fill', 'none');
    pat.appendChild(link1); pat.appendChild(link2);
    defs.appendChild(pat);
    svg.appendChild(defs);

    // 中心点（50,70），四条链连到四角
    var corners = [[0, 0], [100, 0], [0, 140], [100, 140]];
    corners.forEach(function (c) {
      var ln = document.createElementNS(NS, 'line');
      ln.setAttribute('x1', '50'); ln.setAttribute('y1', '70');
      ln.setAttribute('x2', String(c[0])); ln.setAttribute('y2', String(c[1]));
      ln.setAttribute('stroke', 'url(#' + pid + ')');
      ln.setAttribute('stroke-width', '7');
      ln.setAttribute('stroke-linecap', 'round');
      ln.setAttribute('pathLength', '100');
      ln.setAttribute('stroke-dasharray', '100');
      ln.setAttribute('stroke-dashoffset', '100');
      ln.setAttribute('class', 'sc-chain');
      svg.appendChild(ln);
    });
    return svg;
  }

  function syncLockBadge(card, on) {
    var badge = card.querySelector('.sc-lock');
    if (on && !badge) {
      badge = h('div', { class: 'sc-lock' });
      badge.appendChild(lockSVG());
      badge.appendChild(h('div', { class: 'sc-lock-head', text: '🔒' }));
      card.appendChild(badge);
    } else if (!on && badge) {
      badge.parentNode.removeChild(badge);
    }
  }

'''
s = s[:i] + new_block + s[j:]
io.open(p, "w", encoding="utf-8").write(s)
print("[lock] SVG 锁链已替换虚线")
