/* =========================================================================
 *  battleview.js —— 战斗表现层
 *  每帧把 BattleSim 的状态同步到 DOM：位置 / 血条 / 蓝条 / 护盾；
 *  引擎抛出的 events 变成打击感：跳字、闪白、黑闪、技能名、领域、震屏。
 * ========================================================================= */
(function (global) {
  'use strict';

  var JJK = global.JJK = global.JJK || {};
  var U = JJK.util, D = JJK.data, W = JJK.Widgets, FX = JJK.FX, h = U.h;

  var layer = null;
  var els = {};        // battleUnitId -> element
  var active = false;
  var lastCell = 88;
  var hitScorer = {};

  function init() {
    layer = document.getElementById('battle-layer');
  }

  function cellPx() {
    var cs = FX.getCell();
    if (cs) lastCell = cs;
    return lastCell;
  }

  /* ============================================================== 令牌 */
  function createUnitEl(u) {
    var def = u.def;
    var unitData = D.unitById[def.id] || {
      id: def.id, name: def.name || '咒灵', cost: 1, element: def.element || '咒灵',
      card: def.card || '', icon: def.icon || '', traits: def.traits || []
    };
    var el = h('div', {
      class: 'unit battle-unit team-' + (u.team === 0 ? 'mine' : 'foe') + ' ' +
        (u.isClone ? 'is-clone ' : '')
    });
    el.dataset.buid = String(u.id);
    // 克隆种类：式神 / 影分身，用来区分角标文案与配色
    if (u.isClone) el.dataset.clone = u.cloneKind || 'shikigami';

    var token;
    if (unitData.card) {
      token = W.unitToken(unitData, u.star, def.items || [], { showItems: false, showStars: true });
    } else {
      // PvE 咒灵：没有立绘，用程序绘制的"咒灵面具"
      token = W.curseToken(def.name || '咒灵');
    }
    el.appendChild(token);

    // 血条 / 蓝条 / 护盾
    var bars = h('div', { class: 'tk-bars' }, [
      h('div', { class: 'tk-ult' }, [h('i')]),
      h('div', { class: 'tk-mp' }, [h('i')]),
      h('div', { class: 'tk-hp' }, [h('i')])
    ]);
    token.appendChild(bars);
    token.appendChild(h('div', { class: 'tk-shield', style: 'opacity:0' }));

    el.addEventListener('mouseenter', function () {
      if (!unitData.id) return;
      JJK.Tooltip.showUnitNow(def.id, el, {
        star: u.star, items: def.items || [], showEquipHint: false
      });
    });
    el.addEventListener('mouseleave', function () { JJK.Tooltip.hide(); });

    layer.appendChild(el);
    return el;
  }

  function syncOne(u, el) {
    var cs = cellPx();
    var tx = u.pos.x * 100;
    var ty = u.pos.y * 100;
    if (el.dataset.px !== String(u.pos.x) || el.dataset.py !== String(u.pos.y)) {
      el.dataset.px = String(u.pos.x);
      el.dataset.py = String(u.pos.y);
      el.style.transform = 'translate3d(' + tx + '%,' + ty + '%,0)';
    }
    var hpRatio = Math.max(0, u.hp / Math.max(1, u.maxHp));
    var mpRatio = Math.max(0, Math.min(1, u.mana / Math.max(1, u.manaMax)));
    var hpBar = el.querySelector('.tk-hp > i');
    var hpWrap = el.querySelector('.tk-hp');
    var mpBar = el.querySelector('.tk-mp > i');
    var mpWrap = el.querySelector('.tk-mp');
    var ultBar = el.querySelector('.tk-ult > i');
    var ultWrap = el.querySelector('.tk-ult');
    var sh = el.querySelector('.tk-shield');

    if (hpBar) hpBar.style.width = (hpRatio * 100).toFixed(1) + '%';
    if (hpWrap) {
      hpWrap.classList.toggle('low', hpRatio <= 0.5 && hpRatio > 0.25);
      hpWrap.classList.toggle('crit', hpRatio <= 0.25);
    }
    if (mpBar) mpBar.style.width = (mpRatio * 100).toFixed(1) + '%';
    if (mpWrap) mpWrap.classList.toggle('full', u.mana >= u.manaMax - 0.01);
    // 必杀槽：满了会亮，放完清零
    if (ultBar && u.ultCost) {
      var ur = Math.max(0, Math.min(1, (u.ult || 0) / u.ultCost));
      ultBar.style.width = (ur * 100).toFixed(1) + '%';
      if (ultWrap) {
        ultWrap.classList.toggle('full', (u.ult || 0) >= u.ultCost - 0.5);
        ultWrap.style.display = u.ultSpec ? '' : 'none';
      }
    } else if (ultWrap) {
      ultWrap.style.display = 'none';
    }
    if (sh) {
      var sr = Math.min(1, (u.shield || 0) / Math.max(1, u.maxHp));
      sh.style.opacity = sr > 0.005 ? '1' : '0';
      sh.style.transform = 'scaleX(' + sr.toFixed(3) + ')';
    }
    el.classList.toggle('mana-full', u.mana >= u.manaMax - 0.01 && u.alive);
  }

  /* ============================================================== 事件 */
  function unitElById(id) { return els[id]; }

  function onEvents(events) {
    for (var i = 0; i < events.length; i++) handleEvent(events[i]);
  }

  function handleEvent(e) {
    switch (e.t) {
      case 'dmg': {
        var big = !!e.skill;
        // 字号按伤害量做对数分级（10-100 / 100-1000 / 1000+）
        var mag = e.amount >= 1000 ? 'crit' : (big ? 'skill' : '');
        FX.float(e.pos, String(e.amount), mag);
        FX.hit(e.pos, { scale: big ? 1.2 : 0.9, particles: big ? 22 : 12 });
        FX.shock(e.pos);
        // 按伤害量级分层的打击音：轻击 / 重击 / 技能命中
        if (big) JJK.Audio.play('hitHeavy');
        else if (e.skill) JJK.Audio.play('hitCombo');
        else JJK.Audio.play('hitLight');
        flashUnit(e.targetId);
        if (big && e.from) {
          var ang = Math.atan2(e.pos.y - e.from.y, e.pos.x - e.from.x) * 180 / Math.PI;
          FX.slash(e.pos, ang, e.team === 0 ? '#ffe9a8' : '#ffb3c0');
          FX.star(e.pos, e.team === 0 ? '#ffe9a8' : '#ffb3c0');
          if (JJK.App && JJK.App.hitstop) JJK.App.hitstop(55);
        }
        break;
      }
      case 'bf': {
        FX.blackFlash(e.pos);
        // 黑色闪电：从命中点向外劈开
        (function () {
          var c = FX.cellCenter(e.pos.x, e.pos.y);
          if (JJK.Cut) JJK.Cut.boltStorm(c.px, c.py, { count: 5 });
        })();
        FX.crit(e.pos, '#ff2d55');
        FX.float({ x: e.pos.x, y: e.pos.y - 0.35 }, '黑闪', 'bf');
        JJK.Audio.play('bfThunder');
        if (JJK.App && JJK.App.hitstop) JJK.App.hitstop(110);
        break;
      }
      case 'heal': {
        FX.float(e.pos, '+' + e.amount, 'heal');
        FX.ring(e.pos, 'rgba(92,224,154,.9)');
        JJK.Audio.play('heal');
        break;
      }
      case 'shield': {
        FX.ring(e.pos, 'rgba(255,209,102,.9)');
        break;
      }
      case 'dodge': {
        FX.float(e.pos, '闪避', 'miss');
        break;
      }
      case 'miss': {
        FX.float(e.pos, '幻惑', 'miss');
        break;
      }
      case 'immune': {
        FX.float(e.pos, '无效', 'miss');
        FX.ring(e.pos, 'rgba(196,164,255,.85)');
        break;
      }
      case 'revive': {
        FX.float(e.pos, '复活', 'heal');
        FX.ring(e.pos, 'rgba(92,224,154,.95)');
        var rv = unitElById(e.unitId);
        if (rv) {
          rv.dataset.deadTimer = '0';      // 取消挂起的「隐藏」回调
          rv.classList.remove('dying', 'is-dead');
          rv.style.display = '';
          rv.classList.add('is-reviving');
          setTimeout(function () { rv.classList.remove('is-reviving'); }, 620);
        }
        JJK.Audio.play('heal');
        break;
      }
      case 'ult': {
        var ultU = JJK.data.unitById[e.defId];
        if (JJK.Cut) JJK.Cut.ultCutIn(ultU, e.name, e.team);
        FX.shake(16);
        FX.hitstopFlash(0.9);
        FX.ring(e.pos, e.team === 0 ? 'rgba(255,209,102,.95)' : 'rgba(255,90,120,.95)');
        JJK.Audio.play('ult');
        break;
      }
      case 'cast': {
        var isFoe = e.team === 1;
        FX.skillName(e.pos, e.name, isFoe);
        FX.ring(e.pos, isFoe ? 'rgba(255,120,140,.9)' : 'rgba(196,164,255,.92)');
        var cu = unitElById(e.srcId);
        if (cu) {
          cu.classList.remove('is-casting');
          void cu.offsetWidth;
          cu.classList.add('is-casting');
          setTimeout(function () { if (cu) cu.classList.remove('is-casting'); }, 520);
        }
        JJK.Audio.play('cast');
        break;
      }
      case 'attack': {
        var atk = unitElById(e.srcId);
        if (atk) {
          var dx = (e.to.x - e.from.x) * lastCell * 0.28;
          var dy = (e.to.y - e.from.y) * lastCell * 0.28;
          atk.style.setProperty('--lx', dx.toFixed(1) + 'px');
          atk.style.setProperty('--ly', dy.toFixed(1) + 'px');
          atk.classList.remove('is-attacking');
          void atk.offsetWidth;
          atk.classList.add('is-attacking');
          setTimeout(function () { if (atk) atk.classList.remove('is-attacking'); }, 240);
          // 远程单位：飞一颗咒力弹
          var melee = atk.dataset.melee === '1';
          if (!melee) FX.bolt(e.from, e.to, e.team === 0 ? '#c4a4ff' : '#ff8fa2', 0.26);
        JJK.Audio.play(melee ? 'slash' : 'hitLight');
        }
        break;
      }
      case 'death': {
        var de = unitElById(e.unitId);
        if (de) {
          de.style.setProperty('--dx', de.dataset.tx || '0px');
          de.style.setProperty('--dy', de.dataset.ty || '0px');
          de.classList.add('dying');
          // 打标记：复活时会被清掉，延时回调就不会再把棋子藏起来
          de.dataset.deadTimer = '1';
          setTimeout(function () {
            if (!de || de.dataset.deadTimer !== '1') return;   // 已被复活取消
            de.classList.add('is-dead');
            de.style.display = 'none';
          }, 520);
        }
        JJK.Audio.play('death');
        break;
      }
      case 'tier4': {
        // 羁绊 4 人档生效：专属横幅 + 色晕 + 音效
        var t4 = e.color || '#ffd166';
        FX.banner(e.title || '羁 绊 觉 醒', e.text || '', 1900, t4);
        FX.ring({ x: e.team === 0 ? 2 : 5, y: 1 }, t4);
        FX.shake(6);
        JJK.Audio.play('trait');
        break;
      }
      case 'domain': {
        // 领域展开：全屏暗幕 + 领域阵，比普通必杀多一层环境变化
        FX.domain(e.team);
        FX.shake(10);
        JJK.Audio.play('domain');
        // 领域持续底噪 + 朗读领域名（语音合成，不涉及版权音频）
        if (JJK.Audio.startHum) JJK.Audio.startHum();
        if (JJK.Audio.announceDomain) JJK.Audio.announceDomain(e.name);
        break;
      }
      case 'linkActive': {
        FX.banner('异 格 联 动', e.name + (e.team === 0 ? ' · 我方' : ' · 敌方'), 1700);

        JJK.Audio.play('trait');
        break;
      }
      case 'linkCast': {
        FX.float({ x: e.pos.x, y: e.pos.y - 0.3 }, '双发', 'skill');
        FX.ring(e.pos, 'rgba(91,184,255,.95)');
        break;
      }
      case 'linkStack': {
        FX.float({ x: e.pos.x, y: e.pos.y }, '+' + e.stacks, 'label');
        break;
      }
      case 'linkCharge': {
        FX.float({ x: e.pos.x, y: e.pos.y - 0.3 }, '充能', 'skill');
        FX.ring(e.pos, 'rgba(255,92,122,.95)');
        break;
      }
      case 'domain': {
        FX.domain(e.team);
        FX.banner('领 域 展 开', e.team === 0 ? '我方特级术师展开领域 · 全属性 +22%' : '敌方特级术师展开领域 · 全属性 +22%', 1800);
        JJK.Audio.play('domain');
        break;
      }
      case 'skillDomain': {
        FX.domain(e.team);
        break;
      }
      case 'domainEnd': {
        FX.banner('领 域 收 束', '属性加成结束', 1100);
        JJK.Audio.play('domainEnd');
        if (JJK.Audio.stopHum) JJK.Audio.stopHum();
        break;
      }
      case 'overtime': {
        FX.banner('加 时 开 始', '双方开始受到咒力反噬 · 战斗将强制结束', 2200);
        JJK.Audio.play('overtime');
        var band = h('div', { class: 'overtime-band' });
        document.body.appendChild(band);
        setTimeout(function () { if (band.parentNode) band.parentNode.removeChild(band); }, 3200);
        break;
      }
      case 'spawn': {
        // 新召唤物由下一帧 sync 自动创建
        FX.ring(e.pos, 'rgba(110,231,240,.9)');
        break;
      }
      default: break;
    }
  }

  function unitElsAt(cell) {
    for (var id in els) {
      if (!els.hasOwnProperty(id)) continue;
      var u = els[id];
      if (u.dataset.px === String(cell.x) && u.dataset.py === String(cell.y)) return u;
    }
    return null;
  }

  function flashUnit(id) {
    var el = unitElById(id);
    if (!el) return;
    el.classList.remove('is-hit');
    void el.offsetWidth;
    el.classList.add('is-hit');
    el.classList.add('is-moving');
    setTimeout(function () {
      if (el) { el.classList.remove('is-hit'); el.classList.remove('is-moving'); }
    }, 200);
  }

  /* ============================================================== 生命周期 */
  function start(sim) {
    lastCell = cellPx();
    clearAll();          // 注意：clearAll() 会把 active 置 false
    active = true;
    sim.units.forEach(function (u) {
      var el = createUnitEl(u);
      el.dataset.melee = (u.atkRange <= 1) ? '1' : '0';
      els[u.id] = el;
      syncOne(u, el);
    });
    // 入场：给令牌一个缩放入场（用 CSS 变量控制延迟）。
    // 不用 setTimeout 改 opacity —— 一旦定时器被节流，棋子就会永久隐身。
    var i = 0;
    sim.units.forEach(function (u) {
      var el = els[u.id];
      if (!el) return;
      el.style.setProperty('--in-delay', (Math.min(260, i * 18)) + 'ms');
      el.classList.add('just-spawned');
      i++;
    });
  }

  function sync(sim) {
    if (!active || !sim) return;
    // 新增单位（召唤物 / 分身）
    for (var i = 0; i < sim.units.length; i++) {
      var u = sim.units[i];
      if (!els[u.id] && u.alive) {
        var el = createUnitEl(u);
        el.dataset.melee = (u.atkRange <= 1) ? '1' : '0';
        els[u.id] = el;
        el.classList.add('just-spawned');
        el.style.setProperty('--in-delay', '0ms');
      }
      if (els[u.id]) syncOne(u, els[u.id]);
    }
  }

  function clearAll() {
    // 战斗结束 / 离开战场：兜底停掉领域持续音，避免残留
    if (JJK.Audio && JJK.Audio.stopHum) JJK.Audio.stopHum();
    if (layer) U.clear(layer);
    els = {};
    active = false;
    JJK.Tooltip.hide();
  }

  function stop() {
    clearAll();
  }

  JJK.BattleView = {
    init: init,
    start: start,
    sync: sync,
    stop: stop,
    onEvents: onEvents,
    isActive: function () { return active; }
  };

})(window);
