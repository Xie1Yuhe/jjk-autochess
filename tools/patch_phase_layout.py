# -*- coding: utf-8 -*-
r"""
patch_phase_layout.py —— 按阶段自动调整商店/棋盘占比

需求：
  · 购买阶段：商店放大并上浮到屏幕中间，棋盘缩小淡化（可点按钮展开查看）
  · 战斗阶段：商店自动收起，棋盘占满

做法：在 <body> 上打 `phase-buy` / `phase-battle` 类，纯 CSS 过渡。
另外在 HUD 加一个「展开棋盘」小按钮，切 `board-expanded`。
"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------- 1) main.js：阶段变化时打 body 类 ----------------
mp = os.path.join(ROOT, "js", "main.js")
s = io.open(mp, encoding="utf-8").read()
old = """    g.bus.on('change', function (part) {
      if (!App.inGame) return;"""
new = """    // 阶段 → body 类：驱动「购买时商店上浮 / 战斗时商店收起」的布局
    function applyPhaseClass() {
      var ph = App.game ? App.game.phase : '';
      var body = document.body;
      body.classList.toggle('phase-buy', ph === 'planning' || ph === 'idle');
      body.classList.toggle('phase-battle', ph === 'battle' || ph === 'result');
    }
    App.applyPhaseClass = applyPhaseClass;
    g.bus.on('phase', applyPhaseClass);

    g.bus.on('change', function (part) {
      if (!App.inGame) return;
      if (part === 'phase' || part === 'all') applyPhaseClass();"""
assert old in s, "bus anchor"
s = s.replace(old, new, 1)
io.open(mp, "w", encoding="utf-8").write(s)
print("[layout] main.js 已按阶段切换 body 类")

# ---------------- 2) index.html：加「展开棋盘」按钮 ----------------
ip = os.path.join(ROOT, "index.html")
h = io.open(ip, encoding="utf-8").read()
if 'btn-board-toggle' not in h:
    old2 = '<div class="shop-dock">'
    new2 = '''<button class="board-toggle" id="btn-board-toggle" title="展开/收起棋盘">
        <span class="bt-icon">▦</span><span class="bt-text">展开棋盘</span>
      </button>

      <div class="shop-dock">'''
    assert old2 in h, "shop-dock anchor"
    h = h.replace(old2, new2, 1)
    io.open(ip, "w", encoding="utf-8").write(h)
    print("[layout] index.html 已加展开棋盘按钮")

# ---------------- 3) screens.js：按钮行为 ----------------
sp = os.path.join(ROOT, "js", "ui", "screens.js")
sc = io.open(sp, encoding="utf-8").read()
if 'btn-board-toggle' not in sc:
    anchor = "  function openSettings() {"
    add = """  // 展开/收起棋盘（购买阶段商店会占住中间，点这个临时看棋盘）
  function bindBoardToggle() {
    var btn = document.getElementById('btn-board-toggle');
    if (!btn) return;
    btn.addEventListener('click', function () {
      var on = document.body.classList.toggle('board-expanded');
      var t = btn.querySelector('.bt-text');
      if (t) t.textContent = on ? '收起棋盘' : '展开棋盘';
      JJK.Audio.play('click');
    });
  }

""" + anchor
    assert anchor in sc, "screens anchor"
    sc = sc.replace(anchor, add, 1)
    # init 里调用
    sc = sc.replace("  function init() {", "  function init() {\n    bindBoardToggle();", 1)
    io.open(sp, "w", encoding="utf-8").write(sc)
    print("[layout] screens.js 已接按钮")
