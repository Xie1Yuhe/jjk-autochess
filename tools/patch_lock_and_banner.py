# -*- coding: utf-8 -*-
r"""
patch_lock_and_banner.py

1. FX.banner 支持第 4 个参数「主色」，羁绊 4 人档横幅用各羁绊自己的颜色
2. 商店锁定时，每张卡上方出现 🔒 与锁链动态效果
"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------- 1) FX.banner 支持颜色 ----------------
fxp = os.path.join(ROOT, "js", "ui", "fx.js")
s = io.open(fxp, encoding="utf-8").read()
old = """  function banner(main, sub, life) {"""
new = """  function banner(main, sub, life, color) {"""
assert old in s, "banner sig"
s = s.replace(old, new, 1)

old2 = """    document.body.appendChild(el);
    bannerTi"""
new2 = """    if (color) {
      el.style.setProperty('--bb', color);
      el.classList.add('has-tint');
    }
    document.body.appendChild(el);
    bannerTi"""
assert old2 in s, "banner append"
s = s.replace(old2, new2, 1)
io.open(fxp, "w", encoding="utf-8").write(s)
print("[fx] banner 支持颜色")

# ---------------- 2) 商店锁定标记 ----------------
shp = os.path.join(ROOT, "js", "ui", "shop.js")
sh = io.open(shp, encoding="utf-8").read()

old3 = """      card.classList.toggle('is-locked', !!g.shopLocked);"""
new3 = """      card.classList.toggle('is-locked', !!g.shopLocked);
      syncLockBadge(card, !!g.shopLocked);"""
assert old3 in sh, "sync anchor"
sh = sh.replace(old3, new3, 1)

old4 = """  function invalidate() { lastSig = ''; }"""
new4 = """  // 锁定标记：卡上方一个 🔒 + 两条垂下来的锁链
  function syncLockBadge(card, on) {
    var badge = card.querySelector('.sc-lock');
    if (on && !badge) {
      badge = h('div', { class: 'sc-lock' }, [
        h('div', { class: 'sc-lock-head', text: '🔒' }),
        h('div', { class: 'sc-lock-chain l' }),
        h('div', { class: 'sc-lock-chain r' })
      ]);
      card.appendChild(badge);
    } else if (!on && badge) {
      badge.parentNode.removeChild(badge);
    }
  }

  function invalidate() { lastSig = ''; }"""
assert old4 in sh, "invalidate anchor"
sh = sh.replace(old4, new4, 1)

# 首次渲染时也要挂上
old5 = """      if (id && D.unitById[id]) rail.appendChild(cardFor(id, i));
      else rail.appendChild(emptyCard(i));"""
new5 = """      var el = null;
      if (id && D.unitById[id]) el = cardFor(id, i);
      else el = emptyCard(i);
      rail.appendChild(el);
      if (el && id) syncLockBadge(el, !!g.shopLocked);"""
assert old5 in sh, "render anchor"
sh = sh.replace(old5, new5, 1)
io.open(shp, "w", encoding="utf-8").write(sh)
print("[shop] 锁定标记已接入")

# 徽章函数要在 cardFor 之前可用（函数声明会提升，无需额外处理）
