/* Stage — a raw-WebGL slider for the four tools (no libraries, no assets).
 *
 * Each destination is a curved plane whose surface is a procedural shader "artwork".
 * One float `pos` drives everything: drag / wheel / keys move a target, a
 * critically-damped spring chases it, and its *velocity* bends, shears and
 * colour-splits the planes so the interface feels like cloth moving through
 * space. At rest the planes keep a slow idle sway. Falls back to the classic
 * page (cards grid) if WebGL is unavailable, the context is lost, or JS is off.
 */
(function () {
  'use strict';
  var stage = document.getElementById('stage');
  if (!stage || /[?&]classic\b/.test(location.search)) return;

  var canvas = stage.querySelector('canvas');
  var gl = null;
  try {
    gl = canvas.getContext('webgl', { alpha: true, antialias: true, premultipliedAlpha: true, powerPreference: 'high-performance' });
  } catch (e) { /* fall through */ }
  if (!gl) return;

  var N = 3;
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var fine = window.matchMedia('(pointer: fine)').matches;
  var COLORS = [[94, 194, 183], [155, 140, 255], [229, 96, 77]];
  var INK = ['#06201c', '#14102e', '#ffffff'];

  /* ------------------------------------------------------------ shaders */
  var VS = [
    'attribute vec2 a_uv;',
    'uniform vec2 u_res; uniform vec2 u_size; uniform float u_rel; uniform float u_pitch; uniform float u_cy;',
    'uniform float u_vel; uniform float u_time; uniform vec2 u_mouse; uniform float u_open; uniform float u_intro;',
    'uniform float u_hover; uniform float u_motion;',
    'varying vec2 v_uv;',
    'void main() {',
    '  v_uv = a_uv;',
    '  vec2 p = a_uv - 0.5;',
    '  float o = u_open;',
    '  float live = (1.0 - o) * u_motion;',
    '  float rel = u_rel * (1.0 - o);',
    '  float ar = abs(rel);',
    '  float t = u_time;',
    '  vec2 size = mix(u_size * (1.0 + 0.035 * u_hover), u_res * 1.12, o);',
    '  vec2 l = p * size;',
    '  float v = u_vel * live;',
    /* idle sway + velocity-driven bend */
    '  float sway = sin(t * 0.55 + rel * 1.9) * 0.032 * live + sin(t * 0.31 + 1.7) * 0.012 * live;',
    '  float ang = (-rel * 0.46 + sway + u_mouse.x * 0.07 * (1.0 - ar)) * (1.0 - o);',
    '  float ca = cos(ang), sa = sin(ang);',
    '  float cx = rel * u_pitch;',
    '  float cz = -ar * ar * 150.0 - ar * 70.0;',
    '  float ripple = (sin(p.x * 3.2 + t * 0.7 + rel) + sin(p.y * 2.6 - t * 0.55)) * 4.5 * live;',
    '  float tilt = p.x * v * 260.0;',
    '  float x = cx + l.x * ca + sin(p.y * 4.0 + t * 1.6 + rel) * v * 22.0;',
    '  float z = cz + l.x * sa + ripple + tilt;',
    '  float y = l.y + l.x * v * 0.11 + sin(p.x * 5.0 - t * 1.2) * v * 14.0',
    '          + sin(t * 0.8 + rel * 1.3) * 6.0 * live + u_cy - (1.0 - u_intro) * u_res.y * 0.6',
    '          - u_mouse.y * 10.0 * (1.0 - ar) * live;',
    '  x += -u_mouse.x * 16.0 * (0.4 + ar * 0.8) * live;',
    '  float f = 1300.0;',
    '  float s = f / (f - z);',
    '  vec2 sp = vec2(x, y) * s;',
    '  gl_Position = vec4(sp / (u_res * 0.5), 0.0, 1.0);',
    '}'
  ].join('\n');

  var FS = [
    '#ifdef GL_FRAGMENT_PRECISION_HIGH', 'precision highp float;', '#else', 'precision mediump float;', '#endif',
    'varying vec2 v_uv;',
    'uniform float u_kind; uniform float u_time; uniform float u_rel; uniform float u_vel; uniform float u_aspect;',
    'uniform vec3 u_c; uniform vec3 u_c2; uniform vec2 u_lm; uniform float u_hover; uniform float u_alpha; uniform float u_open;',
    'uniform float u_motion; uniform sampler2D u_tex;',
    'float hash(vec2 p) { p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }',
    'float vnoise(vec2 p) {',
    '  vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);',
    '  return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), f.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), f.x), f.y);',
    '}',
    'float fbm(vec2 p) { float a = 0.5, s = 0.0; for (int i = 0; i < 4; i++) { s += a * vnoise(p); p = p * 2.03 + 11.7; a *= 0.5; } return s; }',

    'vec2 hash22(vec2 p) { return vec2(hash(p), hash(p + 37.7)); }',

    /* Global Monitor — halftone world of four blocs joined by pulsing trade arcs */
    'float arcLine(vec2 p, vec2 a, vec2 b, float h, float tt) {',
    '  vec2 ab = b - a; float L = length(ab); vec2 d = ab / L; vec2 n = vec2(-d.y, d.x);',
    '  float along = dot(p - a, d); float s = clamp(along / L, 0.0, 1.0);',
    '  float dist = abs(dot(p - a, n) - h * sin(3.14159 * s));',
    '  float within = step(0.0, along) * step(along, L);',
    '  float pulse = smoothstep(0.82, 1.0, sin((s * 2.0 - tt * 0.35) * 6.2831) * 0.5 + 0.5);',
    '  return (1.0 - smoothstep(0.0, 0.0045, dist)) * within * (0.3 + 0.7 * pulse);',
    '}',
    'vec3 artBlocs(vec2 q, float t) {',
    '  float cells = 36.0;',
    '  vec2 g = q * cells; vec2 id = floor(g); vec2 f = fract(g) - 0.5;',
    '  vec2 c = (id + 0.5) / cells;',
    '  vec2 b0 = vec2(-0.2, 0.2), b1 = vec2(0.02, 0.27), b2 = vec2(0.2, 0.12), b3 = vec2(-0.02, -0.18);',
    '  float d0 = length(c - b0), d1 = length(c - b1), d2 = length(c - b2), d3 = length(c - b3);',
    '  vec3 k0 = vec3(0.88, 0.69, 0.24), k1 = vec3(0.42, 0.65, 0.88), k2 = vec3(0.85, 0.31, 0.24), k3 = vec3(0.37, 0.72, 0.47);',
    '  vec3 bc = k0; float dm = d0;',
    '  if (d1 < dm) { dm = d1; bc = k1; } if (d2 < dm) { dm = d2; bc = k2; } if (d3 < dm) { dm = d3; bc = k3; }',
    '  float land = smoothstep(0.44, 0.6, fbm(c * 2.4 + vec2(3.0, 1.0) + t * 0.01));',
    '  float pulse = 0.5 + 0.5 * sin(t * 0.8 - dm * 10.0);',
    '  float r = land * (0.16 + 0.2 * pulse * smoothstep(0.5, 0.0, dm));',
    '  float dot_ = 1.0 - smoothstep(r - 0.05, r, length(f));',
    '  vec3 col = mix(u_c2, u_c * 0.2, 0.5 + 0.5 * q.y);',
    '  col += bc * dot_ * (0.45 + 0.55 * smoothstep(0.55, 0.0, dm));',
    '  float arcs = arcLine(q, b0, b2, 0.12, t) + arcLine(q, b1, b3, -0.1, t + 1.3) + arcLine(q, b0, b3, 0.07, t + 2.1) + arcLine(q, b1, b2, 0.06, t + 0.6);',
    '  col += u_c * min(arcs, 1.0) * 0.9;',
    '  vec3 nodes = vec3(0.0);',
    '  nodes += k0 * (1.0 - smoothstep(0.012, 0.03, length(q - b0)));',
    '  nodes += k1 * (1.0 - smoothstep(0.012, 0.03, length(q - b1)));',
    '  nodes += k2 * (1.0 - smoothstep(0.012, 0.03, length(q - b2)));',
    '  nodes += k3 * (1.0 - smoothstep(0.012, 0.03, length(q - b3)));',
    '  return col + nodes * 1.2;',
    '}',

    /* Risk Simulator — a choropleth of drifting cells, red (vulnerable) to green (resilient) */
    'vec3 artRisk(vec2 q, float t) {',
    '  vec2 g = q * 5.6 + vec2(0.3, 0.1); vec2 id = floor(g); vec2 f = fract(g);',
    '  float md = 8.0, md2 = 8.0; vec2 best = vec2(0.0);',
    '  for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++) {',
    '    vec2 o = vec2(float(i), float(j));',
    '    vec2 r = 0.5 + 0.4 * sin(t * 0.22 + 6.2831 * hash22(id + o));',
    '    vec2 d = o + r - f; float dd = dot(d, d);',
    '    if (dd < md) { md2 = md; md = dd; best = id + o; } else if (dd < md2) { md2 = dd; }',
    '  }',
    '  float sc = smoothstep(0.22, 0.78, fbm(best * 0.33 + vec2(t * 0.035, 2.0)));',
    '  vec3 red = vec3(0.86, 0.27, 0.22), yel = vec3(0.95, 0.74, 0.30), grn = vec3(0.36, 0.72, 0.47);',
    '  vec3 cc = sc < 0.5 ? mix(red, yel, sc * 2.0) : mix(yel, grn, (sc - 0.5) * 2.0);',
    '  float edge = sqrt(md2) - sqrt(md);',
    '  float line = 1.0 - smoothstep(0.0, 0.07, edge);',
    '  vec3 col = mix(cc * 0.78, vec3(0.05, 0.05, 0.07), line * 0.95);',
    '  col = mix(col, u_c2 * 2.0, 0.18);',
    '  col += cc * exp(-md * 7.0) * 0.18;',
    '  return col;',
    '}',

    /* Current Tension — event ripples (conflict red / cooperation blue) over a live signal trace */
    'vec3 artTension(vec2 q, float t) {',
    '  vec3 col = mix(u_c2, u_c * 0.16, 0.5 + 0.5 * q.y);',
    '  vec2 g = q * 4.4; vec2 id = floor(g); vec2 f = fract(g) - 0.5;',
    '  vec3 tint = vec3(0.0);',
    '  for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++) {',
    '    vec2 o = vec2(float(i), float(j)); vec2 cid = id + o;',
    '    float h = hash(cid), h2 = hash(cid + 17.3);',
    '    vec2 pos = o + (hash22(cid) - 0.5) * 0.7;',
    '    float period = 5.0 + h * 6.0;',
    '    float ph = fract((t + h * period) / period);',
    '    float d = length(f - pos);',
    '    float rd = (d - ph * 1.15) * 13.0;',
    '    float ring = exp(-rd * rd) * (1.0 - ph);',
    '    vec3 k = h2 < 0.45 ? vec3(0.88, 0.30, 0.25) : vec3(0.40, 0.62, 0.92);',
    '    float on = step(0.38, h);',
    '    tint += k * on * (ring + (1.0 - smoothstep(0.02, 0.055, d)) * (1.0 - ph) * 0.9);',
    '  }',
    '  col += tint * 0.95;',
    '  float tr = 1.0 - smoothstep(0.0, 0.007, abs(q.y - 0.07 * sin(q.x * 7.0 + t * 0.6) - 0.04 * sin(q.x * 17.0 - t * 1.1)));',
    '  col += u_c * tr * 0.7;',
    '  col += u_c * 0.05 * (1.0 - smoothstep(0.0, 0.004, abs(fract(q.y * 8.0) - 0.5) - 0.495));',
    '  return col;',
    '}',

    'vec3 art(vec2 q, float t) {',
    '  if (u_kind < 0.5) return artBlocs(q, t);',
    '  if (u_kind < 1.5) return artTension(q, t);',
    '  return artRisk(q, t);',
    '}',

    'void main() {',
    '  vec2 asp = vec2(u_aspect, 1.0);',
    '  vec2 q = (v_uv - 0.5) * asp;',
    /* the artwork drifts at a different rate than its frame -> depth */
    '  q.x += u_rel * 0.22 * (1.0 - u_open);',
    '  float t = u_time;',
    '  float ch = u_vel * 0.016 * u_motion;',
    '  vec3 col;',
    '  if (abs(ch) > 0.0012) col = vec3(art(q + vec2(ch, 0.0), t).r, art(q, t).g, art(q - vec2(ch, 0.0), t).b);',
    '  else col = art(q, t);',
    /* illustration layer: drifts at its own rate (parallax) and splits colour with speed */
    '  vec2 tuv = (v_uv - 0.5) * 0.985 + 0.5 + vec2(-u_rel * 0.028 * (1.0 - u_open), 0.0);',
    '  vec4 tx = texture2D(u_tex, tuv);',
    '  if (abs(ch) > 0.0012) tx = vec4(texture2D(u_tex, tuv + vec2(ch * 0.7, 0.0)).r, tx.g, texture2D(u_tex, tuv - vec2(ch * 0.7, 0.0)).b, tx.a);',
    '  col = col * (1.0 - tx.a) + tx.rgb;',
    '  vec2 hv = v_uv - 0.5 - u_lm / asp;',
    '  col += u_c * exp(-dot(hv * asp, hv * asp) * 7.0) * u_hover * 0.16;',
    '  float vig = smoothstep(1.0, 0.2, length((v_uv - 0.5) * 1.5));',
    '  col *= mix(0.5, 1.0, vig);',
    '  col *= mix(1.0, 0.42, smoothstep(0.0, 1.3, abs(u_rel)) * (1.0 - u_open));',
    '  col += (hash(gl_FragCoord.xy + fract(t) * 91.0) - 0.5) * 0.045;',
    /* rounded rect mask, in plane-height units */
    '  float r = mix(0.028, 0.0, u_open);',
    '  vec2 dd = abs(v_uv - 0.5) * asp - (asp * 0.5 - r);',
    '  float sd = length(max(dd, 0.0)) + min(max(dd.x, dd.y), 0.0) - r;',
    '  float m = 1.0 - smoothstep(-0.0015, 0.0015, sd);',
    '  float rim = (1.0 - smoothstep(0.0, 0.006, abs(sd + 0.003))) * 0.22;',
    '  col += rim;',
    '  float a = m * u_alpha;',
    '  gl_FragColor = vec4(col * a, a);',
    '}'
  ].join('\n');

  function compile(type, src) {
    var s = gl.createShader(type);
    gl.shaderSource(s, src);
    gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
      if (window.console) console.warn('stage shader:', gl.getShaderInfoLog(s));
      return null;
    }
    return s;
  }
  var vs = compile(gl.VERTEX_SHADER, VS), fs = compile(gl.FRAGMENT_SHADER, FS);
  if (!vs || !fs) return;
  var prog = gl.createProgram();
  gl.attachShader(prog, vs); gl.attachShader(prog, fs);
  gl.bindAttribLocation(prog, 0, 'a_uv');
  gl.linkProgram(prog);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) return;
  gl.useProgram(prog);

  var U = {};
  ['u_res', 'u_size', 'u_rel', 'u_pitch', 'u_cy', 'u_vel', 'u_time', 'u_mouse', 'u_open', 'u_intro', 'u_hover', 'u_motion',
    'u_kind', 'u_aspect', 'u_c', 'u_c2', 'u_lm', 'u_alpha', 'u_tex'].forEach(function (n) { U[n] = gl.getUniformLocation(prog, n); });

  /* subdivided unit grid */
  var COLS = 22, ROWS = 30, verts = [], idx = [];
  for (var j = 0; j <= ROWS; j++) for (var i = 0; i <= COLS; i++) verts.push(i / COLS, j / ROWS);
  for (var jj = 0; jj < ROWS; jj++) for (var ii = 0; ii < COLS; ii++) {
    var a = jj * (COLS + 1) + ii, b = a + 1, c = a + COLS + 1, d = c + 1;
    idx.push(a, b, c, b, d, c);
  }
  var vbo = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(verts), gl.STATIC_DRAW);
  var ibo = gl.createBuffer(); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ibo);
  gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint16Array(idx), gl.STATIC_DRAW);
  gl.enableVertexAttribArray(0);
  gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
  gl.enable(gl.BLEND);
  gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);

  /* illustration textures (Canvas2D -> WebGL), redrawn once web fonts arrive */
  var texs = [];
  function uploadArt() {
    if (!window.StageArt) return;
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
    gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, true);
    for (var k = 0; k < N; k++) {
      var cv = window.StageArt.draw(k, document.createElement('canvas'));
      if (!texs[k]) {
        texs[k] = gl.createTexture();
      }
      gl.bindTexture(gl.TEXTURE_2D, texs[k]);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, cv);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    }
    gl.activeTexture(gl.TEXTURE0);
    gl.uniform1i(U.u_tex, 0);
  }
  uploadArt();
  if (document.fonts && document.fonts.load) {
    Promise.all(['700 40px "Work Sans"', '500 40px "Work Sans"', 'italic 400 32px "Work Sans"', '700 24px "Space Mono"', '400 24px "Space Mono"']
      .map(function (f) { return document.fonts.load(f); })).then(uploadArt, function () {});
  }

  /* ------------------------------------------------------------ state */
  var quality = 1, slowEma = 0, lastDrop = 0;   /* adaptive render scale: sinks when frames get slow */
  var W = 0, H = 0, pw = 0, ph = 0, pitch = 0, cyPx = 0, aspect = 1;
  var pos = 0, target = 0, velS = 0, lastPos = 0;
  var mouse = { x: 0, y: 0, tx: 0, ty: 0, px: -999, py: -999 };
  var hover = 0, hoverT = 0;
  var drag = null, wheel = { acc: 0, base: 0, timer: 0, on: false };
  var opening = -1, openT = 0, openStart = 0;
  var t0 = performance.now(), time = 0, last = t0, active = -1, raf = 0;
  var copies = [].slice.call(stage.querySelectorAll('.slide-copy'));
  var giants = [].slice.call(stage.querySelectorAll('.giant'));
  var navBtns = [].slice.call(stage.querySelectorAll('.stage-index button'));
  var counter = stage.querySelector('.stage-count');

  function wrap(x) { return x; }                       /* two ends, no looping */
  function mod(x) { return clamp(Math.round(x), 0, N - 1); }
  function clamp(x, a, b) { return Math.max(a, Math.min(b, x)); }

  function resize() {
    W = stage.clientWidth; H = stage.clientHeight;
    var dpr = Math.min(window.devicePixelRatio || 1, W < 760 ? 1.6 : 2) * quality;
    canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
    gl.viewport(0, 0, canvas.width, canvas.height);
    var mobile = W < 760;
    var ASPECT = window.StageArt ? window.StageArt.W / window.StageArt.H : 0.78;
    ph = mobile ? H * 0.38 : H * 0.58;
    pw = ph * ASPECT;
    var maxW = mobile ? W * 0.74 : W * 0.34;
    if (pw > maxW) { pw = maxW; ph = pw / ASPECT; }
    pitch = pw * (mobile ? 1.04 : 1.18);
    cyPx = mobile ? H * 0.085 : H * 0.045;     /* px the plane centre sits above the viewport centre */
    aspect = pw / ph;
    var cyScreen = H / 2 - cyPx;
    stage.style.setProperty('--plane-cy', cyScreen + 'px');
    stage.style.setProperty('--plane-h', ph + 'px');
    giants.forEach(function (g) { g.style.marginTop = ''; });
  }

  /* ------------------------------------------------------------ chrome sync */
  function setActive(i) {
    if (i === active) return;
    active = i;
    copies.forEach(function (c, k) {
      var on = k === i;
      c.setAttribute('aria-hidden', on ? 'false' : 'true');
      var a = c.querySelector('a'); if (a) a.tabIndex = on ? 0 : -1;
    });
    navBtns.forEach(function (b, k) { b.setAttribute('aria-current', k === i ? 'true' : 'false'); });
    if (counter) counter.textContent = '0' + (i + 1) + ' / 0' + N;
    stage.style.setProperty('--accent-ink', INK[i]);
  }

  function accentAt(p) {
    p = clamp(p, 0, N - 1);
    var f = Math.min(Math.floor(p), N - 2), k = p - f, a = COLORS[f], b = COLORS[f + 1];
    var s = k * k * (3 - 2 * k);
    return [a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s, a[2] + (b[2] - a[2]) * s];
  }

  function syncDom() {
    var ac = accentAt(pos);
    stage.style.setProperty('--accent', 'rgb(' + (ac[0] | 0) + ',' + (ac[1] | 0) + ',' + (ac[2] | 0) + ')');
    var cy = H / 2 - cyPx;
    for (var i = 0; i < N; i++) {
      var rel = wrap(i - pos), ar = Math.abs(rel);
      var c = copies[i], g = giants[i];
      var o = clamp(1 - ar * 2.3, 0, 1);
      c.style.opacity = o;
      c.style.visibility = o > 0.01 ? 'visible' : 'hidden';
      c.style.transform = 'translate3d(' + (rel * -70).toFixed(1) + 'px,0,0)';
      c.style.pointerEvents = o > 0.85 ? 'auto' : 'none';
      var go = clamp(1.05 - ar * 0.85, 0, 1) * (opening >= 0 ? 0 : 1);
      g.style.opacity = go.toFixed(3);
      g.style.transform = 'translate3d(' + (rel * pitch * 1.9 - 0).toFixed(1) + 'px,0,0) translate(-50%,-50%) scale(' + (1 + ar * 0.06).toFixed(3) + ')';
      g.style.top = cy + 'px';
    }
  }

  /* ------------------------------------------------------------ input */
  function go(i) { target = clamp(Math.round(target) + i, 0, N - 1); }
  function goTo(k) { /* nearest route to slide k */
    target = clamp(k, 0, N - 1);
  }

  function open(i) {
    if (opening >= 0) return;
    var a = copies[i] && copies[i].querySelector('a');
    if (!a) return;
    opening = i; openStart = performance.now(); stage.classList.add('is-opening');
    var dest = a.getAttribute('href');
    setTimeout(function () { location.href = dest; }, reduce ? 120 : 820);
  }

  function inPlane(x, y) {
    var cx = W / 2, cy = H / 2 - cyPx;
    return Math.abs(x - cx) < pw / 2 && Math.abs(y - cy) < ph / 2;
  }

  stage.addEventListener('pointerdown', function (e) {
    if (e.target.closest('a,button') || opening >= 0) return;
    drag = { id: e.pointerId, x: e.clientX, y: e.clientY, t: performance.now(), base: target, lx: e.clientX, lt: performance.now(), v: 0, moved: false };
  });
  window.addEventListener('pointermove', function (e) {
    var r = stage.getBoundingClientRect();
    mouse.tx = ((e.clientX - r.left) / W) * 2 - 1; mouse.ty = ((e.clientY - r.top) / H) * 2 - 1;
    mouse.px = e.clientX - r.left; mouse.py = e.clientY - r.top;
    if (!drag || e.pointerId !== drag.id) return;
    var dx = e.clientX - drag.x;
    if (!drag.moved && Math.abs(dx) > 6) {
      drag.moved = true;
      try { stage.setPointerCapture(e.pointerId); } catch (err) {}
      stage.classList.add('dragging');
    }
    if (drag.moved) {
      target = clamp(drag.base - dx / pitch, -0.25, N - 0.75);
      var now = performance.now(), dt = Math.max(1, now - drag.lt);
      drag.v = drag.v * 0.7 + (-(e.clientX - drag.lx) / pitch / (dt / 1000)) * 0.3;
      drag.lx = e.clientX; drag.lt = now;
    }
  });
  function endDrag(e) {
    if (!drag || (e && e.pointerId !== drag.id)) return;
    var d = drag; drag = null; stage.classList.remove('dragging');
    if (d.moved) {
      var cur = d.base + (-(mouse.px - d.x) / pitch);
      var fling = clamp(d.v * 0.16, -1.1, 1.1);
      var dest = Math.round(cur + fling);
      if (dest === Math.round(d.base) && Math.abs(cur - d.base) > 0.12) dest = Math.round(d.base) + (cur > d.base ? 1 : -1);
      target = clamp(dest, 0, N - 1);
    } else if (performance.now() - d.t < 500) {
      /* a click, not a drag */
      var cx = W / 2, cy = H / 2 - cyPx, x = e.clientX, y = e.clientY;
      var cur2 = mod(target);
      if (inPlane(x, y)) open(cur2);
      else if (Math.abs(y - cy) < ph / 2 + 30) go(x < cx ? -1 : 1);
    }
  }
  window.addEventListener('pointerup', endDrag);
  window.addEventListener('pointercancel', endDrag);

  stage.addEventListener('wheel', function (e) {
    var bar = e.target.closest && e.target.closest('.lang-bar');
    if (bar) { bar.scrollLeft += (e.deltaX || e.deltaY); e.preventDefault(); return; }
    if (opening >= 0) return;
    e.preventDefault();
    var d = Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : e.deltaY;
    if (e.deltaMode === 1) d *= 32;
    if (!wheel.on) { wheel.on = true; wheel.acc = 0; wheel.base = Math.round(target); }
    wheel.acc += d;
    target = clamp(wheel.base + clamp(wheel.acc * 0.0016, -1.3, 1.3), -0.25, N - 0.75);
    clearTimeout(wheel.timer);
    wheel.timer = setTimeout(function () {
      var n = Math.abs(wheel.acc) > 900 ? 2 : (Math.abs(wheel.acc) > 28 ? 1 : 0);
      target = clamp(wheel.base + (wheel.acc < 0 ? -n : n), 0, N - 1);
      wheel.on = false;
    }, 110);
  }, { passive: false });

  window.addEventListener('keydown', function (e) {
    if (opening >= 0 || e.altKey || e.ctrlKey || e.metaKey) return;
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown' || e.key === 'PageDown') { go(document.dir === 'rtl' ? -1 : 1); e.preventDefault(); }
    else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp' || e.key === 'PageUp') { go(document.dir === 'rtl' ? 1 : -1); e.preventDefault(); }
    else if (e.key === 'Home') goTo(0);
    else if (e.key === 'End') goTo(N - 1);
    else if (/^[1-3]$/.test(e.key)) goTo(+e.key - 1);
  });

  stage.querySelector('.arrow-prev').addEventListener('click', function () { go(-1); });
  stage.querySelector('.arrow-next').addEventListener('click', function () { go(1); });
  navBtns.forEach(function (b, k) { b.addEventListener('click', function () { goTo(k); }); });

  /* ------------------------------------------------------------ frame */
  function ease4(x) { return 1 - Math.pow(1 - x, 4); }

  function frame(now) {
    raf = requestAnimationFrame(frame);
    var raw = (now - last) / 1000;
    var dt = Math.min(0.05, raw); last = now;
    if (now - t0 > 2500 && raw < 1) {
      slowEma = slowEma * 0.9 + raw * 0.1;
      if (slowEma > 0.042 && quality > 0.5 && now - lastDrop > 1200) { quality = Math.max(0.5, quality - 0.17); lastDrop = now; slowEma = 0.02; resize(); }
    }
    if (!reduce) time += dt;
    var rate = drag && drag.moved ? 20 : (reduce ? 14 : 5.6);
    lastPos = pos;
    pos += (target - pos) * (1 - Math.exp(-dt * rate));
    if (Math.abs(target - pos) < 0.0004) pos = target;
    var v = dt > 0 ? (pos - lastPos) / dt : 0;
    velS += (v - velS) * (1 - Math.exp(-dt * 11));
    var vN = clamp(velS * 0.3, -1.2, 1.2);
    mouse.x += (mouse.tx - mouse.x) * (1 - Math.exp(-dt * 4));
    mouse.y += (mouse.ty - mouse.y) * (1 - Math.exp(-dt * 4));
    if (reduce) { mouse.x = 0; mouse.y = 0; }

    var act = mod(pos);
    setActive(act);

    /* hover over the centred plane */
    var over = fine && !drag && opening < 0 && Math.abs(wrap(act - pos)) < 0.25 && inPlane(mouse.px, mouse.py);
    hoverT = over ? 1 : 0;
    hover += (hoverT - hover) * (1 - Math.exp(-dt * 7));
    stage.classList.toggle('over', over);

    if (opening >= 0) {
      openT = clamp((now - openStart) / (reduce ? 100 : 760), 0, 1);
      openT = openT < 0.5 ? 4 * openT * openT * openT : 1 - Math.pow(-2 * openT + 2, 3) / 2;
    }
    var introT = (now - t0) / 1000;

    syncDom();

    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.uniform2f(U.u_res, W, H);
    gl.uniform1f(U.u_pitch, pitch);
    gl.uniform1f(U.u_cy, cyPx);
    gl.uniform1f(U.u_vel, vN);
    gl.uniform1f(U.u_time, time % 600);
    gl.uniform2f(U.u_mouse, mouse.x, mouse.y);
    gl.uniform1f(U.u_motion, reduce ? 0 : 1);
    gl.uniform1f(U.u_aspect, aspect);

    /* paint far -> near */
    var order = [0, 1, 2].sort(function (a, b) { return Math.abs(wrap(b - pos)) - Math.abs(wrap(a - pos)); });
    for (var n = 0; n < N; n++) {
      var i = order[n], rel = wrap(i - pos), ar = Math.abs(rel);
      var rank = i;
      var ip = reduce ? 1 : ease4(clamp((introT - 0.1 - 0.13 * rank) / 1.2, 0, 1));
      var alpha = clamp(1.9 - ar, 0, 1) * ip;
      var op = (i === opening) ? openT : 0;
      if (opening >= 0 && i !== opening) alpha *= 1 - clamp(openT * 1.6, 0, 1);
      if (alpha <= 0.002) continue;
      var col = COLORS[i];
      gl.bindTexture(gl.TEXTURE_2D, texs[i]);
      gl.uniform1f(U.u_kind, i);
      gl.uniform1f(U.u_rel, rel);
      gl.uniform2f(U.u_size, pw, ph);
      gl.uniform1f(U.u_open, op);
      gl.uniform1f(U.u_intro, ip);
      gl.uniform1f(U.u_hover, i === act ? hover : 0);
      gl.uniform1f(U.u_alpha, alpha);
      gl.uniform3f(U.u_c, col[0] / 255, col[1] / 255, col[2] / 255);
      gl.uniform3f(U.u_c2, col[0] / 255 * 0.07, col[1] / 255 * 0.07, col[2] / 255 * 0.07 + 0.02);
      /* pointer position in the plane's own art space (height units) */
      var pcx = W / 2 + rel * pitch, pcy = H / 2 - cyPx;
      gl.uniform2f(U.u_lm, (mouse.px - pcx) / ph, -(mouse.py - pcy) / ph);
      gl.drawElements(gl.TRIANGLES, idx.length, gl.UNSIGNED_SHORT, 0);
    }
    if (!stage.classList.contains('ready') && introT > 0.5) stage.classList.add('ready');
  }

  /* ------------------------------------------------------------ boot */
  canvas.addEventListener('webglcontextlost', function (e) {
    e.preventDefault();
    cancelAnimationFrame(raf);
    stage.classList.remove('on'); document.body.classList.remove('stage-on');
  });
  document.addEventListener('visibilitychange', function () {
    cancelAnimationFrame(raf);
    if (!document.hidden) { last = performance.now(); raf = requestAnimationFrame(frame); }
  });
  /* back/forward cache: come back to a clean, un-opened stage */
  window.addEventListener('pageshow', function (e) {
    if (e.persisted) { opening = -1; openT = 0; stage.classList.remove('is-opening'); }
  });
  var rt; window.addEventListener('resize', function () { clearTimeout(rt); rt = setTimeout(resize, 60); });

  stage.classList.add('on');
  document.body.classList.add('stage-on');
  if (fine) stage.classList.add('fine');
  resize();
  /* start on the slide matching a #b2/#c1/#essay/#grammatik hash */
  var h = (location.hash || '').replace('#', '');
  var hi = ['monitor', 'tension', 'risk'].indexOf(h);
  if (hi > 0) { pos = target = hi; lastPos = pos; }
  raf = requestAnimationFrame(frame);
})();
