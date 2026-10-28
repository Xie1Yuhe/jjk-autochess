# -*- coding: utf-8 -*-
r"""
parse_tierlist.py —— 解析官方强度榜（wiki 652351）为结构化数据

输出
    tools/tierlist_raw.json   {"tierOf": {cid: "SSS"..}, "nameOf": {cid: 缩写名}, "tiers": [...]}
    tools/tierlist.txt        人类可读的完整榜单（便于人工核对）

页面结构（关键）
    data.content_json 是一个节点数组，其中 type == "illustrated-book" 的节点承载榜单：
        node["data"] = [
            {"data": {"title": <富文本 "SSS：顶级强者">,
                      "list": [ {"title": <富文本 "核心主C">,
                                 "content": [ {"name": "夏日钉",
                                               "avatar": "//cdnimg...",
                                               "jumpHref": "https://www.gamekee.com/jk/707237.html"}, ... ]} ]}}
        ]
    所以「档次 → 角色 id」可以直接从 jumpHref 里正则取出，不需要 OCR、也不需要点头像跳转。

用法
    python tools\parse_tierlist.py            # 用本地缓存
    python tools\parse_tierlist.py --fetch    # 先联网刷新再解析
"""
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "tools", "wiki_cache", "content_652351.json")
OUT_JSON = os.path.join(ROOT, "tools", "tierlist_raw.json")
OUT_TXT = os.path.join(ROOT, "tools", "tierlist.txt")
PAGE_URL = "https://www.gamekee.com/jk/652351.html"


def fetch():
    """复用 fetch_wiki.py 的抓取逻辑（带正确 header 与节流）。"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import fetch_wiki
    data = fetch_wiki.fetch_detail("652351")
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump(data, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    print("[fetch] 已刷新缓存")


def plain(node):
    """把富文本节点压成纯文本。"""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(plain(x) for x in node)
    if isinstance(node, dict):
        if node.get("text"):
            return node["text"]
        return "".join(plain(x) for x in (node.get("children") or []))
    return ""


def main():
    if "--fetch" in sys.argv or not os.path.exists(CACHE):
        fetch()

    j = json.load(open(CACHE, encoding="utf-8"))
    nodes = json.loads(j["data"]["content_json"])
    books = [n for n in nodes if n.get("type") == "illustrated-book"]
    if not books:
        raise SystemExit("没找到 illustrated-book 节点，页面结构可能变了")
    book = books[0]

    tier_of, name_of, tiers, lines = {}, {}, [], []
    lines.append("官方强度榜（速查）  %s" % PAGE_URL)
    _ts = j["data"].get("updated_at")
    if str(_ts).isdigit():
        import datetime
        _ts = datetime.datetime.fromtimestamp(int(_ts)).strftime("%Y-%m-%d %H:%M")
    lines.append("更新时间：%s" % (_ts or "未知"))
    lines.append("")

    for g in book["data"]:
        d = g["data"]
        title = plain(d.get("title")).strip()
        code = (re.match(r"([A-Z]+)", title) or [None, "?"])[1] if re.match(r"([A-Z]+)", title) else "?"
        entries = []
        for sub in (d.get("list") or []):
            group_label = plain(sub.get("title")).strip()
            chars = sub.get("content") or []
            for c in chars:
                m = re.search(r"/jk/(\d+)\.html", c.get("jumpHref") or "")
                cid = m.group(1) if m else ""
                nm = c.get("name", "")
                entries.append({"name": nm, "id": cid, "group": group_label})
                if cid:
                    tier_of[cid] = code
                    name_of[cid] = nm
        tiers.append({"code": code, "title": title, "entries": entries})
        lines.append("%s（%d 名）" % (title, len(entries)))
        for e in entries:
            lines.append("   %-16s %s" % (e["name"], e["id"] or "(无链接)"))
        lines.append("")

    out = {"source": PAGE_URL, "tiers": tiers, "tierOf": tier_of, "nameOf": name_of}
    json.dump(out, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(OUT_TXT, "w", encoding="utf-8").write("\n".join(lines))

    print("[tierlist] %d 档 / %d 条，带 id 的 %d 条" % (len(tiers), sum(len(t["entries"]) for t in tiers), len(tier_of)))
    for t in tiers:
        print("   %-4s %-8s %2d 名" % (t["code"], t["title"].split("：")[-1], len(t["entries"])))
    print("[tierlist] → %s" % OUT_JSON)
    print("[tierlist] → %s" % OUT_TXT)


if __name__ == "__main__":
    main()
