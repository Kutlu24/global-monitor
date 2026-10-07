/* Stage art — a small "screenshot-like" illustration per destination, drawn with
 * Canvas2D and uploaded by stage.js as a texture over each shader plane.
 * Illustrative only: no real figures are shown, just the shape of each tool.
 * window.StageArt.draw(i, canvas) paints slide i. */
(function () {
  'use strict';
  var W = 768, H = 985;
  var SANS = '"Work Sans", system-ui, sans-serif', MONO = '"Space Mono", ui-monospace, monospace';
  var COL = ['#5ec2b7', '#e5604d'];
  var PATH = ['global-monitor', 'risk-simulator'];
  var BLOC = [['BRICS+', '#e0b13e'], ['EU', '#6aa5e0'], ['US', '#d94f3d'], ['USMCA', '#5fb877']];

  function rr(c, x, y, w, h, r) {
    c.beginPath();
    c.moveTo(x + r, y); c.arcTo(x + w, y, x + w, y + h, r); c.arcTo(x + w, y + h, x, y + h, r);
    c.arcTo(x, y + h, x, y, r); c.arcTo(x, y, x + w, y, r); c.closePath();
  }
  function txt(c, s, x, y, font, color, align) {
    c.font = font; c.fillStyle = color; c.textAlign = align || 'left'; c.textBaseline = 'alphabetic';
    c.fillText(s, x, y);
  }
  function alpha(hex, a) {
    var n = parseInt(hex.slice(1), 16);
    return 'rgba(' + (n >> 16) + ',' + ((n >> 8) & 255) + ',' + (n & 255) + ',' + a + ')';
  }
  function panel(c, x, y, w, h, r, stroke) {
    c.save(); c.shadowColor = 'rgba(0,0,0,0.5)'; c.shadowBlur = 36; c.shadowOffsetY = 16;
    rr(c, x, y, w, h, r); c.fillStyle = 'rgba(16,19,24,0.9)'; c.fill(); c.restore();
    if (stroke) { rr(c, x, y, w, h, r); c.strokeStyle = stroke; c.lineWidth = 2; c.stroke(); }
  }

  function frame(c, i) {
    c.clearRect(0, 0, W, H);
    var g = c.createLinearGradient(0, 0, 0, H);
    g.addColorStop(0, 'rgba(8,10,13,0.30)'); g.addColorStop(0.5, 'rgba(8,10,13,0.5)'); g.addColorStop(1, 'rgba(8,10,13,0.30)');
    c.fillStyle = g; c.fillRect(0, 0, W, H);
    c.font = '700 24px ' + MONO;
    var w = c.measureText(PATH[i]).width + 56;
    rr(c, 40, 40, w, 52, 26); c.fillStyle = 'rgba(12,14,18,0.8)'; c.fill();
    c.strokeStyle = alpha(COL[i], 0.7); c.lineWidth = 2; c.stroke();
    c.beginPath(); c.arc(68, 66, 7, 0, 7); c.fillStyle = COL[i]; c.fill();
    txt(c, PATH[i], 88, 75, '700 24px ' + MONO, '#eceae4');
  }

  /* ---- Global Monitor: four blocs compared across four dimensions ---- */
  function monitor(c) {
    var a = COL[0], x = 70, y = 170, w = 628;
    /* bloc legend */
    var lx = x;
    BLOC.forEach(function (b) {
      c.font = '700 24px ' + SANS;
      var cw = c.measureText(b[0]).width + 62;
      rr(c, lx, y, cw, 54, 27); c.fillStyle = alpha(b[1], 0.16); c.fill(); c.strokeStyle = alpha(b[1], 0.85); c.lineWidth = 2; c.stroke();
      c.beginPath(); c.arc(lx + 28, y + 27, 8, 0, 7); c.fillStyle = b[1]; c.fill();
      txt(c, b[0], lx + 46, y + 36, '700 24px ' + SANS, '#eceae4');
      lx += cw + 10;
    });
    /* grouped bars: four dimensions x four blocs (shape only, no values) */
    panel(c, x, y + 92, w, 560, 28, 'rgba(255,255,255,0.1)');
    var dims = ['Economy', 'Trade', 'Social', 'Military'];
    var shapes = [[0.78, 0.62, 0.9, 0.4], [0.7, 0.8, 0.55, 0.45], [0.5, 0.82, 0.68, 0.74], [0.4, 0.55, 0.92, 0.5]];
    dims.forEach(function (d, r) {
      var ry = y + 92 + 44 + r * 128;
      txt(c, d.toUpperCase(), x + 36, ry + 8, '700 22px ' + MONO, '#a3a3a0');
      BLOC.forEach(function (b, k) {
        var by = ry + 22 + k * 20;
        rr(c, x + 36, by, w - 72, 12, 6); c.fillStyle = 'rgba(255,255,255,0.07)'; c.fill();
        rr(c, x + 36, by, (w - 72) * shapes[r][k], 12, 6); c.fillStyle = b[1]; c.fill();
      });
    });
    /* sources */
    txt(c, 'KEPT IN SYNC WITH', x, 898, '700 20px ' + MONO, a);
    txt(c, 'World Bank · OECD · IMF · UN Comtrade · WTO · UNDP · SIPRI', x, 934, '400 21px ' + MONO, '#a3a3a0');
  }

  /* ---- Risk Simulator: scenario chips, a gradient ranking, vulnerable <-> resilient ---- */
  function risk(c) {
    var a = COL[1], x = 70, y = 170, w = 628;
    txt(c, 'SCENARIO', x, y + 18, '700 22px ' + MONO, a);
    var chips = ['Russia–NATO conflict', 'Hormuz energy shock', 'Climate crisis'];
    var cy = y + 44;
    chips.forEach(function (s, k) {
      c.font = '700 25px ' + SANS;
      var cw = c.measureText(s).width + 48;
      rr(c, x, cy, cw, 56, 28);
      if (k === 1) { c.fillStyle = a; c.fill(); } else { c.fillStyle = 'rgba(16,19,24,0.8)'; c.fill(); c.strokeStyle = alpha(a, 0.6); c.lineWidth = 2; c.stroke(); }
      txt(c, s, x + 24, cy + 37, '700 25px ' + SANS, k === 1 ? '#fff' : '#eceae4');
      cy += 68;
    });
    txt(c, '+ 3 more scenarios', x, cy + 26, '400 22px ' + MONO, '#a3a3a0');

    /* ranked bars: red -> green, shape only */
    var py = cy + 60;
    panel(c, x, py, w, 410, 28, 'rgba(255,255,255,0.1)');
    var lens = [0.94, 0.86, 0.79, 0.7, 0.58, 0.47, 0.36, 0.24];
    lens.forEach(function (l, k) {
      var by = py + 36 + k * 44, t = 1 - k / (lens.length - 1);
      var col = t > 0.5 ? mix([242, 189, 77], [92, 184, 120], (t - 0.5) * 2) : mix([219, 69, 56], [242, 189, 77], t * 2);
      txt(c, String(k + 1), x + 34, by + 22, '700 20px ' + MONO, '#a3a3a0');
      rr(c, x + 78, by + 4, (w - 120) * l, 26, 13); c.fillStyle = 'rgb(' + col.join(',') + ')'; c.fill();
    });
    /* legend */
    var lg = c.createLinearGradient(x, 0, x + w, 0);
    lg.addColorStop(0, '#db4538'); lg.addColorStop(0.5, '#f2bd4d'); lg.addColorStop(1, '#5cb878');
    rr(c, x, py + 442, w, 12, 6); c.fillStyle = lg; c.fill();
    txt(c, 'VULNERABLE', x, py + 484, '700 20px ' + MONO, '#a3a3a0');
    txt(c, 'RESILIENT', x + w, py + 484, '700 20px ' + MONO, '#a3a3a0', 'right');
  }
  function mix(a, b, t) { return [Math.round(a[0] + (b[0] - a[0]) * t), Math.round(a[1] + (b[1] - a[1]) * t), Math.round(a[2] + (b[2] - a[2]) * t)]; }

  var DRAW = [monitor, risk];
  window.StageArt = {
    W: W, H: H,
    draw: function (i, canvas) {
      canvas.width = W; canvas.height = H;
      var c = canvas.getContext('2d');
      frame(c, i); DRAW[i](c);
      return canvas;
    }
  };
})();
