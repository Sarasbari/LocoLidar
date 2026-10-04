const canvas = document.querySelector('#map');
const ctx = canvas.getContext('2d');
const controls = {
  scene: document.querySelector('#scene-select'), play: document.querySelector('#play-button'),
  reset: document.querySelector('#reset-button'), hazard: document.querySelector('#hazard-button'),
  timeline: document.querySelector('#timeline'), cells: document.querySelector('#cells-toggle'),
  points: document.querySelector('#points-toggle'), rings: document.querySelector('#rings-toggle'),
};
let data, metrics, sceneIndex = 0, playing = false, timelineTick = 0, timer;

const hazardStates = [
  { risk: 0.12, level: 'LOW', ttc: 'SAFE', action: 'PROCEED', note: 'Normal recorded-map view' },
  { risk: 0.27, level: 'LOW', ttc: 'SAFE', action: 'PROCEED', note: 'Hazard detected outside conflict zone' },
  { risk: 0.42, level: 'MEDIUM', ttc: '5.8 s', action: 'PROCEED', note: 'Approaching ego corridor' },
  { risk: 0.57, level: 'MEDIUM', ttc: '4.6 s', action: 'PROCEED', note: 'Risk trending upward' },
  { risk: 0.68, level: 'HIGH', ttc: '3.4 s', action: 'SLOW DOWN', note: 'Local refinement visual activated' },
  { risk: 0.79, level: 'HIGH', ttc: '2.5 s', action: 'SLOW DOWN', note: 'Hazard in critical region' },
  { risk: 0.90, level: 'CRITICAL', ttc: '1.6 s', action: 'BRAKE', note: 'Safety intervention required' },
  { risk: 0.97, level: 'CRITICAL', ttc: '0.8 s', action: 'BRAKE', note: 'Final deterministic safety state' },
];

function currentScene() { return data.scenes[sceneIndex]; }
function state() { return hazardStates[timelineTick]; }
function setText(selector, value) { document.querySelector(selector).textContent = value; }
function riskColor(level) { return ({ LOW: '#37d89a', MEDIUM: '#f5ca55', HIGH: '#ff9a52', CRITICAL: '#fb5b66' })[level]; }
function hasHazard() { return timelineTick > 0; }
function refinementActive() { return timelineTick >= 4; }

function drawGridOverlay(x, y, radius, scale) {
  ctx.save();
  ctx.beginPath(); ctx.arc(x, y, radius * scale, 0, Math.PI * 2); ctx.clip();
  ctx.strokeStyle = 'rgba(255,154,82,.72)'; ctx.lineWidth = .55;
  const cell = .25 * scale;
  for (let px = x - radius * scale; px <= x + radius * scale; px += cell) { ctx.beginPath(); ctx.moveTo(px, y - radius * scale); ctx.lineTo(px, y + radius * scale); ctx.stroke(); }
  for (let py = y - radius * scale; py <= y + radius * scale; py += cell) { ctx.beginPath(); ctx.moveTo(x - radius * scale, py); ctx.lineTo(x + radius * scale, py); ctx.stroke(); }
  ctx.restore();
}

function draw() {
  const dpr = devicePixelRatio || 1, rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * dpr; canvas.height = rect.height * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const w = rect.width, h = rect.height, scene = currentScene();
  ctx.fillStyle = '#ffffff'; ctx.fillRect(0, 0, w, h);
  const scale = Math.min(w, h) / 130, cx = w / 2, cy = h * .86;
  const pos = (x, y) => [cx - y * scale, cy - x * scale];
  if (controls.rings.checked) for (const radius of [15, 35, 60]) { ctx.beginPath(); ctx.arc(cx, cy, radius * scale, 0, Math.PI * 2); ctx.strokeStyle = '#dddddd'; ctx.setLineDash([5, 5]); ctx.stroke(); ctx.setLineDash([]); }
  ctx.strokeStyle = '#cccccc'; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(cx - 4 * scale, cy); ctx.lineTo(cx - 4 * scale, cy - 62 * scale); ctx.moveTo(cx + 4 * scale, cy); ctx.lineTo(cx + 4 * scale, cy - 62 * scale); ctx.stroke();
  if (controls.cells.checked) { const colors = { near: '#36d1dc', medium: '#806dd7', far: '#b0b0b0' }; ctx.globalAlpha = .75; for (const cell of scene.cells) { const [x, y] = pos(cell.x * cell.r, cell.y * cell.r); ctx.fillStyle = colors[cell.zone]; ctx.fillRect(x, y - cell.r * scale, cell.r * scale, cell.r * scale); } }
  if (controls.points.checked) { ctx.globalAlpha = .36; ctx.fillStyle = '#000000'; for (const point of scene.display_points) { const [x, y] = pos(point[0], point[1]); ctx.fillRect(x, y, 1.4, 1.4); } }
  ctx.globalAlpha = 1; ctx.fillStyle = '#000000'; ctx.beginPath(); ctx.moveTo(cx, cy - 12); ctx.lineTo(cx - 7, cy + 9); ctx.lineTo(cx + 7, cy + 9); ctx.fill(); ctx.fillStyle = '#000000'; ctx.font = 'bold 11px "Space Mono", monospace'; ctx.fillText('EGO', cx - 12, cy + 25);
  if (hasHazard()) { const hx = 36 - timelineTick * 2.7, hy = 1.3, [x, y] = pos(hx, hy), color = riskColor(state().level); if (refinementActive()) { drawGridOverlay(x, y, 5, scale); ctx.beginPath(); ctx.arc(x, y, 5 * scale, 0, Math.PI * 2); ctx.strokeStyle = color; ctx.setLineDash([4, 4]); ctx.stroke(); ctx.setLineDash([]); } ctx.beginPath(); ctx.arc(x, y, 8, 0, Math.PI * 2); ctx.fillStyle = color; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = '#000000'; ctx.stroke(); ctx.fillStyle = color; ctx.font = 'bold 11px "Space Mono", monospace'; ctx.fillText('DEMO HAZARD', x - 36, y - 13); }
}

