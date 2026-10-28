# -*- coding: utf-8 -*-
r"""
fetch_art.py —— 抓取每个角色的「奥义立绘」（全图）用于必杀切入

来源：gamekee《咒术回战 幻影夜行》wiki 的角色页
      页面数据里的 data.thumb 第一项就是 1920×1078 的必杀演出图，
      正是原作放必杀时的那张横向大图。

输出：assets/art/<unit_id>.webp  （960×540，质量 82）
      前端 js/ui/ultcut.js 会优先用这张，找不到才退回 240×336 的卡面。

用法：
    python tools\fetch_art.py            # 增量：已存在就跳过
    python tools\fetch_art.py --force    # 全部重下
"""
import json
import os
import sys
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "tools", "wiki_cache")
UNITS = os.path.join(ROOT, "data", "units.json")
OUT = os.path.join(ROOT, "assets", "art")

W, H = 960, 540
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Referer": "https://www.gamekee.com/",
}


def norm(u):
    if not u:
        return None
    u = u.strip()
    if u.startswith("//"):
        return "https:" + u
    if u.startswith("http"):
        return u
    if u.startswith("/"):
        return "https://www.gamekee.com" + u
    return None


def split_urls(raw):
    """thumb 是逗号分隔的多个 url，但 url 自己的查询串里也带逗号（format,webp），
    所以只在「,//」或「,http」处切，其余逗号并回前一段。"""
    parts = str(raw).split(",")
    merged = []
    for p in parts:
        if p.startswith("//") or p.startswith("http"):
            merged.append(p)
        elif merged:
            merged[-1] += "," + p
        else:
            merged.append(p)
    return [x for x in merged if x]


def thumb_of(path):
    """从缓存的角色页 JSON 里取奥义立绘地址"""
    try:
        j = json.load(open(path, encoding="utf-8"))
    except Exception:
        return None
    d = j.get("data") or {}
    raw = d.get("thumb") or ""
    urls = []
    for part in split_urls(raw):
        u = norm(part)
        if not u:
            continue
        u = u.split("?")[0]          # 去掉 x-image-process 之类的查询串
        urls.append(u)
    if not urls:
        return None
    # 优先挑最大的那张（w_1920 / w_2048 / w_7680 之类）
    for u in urls:
        if "w_7680" in u or "w_2048" in u or "w_1920" in u or "w_1280" in u:
            return u
    return urls[0]


def download(url, dest):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    tmp = dest + ".tmp"
    open(tmp, "wb").write(data)
    im = Image.open(tmp).convert("RGBA")
    # 等比裁到 16:9，保留中间
    tw, th = W, H
    sw, sh = im.size
    scale = max(tw / sw, th / sh)
    nw, nh = int(sw * scale + 0.5), int(sh * scale + 0.5)
    im = im.resize((nw, nh), Image.LANCZOS)
    left = (nw - tw) // 2
    top = max(0, int((nh - th) * 0.42))     # 略偏上，保住脸
    im = im.crop((left, top, left + tw, top + th))
    im.convert("RGB").save(dest, "WEBP", quality=82, method=6)
    os.remove(tmp)
    return os.path.getsize(dest)


def main():
    force = "--force" in sys.argv
    os.makedirs(OUT, exist_ok=True)
    units = json.load(open(UNITS, encoding="utf-8"))
    files = [f for f in os.listdir(CACHE) if f.startswith("content_") and f.endswith(".json")]
    by_id = {}
    for f in files:
        cid = f[len("content_"):-len(".json")]
        by_id[cid] = os.path.join(CACHE, f)

    ok, skip, missing, failed = 0, 0, [], []
    for u in units:
        uid = u["id"]
        dest = os.path.join(OUT, uid + ".webp")
        if os.path.exists(dest) and not force:
            skip += 1
            continue
        src = by_id.get(uid)
        if not src:
            # 部分角色的页面 id 与棋子 id 不同，退回用 wikiUrl 里的数字
            url = u.get("wikiUrl") or ""
            guess = url.rstrip("/").split("/")[-1].replace(".html", "")
            src = by_id.get(guess)
        if not src:
            missing.append(uid)
            continue
        url = thumb_of(src)
        if not url:
            missing.append(uid)
            continue
        try:
            size = download(url, dest)
            ok += 1
            if ok % 10 == 0:
                print("  已下载 %d ..." % ok)
        except Exception as e:
            failed.append((uid, str(e)[:60]))

    total = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT)) if os.path.isdir(OUT) else 0
    print("[art] 新下载 %d / 跳过 %d / 缺页 %d / 失败 %d" % (ok, skip, len(missing), len(failed)))
    print("[art] 立绘总量 %.1f MB（%d 张）" % (total / 1048576.0,
                                             len([f for f in os.listdir(OUT) if f.endswith(".webp")])))
    if missing:
        print("[art] 缺页角色:", "、".join(missing[:12]), "..." if len(missing) > 12 else "")
    if failed:
        print("[art] 失败:", failed[:5])


if __name__ == "__main__":
    main()
