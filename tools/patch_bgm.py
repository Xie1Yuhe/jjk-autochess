# -*- coding: utf-8 -*-
r"""
patch_bgm.py —— 接入 BGM，并整体提高音效音量

1. master 主音量系数 0.55 → 0.95（原来整体偏小一半）
2. 新增 BGM 层：准备阶段 / 战斗阶段 两首，循环播放，音量 0.45×
3. 音效与 BGM 同受设置里的「声音」开关控制
"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = os.path.join(ROOT, "js", "ui", "audio.js")
s = io.open(p, encoding="utf-8").read()

# ---------- 1) 主音量提高 ----------
before = s.count("volume * 0.55")
s = s.replace("volume * 0.55", "volume * 0.95")
print("主音量系数 0.55 → 0.95，替换 %d 处" % before)

# ---------- 2) 插入 BGM 模块 ----------
anchor = "  /* -------------------------------------------------------------- 控制 */"
bgm = '''  /* --------------------------------------------------------------- BGM */
  var BGM_SRC = {
    prep: 'assets/audio/bgm_prep.m4a',
    battle: 'assets/audio/bgm_battle.m4a'
  };
  var bgmEl = null;
  var bgmName = '';

  function bgmVol() {
    return enabled ? Math.min(1, volume * 0.45) : 0;
  }

  function startBgm(name) {
    var src = BGM_SRC[name];
    if (!src) return;
    if (bgmName === name && bgmEl && !bgmEl.paused) {
      bgmEl.volume = bgmVol();
      return;
    }
    bgmName = name;
    if (!bgmEl) {
      bgmEl = new Audio();
      bgmEl.loop = true;
      bgmEl.preload = 'auto';
    }
    if (bgmEl.getAttribute('src') !== src) {
      bgmEl.setAttribute('src', src);
    }
    bgmEl.volume = bgmVol();
    var pr = bgmEl.play();
    if (pr && pr.catch) pr.catch(function () { /* 需用户手势，忽略 */ });
  }

  function stopBgm() {
    bgmName = '';
    if (bgmEl) {
      try { bgmEl.pause(); } catch (e) { /* ignore */ }
    }
  }

  function syncBgmVolume() {
    if (bgmEl) bgmEl.volume = bgmVol();
    if (!enabled && bgmEl) { try { bgmEl.pause(); } catch (e) {} }
    else if (enabled && bgmName && bgmEl && bgmEl.paused) {
      var pr = bgmEl.play();
      if (pr && pr.catch) pr.catch(function () {});
    }
  }

''' + anchor
if "function startBgm" not in s:
    assert anchor in s, "控制 anchor"
    s = s.replace(anchor, bgm, 1)

# ---------- 3) 开关与音量同步到 BGM ----------
s = s.replace(
    "    if (enabled && ambientOn === false && JJK.App && JJK.App.inGame) startAmbient();",
    "    syncBgmVolume();\n    if (enabled && ambientOn === false && JJK.App && JJK.App.inGame) startAmbient();", 1)
s = s.replace(
    "  function setVolume(v) {\n    volume = Math.max(0, Math.min(1, v));",
    "  function setVolume(v) {\n    volume = Math.max(0, Math.min(1, v));\n    syncBgmVolume();", 1)

# ---------- 4) 导出 ----------
s = s.replace("    setVolume: setVolume,", "    setVolume: setVolume,\n    startBgm: startBgm,\n    stopBgm: stopBgm,", 1)

io.open(p, "w", encoding="utf-8").write(s)
print("[bgm] audio.js 已接入")

# ---------- 5) main.js：按阶段切歌 ----------
mp = os.path.join(ROOT, "js", "main.js")
m = io.open(mp, encoding="utf-8").read()
if "startBgm" not in m:
    old = "      syncDrawer();\n      if (App.refit) App.refit();\n    }"
    new = """      syncDrawer();
      if (App.refit) App.refit();
      // BGM：准备阶段与战斗阶段各一首
      if (typeof JJK.Audio.startBgm === 'function') {
        if (ph === 'battle' || ph === 'result') JJK.Audio.startBgm('battle');
        else if (ph === 'planning' || ph === 'idle') JJK.Audio.startBgm('prep');
      }
    }"""
    assert old in m, "phase anchor"
    m = m.replace(old, new, 1)
    io.open(mp, "w", encoding="utf-8").write(m)
    print("[bgm] main.js 已按阶段切歌")
else:
    print("[bgm] main.js 已有")
