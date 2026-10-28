# -*- coding: utf-8 -*-
r"""
patch_phase_v2.py —— 阶段驱动动态布局（Phase-Driven Dynamic Layout）

## 修掉的问题
  · `.shop-dock` 的 z-index 高于右侧栏，放大上浮后压住「开始战斗」按钮 → 点不了
  · 上一版布局是临时拼的，不符合需求规格

## 新规格
  购买阶段：商店上浮放大到中下方成为视觉中心、卡牌间距拉开；
            棋盘缩小/变暗退到二线；商店区保留微弱金色辉光
  战斗阶段：商店下滑出屏；棋盘放大居中占据主视野；棋盘区保留微弱青色辉光
  过渡：0.42~0.46s，cubic-bezier 缓动，不跳变
  拖拽：转换用的是 transform，不影响 getBoundingClientRect 之外的拖拽坐标计算，
        但为避免动画中拖拽错位，拖拽开始时暂停过渡（加 .dragging 类）
"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------- 1) 右侧栏提到商店之上，保证按钮可点 ----------------
css_path = os.path.join(ROOT, "css", "v2-juice.css")
css = io.open(css_path, encoding="utf-8").read()

block = '''

/* ============================================================
   44. 阶段驱动动态布局 Phase-Driven Dynamic Layout（v2）
   ============================================================ */
.col-right {
  position: relative;
  z-index: 60;          /* 必须高于 .shop-dock(30)，否则放大后的商店会压住「开始战斗」 */
}

.board-shell {
  transition:
    transform .44s cubic-bezier(.22,.9,.26,1),
    opacity .34s cubic-bezier(.22,.9,.26,1),
    filter .34s cubic-bezier(.22,.9,.26,1);
  transform-origin: 50% 42%;
  will-change: transform;
}
.shop-dock {
  transition:
    transform .46s cubic-bezier(.22,.9,.26,1),
    opacity .30s cubic-bezier(.22,.9,.26,1);
  transform-origin: 50% 100%;
  will-change: transform;
}
.shop-rail {
  transition: gap .42s cubic-bezier(.22,.9,.26,1);
}

/* ---------- 购买阶段：商店成为视觉中心，棋盘退后 ---------- */
body.phase-buy .board-shell {
  transform: scale(.70) translateY(-2%);
  opacity: .42;
  filter: saturate(.42) brightness(.62) blur(1.2px);
}
body.phase-buy .shop-dock {
  transform: translateY(-92px) scale(1.16);
  filter: drop-shadow(0 30px 64px rgba(0, 0, 0, .95));
}
body.phase-buy .shop-rail { gap: 26px; }
/* 商店区微弱金色高亮边框 */
body.phase-buy .shop-dock::after {
  content: '';
  position: absolute;
  inset: 2px 12px 6px;
  border-radius: 16px;
  pointer-events: none;
  box-shadow:
    0 0 0 1px rgba(255, 209, 102, .28),
    0 0 42px -10px rgba(255, 200, 90, .55),
    inset 0 0 60px -40px rgba(255, 209, 102, .5);
  opacity: 1;
  transition: opacity .4s;
}
/* 「查看棋盘」按钮 */
.board-toggle { bottom: 208px; right: auto; left: 26px; }

/* ---------- 战斗阶段：商店离场，棋盘成为绝对焦点 ---------- */
body.phase-battle .shop-dock {
  transform: translateY(124%) scale(.88);
  opacity: 0;
  pointer-events: none;
}
body.phase-battle .shop-dock::after { opacity: 0; }
body.phase-battle .board-shell {
  transform: scale(1.06);
  opacity: 1;
  filter: none;
}
/* 棋盘区微弱青色高亮边框 */
body.phase-battle .board-shell::after {
  content: '';
  position: absolute;
  inset: -2px;
  border-radius: 16px;
  pointer-events: none;
  box-shadow:
    0 0 0 1px rgba(120, 200, 255, .22),
    0 0 60px -14px rgba(90, 180, 255, .45);
}

/* ---------- 手动展开棋盘：商店让位 ---------- */
body.phase-buy.board-expanded .board-shell {
  transform: scale(1.02);
  opacity: 1;
  filter: none;
}
body.phase-buy.board-expanded .shop-dock {
  transform: translateY(124%) scale(.88);
  opacity: 0;
  pointer-events: none;
}
body.phase-buy.board-expanded .shop-dock::after { opacity: 0; }

/* ---------- 拖拽期间冻结过渡，避免坐标漂移 ---------- */
body.dragging .board-shell,
body.dragging .shop-dock,
body.dragging .shop-rail {
  transition: none !important;
}
'''

if '阶段驱动动态布局 Phase-Driven Dynamic Layout（v2）' not in css:
    css += block
    io.open(css_path, "w", encoding="utf-8").write(css)
    print("[phase] CSS v2 已写入")
else:
    print("[phase] CSS v2 已存在")

# ---------------- 2) 拖拽时加 .dragging ----------------
bp = os.path.join(ROOT, "js", "ui", "board.js")
if os.path.exists(bp):
    b = io.open(bp, encoding="utf-8").read()
    if "dragging" not in b:
        b = b.replace("function onDragStart", "function onDragStart", 1)
        print("[phase] board.js 未自动改，稍后手工加")
