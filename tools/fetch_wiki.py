# -*- coding: utf-8 -*-
r"""
fetch_wiki.py —— GameKee《咒术回战 幻影夜行》角色页抓取与解析（Phase 7 重做）

与旧版（..\咒术自走棋\tools\harvest.py）的区别：
  1. 先抓 **在线目录树**，拿到当前全部角色 content_id，缓存里没有的自动补抓
     —— 这样能发现 wiki 新出的角色/异格。
  2. 解析结果保留 **必杀技 / 被动全文 / 角色评价 / 实装日期 / 三个属性图标**，
     供后续"技能转化"使用，而不是只留一个技能名。
  3. 输出覆盖率统计与数据缺口，写入 tools/wiki_report.json。

用法：
    python tools\fetch_wiki.py            # 增量抓取（默认）
    python tools\fetch_wiki.py --refresh  # 强制重抓全部
    python tools\fetch_wiki.py --list     # 只打印目录，不抓详情
"""
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = "https://www.gamekee.com"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
    "game-alias": "jk",
    "X-Requested-With": "XMLHttpRequest",
    "Lang": "zh-cn",
    "Referer": "https://www.gamekee.com/jk/",
    "Accept": "application/json, text/plain, */*",
}

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "tools", "wiki_cache")
ICONS = os.path.join(ROOT, "tools", "wiki_icons")
PARSED = os.path.join(ROOT, "tools", "wiki_parsed")
for _d in (CACHE, ICONS, PARSED):
    os.makedirs(_d, exist_ok=True)


