/** Cassie v3 orb — canvas 2D */
(function () {
  'use strict';
  var canvas = document.getElementById('orb');
  var ctx = canvas.getContext('2d', { alpha: false });
  var state = 'idle';
  var amp = 0, targetAmp = 0, t = 0;
  var PAL = {
    idle: [55, 140, 255],
    listening: [45, 200, 110],
    thinking: [255, 170, 45],
    speaking: [210, 90, 255],
    locked: [80, 90, 110]
  };

  function resize() {
    canvas.width = innerWidth;
    canvas.height = innerHeight;
  }
  addEventListener('resize', resize);
  resize();

  window.cassieOrb = {
    setState: function (s) { state = s || 'idle'; },
    setAmplitude: function (a) { targetAmp = Math.max(0, Math.min(1, a)); }
  };

  function draw() {
    t++;
    amp += (targetAmp - amp) * 0.18;
    var w = canvas.width, h = canvas.height, cx = w / 2, cy = h / 2;
    var c = PAL[state] || PAL.idle;
    var pulse = 1 + amp * 0.4 + Math.sin(t * 0.045) * 0.05;
    if (state === 'thinking') pulse += Math.sin(t * 0.09) * 0.08;
    var r = Math.min(w, h) * 0.12 * pulse;

    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, w, h);

    var g = ctx.createRadialGradient(cx, cy, r * 0.1, cx, cy, r * 3.5);
    g.addColorStop(0, 'rgba(' + c[0] + ',' + c[1] + ',' + c[2] + ',0.12)');
    g.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, w, h);

    var orb = ctx.createRadialGradient(cx - r * 0.25, cy - r * 0.35, r * 0.05, cx, cy, r);
    orb.addColorStop(0, '#fff');
    orb.addColorStop(0.25, 'rgb(' + c.join(',') + ')');
    orb.addColorStop(1, 'rgb(' + Math.floor(c[0]*0.2) + ',' + Math.floor(c[1]*0.3) + ',60)');
    ctx.fillStyle = orb;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fill();

    for (var i = 0; i < 3; i++) {
      ctx.strokeStyle = 'rgba(' + c.join(',') + ',' + (0.15 - i * 0.03) + ')';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(cx, cy, r * (1.35 + i * 0.22) + Math.sin(t * 0.02 + i) * 4, 0, Math.PI * 2);
      ctx.stroke();
    }

    var b = 3 + amp * 14;
    var gray = Math.round(150 + amp * 90);
    ctx.strokeStyle = 'rgba(' + gray + ',' + gray + ',' + gray + ',' + (0.2 + amp * 0.55) + ')';
    ctx.lineWidth = b;
    ctx.strokeRect(b, b, w - b * 2, h - b * 2);

    requestAnimationFrame(draw);
  }
  draw();
})();
