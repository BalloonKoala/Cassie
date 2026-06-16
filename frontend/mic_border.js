/**
 * Mic-reactive gray border around the screen edge.
 */
(function () {
  'use strict';

  var micLevel = 0;
  var targetLevel = 0;
  var canvas = document.getElementById('canvas');
  if (!canvas) return;

  window.setMicLevel = function (v) {
    targetLevel = Math.max(0, Math.min(1, Number(v) || 0));
  };

  window.drawMicBorder = function () {
    var ctx = canvas.getContext('2d');
    micLevel += (targetLevel - micLevel) * 0.25;
    var w = window.innerWidth;
    var h = window.innerHeight;
    var thickness = 3 + micLevel * 14;
    var alpha = 0.15 + micLevel * 0.65;
    var gray = Math.round(180 + micLevel * 75);

    ctx.save();
    ctx.strokeStyle = 'rgba(' + gray + ',' + gray + ',' + gray + ',' + alpha + ')';
    ctx.lineWidth = thickness;
    ctx.shadowColor = 'rgba(255,255,255,' + (alpha * 0.5) + ')';
    ctx.shadowBlur = 8 + micLevel * 20;
    var inset = thickness / 2 + 2;
    ctx.strokeRect(inset, inset, w - thickness - 4, h - thickness - 4);
    ctx.restore();
  };
})();
