/* Dashboard APD Monitor - berkomunikasi dengan REST API FastAPI */
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const iso = d => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
document.documentElement.dataset.bsTheme = matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';

async function api(path, opts = {}) {
  const headers = (opts.body && !(opts.body instanceof FormData)) ? { 'Content-Type': 'application/json' } : {};
  const r = await fetch(path, { credentials: 'same-origin', headers, ...opts });
  if (r.status === 401 && !path.includes('/auth/login')) { showLogin(); throw new Error('Sesi berakhir, silakan login.'); }
  if (!r.ok) {
    let m = r.statusText;
    try { m = (await r.json()).detail || m; } catch (e) {}
    throw new Error(typeof m === 'string' ? m : JSON.stringify(m));
  }
  return r.json();
}

/* ---------------- login / navigasi ---------------- */
let view = 'live', timer = null;
function showLogin() { clearInterval(timer); $('#appView').classList.add('d-none'); $('#loginView').classList.remove('d-none'); }
function showApp(user) {
  $('#loginView').classList.add('d-none'); $('#appView').classList.remove('d-none');
  $('#who').textContent = user.username;
  go(view); clearInterval(timer); tick(); timer = setInterval(tick, 1000);
}
function go(v) {
  view = v;
  ['live', 'hist', 'rep'].forEach(x => $('#v-' + x).classList.toggle('d-none', x !== v));
  document.querySelectorAll('.tab').forEach(b => b.classList.toggle('active', b.dataset.view === v));
  if (v === 'hist') loadHistory(1);
  if (v === 'rep') loadReport();
}
document.querySelectorAll('.tab').forEach(b => b.onclick = () => go(b.dataset.view));

$('#loginForm').onsubmit = async e => {
  e.preventDefault(); $('#lerr').classList.add('d-none');
  try { showApp(await api('/api/auth/login', { method: 'POST', body: JSON.stringify({ username: $('#lu').value, password: $('#lp').value }) })); }
  catch (err) { $('#lerr').textContent = err.message; $('#lerr').classList.remove('d-none'); }
};
$('#logout').onclick = async () => { await api('/api/auth/logout', { method: 'POST' }); $('#lp').value = ''; showLogin(); };

/* ---------------- live monitoring ---------------- */
const fields = ['demo', 'webcam', 'file', 'url'];
$('#kind').onchange = () => fields.forEach(f => $('#f-' + f).classList.toggle('d-none', f !== $('#kind').value));
let feedOn = false, ticks = 0, lastId = 0; const fresh = new Map();

function setError(msg) { const b = $('#serr'); b.textContent = msg || ''; b.classList.toggle('d-none', !msg); }

$('#start').onclick = async () => {
  setError(''); const kind = $('#kind').value; let value = null;
  try {
    if (kind === 'webcam') value = $('#f-webcam').value || '0';
    if (kind === 'url') value = $('#f-url').value.trim();
    if (kind === 'file') {
      const f = $('#f-file').files[0]; if (!f) throw new Error('Pilih file video terlebih dahulu.');
      const fd = new FormData(); fd.append('file', f);
      $('#start').disabled = true; $('#start').textContent = 'Mengunggah...';
      value = (await api('/api/source/upload', { method: 'POST', body: fd })).file;
    }
    $('#start').textContent = 'Memuat...';
    await api('/api/source/start', { method: 'POST', body: JSON.stringify({ kind, value }) });
    feedOn = false; await refreshStats();
  } catch (err) { setError(err.message); }
  finally { $('#start').disabled = false; $('#start').textContent = 'Mulai'; }
};
$('#stop').onclick = async () => { try { await api('/api/source/stop', { method: 'POST' }); feedOn = false; await refreshStats(); } catch (e) { setError(e.message); } };

async function refreshStats() {
  const s = await api('/api/stats');
  $('#sW').textContent = s.workers; $('#sC').textContent = s.compliant; $('#sV').textContent = s.violations;
  $('#sF').textContent = s.running ? `${s.fps} FPS / ${(s.delay_ms / 1000).toFixed(2)} dtk` : '-';
  $('#sT').textContent = s.running ? (s.fps >= 10 && s.delay_ms <= 3000 ? 'memenuhi target (≥10 FPS, ≤3 dtk)' : 'di bawah target NFR-02') : '';
  $('#today').textContent = `${s.today_violations} hari ini`;
  const m = $('#mode'); m.textContent = s.running ? (s.mode === 'demo' ? 'MODE DEMO' : 'YOLO - ' + s.source) : 'idle';
  m.className = 'badge ' + (s.running ? (s.mode === 'demo' ? 'text-bg-warning' : 'text-bg-success') : 'text-bg-secondary');
  if (s.error) setError(s.error);
  if (s.running && !feedOn) { $('#feed').src = '/api/stream?t=' + Date.now(); $('#feed').classList.remove('d-none'); $('#feedPh').classList.add('d-none'); feedOn = true; }
  if (!s.running && feedOn) { $('#feed').removeAttribute('src'); $('#feed').classList.add('d-none'); $('#feedPh').classList.remove('d-none'); feedOn = false; }
}

