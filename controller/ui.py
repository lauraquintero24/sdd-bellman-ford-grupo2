"""View del Controller (C-32, FR-14): página de la interfaz web servida en ``GET /ui``.

La página no contiene datos de la red: desde el navegador consulta ``GET /routers``, ``GET /topology`` y
``GET /topology/version`` del Controller, y ``GET /health``, ``GET /status`` y ``GET /forwarding-table`` de cada
router (CORS); envía ``POST /packets`` al router de origen y ``POST /links/fail|restore`` al Controller.
"""

DASHBOARD_HTML = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Red SDN · Bellman-Ford</title>
<style>
  :root { --bg:#f6f7f9; --card:#fff; --text:#1d2433; --muted:#5d6678; --line:#dde1e8; --accent:#2457c5;
          --ok:#1f7a3f; --bad:#b42318; --warn:#9a6700; --chip:#eef2fb; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#14171d; --card:#1c2029; --text:#e6e9ef; --muted:#9aa3b5; --line:#2c3240; --accent:#7aa2ff;
            --ok:#5ccf8a; --bad:#ff7b72; --warn:#e3b341; --chip:#232a38; }
  }
  * { box-sizing: border-box; }
  body { margin:0; font:14px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; background:var(--bg); color:var(--text); }
  header { padding:16px 24px; border-bottom:1px solid var(--line); background:var(--card); display:flex; gap:16px; align-items:baseline; flex-wrap:wrap; }
  header h1 { margin:0; font-size:18px; }
  main { display:grid; grid-template-columns: minmax(260px, 1fr) 2fr; gap:16px; padding:16px 24px; max-width:1300px; margin:0 auto; }
  @media (max-width: 900px) { main { grid-template-columns: 1fr; padding:12px 16px; } }
  section { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px 16px; }
  section h2 { margin:0 0 10px; font-size:15px; }
  .muted { color:var(--muted); }
  .ok { color:var(--ok); } .bad { color:var(--bad); } .warn { color:var(--warn); }
  table { width:100%; border-collapse:collapse; }
  th, td { text-align:left; padding:6px 8px; border-bottom:1px solid var(--line); font-variant-numeric: tabular-nums; }
  th { font-size:12px; color:var(--muted); font-weight:600; }
  tr.router { cursor:pointer; } tr.router:hover { background:var(--chip); } tr.selected { background:var(--chip); }
  code, .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size:12.5px; }
  .chip { display:inline-block; padding:1px 8px; border-radius:999px; background:var(--chip); font-size:12px; }
  form, .row { display:flex; gap:8px; flex-wrap:wrap; align-items:end; }
  label { display:flex; flex-direction:column; gap:3px; font-size:12px; color:var(--muted); }
  select, input, button { font:inherit; padding:5px 8px; border:1px solid var(--line); border-radius:6px; background:var(--card); color:var(--text); }
  button { cursor:pointer; background:var(--accent); color:#fff; border-color:var(--accent); }
  button.secondary { background:transparent; color:var(--accent); }
  .stack > * + * { margin-top:16px; }
  .trace { display:flex; flex-wrap:wrap; gap:6px; align-items:center; margin:6px 0; }
  .hop { border:1px solid var(--line); border-radius:6px; padding:3px 8px; }
  #history li { margin-bottom:6px; }
</style>
</head>
<body>
<header>
  <h1>Red SDN con Bellman-Ford</h1>
  <span>Controller: <strong id="controller-status" class="muted">consultando…</strong></span>
  <span>Versión de topología: <strong id="topology-version">—</strong></span>
  <span class="muted" id="updated-at"></span>
</header>
<main>
  <div class="stack">
    <section>
      <h2>Routers</h2>
      <table id="routers"><thead><tr><th>Router</th><th>Dirección HTTP</th><th>Estado</th><th>Tabla</th></tr></thead><tbody></tbody></table>
      <p class="muted" id="routers-empty" hidden>El Controller no tiene registro de routers (ROUTERS_FILE).</p>
    </section>
    <section>
      <h2>Enlaces</h2>
      <table id="links"><thead><tr><th>Enlace</th><th>Estado</th><th></th></tr></thead><tbody></tbody></table>
    </section>
  </div>
  <div class="stack">
    <section>
      <div class="row" style="justify-content:space-between">
        <h2 style="margin:0">Tabla de forwarding de <span id="table-router">—</span></h2>
        <label>Métrica
          <select id="table-metric">
            <option value="delay">delay</option><option value="inverse_bandwidth">inverse_bandwidth</option><option value="loss">loss</option>
          </select>
        </label>
      </div>
      <p class="muted" id="table-meta">Elija un router.</p>
      <table id="forwarding-table"><thead><tr><th>Destino</th><th>Siguiente salto</th><th>Ruta</th><th>Costo</th><th>Estado</th></tr></thead><tbody></tbody></table>
    </section>
    <section>
      <h2>Enviar un paquete</h2>
      <form id="send-form">
        <label>Origen <select id="send-source"></select></label>
        <label>Destino <select id="send-destination"></select></label>
        <label>Métrica <select id="send-metric">
          <option value="delay">delay</option><option value="inverse_bandwidth">inverse_bandwidth</option><option value="loss">loss</option>
        </select></label>
        <label>Carga <input id="send-payload" value="hola" size="10"></label>
        <button type="submit">Enviar</button>
      </form>
      <div id="send-result" class="muted" style="margin-top:10px">Sin envíos todavía.</div>
      <h2 style="margin-top:14px">Historial</h2>
      <ol id="history" class="mono"></ol>
    </section>
  </div>
</main>
<script>
"use strict";
const state = { routers: [], status: {}, selected: null, tableKey: null, version: null, counter: 0 };
const $ = (id) => document.getElementById(id);
const el = (tag, text, cls) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (cls) n.className = cls; return n; };

