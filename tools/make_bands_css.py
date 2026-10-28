# -*- coding: utf-8 -*-
r"""
bands_layout.css 生成器 —— 三带布局的正式样式

写入 css/bands.css，并在 index.html 中于 v2-juice.css 之后引入，
用更高的层叠顺序覆盖旧的阶段规则（旧的用了 transform 覆盖，必须显式复位）。
"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CSS = r'''
/* ============================================================
   BANDS LAYOUT —— 上层 / 中层 / 下层 三带严格分区
   核心原则：
     1. 三者按 flex column 文档流排布，绝不重叠
     2. 商店只通过 height 展开/收起，不做任何覆盖
     3. 商店展开时棋盘与备战席**不加任何遮罩/变暗**
   ============================================================ */

/* ---------- 屏幕整体：竖向三带 ---------- */
.screen.screen-game {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}
.screen-game .screen-shake {
  position: relative;
  inset: auto;
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

/* ---------- 上层：顶栏 + 羁绊/咒具/操作横带 ---------- */
.screen-game .hud { flex: 0 0 auto; }

.top-strip {
  flex: 0 0 auto;
  display: flex;
  align-items: stretch;
  gap: 10px;
  padding: 8px 18px 6px;
  min-height: 0;
}
.top-strip .panel {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
}
.top-strip .traits-panel { flex: 3 1 0; }
.top-strip .items-panel  { flex: 2 1 0; }
.top-strip .panel-head {
  padding: 3px 8px;
  gap: 6px;
}
.top-strip .panel-body {
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
  gap: 5px;
  padding: 5px 8px;
  max-height: 62px;
  overflow-y: auto;
}
.top-strip .traits-tips { padding: 0 8px 4px; font-size: 10px; }

/* 商店操作按钮：横向一条 */
.top-strip .shop-controls {
  flex: 0 0 auto;
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
  gap: 6px;
  padding: 8px 10px;
  border-radius: 12px;
  background: rgba(12, 9, 18, .55);
  border: 1px solid rgba(255, 255, 255, .07);
}
.top-strip .shop-controls .btn {
  padding: 6px 10px;
  font-size: 11.5px;
}

/* ---------- 中层：棋盘 + 备战席 ---------- */
.screen-game .stage {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  grid-template-columns: none;
  grid-template-rows: none;
  gap: 8px;
  padding: 0 18px 6px;
  overflow: hidden;
}
.screen-game .stage .col-left {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.screen-game .board-shell {
  flex: 1 1 auto;
  min-height: 0;
  transform: none !important;
  opacity: 1 !important;
  filter: none !important;
}
.screen-game .bench-row { flex: 0 0 auto; }

/* 开始战斗：中层右下角，文档流内，不覆盖任何东西 */
.screen-game .start-dock {
  flex: 0 0 auto;
  margin: 0;
  display: flex;
  justify-content: flex-end;
  padding: 0 2px;
}
.screen-game .start-dock .btn-start {
  min-width: 240px;
}

/* ---------- 下层：商店抽屉 ---------- */
.shop-dock {
  position: relative;
  flex: 0 0 auto;
  height: 33vh;
  max-height: 33vh;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 0 18px 10px;
  overflow: hidden;
  transform: none !important;
  opacity: 1 !important;
  filter: none !important;
  transition: height .3s cubic-bezier(.22,.9,.26,1),
              max-height .3s cubic-bezier(.22,.9,.26,1),
              padding .3s cubic-bezier(.22,.9,.26,1);
  background: linear-gradient(180deg, rgba(10, 8, 16, 0) 0%, rgba(8, 6, 13, .72) 40%);
}
/* 收起：只留条带 */
body.drawer-closed .shop-dock {
  height: 42px;
  max-height: 42px;
  padding-bottom: 6px;
}
body.phase-battle .shop-dock {
  height: 42px;
  max-height: 42px;
  padding-bottom: 6px;
}
/* 抽屉头 */
.drawer-head {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 10px;
  height: 38px;
  padding: 0 4px;
  border-radius: 10px 10px 0 0;
}
.dh-grip {
  width: 34px;
  height: 4px;
  border-radius: 3px;
  background: rgba(255, 255, 255, .22);
}
.dh-title {
  font-family: var(--font-black);
  font-size: 12px;
  letter-spacing: .22em;
  color: #e9dcbe;
}
.dh-gold {
  font-size: 11px;
  color: var(--text-faint);
}
.dh-gold b {
  font-family: var(--font-mono, monospace);
  color: #ffd166;
  font-size: 12.5px;
  margin-left: 3px;
}
.dh-hint { font-size: 10.5px; color: var(--text-faint); margin-left: 6px; }
.dh-toggle {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 11px;
  border-radius: 8px;
  border: 1px solid rgba(255, 209, 102, .38);
  background: rgba(255, 209, 102, .10);
  color: #ffd166;
  font-family: var(--font-display);
  font-size: 11.5px;
  cursor: pointer;
  transition: background .16s, border-color .16s;
}
.dh-toggle:hover { background: rgba(255, 209, 102, .2); border-color: rgba(255, 209, 102, .7); }
.dh-arrow { transition: transform .3s cubic-bezier(.22,.9,.26,1); }
body.drawer-closed .dh-arrow,
body.phase-battle .dh-arrow { transform: rotate(180deg); }

/* 商店卡槽：展开时拉大 */
.shop-dock .shop-rail {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  gap: 18px;
  padding: 4px 0 0;
  overflow-x: auto;
  transition: gap .3s cubic-bezier(.22,.9,.26,1);
}
body.drawer-closed .shop-dock .shop-rail,
body.phase-battle .shop-dock .shop-rail {
  opacity: 0;
  pointer-events: none;
  height: 0;
  padding: 0;
  transition: opacity .2s, height .3s;
}
/* 抽屉展开时卡牌放大 */
body:not(.drawer-closed):not(.phase-battle) .shop-dock .shop-card {
  --card-w: 128px;
  --card-h: 178px;
}

/* 商店展开时的轻微辉光（不遮挡、不变暗） */
.shop-dock::before {
  content: '';
  position: absolute;
  inset: 0 12px auto;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255, 209, 102, .6), transparent);
  pointer-events: none;
}

/* ---------- 旧的覆盖式规则全部失效 ---------- */
body.phase-buy .shop-dock,
body.phase-buy .board-shell,
body.phase-buy.board-expanded .shop-dock,
body.phase-buy.board-expanded .board-shell,
body.phase-battle .board-shell,
body.phase-battle .col-left,
body.phase-battle .stage {
  transform: none !important;
  opacity: 1 !important;
  filter: none !important;
}
body.phase-buy .shop-dock::after { opacity: 0 !important; }
.board-toggle { display: none !important; }
'''

out = os.path.join(ROOT, "css", "bands.css")
io.open(out, "w", encoding="utf-8").write(CSS)
print("[bands] css/bands.css 已写入", len(CSS), "字节")

# 在 index.html 里引入（放在 v2-juice.css 之后）
p = os.path.join(ROOT, "index.html")
s = io.open(p, encoding="utf-8").read()
if 'css/bands.css' not in s:
    marker = '<link rel="stylesheet" href="css/v2-juice.css">'
    assert marker in s, "css marker"
    s = s.replace(marker, marker + '\n  <link rel="stylesheet" href="css/bands.css">', 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("[bands] index.html 已引入 bands.css")
