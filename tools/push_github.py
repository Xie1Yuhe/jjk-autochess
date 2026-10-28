# -*- coding: utf-8 -*-
r"""
push_github.py —— 通过 GitHub REST API 增量推送

## 为什么不用 git push
本机 `github.com:443` 被阻断，但 `api.github.com` 可达。

## 增量策略
计算每个文件的 git blob sha1（sha1("blob <len>\0" + content)），
与远端 main 的 tree 比对，只提交新增/修改的文件。
未改动的文件完全跳过 —— 一次小改动通常只需 1~3 个请求。

## 用法
    python tools\push_github.py <owner> <repo> <token> [commit-message]
"""
import base64
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request

API = "https://api.github.com"

EXCLUDE_DIRS = {".git", "dist", "node_modules", "__pycache__"}
EXCLUDE_SUFFIX = (".bak", ".pyc", ".log")
BINARY_EXT = {
    ".webp", ".png", ".jpg", ".jpeg", ".gif", ".ico",
    ".woff", ".woff2", ".ttf", ".otf", ".mp3", ".ogg", ".wav",
}


def api(path, token, method="GET", body=None, retries=4):
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
            with urllib.request.urlopen(req, timeout=120) as r:
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
    raise RuntimeError(last or "unknown")


def blob_sha(data):
    h = hashlib.sha1()
    h.update(b"blob %d\0" % len(data))
    h.update(data)
    return h.hexdigest()


def collect(root):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root).replace("\\", "/")
        if rel_dir == ".":
            rel_dir = ""
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fn in filenames:
            if fn.endswith(EXCLUDE_SUFFIX):
                continue
            rel = (rel_dir + "/" + fn) if rel_dir else fn
            if rel.startswith("dist/"):
                continue
            if rel.startswith("tools/wiki_cache/") or rel.startswith("tools/wiki_parsed/"):
                continue
            if rel.startswith(".github/"):
                continue
            if fn.startswith("_") and fn.endswith(".html"):
                continue
            out.append((rel, os.path.join(dirpath, fn)))
    out.sort()
    return out


def remote_tree(owner, repo, token):
    try:
        ref = api("/repos/%s/%s/git/ref/heads/main" % (owner, repo), token)
        sha = ref["object"]["sha"]
    except Exception:
        return {}, None
    t = api("/repos/%s/%s/git/trees/%s?recursive=1" % (owner, repo, sha), token)
    return ({e["path"]: e["sha"] for e in t.get("tree", []) if e["type"] == "blob"}, sha)


def main():
    if len(sys.argv) < 4:
        print("用法: python tools\\push_github.py <owner> <repo> <token> [msg]")
        return 1
    owner, repo, token = sys.argv[1], sys.argv[2], sys.argv[3]
    msg = sys.argv[4] if len(sys.argv) > 4 else "update"

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files = collect(root)
    remote, head = remote_tree(owner, repo, token)
    print("[push] 本地 %d 个文件，远端 %d 个" % (len(files), len(remote)))

    entries = []
    for rel, full in files:
        with open(full, "rb") as f:
            raw = f.read()
        if remote.get(rel) == blob_sha(raw):
            continue
        ext = os.path.splitext(rel)[1].lower()
        text = None
        if ext not in BINARY_EXT and len(raw) < 900000:
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = None
        if text is not None:
            entries.append({"path": rel, "mode": "100644", "type": "blob", "content": text})
        else:
            r = api("/repos/%s/%s/git/blobs" % (owner, repo), token, "POST",
                    {"content": base64.b64encode(raw).decode("ascii"), "encoding": "base64"})
            entries.append({"path": rel, "mode": "100644", "type": "blob", "sha": r["sha"]})
        print("   + " + rel)

    if not entries:
        print("[push] 没有改动，无需推送")
        return 0

    print("[push] 需提交 %d 个文件" % len(entries))
    tree_sha = None
    BATCH = 150
    for start in range(0, len(entries), BATCH):
        body = {"tree": entries[start:start + BATCH]}
        if tree_sha:
            body["base_tree"] = tree_sha
        tree_sha = api("/repos/%s/%s/git/trees" % (owner, repo), token, "POST", body)["sha"]

    body = {"message": msg, "tree": tree_sha}
    if head:
        body["parents"] = [head]
    commit = api("/repos/%s/%s/git/commits" % (owner, repo), token, "POST", body)
    print("[push] commit: %s" % commit["sha"][:10])

    if head:
        api("/repos/%s/%s/git/refs/heads/main" % (owner, repo), token, "PATCH",
            {"sha": commit["sha"]})
    else:
        api("/repos/%s/%s/git/refs" % (owner, repo), token, "POST",
            {"ref": "refs/heads/main", "sha": commit["sha"]})

    print("[push] 完成 → https://github.com/%s/%s" % (owner, repo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
