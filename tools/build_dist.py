# -*- coding: utf-8 -*-
r"""
build_dist.py —— 生成可直接部署到静态托管的 dist/ 目录

## 为什么要单独打包

根目录里有这些不该发布的东西：
  · tools/   8.8 MB（爬虫、wiki 缓存、测试脚本，含第三方文本）
  · docs/    5.9 MB（开发文档、截图、GIF）
  · *.bak / *.md 里的一些内部记录

游戏本体只需要：index.html + js/ + css/ + data/ + assets/

## 用法
    python tools\build_dist.py
输出：
    dist/
       index.html
       404.html
       .nojekyll        （GitHub Pages 用，防止忽略下划线开头文件）
       js/ css/ data/ assets/
"""
import os
import shutil
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")

INCLUDE_DIRS = ["js", "css", "data", "assets"]
INCLUDE_FILES = ["index.html"]

# 部署时不含的零散文件（开发用）
SKIP_SUFFIX = (".bak", ".pyc")


def copytree(src, dst):
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def main():
    if os.path.isdir(DIST):
        shutil.rmtree(DIST)
    os.makedirs(DIST)

    for f in INCLUDE_FILES:
        shutil.copy2(os.path.join(ROOT, f), os.path.join(DIST, f))

    for d in INCLUDE_DIRS:
        src = os.path.join(ROOT, d)
        if os.path.isdir(src):
            copytree(src, os.path.join(DIST, d))

    # 404 → 回首页（单页游戏，所有路由都回 index）
    idx = open(os.path.join(DIST, "index.html"), encoding="utf-8").read()
    open(os.path.join(DIST, "404.html"), "w", encoding="utf-8").write(idx)

    # GitHub Pages 不忽略下划线开头文件
    open(os.path.join(DIST, ".nojekyll"), "w", encoding="utf-8").write("")

    # 统计
    total = 0
    count = 0
    for r, _, fs in os.walk(DIST):
        for f in fs:
            total += os.path.getsize(os.path.join(r, f))
            count += 1
    print("[dist] 已生成 %s" % DIST)
    print("[dist] %d 个文件 / %.1f MB" % (count, total / 1048576))


if __name__ == "__main__":
    main()