async function getJSON(url, options = {}, timeoutMs = 1500) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const response = await fetch(url, { ...options, signal: ctrl.signal });
    const body = await response.json().catch(() => null);
    return { ok: response.ok, status: response.status, body };
  } finally { clearTimeout(timer); }
}

async function refreshController() {
  try {
    const [health, version] = await Promise.all([getJSON("/health"), getJSON("/topology/version")]);
    $("controller-status").textContent = health.ok ? "en línea" : "error";
    $("controller-status").className = health.ok ? "ok" : "bad";
    if (version.ok) { state.version = version.body.topology_version; $("topology-version").textContent = state.version; }
  } catch (e) {
    $("controller-status").textContent = "no disponible"; $("controller-status").className = "bad";
  }
}

async function loadRouters() {
  const result = await getJSON("/routers");
  state.routers = result.ok ? result.body.routers : [];
  $("routers-empty").hidden = state.routers.length > 0;
  for (const id of ["send-source", "send-destination"]) {
    const select = $(id); select.replaceChildren();
    for (const r of state.routers) select.append(new Option(r.router_id, r.router_id));
  }
  if (state.routers.length > 1) $("send-destination").selectedIndex = state.routers.length - 1;
  if (!state.selected && state.routers.length) state.selected = state.routers[0].router_id;
}

async function refreshRouters() {
  await Promise.all(state.routers.map(async (r) => {
    try {
      const status = await getJSON(r.url + "/status");
      state.status[r.router_id] = status.ok ? status.body : { error: "HTTP " + status.status };
    } catch (e) { state.status[r.router_id] = { down: true }; }
  }));
  const tbody = $("routers").tBodies[0]; tbody.replaceChildren();
  for (const r of state.routers) {
    const s = state.status[r.router_id] || {};
    const tr = el("tr", undefined, "router" + (r.router_id === state.selected ? " selected" : ""));
    tr.addEventListener("click", () => { state.selected = r.router_id; state.tableKey = null; refreshRouters(); refreshTable(); });
    tr.append(el("td", r.router_id), el("td", r.url, "mono"));
    if (s.down) tr.append(el("td", "no disponible", "bad"), el("td", "—"));
    else if (s.error) tr.append(el("td", s.error, "bad"), el("td", "—"));
    else tr.append(el("td", s.sync_status === "ok" ? "en línea" : "sincronizando (" + s.sync_status + ")", s.sync_status === "ok" ? "ok" : "warn"),
                   el("td", s.topology_version ? "v" + s.topology_version : "sin tabla"));
    tbody.append(tr);
  }
}

