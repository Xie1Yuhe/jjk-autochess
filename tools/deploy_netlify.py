# -*- coding: utf-8 -*-
r"""
deploy_netlify.py —— 把 dist/ 部署到 Netlify，得到不含用户名的网址

## 效果
    网址形如  https://jjk-autochess.netlify.app
    完全不含 GitHub 用户名，和你的账号名无关。

## 准备（一次性，你自己做）
1. 注册 https://app.netlify.com （用任意邮箱，可以完全匿名）
2. 右上头像 → User settings → Applications → Personal access tokens
   → New access token → 复制（只显示一次）

## 用法
    python tools\deploy_netlify.py <token> [站点名]

站点名不给就用 jjk-autochess。已存在同名站点会直接部署到它。
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.netlify.com/api/v1"


def call(path, token, method="GET", body=None, ctype="application/json", raw=None):
    url = API + path
    headers = {"Authorization": "Bearer " + token, "User-Agent": "dsh-deploy"}
    data = None
    if raw is not None:
        data = raw
        headers["Content-Type"] = ctype
    elif body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = ctype
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            txt = r.read().decode("utf-8")
            return json.loads(txt) if txt.strip() else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:400]
        raise RuntimeError("HTTP %d %s %s\n%s" % (e.code, method, path, detail))


def main():
    if len(sys.argv) < 2:
        print("用法: python tools\\deploy_netlify.py <token> [站点名]")
        return 1
    token = sys.argv[1]
    name = sys.argv[2] if len(sys.argv) > 2 else "jjk-autochess"

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    zip_path = os.path.join(root, "dist.zip")
    if not os.path.exists(zip_path):
        print("[netlify] 找不到 dist.zip，先运行 python tools\\build_dist.py 并打包")
        return 1

    # 1) 找是否已有同名站点
    site = None
    sites = call("/sites?per_page=100", token)
    for s in sites:
        if s.get("name") == name:
            site = s
            break

    # 2) 没有就创建
    if not site:
        print("[netlify] 创建站点 %s ..." % name)
        site = call("/sites", token, "POST", {"name": name})
    else:
        print("[netlify] 复用已有站点 %s" % name)

    site_id = site["id"]
    url = site.get("ssl_url") or site.get("url")

    # 3) 上传 zip 部署
    print("[netlify] 上传 %.1f MB ..." % (os.path.getsize(zip_path) / 1048576))
    with open(zip_path, "rb") as f:
        blob = f.read()
    dep = call("/sites/%s/deploys" % site_id, token, "POST",
               ctype="application/zip", raw=blob)

    print("[netlify] 部署完成，状态: %s" % dep.get("state"))
    print("[netlify] 网址: %s" % url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
