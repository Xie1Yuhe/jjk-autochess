# -*- coding: utf-8 -*-
r"""
patch_item_ui.py —— 商店 UI 分区：2/3 角色卡 + 1/3 咒具

在 shop.js 里新增咒具栏渲染，能融合的咒具高亮。
"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = os.path.join(ROOT, "js", "ui", "shop.js")
s = io.open(p, encoding="utf-8").read()

# 1) 找到 rail = ... 声明，补 itemRail
anchor = "  function invalidate() { lastSig = ''; }"
block = '''  /* ---------------------------------------------------- 咒具栏 ------ */
  function itemById(id) {
    for (var i = 0; i < D.items.length; i++) if (D.items[i].id === id) return D.items[i];
    return null;
  }

  function renderItemRail() {
    var el = document.getElementById('item-rail');
    if (!el) return;
    var g = game();
    if (!g || !g.itemShop) { el.innerHTML = ''; return; }
    var sig = g.itemShop.join(',') + '|' + g.gold + '|' + (g.itemsBag || []).join(',') + '|' + g.phase;
    if (el.dataset.sig === sig) return;
    el.dataset.sig = sig;
    el.innerHTML = '';

    var head = document.createElement('div');
    head.className = 'ir-head';
    head.innerHTML = '<span class="ir-title">咒 具</span><span class="ir-price">' + (g.itemPrice || 3) + ' 金/件</span>';
    el.appendChild(head);

    var grid = document.createElement('div');
    grid.className = 'ir-grid';
    el.appendChild(grid);

    for (var i = 0; i < 3; i++) {
      var id = g.itemShop[i];
      var it = id ? itemById(id) : null;
      var cell = document.createElement('button');
      cell.className = 'ir-item';
      if (!it) {
        cell.classList.add('is-empty');
        cell.disabled = true;
        grid.appendChild(cell);
        continue;
      }
      var craft = g.itemMergeHint ? g.itemMergeHint(id) : null;
      if (craft) cell.classList.add('can-craft');
      var afford = g.gold >= (g.itemPrice || 3);
      if (!afford) cell.classList.add('is-poor');
      cell.title = it.name + ' · ' + it.text + (craft ? ('\\n可与已有组件融合成「' + craft.name + '」') : '');
      cell.innerHTML =
        '<img src="assets/items/' + it.icon + '" alt="" draggable="false">' +
        '<span class="ir-name">' + it.name + '</span>' +
        '<span class="ir-cost">' + (g.itemPrice || 3) + '</span>' +
        (craft ? '<span class="ir-craft">可融合</span>' : '');
      (function (idx) {
        cell.addEventListener('click', function () {
          var r = game().buyItemFromShop(idx);
          if (r && r.ok) {
            JJK.Audio.play('buy');
            el.dataset.sig = '';
            renderItemRail();
          } else {
            JJK.Audio.play('deny');
          }
        });
      })(i);
      grid.appendChild(cell);
    }
  }

''' + anchor
if "function renderItemRail" not in s:
    assert anchor in s, "invalidate anchor"
    s = s.replace(anchor, block, 1)

# 2) render() 里同步渲染咒具栏
old2 = """      rail.appendChild(el);
      if (el && id) syncLockBadge(el, !!g.shopLocked);
    }
  }"""
new2 = """      rail.appendChild(el);
      if (el && id) syncLockBadge(el, !!g.shopLocked);
    }
    renderItemRail();
  }"""
if old2 in s:
    s = s.replace(old2, new2, 1)
else:
    s = s.replace("  function refreshAffordability() {", "  function refreshAffordability() {\n    renderItemRail();", 1)

# 3) 导出
s = s.replace("    invalidate: invalidate", "    invalidate: invalidate,\n    renderItems: renderItemRail")

io.open(p, "w", encoding="utf-8").write(s)
print("[itemshop] shop.js UI 已加咒具栏")
