# -*- coding: utf-8 -*-
"""给 index.html 加 loading 屏与 og 分享卡片"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = os.path.join(ROOT, "index.html")
s = io.open(p, encoding="utf-8").read()

BOOT_CSS = """  <style>
    #boot{position:fixed;inset:0;z-index:99999;display:grid;place-items:center;
      background:#08060d;color:#e8c85a;font-family:system-ui,sans-serif;letter-spacing:.3em;
      font-size:13px;transition:opacity .4s}
    #boot.hide{opacity:0;pointer-events:none}
    #boot i{display:block;width:120px;height:2px;margin-top:14px;background:rgba(232,200,90,.18);
      position:relative;overflow:hidden;border-radius:2px}
    #boot i::after{content:'';position:absolute;inset:0;width:40%;background:#e8c85a;
      animation:bootrun 1.1s ease-in-out infinite}
    @keyframes bootrun{0%{left:-40%}100%{left:100%}}
  </style>
</head>"""

OG = """  <meta property="og:type" content="website">
  <meta property="og:title" content="咒术回战 · 幻影夜行 自走棋">
  <meta property="og:description" content="111 名术师与咒灵、10 条羁绊、专属必杀与领域展开。非商业同人作品。">
  <meta property="og:image" content="assets/cards/687394.webp">
  <meta name="twitter:card" content="summary_large_image">
</head>"""

if 'id="boot"' not in s:
    s = s.replace("</head>", BOOT_CSS, 1)
    s = s.replace("<body>", '<body>\n  <div id="boot">咒 术 自 走 棋<i></i></div>', 1)
    print("[pub] loading 屏已加")
else:
    print("[pub] loading 屏已存在")

if "og:title" not in s:
    s = s.replace("</head>", OG, 1)
    print("[pub] og 卡片已加")
else:
    print("[pub] og 卡片已存在")

io.open(p, "w", encoding="utf-8").write(s)
print("[pub] index.html 已保存")