async function refreshAlerts() {
  const d = await api('/api/violations?size=8'), box = $('#alerts');
  d.items.forEach(v => { if (v.id > lastId && lastId !== 0) fresh.set(v.id, Date.now() + 8000); });
  lastId = Math.max(lastId, ...d.items.map(v => v.id), 0);
  if (!d.items.length) return;
  box.innerHTML = d.items.map(v => {
    const isNew = (fresh.get(v.id) || 0) > Date.now();
    return `<div class="list-group-item ${isNew ? 'list-group-item-danger' : ''} px-1">
      <div class="d-flex justify-content-between"><b class="text-danger">${esc(v.jenis)}</b>${isNew ? '<span class="badge text-bg-danger">BARU</span>' : ''}</div>
      <small class="text-secondary">Pekerja ${v.track_id ?? '-'} | ${esc(v.camera)} | ${esc(v.timestamp.replace('T', ' '))}</small></div>`;
  }).join('');
}

async function tick() {
  if (view !== 'live') return;
  try { await refreshStats(); if (ticks++ % 2 === 0) await refreshAlerts(); } catch (e) { /* sesi habis ditangani api() */ }
}

/* ---------------- riwayat pelanggaran (FR-06) ---------------- */
let hPage = 1, hPages = 1;
async function loadHistory(page) {
  hPage = page; const p = new URLSearchParams({ page, size: 12 });
  if ($('#hFrom').value) p.set('date_from', $('#hFrom').value);
  if ($('#hTo').value) p.set('date_to', $('#hTo').value);
  if ($('#hJenis').value) p.set('jenis', $('#hJenis').value);
  try {
    const d = await api('/api/violations?' + p);
    hPages = Math.max(1, Math.ceil(d.total / d.size));
    $('#hBody').innerHTML = d.items.map(v => `<tr>
      <td>${esc(v.timestamp.replace('T', ' '))}</td><td>${esc(v.camera)}</td><td>${v.track_id ?? '-'}</td>
      <td><span class="badge text-bg-danger">${esc(v.jenis)}</span></td>
      <td><img class="thumb" loading="lazy" src="${v.snapshot_url}" data-t="${esc(v.jenis)} - ${esc(v.timestamp.replace('T', ' '))}" alt="bukti"></td></tr>`).join('')
      || '<tr><td colspan="5" class="text-secondary text-center py-4">Tidak ada pelanggaran pada filter ini.</td></tr>';
    $('#hInfo').textContent = `${d.total} pelanggaran | halaman ${hPage} dari ${hPages}`;
    $('#hPrev').disabled = hPage <= 1; $('#hNext').disabled = hPage >= hPages;
  } catch (e) { $('#hInfo').textContent = e.message; }
}
$('#hForm').onsubmit = e => { e.preventDefault(); loadHistory(1); };
$('#hReset').onclick = () => { $('#hForm').reset(); loadHistory(1); };
$('#hPrev').onclick = () => loadHistory(hPage - 1);
$('#hNext').onclick = () => loadHistory(hPage + 1);
$('#hBody').onclick = e => {
  if (!e.target.classList.contains('thumb')) return;
  $('#snapImg').src = e.target.src; $('#snapTitle').textContent = e.target.dataset.t;
  bootstrap.Modal.getOrCreateInstance($('#snapModal')).show();
};

/* ---------------- laporan kepatuhan (FR-07) ---------------- */
let chDay, chType;
async function loadReport() {
  if (!$('#rTo').value) { const t = new Date(); $('#rTo').value = iso(t); t.setDate(t.getDate() - 6); $('#rFrom').value = iso(t); }
  const q = `start=${$('#rFrom').value}&end=${$('#rTo').value}`;
  $('#exCsv').href = `/api/reports/export?format=csv&${q}`; $('#exPdf').href = `/api/reports/export?format=pdf&${q}`;
  try {
    const s = await api('/api/reports/summary?' + q);
    $('#rTot').textContent = s.total;
    $('#rRate').textContent = s.compliance_rate == null ? 'belum ada data' : s.compliance_rate + '%';
    const top = Object.entries(s.by_type).sort((a, b) => b[1] - a[1])[0];
    $('#rTop').textContent = top && top[1] ? `${top[0]} (${top[1]})` : '-';
    chDay && chDay.destroy(); chType && chType.destroy();
    chDay = new Chart($('#cDay'), { type: 'bar', data: { labels: s.per_day.map(d => d.date.slice(5)), datasets: [{ label: 'Pelanggaran', data: s.per_day.map(d => d.count), backgroundColor: '#dc2626' }] }, options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } } });
    chType = new Chart($('#cType'), { type: 'doughnut', data: { labels: Object.keys(s.by_type), datasets: [{ data: Object.values(s.by_type), backgroundColor: ['#f59e0b', '#dc2626', '#1e3a5f'] }] }, options: { plugins: { legend: { position: 'bottom' } } } });
  } catch (e) { $('#rTop').textContent = e.message; }
}
$('#rForm').onsubmit = e => { e.preventDefault(); loadReport(); };

/* ---------------- mulai: cek sesi ---------------- */
api('/api/auth/me').then(showApp).catch(showLogin);
