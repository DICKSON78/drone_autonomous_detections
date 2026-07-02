const API = `http://${location.host}`;
const WS = `ws://${location.host}/ws`;

// ── Splash Screen ──
const splashStatuses = [
  'Initializing systems...', 'Connecting to backend...',
  'Loading telemetry...', 'Calibrating sensors...',
  'Establishing secure link...', 'Starting radar...',
  'Activating AI agent...', 'System ready'
];
let splashIdx = 0;
function updateSplash() {
  const bar = document.getElementById('splashBar');
  const status = document.getElementById('splashStatus');
  if (!bar) return;
  splashIdx = Math.min(splashIdx + 1, splashStatuses.length - 1);
  bar.style.width = `${(splashIdx / (splashStatuses.length - 1)) * 100}%`;
  if (status) status.textContent = splashStatuses[splashIdx];
  if (splashIdx < splashStatuses.length - 1) {
    setTimeout(updateSplash, 850);
  } else {
    setTimeout(() => {
      const s = document.getElementById('splash');
      if (s) s.classList.add('hidden');
    }, 1600);
  }
}
setTimeout(updateSplash, 200);

let droneState = {};
let ws = null;
let micActive = false;
let recognition = null;
let telemHistory = [];
let miniChartPoints = [];

// ── View Switching ──
function switchView(name) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById(`view-${name}`).classList.add('active');
  document.querySelector(`[data-view="${name}"]`).classList.add('active');
  if (name === 'radar') setTimeout(initRadar, 100);
  if (name === 'services') checkServices();
  if (name === 'history') loadHistory();
  if (name === 'map') updateMap();
  if (name === 'agent') setTimeout(initHolo, 100);
}

// ── Agent Tab Switching ──
function switchAgentTab(name) {
  document.querySelectorAll('.atab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.apanel').forEach(p => p.classList.remove('active'));
  document.querySelector(`[data-atab="${name}"]`).classList.add('active');
  document.getElementById(`apanel-${name}`).classList.add('active');
  if (name === 'jarvins') setTimeout(initHolo, 50);
}

// ── WebSocket ──
function connectWS() {
  if (ws && ws.readyState === WebSocket.OPEN) return;
  try {
    ws = new WebSocket(WS);
    ws.onopen = () => addMsg('info', 'Connected.');
    ws.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data);
        if (d.type === 'response') {
          addMsg('agent', d.text);
          speak(d.text);
          setAgentStatus('STANDBY', '');
        } else if (d.lat !== undefined) {
          droneState = d;
          updateDash(d);
          drawMiniChart(d.altitude || 0);
          drawRadar(d);
        }
      } catch {}
    };
    ws.onclose = () => setTimeout(connectWS, 2000);
    ws.onerror = () => ws.close();
  } catch {}
}
connectWS();

// Alternative: poll via HTTP
setInterval(async () => {
  try {
    const r = await fetch(`${API}/api/state`);
    const s = await r.json();
    droneState = s;
    updateDash(s);
    drawMiniChart(s.altitude || 0);
    if (document.getElementById('view-radar').classList.contains('active')) drawRadar(s);
    if (document.getElementById('view-map').classList.contains('active')) updateMap();
  } catch {}
}, 500);

// ── Dashboard ──
function updateDash(s) {
  setT('d-conn', s.connected ? 'Connected' : 'Disconnected');
  setT('d-arm', s.armed ? '✓' : '✗');
  setT('d-air', s.in_air ? '✓' : '✗');
  setT('d-alt', `${(s.altitude||0).toFixed(1)} m`);
  setT('d-head', `${Math.round(s.heading||0)}°`);
  setT('d-speed', `${(s.speed||0).toFixed(1)} m/s`);
  setT('d-bat', `${(s.battery||0).toFixed(0)}%`);
  const gps = s.lat && s.lon ? `${s.lat.toFixed(4)}, ${s.lon.toFixed(4)}` : '—';
  setT('d-gps', gps);
  setT('d-wp', s.waypoint || 0);
  const pct = Math.min(100, ((s.altitude||0)/50)*100);
  document.getElementById('altFill').style.height = `${pct}%`;
  setT('altV', (s.altitude||0).toFixed(1));
  const h = s.heading||0;
  document.getElementById('cNeedle').style.transform = `rotate(${h}deg)`;
  setT('cDeg', `${Math.round(h)}°`);
}

