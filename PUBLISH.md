# 怎么把这个游戏公开到互联网上

> 项目是**纯静态网页**：没有后端、没有数据库、运行时零 fetch，
> 所有数据都烤进了 `data/game-data.js`，存档走浏览器 `localStorage`。
> 所以随便找个静态托管丢上去就能玩，不需要买服务器。

---

## 一、先打包（一条命令）

```bat
python tools\build_dist.py
```

生成 `dist/`：**397 个文件 / 10.0 MB**，只含游戏本体：

```
dist/
  index.html        游戏入口
  404.html          随便访问什么路径都回首页
  .nojekyll         GitHub Pages 用
  js/  css/  data/  assets/
```

上传时**只传 `dist/` 里的内容**，别把 `tools/`（爬虫与 wiki 缓存）、
`docs/`（开发文档）一起传上去。

---

## 二、三个可选方案

### 方案 A：Cloudflare Pages（最推荐）

**优点**：免费、全球 CDN、带宽不限、可绑自己的域名、拖拽即上线。

1. 注册 [dash.cloudflare.com](https://dash.cloudflare.com)（免费）
2. 左侧 **Workers & Pages → Create → Pages → Upload assets**
3. 把 `dist` 文件夹整个拖进去
4. 得到一个 `xxx.pages.dev` 的网址，立刻能玩

**更新**：重新拖一次即可，旧版本自动保留、可回滚。

---

### 方案 B：GitHub Pages

**优点**：免费、有版本历史、可以和源码放一起。

1. 建一个仓库（Public）
2. 把 `dist` 里的**所有内容**推到仓库根目录（`index.html` 必须在根）
3. 仓库 **Settings → Pages → Source: Deploy from a branch → main / (root)**
4. 等 1 分钟，访问 `https://你的用户名.github.io/仓库名/`

> 注意：必须带 `.nojekyll` 文件（`build_dist.py` 已生成），
> 否则 GitHub 会忽略 `_` 开头的文件。

---

### 方案 C：itch.io（最适合同人游戏）

**优点**：本身就是独立/同人游戏社区，能自动获得玩家流量；支持「免费 + 打赏」。

1. 注册 [itch.io](https://itch.io)，**Create new project**
2. Kind of project 选 **HTML**
3. 把 `dist` 文件夹**压缩成 zip**（`index.html` 要在 zip 根目录）
4. 上传 zip，勾选 **This file will be played in the browser**
5. 视口建议填 `1280 × 720`
6. 定价选 **No payments** 或 **$0 or donate**

> itch 是三者里唯一「自带玩家」的平台，适合你现在这个阶段。

---

## 三、上线前检查清单

| 检查项 | 状态 |
|---|---|
| 无绝对路径引用（`/js/...`） | ✅ 已验证 |
| 运行时无 `fetch`（不依赖接口） | ✅ 已验证 |
| HTTP 环境下可正常加载 | ✅ 已用 `python -m http.server` 验证 |
| 体积 10 MB | ✅ 首次加载约 3~8 秒（视网速） |
| 存档本地化 | ✅ localStorage，换设备不通用 |
| 移动端 | ⚠️ 未适配，目前按桌面 1280+ 设计 |

**建议**：第一次打开时给个加载提示（现在资源加载完成前是空白）。
如果需要，我可以加一个 `<div id="boot">载入中…</div>` 的极简 loading。

---

## 四、必须提醒你的法律风险

这是**《咒术回战》的同人作品**，角色、名称、立绘都归集英社 / 东宝 / サムザップ所有。

我的建议（不是法律意见，请自行判断）：

1. **完全免费，绝不收费**——不设付费、不接广告、不接受打赏
   （itch 上选 "No payments"，别选 donation）
2. **显式标注同人**——页脚已经有「非商业同人作品，角色与世界版权归芥见下下…」，保留它
3. **注明素材来源**——数值与技能文本来自 gamekee wiki，页脚也写了
4. **随时准备下架**——如果版权方提出异议，立刻关闭，别争
5. **优先选 itch.io 而不是自建域名**——同人社区对这类作品的容忍度更高，
   而且不会因为域名备案之类的事被卡

如果你想降低风险，还有一条路：**把角色名和立绘换成原创的**，
只保留玩法。这样就是一个完全合法的自走棋，但也就不是「咒术」同人了。

---

## 五、上线之后可以做的

- 加个**分享卡片**（og:image / og:title），微信/推特转发时有预览图
- 加**访问统计**（Cloudflare Web Analytics，免费且无 cookie）
- 把 `docs/` 里的设计文档整理成开发者日志，发到 itch 页面当更新说明

---

# 附：哪个方案「同步修改」最方便？

## 结论

| 方案 | 同步方式 | 工作量 | 推荐度 |
|---|---|---|---|
| **GitHub Pages（+Actions）** | `git push` → 自动构建发布 | 一次配置，之后 1 条命令 | ⭐⭐⭐⭐⭐ |
| **Cloudflare Pages（连仓库）** | `git push` → 自动构建发布 | 一次配置，之后 1 条命令 | ⭐⭐⭐⭐⭐ |
| itch.io | 手动重新打包上传 zip | 每次都要手动 | ⭐⭐ |
| 拖拽上传（CF/Netlify） | 手动拖文件夹 | 每次都要手动 | ⭐⭐ |

**推荐 GitHub Pages**：仓库就是唯一真相，改完推一下，1 分钟后线上自动更新。

## 已经给你配好了

```
.gitignore                        排除 dist/、wiki_cache/、临时文件
.github/workflows/deploy.yml      push 到 main 自动构建并发布
同步并发布.bat                     一键：暂存 → 提交 → 推送
```

仓库已 init 并完成首次提交（652 个文件，已排除 8.8MB 的 wiki 缓存和 dist）。

## 你只需要做三件事（一次性）

1. 在 GitHub 建一个 **Public** 仓库（不要勾选任何初始化文件）
2. 本地执行：
   ```
   git remote add origin https://github.com/你的用户名/仓库名.git
   git branch -M main
   git push -u origin main
   ```
3. 仓库 **Settings → Pages → Source 选 "GitHub Actions"**

之后每次改完，**双击 `同步并发布.bat`**，输入一句说明，回车即可。
Actions 会自动跑 `build_dist.py` 并把 `dist/` 发布出去。

> 如果选 Cloudflare Pages：连仓库后，构建命令填 `python tools/build_dist.py`，
> 输出目录填 `dist`。其余体验一致，但国内访问速度通常更好。

## 为什么不让 dist/ 入库

- `dist/` 是 `tools/build_dist.py` 的产物，入库会**每次提交翻倍体积**
- CI 里重新生成更可靠，也不会出现「源码改了但 dist 忘了重新打包」的事故
- `.gitignore` 已经排掉了