async function refreshTable() {
  const router = state.routers.find((r) => r.router_id === state.selected);
  $("table-router").textContent = router ? router.router_id : "—";
  if (!router) return;
  const metric = $("table-metric").value;
  let result;
  try { result = await getJSON(router.url + "/forwarding-table?metric=" + encodeURIComponent(metric)); }
  catch (e) { $("table-meta").textContent = "Router " + router.router_id + " no disponible."; $("table-meta").className = "bad"; state.tableKey = null; return; }
  if (!result.ok) { $("table-meta").textContent = (result.body && result.body.error) ? result.body.error.code + ": " + result.body.error.message : "HTTP " + result.status; $("table-meta").className = "warn"; state.tableKey = null; return; }
  const table = result.body;
  const key = [table.router_id, table.metric, table.topology_version].join("|");
  if (key === state.tableKey) return;  // solo se redibuja si cambia la información de enrutamiento
  state.tableKey = key;
  $("table-meta").className = "muted";
  $("table-meta").textContent = "Router " + table.router_id + " (" + table.url + ") · métrica " + table.metric +
    " · versión de topología " + table.topology_version + " · sincronizada " + (table.synced_at || "—");
  const tbody = $("forwarding-table").tBodies[0]; tbody.replaceChildren();
  for (const e of table.entries) {
    const tr = el("tr");
    tr.append(el("td", e.destination), el("td", e.next_hop || "—"), el("td", e.path ? e.path.join(" → ") : "—", "mono"),
              el("td", e.total_cost || "—", "mono"), el("td", e.status === "active" ? "activa" : "inalcanzable", e.status === "active" ? "ok" : "bad"));
    tbody.append(tr);
  }
}

async function refreshLinks() {
  const result = await getJSON("/topology").catch(() => null);
  if (!result || !result.ok) return;
  const topo = result.body;
  const tbody = $("links").tBodies[0]; tbody.replaceChildren();
  for (const l of topo.links) {
    const tr = el("tr");
    const arrow = topo.directed ? " → " : " — ";
    const button = el("button", l.active ? "Fallar" : "Restaurar", "secondary");
    button.addEventListener("click", async () => {
      await getJSON("/links/" + (l.active ? "fail" : "restore"), { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: l.source, target: l.target }) });
      await refreshAll();
    });
    const td = el("td"); td.append(button);
    tr.append(el("td", l.source + arrow + l.target + "  (d=" + l.delay_ms + ", b=" + l.bandwidth_mbps + ", p=" + l.loss_probability + ")", "mono"),
              el("td", l.active ? "activo" : "fallado", l.active ? "ok" : "bad"), td);
    tbody.append(tr);
  }
}

async function sendPacket(event) {
  event.preventDefault();
  const source = $("send-source").value, destination = $("send-destination").value, metric = $("send-metric").value;
  const router = state.routers.find((r) => r.router_id === source);
  const packetId = "ui-" + Date.now() + "-" + (++state.counter);
  const out = $("send-result"); out.className = ""; out.replaceChildren(el("span", "Enviando " + packetId + "…", "muted"));
  let result;
  try {
    result = await getJSON(router.url + "/packets", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ packet_id: packetId, source, destination, metric, payload: $("send-payload").value }) }, 15000);
  } catch (e) { result = { ok: false, status: 0, body: null }; }
  out.replaceChildren();
  let summary;
  if (result.ok) {
    const b = result.body;
    out.append(el("div", "Reenviado · ruta " + b.route.path.join(" → ") + " · costo " + b.route.total_cost + " (" + metric + ") · versión " + b.topology_version, "ok"));
    const trace = el("div", undefined, "trace");
    for (const h of b.trace) trace.append(el("span", h.hop_index + ". " + h.node + " (" + h.router_url + ")", "hop mono"));
    out.append(trace);
    summary = packetId + "  " + source + "→" + destination + " " + metric + ": " + b.route.path.join("→") + " costo " + b.route.total_cost;
  } else {
    const err = result.body && result.body.error;
    const text = err ? (result.status + " " + err.code + ": " + err.message + (err.details && err.details.at_router ? " (en " + err.details.at_router + ")" : ""))
                     : (result.status ? "HTTP " + result.status : "sin respuesta del router " + source);
    out.append(el("div", text, "bad"));
    summary = packetId + "  " + source + "→" + destination + " " + metric + ": " + text;
  }
  const li = el("li", summary); $("history").prepend(li);
  while ($("history").children.length > 10) $("history").lastChild.remove();
}

async function refreshAll() {
  await refreshController();
  await Promise.all([refreshRouters(), refreshLinks()]);
  await refreshTable();
  $("updated-at").textContent = "actualizado " + new Date().toLocaleTimeString();
}

$("send-form").addEventListener("submit", sendPacket);
$("table-metric").addEventListener("change", () => { state.tableKey = null; refreshTable(); });
loadRouters().then(refreshAll);
setInterval(refreshAll, 2000);
</script>
</body>
</html>
"""
