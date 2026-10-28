# DESIGN_RESEARCH_UI.md —— 网页端「UI 灵动化」调研与实现记录

> Phase 7 第一步的技术依据。每条都写清楚**参考了什么 → 落到代码的哪里**。

## 1. 调研来源

| 来源 | 取到的结论 | 落地位置 |
|---|---|---|
| [Game Mechanics #40 Screen Effects (Juice/Polish/Feel)](https://github.com/raduacg/game-mechanics-optimizations/blob/main/G_05_screen_effects.md) | 震屏分级：轻 ±2-5px / 中 ±5-10px / 重 ±10-20px，指数衰减；顿帧：轻 33-50ms、重 83-133ms、暴击 133-200ms；跳字 1 秒上升 50-150px、按 log 分级、最后 0.3s 淡出；粒子必须对象池 | `fx.js` 的 `shake/hitstopFlash/float`、`particles.js` 的对象池、`main.js` 的 `App.hitstop` |
| [TFT:Gold（LoL Wiki）](https://wiki.leagueoflegends.com/en-us/TFT:Gold) | 利息 10 金 +1 上限 5；连胜/连败 3-4/5/6+ → +1/+2/+3；**PvP 获胜额外 +1 金** | 见 DESIGN_RESEARCH.md §1 与 P3 补丁 |
| [OP.GG TFT Damage Formula](https://op.gg/tft/game-guide/damage-formula) | 玩家伤害 = 存活单位伤害 + 回合基础伤害（R7+ 为 +17） | 见 DESIGN_RESEARCH.md §5 |
| 商业自走棋的材质语言（观察总结） | 半透明磨砂 + 1px 上亮下暗的渐变描边 + 品质色弱发光 + 多层阴影（近锐利 / 远弥散） | `v2-juice.css` §1「材质与厚度」 |

## 2. 四条体验目标的实现

### 2.1 整体氛围（厚重感 / 沉浸感）
- 面板：三层叠加（顶部高光扫过 + 主体渐变 + 底部加深），`backdrop-filter: blur(18px) saturate(1.3)`；
  用 `mask-composite: exclude` 做出**只描边不填充**的渐变边框，模拟被打磨的金属边缘。
- 阴影分三层：`0 1px 2px`（贴地）+ `0 8px 18px -6px`（中景）+ `0 28px 64px -28px`（远景弥散）。
- 顶栏/按钮做了内凹与外凸的分层：`inset 0 1px 0 rgba(255,255,255,.12)` + `inset 0 -1px 0 rgba(0,0,0,.55)`。
- 棋盘：叠加了一层**手写 SVG 符纹底纹**（data URI，离线可用）+ 中心竞技场打光 + 敌方半场红调压暗。
- 新增常驻「咒力浮尘」粒子（Canvas，极低密度），让空棋盘也有呼吸感。

### 2.2 卡牌的物理感
- 悬停：`perspective(760px) translateY(-16px) translateZ(26px) scale(1.055)`，
  缓动 `cubic-bezier(0.34, 1.56, 0.64, 1)`（带 overshoot 的弹性），340ms。
- 3D 倾斜：指针位置 → `--rx/--ry`（±12°/±14°），同时驱动 `--mx/--my` 让**光泽跟随指针**（`soft-light` 混合）。
- 品质色同时出现在：外发光、描边、费用圆章描边、名字条背景。
- 立绘与底板：三层渐变遮罩（顶部压暗 / 中部过渡 / 底部实心），杜绝硬切；名字条自带压暗底，
  即使立绘很亮也保证文字对比度 ≥ 7:1。
- 拖拽克隆体：`scale(1.12) rotate(1.5deg)` + 金色描边 + 双层投影 + 名字牌呼吸。

### 2.3 战斗的打击感
| 事件 | 表现 |
|---|---|
| 普通命中 | 跳字（弧线）+ 白闪（brightness 2.4）+ 冲击环 + 12-22 个火花粒子 + 55ms 顿帧 |
| 技能命中 | 更大字号 + 十字星芒 + 挥砍弧光 + 震屏 |
| 黑闪 | 径向爆闪 + 46 粒子 + 屏震 12px + 110ms 顿帧 + 全屏白脉冲 |
| 领域展开 | 全屏阵法扩散 + 46 个向上飘的咒力粒子 + 震屏 16px |
| 掉血 | 全屏红色暗角脉冲 + 数值红闪 |

跳字细节：字号按伤害量分级（<100 / 100-999 / 1000+ → `crit`），
轨迹是**弧线**（`--dx` 水平漂移 + `--rise` 抬升 + `--rot` 随机旋转），
0-16% 做 `scale(1.55)→1` 的弹入，64% 后开始淡出。

### 2.4 变强的感知
- **羁绊激活**：整行金色/品质色炸光 1 秒 + 顶部药丸横幅（图标 + 「X 激活」+ 第 N 档）+ 轻微震屏 + 音效。
  （关键修复：动画结束后用定时器摘掉 `is-flash`，否则浏览器暂停动画时会永久停在 0% 帧。）
- **金币变化**：顶栏数字 `scale(1.10)→1` 弹跳 + 绿/红染色 + 锚点旁漂浮 `+12`。
- **升级人口**：全屏「人 口 提 升 / LEVEL N」金色横幅 + 震屏 + 音效。
- **升星**：金色扩散环 + `★N` 上飘 + 震屏（原有），现在额外有粒子。

## 3. 性能

- 粒子用 Canvas + **对象池**（260 个预分配），命中时不创建 DOM/对象，避免 GC 抖动。
- 所有 DOM 特效节点都带自杀定时器，不会累积。
- `backdrop-filter` 只用在 3 个主面板与顶栏，避免整页模糊。
- 尊重 `prefers-reduced-motion`：震屏、顿帧、横幅动画都会降级。

## 4. 验收方式

```powershell
# 关键交互态的自动化截图（?dev= 是开发用开关，不影响正常入口）
index.html?dev=late&r=9         # 备战态（满人口 + 多羁绊）
index.html?dev=late-battle&r=9&t=4   # 战斗态（跳字/粒子/血条）
index.html?dev=hover&r=9        # 卡牌悬停 + 选中 + 详情浮层
index.html?dev=banner&r=9       # 羁绊激活横幅 + 金币漂浮 + 升级横幅
```
