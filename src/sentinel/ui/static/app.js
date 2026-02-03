let timer = null;
let refreshSeconds = 1800;

function el(id) { return document.getElementById(id); }

async function getPresets() {
  const res = await fetch("/api/presets");
  return await res.json();
}

function setStatus(text) {
  el("status").textContent = text;
}

function badgeClass(action, regime) {
  if (action.startsWith("A+")) return "good";
  if (regime === "chaos") return "bad";
  if (regime === "range") return "warn";
  return "muted";
}

function buildPayload() {
  return {
    exchange: el("exchange").value.trim() || "binance",
    preset: el("preset").value,
    timeframe: el("timeframe").value.trim() || null,
    bars: parseInt(el("bars").value || "0", 10) || null,
    max_pairs: parseInt(el("max_pairs").value || "0", 10) || 50,
    limit: parseInt(el("limit").value || "20", 10) || 20,

    quality: el("quality").checked,
    min_qv: parseFloat(el("min_qv").value || "0") || 0,

    setups: el("setups").checked,
    brief: el("brief").checked,
    exclude_stables: el("exclude_stables").checked,

    risk_usdt: parseFloat(el("risk_usdt").value || "1") || 1.0,
    fee_buffer_pct: parseFloat(el("fee_buffer_pct").value || "0.1") || 0.10
  };
}

async function runScan() {
  setStatus("Scanning…");
  const t0 = performance.now();

  const payload = buildPayload();
  const res = await fetch("/api/scan", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload)
  });

  if (!res.ok) {
    setStatus("Error");
    el("meta").textContent = `Request failed: ${res.status}`;
    return;
  }

  const data = await res.json();
  const t1 = performance.now();

  refreshSeconds = data.refresh_seconds || refreshSeconds;

  el("meta").textContent =
    `Exchange: ${data.exchange} • TF: ${data.timeframe} • Bars: ${data.bars} • Refresh: ${refreshSeconds}s • ${(t1 - t0).toFixed(0)}ms`;

  // table
  const tbody = el("tbody");
  tbody.innerHTML = "";
  for (const r of data.rows) {
    const tr = document.createElement("tr");

    const cls = badgeClass(r.action, r.regime);

    tr.innerHTML = `
      <td><span class="badge ${cls}">${r.symbol}</span></td>
      <td class="${cls}">${r.regime}</td>
      <td>${r.atr_pct.toFixed(2)}</td>
      <td>${r.trend_strength.toFixed(3)}</td>
      <td class="${cls}">${r.action}</td>
      <td class="muted">${r.note || ""}</td>
    `;
    tbody.appendChild(tr);
  }

  // briefing
  const briefOn = el("brief").checked;
  const bp = el("briefingPanel");
  const pre = el("briefing");
  if (briefOn && data.briefing) {
    bp.style.display = "block";
    pre.textContent = data.briefing;
  } else {
    bp.style.display = "none";
    pre.textContent = "";
  }

  setStatus("Updated");
}

function applyPreset(p) {
  el("timeframe").value = p.timeframe;
  el("bars").value = p.bars;
  el("max_pairs").value = p.max_pairs;
  refreshSeconds = p.refresh_seconds;
}

function startAuto() {
  if (timer) return;
  setStatus(`Auto (${refreshSeconds}s)`);
  timer = setInterval(runScan, refreshSeconds * 1000);
  el("toggle").textContent = "Stop Auto";
}

function stopAuto() {
  if (!timer) return;
  clearInterval(timer);
  timer = null;
  setStatus("Idle");
  el("toggle").textContent = "Start Auto";
}

async function init() {
  const presetData = await getPresets();
  const presets = {};
  for (const p of presetData.presets) presets[p.key] = p;

  // default preset
  const currentKey = el("preset").value || "swing";
  applyPreset(presets[currentKey]);

  el("preset").addEventListener("change", () => {
    const p = presets[el("preset").value];
    applyPreset(p);
    if (timer) { stopAuto(); startAuto(); }
  });

  el("run").addEventListener("click", runScan);

  el("toggle").addEventListener("click", () => {
    if (timer) stopAuto();
    else startAuto();
  });

  // first run
  await runScan();
}

init().catch((e) => {
  console.error(e);
  setStatus("Init error");
});
