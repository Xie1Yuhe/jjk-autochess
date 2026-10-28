# -*- coding: utf-8 -*-
r"""
bands_v2.py —— 只改商店抽屉，侧栏原样保留

结构（保持原样）：
```
.screen-shake (flex column)
  header#hud
  .stage (grid: col-left | col-right)   ← 侧栏不动
  .shop-dock                            ← 改成 height 抽屉
  .log-dock
```

改动仅三点：
  1. 商店不再用 transform 覆盖，改成改变 height（30vh ↔ 42px）
  2. 移除购买阶段对棋盘/备战席的变暗
  3. 抽屉头加「收起/展开」按钮与金币显示
"""
import io
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
root = ROOT

# ---------------- 1) 覆盖式 CSS 复位 + 抽屉样式 ----------------
css = r'''
/* ============================================================
   商店抽屉（只改 height，不复盖、不变暗；侧栏保持原样）
   ============================================================ */

/* 舞台占满剩余高度 */
.screen-game .screen-shake { display: flex; flex-direction: column; }
.screen-game .stage { flex: 1 1 auto; min-height: 0; }

/* 商店：参与文档流的抽屉 */
.shop-dock {
  position: relative;
  flex: 0 0 auto;
  height: 30vh;
  max-height: 30vh;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 0 18px 8px;
  overflow: hidden;
  transform: none !important;
  opacity: 1 !important;
  filter: none !important;
  transition: height .3s cubic-bezier(.22,.9,.26,1),
              max-height .3s cubic-bezier(.22,.9,.26,1),
              padding .3s cubic-bezier(.22,.9,.26,1);
  background: linear-gradient(180deg, rgba(10, 8, 16, 0) 0%, rgba(8, 6, 13, .72) 42%);
}
body.drawer-closed .shop-dock,
body.phase-battle .shop-dock {
  height: 42px;
  max-height: 42px;
  padding-bottom: 4px;
}

/* 抽屉头 */
.drawer-head {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 10px;
  height: 38px;
  padding: 0 2px;
}
.dh-grip {
  width: 34px; height: 4px; border-radius: 3px;
  background: rgba(255, 255, 255, .22);
}
.dh-title {
  font-family: var(--font-black);
  font-size: 12px;
  letter-spacing: .22em;
  color: #e9dcbe;
}
.dh-gold { font-size: 11px; color: var(--text-faint); }
.dh-gold b {
  font-family: var(--font-mono, monospace);
  color: #ffd166; font-size: 12.5px; margin-left: 3px;
}
.dh-hint { font-size: 10.5px; color: var(--text-faint); }
.dh-toggle {
  margin-left: auto;
  display: inline-flex; align-items: center; gap: 5px;
  padding: 5px 11px; border-radius: 8px;
  border: 1px solid rgba(255, 209, 102, .38);
  background: rgba(255, 209, 102, .10);
  color: #ffd166;
  font-family: var(--font-display);
  font-size: 11.5px;
  cursor: pointer;
  transition: background .16s, border-color .16s;
}
.dh-toggle:hover { background: rgba(255, 209, 102, .2); border-color: rgba(255,209,102,.7); }
.dh-arrow { transition: transform .3s cubic-bezier(.22,.9,.26,1); }
body.drawer-closed .dh-arrow,
body.phase-battle .dh-arrow { transform: rotate(180deg); }

/* 卡槽 */
.shop-dock .shop-rail {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  gap: 18px;
  padding-top: 4px;
  overflow-x: auto;
}
body.drawer-closed .shop-dock .shop-rail,
body.phase-battle .shop-dock .shop-rail {
  opacity: 0; height: 0; padding: 0; pointer-events: none;
}
/* 抽屉展开时卡牌更大 */
body:not(.drawer-closed):not(.phase-battle) .shop-dock .shop-card {
  --card-w: 132px;
  --card-h: 184px;
}
.shop-dock::before {
  content: '';
  position: absolute;
  inset: 0 12px auto;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255,209,102,.6), transparent);
  pointer-events: none;
}

/* ---------- 关键：棋盘/备战席在任何阶段都不变暗、不缩放 ---------- */
body.phase-buy .board-shell,
body.phase-buy.board-expanded .board-shell,
body.phase-battle .board-shell,
body.phase-buy.board-expanded .shop-dock {
  transform: none !important;
  opacity: 1 !important;
  filter: none !important;
}
body.phase-buy .shop-dock::after { opacity: 0 !important; }
'''

path = os.path.join(root, "css", "bands.css")
io.open(path, "w", encoding="utf-8").write(css)
print("[drawer] bands.css 已重写（只改商店，侧栏不动）")

# ---------------- 2) index.html 引入 + 抽屉头 ----------------
p = os.path.join(root, "index.html")
s = io.open(p, encoding="utf-8").read()

if 'css/bands.css' not in s:
    marker = '<link rel="stylesheet" href="css/v2-juice.css">'
    s = s.replace(marker, marker + '\n  <link rel="stylesheet" href="css/bands.css">', 1)
    print("[drawer] 已引入 bands.css")

old_shop = '''      <div class="shop-dock">
        <div class="shop-rail" id="shop-rail"></div>
      </div>'''
new_shop = '''      <!-- 商店抽屉：只改变自身高度，绝不复盖备战席 -->
      <div class="shop-dock" id="shop-dock">
        <div class="drawer-head" id="drawer-head">
          <span class="dh-grip"></span>
          <span class="dh-title">商 店</span>
          <span class="dh-gold">金币 <b id="dh-gold">0</b></span>
          <span class="dh-hint">拖动卡牌到备战席</span>
          <button class="dh-toggle" id="btn-drawer">
            <span class="dh-arrow">▾</span><span class="dh-label">收起</span>
          </button>
        </div>
        <div class="shop-rail" id="shop-rail"></div>
      </div>'''
if 'drawer-head' not in s:
    assert old_shop in s, "shop anchor"
    s = s.replace(old_shop, new_shop, 1)
    print("[drawer] 抽屉头已加入")

io.open(p, "w", encoding="utf-8").write(s)
