/**
 * Cassie holographic orb — Canvas 2D, Pi-friendly, no WebGL.
 */
(function () {
  'use strict';

  var canvas = document.getElementById('canvas');
  if (!canvas) return;

  var ctx = canvas.getContext('2d', { alpha: false });
  var targetState = 'idle';
  var amplitude = 0;
  var targetAmp = 0;
  var t = 0;
  var dpr = 1;

  var PALETTES = {
    idle:      { h: 215, s: 85, l: 58, accent: 195, rim: 240 },
    listening: { h: 152, s: 90, l: 52, accent: 170, rim: 180 },
    thinking:  { h: 38,  s: 95, l: 58, accent: 25,  rim: 55  },
    speaking:  { h: 310, s: 88, l: 58, accent: 280, rim: 330 }
  };

  var color = { h: 215, s: 85, l: 58, accent: 195, rim: 240 };
  var floatY = 0;
  var rotY = 0;
  var rotX = 0.35;
  var sparkPhase = 0;

  var PARTICLE_COUNT = 36;
  var particles = [];
  var i;

  for (i = 0; i < PARTICLE_COUNT; i++) {
    particles.push({
      theta: Math.random() * Math.PI * 2,
      phi: Math.acos(2 * Math.random() - 1),
      speed: 0.004 + Math.random() * 0.012,
      size: 0.8 + Math.random() * 2.2,
      twinkle: Math.random() * Math.PI * 2
    });
  }

  var RING_COUNT = 14;
  var rings = [];
  for (i = 0; i < RING_COUNT; i++) {
    rings.push({
      tilt: (i / RING_COUNT) * Math.PI,
      spin: (Math.random() - 0.5) * 0.008,
      wobble: Math.random() * Math.PI * 2
    });
  }

  function hsl(h, s, l, a) {
    return 'hsla(' + h + ',' + s + '%,' + l + '%,' + (a != null ? a : 1) + ')';
  }

  function lerp(a, b, f) {
    return a + (b - a) * f;
  }

  function lerpColor(cur, tgt, f) {
    return {
      h: lerp(cur.h, tgt.h, f),
      s: lerp(cur.s, tgt.s, f),
      l: lerp(cur.l, tgt.l, f),
      accent: lerp(cur.accent, tgt.accent, f),
      rim: lerp(cur.rim, tgt.rim, f)
    };
  }

  function resize() {
    /* Pi 3: keep DPR at 1 — high DPR + kiosk timing causes partial canvas clears */
    dpr = 1;
    var w = window.innerWidth || document.documentElement.clientWidth || screen.width || 800;
    var h = window.innerHeight || document.documentElement.clientHeight || screen.height || 480;
    canvas.width = w;
    canvas.height = h;
    canvas.style.width = w + 'px';
    canvas.style.height = h + 'px';
    ctx.setTransform(1, 0, 0, 1, 0, 0);
  }

  window.addEventListener('resize', resize);
  resize();

  window.setSphereState = function (s) {
    targetState = s || 'idle';
  };

  window.setSphereAmplitude = function (a) {
    targetAmp = Math.max(0, Math.min(1, Number(a) || 0));
  };

  function stateSpeed() {
    if (targetState === 'thinking') return 1.8;
    if (targetState === 'speaking') return 1.4 + amplitude * 0.8;
    if (targetState === 'listening') return 0.9 + amplitude * 0.6;
    return 0.55;
  }

  function drawBackground(w, h, cx, cy, r) {
    var bg = ctx.createRadialGradient(cx, cy - r * 0.2, r * 0.2, cx, cy, Math.max(w, h) * 0.75);
    bg.addColorStop(0, '#040810');
    bg.addColorStop(0.35, '#020406');
    bg.addColorStop(1, '#000000');
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, w, h);

    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    var mist = ctx.createRadialGradient(cx, cy, r * 0.5, cx, cy, r * 3.5);
    mist.addColorStop(0, hsl(color.h, color.s, color.l, 0.07));
    mist.addColorStop(0.5, hsl(color.accent, color.s - 10, color.l - 10, 0.03));
    mist.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = mist;
    ctx.fillRect(0, 0, w, h);
    ctx.restore();

    ctx.save();
    ctx.globalAlpha = 0.035;
    for (i = 0; i < 40; i++) {
      var sx = (Math.sin(i * 127.1 + t * 0.001) * 0.5 + 0.5) * w;
      var sy = (Math.cos(i * 269.5 + t * 0.0013) * 0.5 + 0.5) * h;
      var ss = 0.5 + (i % 3) * 0.5;
      ctx.fillStyle = '#fff';
      ctx.beginPath();
      ctx.arc(sx, sy, ss, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
  }

  function drawFloorReflection(cx, cy, r) {
    ctx.save();
    ctx.translate(cx, cy + r * 1.15);
    ctx.scale(1, 0.22);
    var refl = ctx.createRadialGradient(0, 0, r * 0.1, 0, 0, r * 1.4);
    refl.addColorStop(0, hsl(color.h, color.s, color.l + 20, 0.22));
    refl.addColorStop(0.45, hsl(color.accent, color.s, color.l, 0.08));
    refl.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = refl;
    ctx.beginPath();
    ctx.arc(0, 0, r * 1.35, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  function drawOuterBloom(cx, cy, r) {
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    var layers = [
      { scale: 4.2, alpha: 0.025 },
      { scale: 3.0, alpha: 0.04 },
      { scale: 2.1, alpha: 0.06 },
      { scale: 1.55, alpha: 0.09 },
      { scale: 1.25, alpha: 0.12 }
    ];
    for (i = 0; i < layers.length; i++) {
      var L = layers[i];
      var g = ctx.createRadialGradient(cx, cy, r * 0.05, cx, cy, r * L.scale);
      g.addColorStop(0, hsl(color.h, color.s, color.l + 15, L.alpha * (0.7 + amplitude * 0.5)));
      g.addColorStop(0.35, hsl(color.accent, color.s, color.l, L.alpha * 0.6));
      g.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(cx, cy, r * L.scale, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
  }

  function drawHoloRings(cx, cy, r) {
    var speed = stateSpeed();
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    for (i = 0; i < rings.length; i++) {
      var ring = rings[i];
      var tilt = ring.tilt + Math.sin(t * 0.01 + ring.wobble) * 0.08;
      var spin = t * ring.spin * speed + ring.wobble;
      var rx = r * (1.05 + Math.sin(tilt) * 0.08);
      var ry = r * (0.28 + Math.abs(Math.cos(tilt)) * 0.12);
      var alpha = 0.06 + Math.abs(Math.sin(tilt)) * 0.14;
      if (targetState === 'thinking') alpha += 0.06;
      ctx.strokeStyle = hsl(color.rim, 80, 72, alpha);
      ctx.lineWidth = 0.8 + (i % 3) * 0.35;
      ctx.beginPath();
      ctx.ellipse(cx, cy + floatY, rx, ry, spin, 0, Math.PI * 2);
      ctx.stroke();
    }
    ctx.restore();
  }

  function project(theta, phi, radius) {
    var x = radius * Math.sin(phi) * Math.cos(theta + rotY);
    var y = radius * Math.cos(phi);
    var z = radius * Math.sin(phi) * Math.sin(theta + rotY);
    var y2 = y * Math.cos(rotX) - z * Math.sin(rotX);
    var z2 = y * Math.sin(rotX) + z * Math.cos(rotX);
    return { x: x, y: y2, z: z2, depth: z2 };
  }

  function drawParticles(cx, cy, r) {
    var speed = stateSpeed();
    var sorted = [];
    for (i = 0; i < particles.length; i++) {
      var p = particles[i];
      p.theta += p.speed * speed * (targetState === 'listening' ? 1.5 : 1);
      var pt = project(p.theta, p.phi, r * 1.02);
      sorted.push({ p: p, pt: pt });
    }
    sorted.sort(function (a, b) { return a.pt.depth - b.pt.depth; });

    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    for (i = 0; i < sorted.length; i++) {
      var item = sorted[i];
      var p = item.p;
      var pt = item.pt;
      var depthNorm = (pt.depth + r) / (2 * r);
      var alpha = 0.25 + depthNorm * 0.55;
      var sz = p.size * (0.6 + depthNorm * 0.7);
      var tw = 0.5 + 0.5 * Math.sin(t * 0.06 + p.twinkle);
      ctx.fillStyle = hsl(color.rim, 70, 80, alpha * tw * (0.6 + amplitude * 0.4));
      ctx.beginPath();
      ctx.arc(cx + pt.x, cy + pt.y + floatY, sz, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
  }

  function drawPlasmaCore(cx, cy, r) {
    ctx.save();
    ctx.beginPath();
    ctx.arc(cx, cy + floatY, r, 0, Math.PI * 2);
    ctx.clip();

    var base = ctx.createRadialGradient(
      cx - r * 0.35, cy - r * 0.4 + floatY, r * 0.05,
      cx, cy + floatY, r * 1.05
    );
    base.addColorStop(0, 'rgba(255,255,255,0.95)');
    base.addColorStop(0.18, hsl(color.h, color.s - 5, color.l + 28, 0.92));
    base.addColorStop(0.45, hsl(color.h, color.s, color.l, 0.88));
    base.addColorStop(0.78, hsl(color.accent, color.s + 5, color.l - 18, 0.95));
    base.addColorStop(1, hsl(color.h, color.s + 10, color.l - 32, 1));
    ctx.fillStyle = base;
    ctx.fillRect(cx - r, cy - r + floatY, r * 2, r * 2);

    ctx.globalCompositeOperation = 'overlay';
    for (i = 0; i < 5; i++) {
      var ox = Math.sin(t * 0.025 + i * 1.7) * r * 0.35;
      var oy = Math.cos(t * 0.02 + i * 2.3) * r * 0.3;
      var blob = ctx.createRadialGradient(cx + ox, cy + oy + floatY, 0, cx + ox, cy + oy + floatY, r * 0.65);
      blob.addColorStop(0, hsl(color.accent + i * 8, 90, 65, 0.35));
      blob.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = blob;
      ctx.fillRect(cx - r, cy - r + floatY, r * 2, r * 2);
    }

    ctx.globalCompositeOperation = 'source-atop';
    ctx.globalAlpha = 0.07;
    for (i = 0; i < r * 2; i += 3) {
      var scanY = (i + (t * 2) % 6) - r + floatY;
      ctx.fillStyle = '#fff';
      ctx.fillRect(cx - r, cy + scanY, r * 2, 1);
    }

    ctx.restore();
  }

  function drawRimLight(cx, cy, r) {
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    var rim = ctx.createRadialGradient(cx, cy + floatY, r * 0.82, cx, cy + floatY, r * 1.02);
    rim.addColorStop(0, 'rgba(0,0,0,0)');
    rim.addColorStop(0.55, hsl(color.rim, 90, 75, 0.15));
    rim.addColorStop(0.85, hsl(color.rim, 95, 85, 0.55 + amplitude * 0.25));
    rim.addColorStop(1, hsl(color.h, 80, 60, 0.2));
    ctx.fillStyle = rim;
    ctx.beginPath();
    ctx.arc(cx, cy + floatY, r, 0, Math.PI * 2);
    ctx.fill();

    var specX = cx - r * 0.32 + Math.sin(t * 0.015) * r * 0.06;
    var specY = cy - r * 0.38 + floatY + Math.cos(t * 0.012) * r * 0.04;
    var spec = ctx.createRadialGradient(specX, specY, 0, specX, specY, r * 0.55);
    spec.addColorStop(0, 'rgba(255,255,255,0.85)');
    spec.addColorStop(0.25, 'rgba(255,255,255,0.25)');
    spec.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = spec;
    ctx.beginPath();
    ctx.arc(cx, cy + floatY, r, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  function drawEnergyArcs(cx, cy, r) {
    var speed = stateSpeed();
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    var arcCount = 3;
    for (i = 0; i < arcCount; i++) {
      var baseAngle = (t * 0.018 * speed) + (i / arcCount) * Math.PI * 2;
      var arcR = r * (1.35 + i * 0.12);
      ctx.strokeStyle = hsl(color.accent + i * 15, 90, 70, 0.12 + amplitude * 0.15);
      ctx.lineWidth = 2 + i * 0.5;
      ctx.lineCap = 'round';
      ctx.beginPath();
      ctx.arc(cx, cy + floatY, arcR, baseAngle, baseAngle + Math.PI * 0.55);
      ctx.stroke();
    }
    ctx.restore();
  }

  function drawThinkingSparks(cx, cy, r) {
    if (targetState !== 'thinking' && targetState !== 'speaking') return;
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    sparkPhase += 0.08;
    for (i = 0; i < 8; i++) {
      var ang = sparkPhase + i * 0.785;
      var dist = r * (1.15 + 0.08 * Math.sin(t * 0.1 + i));
      var sx = cx + Math.cos(ang) * dist;
      var sy = cy + floatY + Math.sin(ang) * dist * 0.35;
      var sg = ctx.createRadialGradient(sx, sy, 0, sx, sy, 6);
      sg.addColorStop(0, hsl(color.rim, 100, 85, 0.9));
      sg.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = sg;
      ctx.beginPath();
      ctx.arc(sx, sy, 5, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
  }

  function drawSphere() {
    var w = window.innerWidth;
    var h = window.innerHeight;
    var cx = w / 2;
    var cy = h / 2;
    var baseR = Math.min(w, h) * 0.11;

    amplitude += (targetAmp - amplitude) * 0.18;
    color = lerpColor(color, PALETTES[targetState] || PALETTES.idle, 0.04);

    var breathe = 1 + Math.sin(t * 0.022) * 0.035;
    var pulse = 1 + amplitude * 0.42;
    if (targetState === 'thinking') pulse += Math.sin(t * 0.07) * 0.07;
    if (targetState === 'speaking') pulse += Math.sin(t * 0.11) * 0.12 * (0.3 + amplitude);
    if (targetState === 'listening') pulse += Math.sin(t * 0.09) * 0.05 * (0.4 + amplitude);

    floatY = Math.sin(t * 0.018) * baseR * 0.06;
    rotY += 0.006 * stateSpeed();
    rotX = 0.32 + Math.sin(t * 0.008) * 0.06;

    var r = baseR * breathe * pulse;

    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, w, h);
    ctx.clearRect(0, 0, w, h);

    drawBackground(w, h, cx, cy, r);
    drawFloorReflection(cx, cy, r);
    drawOuterBloom(cx, cy, r);
    drawEnergyArcs(cx, cy, r);
    drawHoloRings(cx, cy, r);
    drawParticles(cx, cy, r);
    drawPlasmaCore(cx, cy, r);
    drawRimLight(cx, cy, r);
    drawThinkingSparks(cx, cy, r);

    if (typeof window.drawMicBorder === 'function') {
      window.drawMicBorder();
    }
  }

  function loop() {
    t++;
    drawSphere();
    requestAnimationFrame(loop);
  }

  loop();
})();
