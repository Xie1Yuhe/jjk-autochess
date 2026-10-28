# -*- coding: utf-8 -*-
r"""
push_github.py —— 通过 GitHub REST API 推送仓库

## 为什么不用 git push
本机 `github.com:443` 被阻断（Connection reset），但 `api.github.com` 可达。
所以改用 Git Data API：
  · 二进制文件 → POST /git/blobs（base64）
  · 文本文件   → 直接内联在 /git/trees 的 content 字段里
  · 分批建 tree（base_tree 链式）→ 建 commit → 更新 main 引用

## 用法
    python tools\push_github.py <owner> <repo> <token> [commit-message]
"""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

API = "https://api.github.com"

EXCLUDE_DIRS = {".git", "dist", "node_modules", "__pycache__", "tools/wiki_cache"}
EXCLUDE_SUFFIX = (".bak", ".pyc", ".log")
EXCLUDE_PREFIX = ("_",)

BINARY_EXT = {
    ".webp", ".png", ".jpg", ".jpeg", ".gif", ".ico",
    ".woff", ".woff2", ".ttf", ".otf", ".mp3", ".ogg", ".wav",
}


def api(path, token, method="GET", body=None, retries=3):
    url = API + path
    data = None
    headers = {
        "Authorization": "Bearer " + token,
        "User-Agent": "dsh-push",
        "Accept": "application/vnd.github+json",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:400]
            if e.code in (502, 503, 504) and attempt < retries - 1:
                time.sleep(2 + attempt * 2)
                last = detail
                continue
            raise RuntimeError("HTTP %d %s %s\n%s" % (e.code, method, path, detail))
        except Exception as e:
            last = str(e)
            if attempt < retries - 1:
                time.sleep(2 + attempt * 2)
                continue
            raise
    raise RuntimeError(last or "unknown error")


def collect(root):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root).replace("\\", "/")
        if rel_dir == ".":
            rel_dir = ""
        # 剪枝
        dirnames[:] = [d for d in dirnames
                       if (os.path.join(rel_dir, d).lstrip("/") if rel_dir else d) not in EXCLUDE_DIRS
                       and d not in ("node_modules", "__pycache__", ".git")]
        for fn in filenames:
            if fn.endswith(EXCLUDE_SUFFIX):
                continue
            if fn.startswith(EXCLUDE_PREFIX) and fn.endswith(".html"):
                continue
            rel = (rel_dir + "/" + fn) if rel_dir else fn
            if rel == "dist" or rel.startswith("dist/"):
                continue
            if rel.startswith("tools/wiki_cache/"):
                continue
            if rel.startswith(".github/"):   # token 无 workflow scope，先跳过
                continue
            out.append((rel, os.path.join(dirpath, fn)))
    out.sort()
    return out


def main():
    if len(sys.argv) < 4:
        print("用法: python tools\\push_github.py <owner> <repo> <token> [msg]")
        return 1
    owner, repo, token = sys.argv[1], sys.argv[2], sys.argv[3]
    msg = sys.argv[4] if len(sys.argv) > 4 else "update"

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files = collect(root)
    print("[push] 待推送 %d 个文件" % len(files))

    # 1) 二进制先建 blob
    entries = []
    blobs = 0
    for i, (rel, full) in enumerate(files):
        ext = os.path.splitext(rel)[1].lower()
        size = os.path.getsize(full)
        if ext in BINARY_EXT:
            with open(full, "rb") as f:
                content = base64.b64encode(f.read()).decode("ascii")
            r = api("/repos/%s/%s/git/blobs" % (owner, repo), token, "POST",
                    {"content": content, "encoding": "base64"})
            entries.append({"path": rel, "mode": "100644", "type": "blob", "sha": r["sha"]})
            blobs += 1
        else:
            try:
                text = open(full, "r", encoding="utf-8").read()
            except UnicodeDecodeError:
                with open(full, "rb") as f:
                    content = base64.b64encode(f.read()).decode("ascii")
                r = api("/repos/%s/%s/git/blobs" % (owner, repo), token, "POST",
                        {"content": content, "encoding": "base64"})
                entries.append({"path": rel, "mode": "100644", "type": "blob", "sha": r["sha"]})
                blobs += 1
                continue
            if len(text) > 900000:   # 超大文件也走 blob
                with open(full, "rb") as f:
                    content = base64.b64encode(f.read()).decode("ascii")
                r = api("/repos/%s/%s/git/blobs" % (owner, repo), token, "POST",
                        {"content": content, "encoding": "base64"})
                entries.append({"path": rel, "mode": "100644", "type": "blob", "sha": r["sha"]})
                blobs += 1
                continue
            entries.append({"path": rel, "mode": "100644", "type": "blob", "content": text})
        if (i + 1) % 50 == 0:
            print("   已处理 %d/%d（blob %d）" % (i + 1, len(files), blobs))

    print("[push] blob 上传完成：%d 个二进制" % blobs)

    # 2) 分批建 tree
    tree_sha = None
    BATCH = 120
    for start in range(0, len(entries), BATCH):
        chunk = entries[start:start + BATCH]
        body = {"tree": chunk}
        if tree_sha:
            body["base_tree"] = tree_sha
        r = api("/repos/%s/%s/git/trees" % (owner, repo), token, "POST", body)
        tree_sha = r["sha"]
        print("[push] tree 批次 %d-%d → %s" % (start, start + len(chunk) - 1, tree_sha[:10]))

    # 3) 建 commit
    commit = api("/repos/%s/%s/git/commits" % (owner, repo), token, "POST",
                 {"message": msg, "tree": tree_sha})
    print("[push] commit: %s" % commit["sha"])

    # 4) 更新/创建 main 引用
    try:
        api("/repos/%s/%s/git/refs/heads/main" % (owner, repo), token, "PATCH",
            {"sha": commit["sha"], "force": True})
        print("[push] 已更新 main")
    except RuntimeError:
        api("/repos/%s/%s/git/refs" % (owner, repo), token, "POST",
            {"ref": "refs/heads/main", "sha": commit["sha"]})
        print("[push] 已创建 main")

    print("[push] 完成 → https://github.com/%s/%s" % (owner, repo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