function setT(id, t) { const e = document.getElementById(id); if (e) e.textContent = t; }

// ── Mini Chart ──
function drawMiniChart(alt) {
  miniChartPoints.push(alt);
  if (miniChartPoints.length > 60) miniChartPoints.shift();
  const c = document.getElementById('miniChart');
  if (!c) return;
  const ctx = c.getContext('2d');
  const w = c.width, h = c.height;
  ctx.clearRect(0, 0, w, h);
  if (miniChartPoints.length < 2) return;
  ctx.strokeStyle = '#00f0ff';
  ctx.lineWidth = 2;
  ctx.beginPath();
  const max = Math.max(20, ...miniChartPoints);
  miniChartPoints.forEach((v, i) => {
    const x = (i / (miniChartPoints.length-1)) * w;
    const y = h - (v / max) * (h - 10) - 5;
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  });
  ctx.stroke();
}

// ── Quick Actions ──
function cmd(text) {
  addMsg('user', text);
  setAgentStatus('THINKING', 'thinking');
  if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({text}));
  else addMsg('agent', 'Not connected.');
}

// ── Agent Chat ──
function sendMsg() {
  const inp = document.getElementById('aInp');
  const t = inp.value.trim();
  if (!t) return;
  inp.value = '';
  cmd(t);
}

function addMsg(type, text) {
  const el = document.createElement('div');
  el.className = `a-msg ${type}`;
  el.textContent = text;
  const c = document.getElementById('agentMsgs');
  c.appendChild(el);
  el.scrollIntoView({behavior:'smooth'});
}

function toggleMic() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) { addMsg('info', 'Voice not supported.'); return; }
  if (micActive) { stopMic(); return; }
  recognition = new SR();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = 'sw-TZ,en-US';
  recognition.onresult = (e) => { setAgentStatus('THINKING', 'thinking'); cmd(e.results[0][0].transcript); };
  recognition.onerror = () => stopMic();
  recognition.onend = () => stopMic();
  recognition.start();
  micActive = true;
  setAgentStatus('LISTENING', 'listening');
  const btn = document.getElementById('aMicBtn');
  btn.classList.add('recording');
  btn.innerHTML = '<span class="qb-icon">⏹</span>';
}

function stopMic() {
  if (recognition) { try { recognition.stop(); } catch{} recognition = null; }
  micActive = false;
  setAgentStatus('STANDBY', '');
  const btn = document.getElementById('aMicBtn');
  btn.classList.remove('recording');
  btn.innerHTML = '<span class="qb-icon">🎤</span>';
}

