# -*- coding: utf-8 -*-
"""扫描源码中的「攻击」字样与可疑的代码泄漏痕迹"""
import io
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP = (".git", "dist", "wiki_cache", "wiki_parsed", "assets")

hits = []
sus = []
for dirpath, dirnames, files in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in SKIP]
    for f in files:
        if not f.endswith((".js", ".html", ".css")):
            continue
        p = os.path.join(dirpath, f)
        try:
            s = io.open(p, encoding="utf-8").read()
        except Exception:
            continue
        for i, line in enumerate(s.split("\n"), 1):
            if "攻击" in line:
                hits.append("%s:%d: %s" % (os.path.relpath(p, ROOT), i, line.strip()[:110]))
            if re.search(r"\[object Object\]|undefined|NaN|\$\{", line) and "javascript" not in line:
                sus.append("%s:%d: %s" % (os.path.relpath(p, ROOT), i, line.strip()[:110]))

print("=== 源码中的「攻击」 ===")
print("\n".join(hits[:30]) if hits else "（无）")
print("\n=== 可能泄漏到界面的代码痕迹 ===")
print("\n".join(sus[:24]) if sus else "（无）")