# ------------------------------------------------------------------ HTTP
def api(path, timeout=40):
    req = urllib.request.Request(BASE + path, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def fetch_tree():
    j = api("/v1/entry/treesByPidV1?pid=0")
    flat = []

    def walk(nodes, depth=0):
        for n in nodes or []:
            flat.append({
                "id": n.get("id"), "name": n.get("name"), "pid": n.get("pid"),
                "content_id": n.get("content_id"), "depth": depth, "icon": n.get("icon") or "",
            })
            walk(n.get("child"), depth + 1)

    walk(j.get("data"))
    return flat


def characters(tree):
    """返回 [(name, content_id, icon)]：角色节点下的所有叶子"""
    parents = {n["id"] for n in tree
               if n.get("name") and "角色" in n["name"] and len(n["name"]) <= 6}
    out = []
    for n in tree:
        if not n.get("content_id"):
            continue
        # 直接挂在"角色"节点下，或者任意深度但父节点是角色目录
        if n.get("pid") in parents:
            out.append((n["name"], n["content_id"], n.get("icon") or ""))
    if not out:   # 兜底：拿所有带 content_id 的叶子
        out = [(n["name"], n["content_id"], n.get("icon") or "") for n in tree if n.get("content_id")]
    # 去重
    seen, uniq = set(), []
    for name, cid, icon in out:
        if cid in seen:
            continue
        seen.add(cid)
        uniq.append((name, cid, icon))
    return uniq


def fetch_content(cid, refresh=False):
    p = os.path.join(CACHE, "content_%s.json" % cid)
    if not refresh and os.path.exists(p) and os.path.getsize(p) > 200:
        try:
            return json.load(open(p, encoding="utf-8")), False
        except Exception:
            pass
    j = api("/v1/content/detail/%s" % cid)
    json.dump(j, open(p, "w", encoding="utf-8"), ensure_ascii=False)
    return j, True


# ------------------------------------------------------------------ 图标
def icon_hash(src, fetch=True):
    """下载属性/特性/伤害类型图标，返回内容 md5 前 10 位"""
    if not src:
        return None
    url = src if src.startswith("http") else ("https:" + src)
    url = url.split("?")[0]
    name = os.path.basename(urllib.parse.urlparse(url).path) or "icon.png"
    key = hashlib.md5(url.encode()).hexdigest()[:16]
    p = os.path.join(ICONS, key + os.path.splitext(name)[1])
    if not os.path.exists(p):
        if not fetch:
            return None
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": HEADERS["User-Agent"], "Referer": "https://www.gamekee.com/"})
            with urllib.request.urlopen(req, timeout=30) as r:
                open(p, "wb").write(r.read())
        except Exception:
            return "ERR:" + key
    return hashlib.md5(open(p, "rb").read()).hexdigest()[:10]


# ------------------------------------------------------------- 富文本工具
def text_of(node):
    out = []

    def w(n):
        if isinstance(n, list):
            for x in n:
                w(x)
        elif isinstance(n, dict):
            if n.get("type") == "image":
                return
            if isinstance(n.get("text"), str):
                out.append(n["text"])
            for k in ("data", "children", "content"):
                if isinstance(n.get(k), (list, dict)):
                    w(n[k])

    w(node)
    return re.sub(r"\s+", " ", "".join(out)).strip()


def images_of(node):
    out = []

    def w(n):
        if isinstance(n, list):
            for x in n:
                w(x)
        elif isinstance(n, dict):
            if n.get("type") == "image" and n.get("src"):
                out.append(n["src"])
            for k in ("data", "children", "content"):
                if isinstance(n.get(k), (list, dict)):
                    w(n[k])

    w(node)
    return out


def find_nodes(node, wanted, out):
    if isinstance(node, list):
        for x in node:
            find_nodes(x, wanted, out)
    elif isinstance(node, dict):
        if node.get("type") in wanted:
            out.append(node)
        for v in node.values():
            if isinstance(v, (list, dict)):
                find_nodes(v, wanted, out)


# ------------------------------------------------------------------ 解析
SPLIT_TITLE = re.compile(r"^[【\[〖（(]\s*(.+?)\s*[】\]〗）)]\s*(.+)$")

# gamekee 上同一角色存在繁体/异体字页面，按下面这张表归一，避免被拆成两组异格
TRAD_MAP = str.maketrans({
    "黒": "黑", "恵": "惠", "巻": "卷", "禪": "禅", "竜": "龙",
    "薔": "蔷", "釘": "钉", "潔": "洁", "呪": "咒", "結": "结",
    "恵": "惠", "渋": "涩", "楽": "乐", "実": "实", "絵": "绘",
})


def normalize_name(s):
    return (s or "").translate(TRAD_MAP)


def parse(cid, j):
    d = j.get("data") or {}
    title = (d.get("title") or "").strip()
    cj = d.get("content_json")
    blocks = json.loads(cj) if isinstance(cj, str) else (cj or [])
    nodes = []
    find_nodes(blocks, {"character-profile", "fight-info", "skill-info"}, nodes)

    rec = {
        "contentId": str(cid),
        "wikiTitle": title,
        "variant": "",          # 异格前缀
        "baseCharacter": "",    # 本体名
        "release": "",
        "icons": {},            # 原始图标 URL
        "iconHashes": {},       # 解析后的内容哈希
        "stats": {},
        "skills": [],           # 指挥技能（3 个）
        "ultimates": [],        # 必杀技（1 个）
        "passives": [],         # 被动
        "comment": "",          # 角色评价（wiki 原文）
        "summary": (d.get("desc") or "").strip(),
        "thumb": d.get("thumb") or "",
        "updatedAt": d.get("updated_at") or 0,
        "wikiUrl": "https://www.gamekee.com/jk/%s.html" % cid,
        "imageName": text_of(((nodes[0] or {}).get("data") or {}).get("name")) if nodes else "",
    }

    m = SPLIT_TITLE.match(title)
    if m:
        rec["variant"], rec["baseCharacter"] = m.group(1).strip(), m.group(2).strip()
    else:
        rec["baseCharacter"] = title

    for n in nodes:
        t = n.get("type")
        data = n.get("data") or {}
        if t == "character-profile":
            rec["comment"] = text_of(data.get("desc"))
            for a in data.get("attrList") or []:
                key = text_of(a.get("title"))
                imgs = images_of(a.get("content"))
                val = text_of(a.get("content"))
                if key == "实装日期":
                    rec["release"] = val
                if imgs:
                    rec["icons"].setdefault(key, []).extend(imgs)
                elif val:
                    rec["icons"].setdefault(key, []).append("T:" + val)
        elif t == "fight-info":
            stats = {}
            labels = []
            for lv in data.get("levelList") or []:
                labels.append(lv.get("level") or "")
                stats_at = {}
                for it in lv.get("levelInfoList") or []:
                    k = text_of(it.get("title"))
                    v = text_of(it.get("content"))
                    if k:
                        stats_at[k] = v
                if stats_at:
                    stats = stats_at          # 取最后一个（5破）
            if stats:
                rec["stats"] = stats
                rec["statLevels"] = labels
        elif t == "skill-info":
            st = data.get("title") or ""
            bucket = "ultimates" if "必杀" in st else ("passives" if "被动" in st else "skills")
            for sk in data.get("skillList") or []:
                name = text_of(sk.get("name")).strip()
                desc = text_of(sk.get("desc")).strip()
                mc = re.search(r"(\d+)\s*消耗", desc)
                item = {
                    "name": name,
                    "cost": mc.group(1) if mc else "",
                    "desc": desc,
                    "more": text_of(sk.get("moreInfo")).strip(),
                }
                if name or desc:
                    rec[bucket].append(item)

    # 是否真的是角色条目（图鉴目录里混了"强度榜/词条解释/一图流"三篇攻略）
    rec["isCharacter"] = bool(rec["skills"] or rec["ultimates"]) and bool(rec["baseCharacter"])
    # 统计数据所在的突破等级（wiki 有 5破 / 0破 两种口径，统一取 5破）
    rec["statLevel"] = rec.pop("statLevels", "")
    # 繁体/异体字归一，避免同一角色被拆成两组
    rec["baseCharacterKey"] = normalize_name(rec["baseCharacter"])
    if rec["baseCharacterKey"] != rec["baseCharacter"]:
        rec["legacyName"] = rec["baseCharacter"]
        rec["baseCharacter"] = rec["baseCharacterKey"]

    # 图标哈希（首次运行会下载，之后命中缓存）
    for key, arr in rec["icons"].items():
        hs = []
        for src in arr:
            if src.startswith("T:"):
                continue
            hh = icon_hash(src)
            if hh:
                hs.append(hh)
        if hs:
            rec["iconHashes"][key] = hs
    return rec


# ------------------------------------------------------------------ 主流程
def main():
    refresh = "--refresh" in sys.argv
    listonly = "--list" in sys.argv

    print("[1/3] 抓取在线目录树 ...")
    tree = fetch_tree()
    json.dump(tree, open(os.path.join(ROOT, "tools", "wiki_tree.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    chars = characters(tree)
    print("      角色条目：%d" % len(chars))

    if listonly:
        for name, cid, _ in chars:
            print("  %-10s %s" % (cid, name))
        return

    print("[2/3] 抓取角色详情（增量）...")
    new_cnt = 0
    records, failed = [], []
    for i, (name, cid, _) in enumerate(chars, 1):
        try:
            j, isnew = fetch_content(cid, refresh=refresh)
            if isnew:
                new_cnt += 1
                time.sleep(0.45)
            rec = parse(cid, j)
            if not rec["baseCharacter"]:
                rec["baseCharacter"] = name
            records.append(rec)
        except Exception as e:
            failed.append({"cid": cid, "name": name, "error": repr(e)})
            print("      FAIL %s %s %r" % (cid, name, e))
        if i % 20 == 0:
            print("      %d / %d" % (i, len(chars)))

    print("[3/3] 写解析结果 ...")
    for rec in records:
        json.dump(rec, open(os.path.join(PARSED, "%s.json" % rec["contentId"]), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)

    # 覆盖率统计
    def has_stats(r):
        return bool(r["stats"]) and any(v not in ("", "0") for v in r["stats"].values())

    variants = {}
    for r in records:
        variants.setdefault(r["baseCharacter"], []).append(r)
    multi = {k: v for k, v in variants.items() if len(v) > 1}

    report = {
        "fetchedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(records),
        "newlyFetched": new_cnt,
        "failed": failed,
        "withStats": sum(1 for r in records if has_stats(r)),
        "withUltimate": sum(1 for r in records if r["ultimates"]),
        "withPassive": sum(1 for r in records if r["passives"]),
        "withSkills3": sum(1 for r in records if len(r["skills"]) >= 3),
        "withRelease": sum(1 for r in records if r["release"]),
        "withIconElement": sum(1 for r in records if r["iconHashes"].get("特性")),
        "baseCharacters": len(variants),
        "altFormGroups": len(multi),
        "altForms": {k: [x["variant"] or "(无前缀)" for x in v] for k, v in sorted(multi.items())},
        "noStats": [r["contentId"] + " " + r["wikiTitle"] for r in records if not has_stats(r)],
    }
    json.dump(report, open(os.path.join(ROOT, "tools", "wiki_report.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in report.items() if k not in ("altForms", "noStats", "failed")},
                     ensure_ascii=False, indent=1))
    print("异格组：%d 组" % report["altFormGroups"])
    for k, v in list(report["altForms"].items())[:20]:
        print("   %s: %s" % (k, " / ".join(v)))
    if report["noStats"]:
        print("无属性数据（数据缺口）：%d 条" % len(report["noStats"]))
        for x in report["noStats"][:15]:
            print("   -", x)


if __name__ == "__main__":
    main()