function render() {
  const scene = currentScene(), frame = scene.metrics, current = state(), maxCellCount = Math.max(frame.adaptive_2_5d_cells, frame.uniform_fine_occupied_cells, 1);
  setText('#adaptive-cells', frame.adaptive_2_5d_cells.toLocaleString()); setText('#uniform-cells', frame.uniform_fine_occupied_cells.toLocaleString()); setText('#reduction', `${frame.adaptive_cell_reduction_vs_uniform_fine_percent}%`); setText('#latency', `${frame.mapping_only_latency_ms} ms`);
  document.querySelector('#uniform-bar').style.width = `${(frame.uniform_fine_occupied_cells / maxCellCount) * 100}%`; document.querySelector('#adaptive-bar').style.width = `${(frame.adaptive_2_5d_cells / maxCellCount) * 100}%`;
  setText('#replay-label', `${scene.title} · Step ${timelineTick + 1}/${hazardStates.length} · ${current.note}`); setText('#map-label', hasHazard() ? 'RECORDED + DEMO HAZARD' : 'RECORDED REPLAY');
  setText('#risk-level', current.level); document.querySelector('#risk-level').style.color = riskColor(current.level); setText('#risk-score', current.risk.toFixed(2)); setText('#ttc', current.ttc); setText('#action', current.action);
  const refinement = document.querySelector('#refinement-status'); refinement.textContent = refinementActive() ? 'LOCAL REFINEMENT · VISUAL ACTIVE · 5 m / 0.25 m' : 'LOCAL REFINEMENT · INACTIVE'; refinement.classList.toggle('active', refinementActive()); refinement.classList.toggle('inactive', !refinementActive()); controls.timeline.value = timelineTick; draw();
}

function evidence() {
  const claims = metrics.claims, items = [['Frame processing', claims.frame_processing.status, claims.frame_processing.value], ['Semantic accuracy', claims.semantic_validation_accuracy.status, claims.semantic_validation_accuracy.reason], ['Semantic class coverage', claims.semantic_class_coverage.status, `Observed labels: ${claims.semantic_class_coverage.value.join(', ')}`], ['Voxel-memory claims', claims.sparse_voxel_memory_reduction.status, 'Not shown as achieved'], ['Real-time target', claims.target_realtime_performance.status, 'Target only']];
  document.querySelector('#evidence-list').innerHTML = items.map(([name, status, value]) => `<li><b>${name}</b> · ${status}<br>${value}</li>`).join(''); setText('#frame-proof', `${metrics.results.frames_validated}/${metrics.input.prediction_files_discovered} cached files validated · generated evidence ledger`);
}
function stop() { playing = false; clearInterval(timer); controls.play.textContent = '▶ Play scenario'; }
function tick() { timelineTick = Math.min(timelineTick + 1, hazardStates.length - 1); if (timelineTick === hazardStates.length - 1) stop(); render(); }
function start() { if (playing) { stop(); return; } if (timelineTick === hazardStates.length - 1) timelineTick = 0; playing = true; controls.play.textContent = '❚❚ Pause scenario'; timer = setInterval(tick, 900); render(); }

async function init() {
  [data, metrics] = await Promise.all(['./data/demo-data.json', './data/metrics.json'].map(url => fetch(url).then(response => { if (!response.ok) throw Error(`Could not load ${url}`); return response.json(); })));
  data.scenes.forEach((scene, index) => controls.scene.add(new Option(scene.title, index)));
  controls.scene.onchange = event => { sceneIndex = Number(event.target.value); timelineTick = 0; stop(); render(); };
  controls.play.onclick = start; controls.reset.onclick = () => { timelineTick = 0; stop(); render(); }; controls.hazard.onclick = () => { timelineTick = 1; stop(); render(); }; controls.timeline.oninput = event => { timelineTick = Number(event.target.value); stop(); render(); };
  [controls.cells, controls.points, controls.rings].forEach(control => control.onchange = draw); evidence(); render(); addEventListener('resize', draw);
}
init().catch(error => { document.body.innerHTML = `<main class="panel" style="margin:3rem">Could not load demo evidence: ${error.message}</main>`; });