function speak(text) {
  if (!('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = 'en-US'; u.rate = 1.0;
  const v = speechSynthesis.getVoices().find(v => v.lang.startsWith('en'));
  if (v) u.voice = v;
  u.onstart = () => setAgentStatus('SPEAKING', 'speaking');
  u.onend = () => setAgentStatus('STANDBY', '');
  speechSynthesis.speak(u);
}

// ── Agent Hologram ──
let holoFrame = null;
let holoPhase = 0;

function setAgentStatus(text, cls) {
  const el = document.getElementById('agentStatus');
  if (!el) return;
  el.textContent = text;
  el.className = 'agent-status' + (cls ? ' ' + cls : '');
}

function drawHolo() {
  const c = document.getElementById('holoCanvas');
  if (!c) return;
  if (!c.parentElement) return;
  const rect = c.parentElement.getBoundingClientRect();
  if (rect.width === 0 || rect.height === 0) { holoFrame = requestAnimationFrame(drawHolo); return; }
  c.width = rect.width;
  c.height = rect.height;
  const w = c.width, h = c.height;
  const ctx = c.getContext('2d');
  const cx = w / 2, cy = h / 2;
  const radius = Math.min(w, h) * 0.38;
  const status = (document.getElementById('agentStatus')?.textContent || '').trim();

  ctx.clearRect(0, 0, w, h);

  const phase = holoPhase;

  const glowColor = status === 'SPEAKING' ? '77,255,180'
    : status === 'LISTENING' ? '77,124,255'
    : '0,240,255';
  const glowMain = `rgb(${glowColor})`;

  // ── Background ──
  ctx.fillStyle = '#050810';
  ctx.fillRect(0, 0, w, h);

  // ── Concentric Rings ──
  for (let i = 0; i < 6; i++) {
    const rr = radius * (0.2 + i * 0.13);
    const ra = 0.04 + Math.sin(phase * 0.3 + i * 0.5) * 0.02;
    ctx.strokeStyle = `rgba(${glowColor},${Math.max(0, ra)})`;
    ctx.lineWidth = 0.5;
    ctx.beginPath();
    ctx.arc(cx, cy, rr, 0, Math.PI * 2);
    ctx.stroke();
  }

  // ── Subtle Crosshairs ──
  ctx.strokeStyle = `rgba(${glowColor},0.03)`;
  ctx.lineWidth = 0.5;
  ctx.setLineDash([4, 8]);
  ctx.beginPath();
  ctx.moveTo(cx - radius, cy); ctx.lineTo(cx + radius, cy);
  ctx.moveTo(cx, cy - radius); ctx.lineTo(cx, cy + radius);
  ctx.stroke();
  ctx.setLineDash([]);

  // ── Voice Wave Rings ──
  const waveCount = status === 'SPEAKING' ? 6 : status === 'LISTENING' ? 4 : 2;
  const waveSpeed = status === 'SPEAKING' ? 4 : status === 'LISTENING' ? 2.5 : 1;
  for (let i = 0; i < waveCount; i++) {
    const wPhase = phase * waveSpeed + i * 1.26;
    const wRadius = radius * (0.05 + (Math.sin(wPhase) * 0.5 + 0.5) * 0.9);
    const waveAlpha = status === 'SPEAKING'
      ? (0.9 - (wRadius / radius) * 0.7) * (0.7 + Math.sin(phase * 5 + i * 2) * 0.3)
      : status === 'LISTENING'
      ? (0.5 - (wRadius / radius) * 0.35) * (0.6 + Math.sin(phase * 3 + i) * 0.3)
      : (0.12 - (wRadius / radius) * 0.08) * (0.5 + Math.sin(phase * 1.5 + i) * 0.3);
    if (waveAlpha <= 0.01) continue;

    // Outer glow fill
    ctx.shadowColor = glowMain;
    ctx.shadowBlur = status === 'SPEAKING' ? 40 : status === 'LISTENING' ? 25 : 10;
    ctx.strokeStyle = `rgba(${glowColor},${Math.max(0, waveAlpha)})`;
    ctx.lineWidth = status === 'SPEAKING' ? 3 - (i * 0.35) : status === 'LISTENING' ? 2.5 - (i * 0.4) : 1.5 - (i * 0.3);
    ctx.beginPath();
    ctx.arc(cx, cy, wRadius, 0, Math.PI * 2);
    ctx.stroke();

    // Inner fill glow
    ctx.shadowBlur = 0;
    ctx.fillStyle = `rgba(${glowColor},${waveAlpha * 0.15})`;
    ctx.beginPath();
    ctx.arc(cx, cy, wRadius * 0.9, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.shadowBlur = 0;

  // ── Central AI Core ──
  const corePulse = 1 + Math.sin(phase * (status === 'SPEAKING' ? 4 : status === 'LISTENING' ? 2.5 : 1)) * 0.04;
  const coreR = radius * 0.22 * corePulse;

  // Outer glow
  const outerGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, coreR * 3);
  outerGrad.addColorStop(0, `rgba(${glowColor},${status === 'SPEAKING' ? 0.2 : 0.1})`);
  outerGrad.addColorStop(0.5, `rgba(${glowColor},${status === 'SPEAKING' ? 0.06 : 0.03})`);
  outerGrad.addColorStop(1, `rgba(${glowColor},0)`);
  ctx.fillStyle = outerGrad;
  ctx.beginPath();
  ctx.arc(cx, cy, coreR * 3, 0, Math.PI * 2);
  ctx.fill();

  // Core body
  ctx.shadowColor = glowMain;
  ctx.shadowBlur = status === 'SPEAKING' ? 50 : 35;
  const coreGrad = ctx.createRadialGradient(cx - coreR * 0.3, cy - coreR * 0.3, 0, cx, cy, coreR);
  coreGrad.addColorStop(0, `rgba(255,255,255,${status === 'SPEAKING' ? 0.5 : 0.3})`);
  coreGrad.addColorStop(0.3, `rgba(${glowColor},${status === 'SPEAKING' ? 0.5 : 0.25})`);
  coreGrad.addColorStop(0.7, `rgba(${glowColor},0.12)`);
  coreGrad.addColorStop(1, `rgba(${glowColor},0)`);
  ctx.fillStyle = coreGrad;
  ctx.beginPath();
  ctx.arc(cx, cy, coreR, 0, Math.PI * 2);
  ctx.fill();

  // Core ring
  ctx.shadowBlur = 15;
  ctx.strokeStyle = `rgba(${glowColor},${0.3 + Math.sin(phase * 2) * 0.12})`;
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.arc(cx, cy, coreR, 0, Math.PI * 2);
  ctx.stroke();
  ctx.shadowBlur = 0;

  // Inner core dot
  ctx.shadowColor = glowMain;
  ctx.shadowBlur = 25;
  ctx.fillStyle = `rgba(255,255,255,${status === 'SPEAKING' ? 0.8 + Math.sin(phase * 4) * 0.2 : 0.5 + Math.sin(phase * 2) * 0.2})`;
  ctx.beginPath();
  ctx.arc(cx, cy, 2, 0, Math.PI * 2);
  ctx.fill();
  ctx.shadowBlur = 0;

  // ── Corner Brackets ──
  const bracket = 24;
  ctx.strokeStyle = `rgba(${glowColor},0.10)`;
  ctx.lineWidth = 1;
  [[1,1,-1,0,0,-1],[0,1,1,0,0,-1],[1,0,-1,0,0,1],[0,0,1,0,0,1]].forEach(([mx,my,dx1,dy1,dx2,dy2], idx) => {
    const bx = mx ? w - bracket : bracket;
    const by = my ? h - bracket : bracket;
    ctx.beginPath();
    ctx.moveTo(bx + dx1 * bracket * 0.6, by);
    ctx.lineTo(bx, by);
    ctx.lineTo(bx, by + dy2 * bracket * 0.6);
    ctx.stroke();
  });

  const speedMul = status === 'SPEAKING' ? 2.5 : status === 'LISTENING' ? 1.5 : 1;
  holoPhase += 0.018 * speedMul;
  holoFrame = requestAnimationFrame(drawHolo);
}

function initHolo() { if (holoFrame) cancelAnimationFrame(holoFrame); drawHolo(); }
setTimeout(initHolo, 200);

// ── Radar (Canvas PPI) ──
let radarAnim = null;

function initRadar() {
  const c = document.getElementById('radarCanvas');
  if (!c) return;
  const rect = c.parentElement.getBoundingClientRect();
  c.width = rect.width;
  c.height = rect.height;
  if (radarAnim) { cancelAnimationFrame(radarAnim); radarAnim = null; }
}

let sweepAngle = 0;
let detTrails = {};

function drawRadar(state) {
  const c = document.getElementById('radarCanvas');
  if (!c || !c.isConnected) return;
  const w = c.width, h = c.height;
  const cx = w/2, cy = h/2;
  const r = Math.min(w, h) * 0.44;
  const ctx = c.getContext('2d');

  const pal = '#ffb347';
  const pal2 = '#ff8c00';
  const palRgb = '255,179,71';
  const pal2Rgb = '255,140,0';

  ctx.clearRect(0, 0, w, h);

  // ── Background ──
  const bgGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
  bgGrad.addColorStop(0, 'rgba(15,18,30,1)');
  bgGrad.addColorStop(1, 'rgba(5,8,16,1)');
  ctx.fillStyle = bgGrad;
  ctx.fillRect(0, 0, w, h);

  // ── Fine Grid ──
  ctx.strokeStyle = `rgba(${palRgb},0.04)`;
  ctx.lineWidth = 0.5;
  for (let i = 0; i < 20; i++) {
    ctx.beginPath();
    ctx.moveTo(cx - r + i * (r/10), cy - r);
    ctx.lineTo(cx - r + i * (r/10), cy + r);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(cx - r, cy - r + i * (r/10));
    ctx.lineTo(cx + r, cy - r + i * (r/10));
    ctx.stroke();
  }

  // ── Range Rings with Labels ──
  const ringFractions = [0.2, 0.4, 0.6, 0.8, 1.0];
  const rangeMax = 50;
  ctx.font = '20px "Share Tech Mono", monospace';
  ctx.textAlign = 'left';
  ringFractions.forEach((f, i) => {
    const rr = r * f;
    ctx.strokeStyle = `rgba(${palRgb},${0.08 + i * 0.02})`;
    ctx.lineWidth = i === ringFractions.length - 1 ? 1.5 : 0.5;
    ctx.beginPath();
    ctx.arc(cx, cy, rr, 0, Math.PI * 2);
    ctx.stroke();
    // Distance label on right side
    const dist = Math.round(rangeMax * f);
    ctx.fillStyle = `rgba(${palRgb},0.2)`;
    ctx.fillText(`${dist}m`, cx + rr + 8, cy + 7);
  });

  // ── Range Scale (top left) ──
  ctx.strokeStyle = `rgba(${palRgb},0.4)`;
  ctx.lineWidth = 2;
  const scaleX = 30, scaleY = 30;
  ctx.beginPath();
  ctx.moveTo(scaleX, scaleY);
  ctx.lineTo(scaleX + 80, scaleY);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(scaleX, scaleY - 5);
  ctx.lineTo(scaleX, scaleY + 5);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(scaleX + 80, scaleY - 5);
  ctx.lineTo(scaleX + 80, scaleY + 5);
  ctx.stroke();
  ctx.fillStyle = `rgba(${palRgb},0.4)`;
  ctx.font = '18px "Share Tech Mono", monospace';
  ctx.textAlign = 'center';
  ctx.fillText('50m', scaleX + 40, scaleY - 6);

  // ── Bearing Ticks ──
  for (let i = 0; i < 36; i++) {
    const a = (i / 36) * Math.PI * 2 - Math.PI / 2;
    const isMajor = i % 3 === 0;
    const inner = r * (isMajor ? 0.88 : 0.93);
    const outer = r * 0.99;
    ctx.strokeStyle = `rgba(${palRgb},${isMajor ? 0.25 : 0.08})`;
    ctx.lineWidth = isMajor ? 2 : 0.5;
    ctx.beginPath();
    ctx.moveTo(cx + Math.cos(a) * inner, cy + Math.sin(a) * inner);
    ctx.lineTo(cx + Math.cos(a) * outer, cy + Math.sin(a) * outer);
    ctx.stroke();
  }

  // ── Bearing Numbers ──
  ctx.font = '18px "Share Tech Mono", monospace';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  for (let i = 0; i < 12; i++) {
    const a = (i / 12) * Math.PI * 2 - Math.PI / 2;
    const labelR = r * 1.08;
    const lx = cx + Math.cos(a) * labelR;
    const ly = cy + Math.sin(a) * labelR;
    if (lx < 20 || lx > w - 20 || ly < 20 || ly > h - 20) continue;
    ctx.fillStyle = `rgba(${palRgb},0.2)`;
    ctx.fillText(`${i * 30}`, lx, ly);
  }

  // ── Crosshairs ──
  ctx.strokeStyle = `rgba(${palRgb},0.05)`;
  ctx.lineWidth = 0.5;
  ctx.beginPath();
  ctx.moveTo(cx - r * 0.95, cy); ctx.lineTo(cx + r * 0.95, cy);
  ctx.moveTo(cx, cy - r * 0.95); ctx.lineTo(cx, cy + r * 0.95);
  ctx.stroke();

  // ── Heading Marker ──
  const head = (state.heading || 0) * Math.PI / 180;
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(head);
  ctx.strokeStyle = `rgba(${pal2Rgb},0.4)`;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(0, -r * 0.85);
  ctx.lineTo(0, -r * 0.92);
  ctx.stroke();
  ctx.fillStyle = `rgba(${pal2Rgb},0.4)`;
  ctx.font = '16px "Share Tech Mono", monospace';
  ctx.textAlign = 'center';
  ctx.fillText('HDG', 0, -r * 0.86);
  ctx.restore();

  // ── Heading Line ──
  ctx.strokeStyle = `rgba(${pal2Rgb},0.15)`;
  ctx.lineWidth = 1;
  ctx.setLineDash([4, 8]);
  ctx.beginPath();
  ctx.moveTo(cx, cy);
  ctx.lineTo(cx + Math.cos(head) * r * 0.85, cy + Math.sin(head) * r * 0.85);
  ctx.stroke();
  ctx.setLineDash([]);

  // ── Detections with Trails ──
  const dets = state.detections || [];
  const now = Date.now();

  // Track existing contacts
  dets.forEach(d => {
    const key = d.class_name || `obj_${d.bearing_h}_${Math.round(d.distance)}`;
    if (!detTrails[key]) detTrails[key] = [];
    const px = cx + Math.sin(head + (d.bearing_h || 0)) * r * (1 - Math.min(1, (d.distance || 10) / rangeMax));
    const py = cy - Math.cos(head + (d.bearing_h || 0)) * r * (1 - Math.min(1, (d.distance || 10) / rangeMax));
    detTrails[key].push({ x: px, y: py, t: now });
    if (detTrails[key].length > 8) detTrails[key].shift();
  });

  // Clean old trails
  Object.keys(detTrails).forEach(k => {
    detTrails[k] = detTrails[k].filter(p => now - p.t < 3000);
    if (detTrails[k].length === 0) delete detTrails[k];
  });

  // Draw trails
  Object.values(detTrails).forEach(trail => {
    trail.forEach((p, i) => {
      const age = (now - p.t) / 3000;
      ctx.fillStyle = `rgba(${palRgb},${0.08 * (1 - age)})`;
      ctx.beginPath();
      ctx.arc(p.x, p.y, 2 * (1 - age), 0, Math.PI * 2);
      ctx.fill();
    });
  });

  // Draw detection blips
  dets.forEach(d => {
    const dist = d.distance || 10;
    const bh = d.bearing_h || 0;
    const rad = Math.min(1, dist / rangeMax);
    const angle = head + bh;
    const dx = cx + Math.sin(angle) * r * (1 - rad);
    const dy = cy - Math.cos(angle) * r * (1 - rad);
    const sz = Math.max(5, 14 - rad * 10);

    // Blip glow
    ctx.shadowColor = `rgb(${pal2Rgb})`;
    ctx.shadowBlur = 15;
    ctx.fillStyle = `rgba(${pal2Rgb},0.6)`;
    ctx.beginPath();
    ctx.arc(dx, dy, sz, 0, Math.PI * 2);
    ctx.fill();

    // Blip core
    ctx.shadowBlur = 0;
    ctx.fillStyle = `rgba(255,255,255,0.8)`;
    ctx.beginPath();
    ctx.arc(dx, dy, sz * 0.4, 0, Math.PI * 2);
    ctx.fill();

    // ID tag
    ctx.fillStyle = `rgba(${palRgb},0.8)`;
    ctx.font = '20px "Share Tech Mono", monospace';
    ctx.textAlign = 'left';
    ctx.fillText(d.class_name || '?', dx + sz + 6, dy + 7);

    // Range/Bearing readout
    ctx.fillStyle = `rgba(${palRgb},0.35)`;
    ctx.font = '16px "Share Tech Mono", monospace';
    ctx.fillText(`${Math.round(dist)}m ${Math.round(bh * 180 / Math.PI)}°`, dx + sz + 6, dy + 26);
  });

  // ── PPI Sweep ──
  sweepAngle = (sweepAngle + 0.025) % (Math.PI * 2);

  // Sweep gradient cone
  const sweepGrad = ctx.createConicGradient(sweepAngle - Math.PI / 2, cx, cy);
  sweepGrad.addColorStop(0, `rgba(${palRgb},0)`);
  sweepGrad.addColorStop(0.85, `rgba(${palRgb},0)`);
  sweepGrad.addColorStop(0.92, `rgba(${palRgb},0.02)`);
  sweepGrad.addColorStop(0.97, `rgba(${palRgb},0.04)`);
  sweepGrad.addColorStop(1, `rgba(${palRgb},0)`);
  ctx.fillStyle = sweepGrad;
  ctx.beginPath();
  ctx.arc(cx, cy, r, sweepAngle - 1.2, sweepAngle);
  ctx.closePath();
  ctx.fill();

  // Sweep leading edge
  ctx.shadowColor = `rgb(${palRgb})`;
  ctx.shadowBlur = 25;
  ctx.strokeStyle = `rgba(${palRgb},0.7)`;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(cx, cy);
  ctx.lineTo(cx + Math.cos(sweepAngle - Math.PI / 2) * r, cy + Math.sin(sweepAngle - Math.PI / 2) * r);
  ctx.stroke();
  ctx.shadowBlur = 0;

  // ── Center Dot ──
  ctx.shadowColor = `rgb(${palRgb})`;
  ctx.shadowBlur = 20;
  ctx.fillStyle = `rgba(${palRgb},0.7)`;
  ctx.beginPath();
  ctx.arc(cx, cy, 3.5, 0, Math.PI * 2);
  ctx.fill();

  ctx.shadowBlur = 0;
  ctx.fillStyle = `rgba(255,255,255,0.9)`;
  ctx.beginPath();
  ctx.arc(cx, cy, 1.5, 0, Math.PI * 2);
  ctx.fill();

  // ── Digital Readouts ──
  ctx.font = '20px "Share Tech Mono", monospace';
  ctx.textAlign = 'right';
  ctx.fillStyle = `rgba(${palRgb},0.3)`;
  ctx.fillText(`AZ ${Math.round(state.heading || 0)}°`, w - 20, 28);
  ctx.fillText(`SPD ${(state.speed || 0).toFixed(1)}m/s`, w - 20, 52);
  ctx.textAlign = 'left';
  ctx.fillText(`ALT ${(state.altitude || 0).toFixed(1)}m`, 20, h - 20);

  radarAnim = requestAnimationFrame(() => drawRadar(droneState));
}

function resizeRadar() {
  const c = document.getElementById('radarCanvas');
  if (c) { c.width = c.parentElement.clientWidth; c.height = c.parentElement.clientHeight; }
}
window.addEventListener('resize', resizeRadar);

// ── Services ──
const SVC_DEFS = [
  { name: 'Command Center', desc: 'This unified backend (:8007)', port: '', path: '/api/health' },
  { name: 'Drone Bridge', desc: 'MAVLink bridge (UDP :14550)', port: '' },
  { name: 'Grafana', desc: 'Dashboard UI (:3000)', port: '3000', path: '/api/health' },
  { name: 'Prometheus', desc: 'Metrics storage (:9090)', port: '9090', path: '/-/ready' },
  { name: 'InfluxDB', desc: 'Time-series DB (:8086)', port: '8086', path: '/health' },
];

async function checkServices() {
  const grid = document.getElementById('svcGrid');
  grid.innerHTML = SVC_DEFS.map(s => `
    <div class="svc-card" id="svc-${s.name.replace(/\s/g,'')}">
      <div class="svc-icon up">◈</div>
      <div class="svc-info">
        <div class="svc-name">${s.name}</div>
        <div class="svc-desc">${s.desc}</div>
        <div class="svc-stat"><span class="svc-dot" id="sdot-${s.name.replace(/\s/g,'')}"></span><span class="svc-lbl" id="slbl-${s.name.replace(/\s/g,'')}">Checking...</span></div>
      </div>
    </div>
  `).join('');
  for (const svc of SVC_DEFS) {
    const id = svc.name.replace(/\s/g,'');
    const dot = document.getElementById(`sdot-${id}`);
    const lbl = document.getElementById(`slbl-${id}`);
    try {
      if (!svc.path) {
        // Check if bridge is connected via our state
        const r = await fetch(`${API}/api/health`);
        const d = await r.json();
        const ok = d.bridge;
        dot.className = `svc-dot ${ok ? 'up' : 'down'}`;
        lbl.textContent = ok ? 'Connected' : 'Disconnected';
        lbl.style.color = ok ? 'var(--accent)' : 'var(--dng)';
        document.getElementById(`svc-${id}`).querySelector('.svc-icon').className = `svc-icon ${ok ? 'up' : 'down'}`;
      } else {
        const p = svc.port || location.port;
        const host = location.hostname;
        const r = await fetch(`http://${host}:${p}${svc.path}`, { signal: AbortSignal.timeout(2000) });
        const ok = r.ok || r.status < 500;
        dot.className = `svc-dot ${ok ? 'up' : 'down'}`;
        lbl.textContent = ok ? 'Running' : 'Error';
        lbl.style.color = ok ? 'var(--accent)' : 'var(--dng)';
        document.getElementById(`svc-${id}`).querySelector('.svc-icon').className = `svc-icon ${ok ? 'up' : 'down'}`;
      }
    } catch {
      dot.className = 'svc-dot down';
      lbl.textContent = 'Stopped';
      lbl.style.color = 'var(--dng)';
      document.getElementById(`svc-${id}`).querySelector('.svc-icon').className = 'svc-icon down';
    }
  }
}

// ── Map ──
function updateMap() {
  const c = document.getElementById('mapCanvas');
  const info = document.getElementById('mapInfo');
  if (!c) return;
  const w = c.parentElement.clientWidth, h = c.parentElement.clientHeight;
  c.width = w; c.height = h;
  const ctx = c.getContext('2d');
  ctx.fillStyle = '#111827';
  ctx.fillRect(0, 0, w, h);

  if (!droneState.lat && !droneState.lon) {
    ctx.fillStyle = '#8898b0';
    ctx.font = '14px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('Waiting for GPS...', w/2, h/2);
    return;
  }

  const cx = w/2, cy = h/2;
  // Grid
  ctx.strokeStyle = 'rgba(0,240,255,0.1)';
  ctx.lineWidth = 0.5;
  for (let i = 0; i < 20; i++) {
    ctx.beginPath();
    ctx.arc(cx, cy, (i/20) * Math.min(w,h)/2, 0, Math.PI*2);
    ctx.stroke();
  }

  // Drone
  const head = (droneState.heading || 0) * Math.PI/180;
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(head);
  ctx.fillStyle = '#00f0ff';
  ctx.shadowColor = '#00f0ff';
  ctx.shadowBlur = 15;
  ctx.beginPath();
  ctx.moveTo(0, -15);
  ctx.lineTo(-8, 8);
  ctx.lineTo(8, 8);
  ctx.closePath();
  ctx.shadowBlur = 0;
  ctx.fill();
  ctx.restore();

  // Trail (just last position)
  ctx.fillStyle = 'rgba(0,240,255,0.3)';
  ctx.beginPath();
  ctx.arc(cx, cy, 3, 0, Math.PI*2);
  ctx.fill();

  info.textContent = `◈ ${droneState.lat.toFixed(6)}, ${droneState.lon.toFixed(6)}  |  Alt: ${(droneState.altitude||0).toFixed(1)}m  |  ${Math.round(droneState.heading||0)}°`;
}

// ── History ──
async function loadHistory() {
  try {
    const r = await fetch(`${API}/api/telemetry?hours=2`);
    const data = await r.json();
    drawLineChart('histAlt', data, 'altitude', '#00f0ff', 'Altitude (m)');
    drawLineChart('histSpeed', data, 'speed', '#3b82f6', 'Speed (m/s)');
    drawLineChart('histBat', data, 'battery', '#f59e0b', 'Battery (%)');
  } catch {}
  try {
    const r = await fetch(`${API}/api/events`);
    const events = await r.json();
    const log = document.getElementById('eventsLog');
    log.innerHTML = events.map(e =>
      `<div class="evt-${e.event_type === 'command' ? 'cmd' : 'alert'}">[${new Date(e.ts*1000).toLocaleTimeString()}] ${e.message}</div>`
    ).join('');
  } catch {}
}

function drawLineChart(canvasId, data, key, color, label) {
  const c = document.getElementById(canvasId);
  if (!c) return;
  const ctx = c.getContext('2d');
  const w = c.width = c.clientWidth;
  const h = c.height;
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = '#111827';
  ctx.fillRect(0, 0, w, h);

  const vals = data.map(d => d[key]).filter(v => v !== null && v !== undefined);
  if (vals.length < 2) {
    ctx.fillStyle = '#8898b0';
    ctx.font = '12px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('No data', w/2, h/2);
    return;
  }

  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const range = max - min || 1;
  const padX = 10, padY = 10;
  const cw = w - padX*2, ch = h - padY*2;

  // Label
  ctx.fillStyle = '#8898b0';
  ctx.font = '10px sans-serif';
  ctx.fillText(`${label} (${min.toFixed(1)}-${max.toFixed(1)})`, padX, 12);

  // Grid lines
  ctx.strokeStyle = 'rgba(255,255,255,0.05)';
  ctx.lineWidth = 0.5;
  for (let i = 0; i < 4; i++) {
    const y = padY + (i/4) * ch;
    ctx.beginPath();
    ctx.moveTo(padX, y); ctx.lineTo(w-padX, y);
    ctx.stroke();
  }

  // Line
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.beginPath();
  vals.forEach((v, i) => {
    const x = padX + (i/(vals.length-1)) * cw;
    const y = padY + ch - ((v - min)/range) * ch;
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  });
  ctx.stroke();

  // Fill
  ctx.lineTo(padX + cw, padY + ch);
  ctx.lineTo(padX, padY + ch);
  ctx.closePath();
  ctx.fillStyle = color.replace(')', ',0.1)').replace('rgb', 'rgba');
  ctx.fill();
}

// ── Init ──
setTimeout(initRadar, 500);
setTimeout(checkServices, 1000);
window.addEventListener('resize', () => {
  resizeRadar();
  if (document.getElementById('view-map').classList.contains('active')) updateMap();
  if (document.getElementById('view-history').classList.contains('active')) loadHistory();
});
