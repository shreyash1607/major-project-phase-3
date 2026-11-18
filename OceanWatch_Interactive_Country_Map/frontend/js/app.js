const API = window.API_BASE ?? ((location.protocol !== "file:" && ["8000", ""].includes(location.port)) ? "" : "http://localhost:8000");
const $ = s => document.querySelector(s), COLOR = { oil_like: "#e5a65c", suspected_debris: "#56b6c2" };
const LABEL = { oil_like: "Oil-like feature", suspected_debris: "Suspected debris" };
const map = L.map("map", { worldCopyJump: true, minZoom: 2 }).setView([24, 60], 3);
const T = (u, o) => L.tileLayer(u, { maxZoom: 13, ...o });
const sat = T("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", { attribution: "Esri, Maxar, Earthstar" }).addTo(map);
const ocean = T("https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}", { attribution: "Esri, GEBCO, NOAA" });
const gray = T("https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}", { attribution: "Esri", maxZoom: 16 });
const osm = T("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "© OpenStreetMap contributors", maxZoom: 18 });
L.control.layers({ "Satellite": sat, "Ocean": ocean, "Dark gray": gray, "Streets": osm }, null, { position: "topright" }).addTo(map);
const lg = L.control({ position: "bottomleft" }); lg.onAdd = () => { const d = L.DomUtil.create("div", "legend"); d.innerHTML = `<i style="background:${COLOR.oil_like}"></i>Oil-like (SAR)<br><i style="background:${COLOR.suspected_debris}"></i>Suspected debris (optical)`; return d; }; lg.addTo(map);
const layer = L.layerGroup().addTo(map); let alerts = [], allAlerts = [], selected = null, markers = {}, countryFeature = null, countryGeoLayer = null, inspectMarker = null, inspectCircle = null;
const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
let demo = false, DB = null;
const save = () => { try { localStorage.setItem("mpd_demo", JSON.stringify(DB)); } catch {} };
const fresh = () => JSON.parse(JSON.stringify(window.DEMO_ALERTS));
async function demoApi(u, o = {}) {  // offline stand-in for the REST API (same shapes as backend/app/main.py)
  if (!DB) { try { DB = JSON.parse(localStorage.getItem("mpd_demo")); } catch {} DB = DB || fresh(); }
  const url = new URL(u, "http://x"), p = url.pathname, q = url.searchParams;
  if (p === "/api/alerts") return DB.filter(a => a.confidence >= +(q.get("min_confidence") || 0) && (!q.get("kind") || a.kind === q.get("kind")) && (!q.get("status") || a.status === q.get("status")));
  const m = p.match(/^\/api\/alerts\/(\d+)(\/review)?$/);
  if (m) { const a = DB.find(x => x.id === +m[1]); if (m[2]) { Object.assign(a, JSON.parse(o.body), { reviewed_at: new Date().toISOString() }); save(); } return a; }
  if (p === "/api/inspect") {
    const lat=+(q.get("lat")||0), lon=+(q.get("lon")||0), radius=+(q.get("radius_km")||250);
    const rad=x=>x*Math.PI/180, near=DB.map(a=>({...a,distance_km:6371*2*Math.asin(Math.sqrt(Math.sin(rad(a.lat-lat)/2)**2+Math.cos(rad(lat))*Math.cos(rad(a.lat))*Math.sin(rad(a.lon-lon)/2)**2))})).filter(a=>a.distance_km<=radius).sort((a,b)=>a.distance_km-b.distance_km);
    return {query:{lat,lon,radius_km:radius},count:near.length,alerts:near,data_note:"Synthetic demo alert catalogue; not a live global pollution feed."};
  }
  if (p === "/api/stats") {
    const grp = k => Object.entries(DB.reduce((r, a) => ((r[a[k]] = r[a[k]] || []).push(a), r), {}));
    return { by_kind: grp("kind").map(([kind, v]) => ({ kind, n: v.length, avg_conf: +(v.reduce((s, a) => s + a.confidence, 0) / v.length).toFixed(3) })),
      by_status: grp("status").map(([status, v]) => ({ status, n: v.length })), scenes: window.DEMO_SCENES, false_alarms_per_scene: +(DB.filter(a => a.status === "rejected").length / window.DEMO_SCENES).toFixed(2) };
  }
  if (p === "/api/demo/reset") { DB = fresh(); save(); return { ok: true }; }
}
const j = async (u, o) => {
  if (!demo) {
    try { const r = await fetch(API + u, o); if (!r.ok) throw new Error(r.status); return await r.json(); }
    catch (e) { if (e instanceof TypeError && window.DEMO_ALERTS) { demo = true; $("#demo").hidden = false; } else throw e; }
  }
  return demoApi(u, o);
};

async function load() {
  const q = new URLSearchParams({ min_confidence: $("#f-conf").value / 100 });
  if ($("#f-kind").value) q.set("kind", $("#f-kind").value); if ($("#f-status").value) q.set("status", $("#f-status").value);
  allAlerts = await j("/api/alerts?" + q);
  alerts = countryFeature ? allAlerts.filter(a => featureContains(countryFeature, a.lon, a.lat)) : allAlerts.slice();
  const k = $("#f-sort").value; alerts.sort((a, b) => k === "area" ? b.area_km2 - a.area_km2 : k === "date" ? b.acquired_at.localeCompare(a.acquired_at) : b.confidence - a.confidence);
  draw(); stats();
}
function draw() {
  layer.clearLayers(); markers = {}; $("#count").textContent = `(${alerts.length})`;
  $("#list").innerHTML = alerts.map(a => `<li class="${a.kind} ${a.id === selected ? "sel" : ""}" data-id="${a.id}"><b>${LABEL[a.kind]}</b><span class="badge ${a.confidence > .7 ? "hi" : a.confidence > .4 ? "mid" : "lo"}">${Math.round(a.confidence * 100)}%</span><small>${esc(a.region)} · ${a.area_km2.toFixed(2)} km² · ${a.status}</small></li>`).join("");
  const bins = Array(10).fill(0); alerts.forEach(a => bins[Math.min(9, Math.floor(a.confidence * 10))]++);
  $("#hist").innerHTML = bins.map(n => `<i title="${n} alerts" style="height:${n / Math.max(1, ...bins) * 100}%"></i>`).join("");
  alerts.forEach(a => {
    const m = L.geoJSON(a.polygon, { style: { color: COLOR[a.kind], weight: 2, fillOpacity: .15 + a.confidence * .4 } }).addTo(layer);
    const dot = L.circleMarker([a.lat, a.lon], { radius: 5 + a.confidence * 6, color: "#fff", weight: 1, fillColor: COLOR[a.kind], fillOpacity: .9 }).addTo(layer);
    [m, dot].forEach(x => x.on("click", () => select(a.id))); markers[a.id] = dot;
  });
  const b = alerts.length && L.featureGroup([...layer.getLayers()]).getBounds(); if (b && b.isValid() && !selected && !countryFeature) map.fitBounds(b.pad(.3), { maxZoom: 5 });
}
async function stats() {
  const s = await j("/api/stats"), n = k => (s.by_kind.find(x => x.kind === k) || {}).n || 0;
  const pend = (s.by_status.find(x => x.status === "pending") || {}).n || 0;
  $("#stats").innerHTML = [["Scenes", s.scenes], ["Oil-like", n("oil_like")], ["Debris", n("suspected_debris")], ["Pending review", pend]].map(([l, v]) => `<div class="stat"><b>${v}</b><span>${l}</span></div>`).join("");
}
async function select(id) {
  selected = id; const a = await j("/api/alerts/" + id); draw(); map.flyTo([a.lat, a.lon], 9);
  $("#right").innerHTML = `<h3>${LABEL[a.kind]}</h3><span class="pill ${a.status}">${a.status}</span>
  <div class="bar"><i style="width:${a.confidence * 100}%"></i></div><b>${Math.round(a.confidence * 100)}% model confidence</b> <small>(uncalibrated baseline)</small>
  <h3>Uncertainty flags</h3>${a.flags.length ? a.flags.map(f => `<span class="pill flag">${esc(f.replaceAll("_", " "))}</span>`).join("") : "<small>None raised</small>"}
  <h3>Provenance</h3><dl><dt>Sensor</dt><dd>${esc(a.sensor)}</dd><dt>Product</dt><dd>${esc(a.product_id)}</dd><dt>Acquired</dt><dd>${esc(a.acquired_at)}</dd>
  <dt>Region</dt><dd>${esc(a.region)}</dd><dt>Area</dt><dd>${a.area_km2.toFixed(3)} km²</dd><dt>Wind</dt><dd>${a.wind_ms} m/s</dd><dt>Cloud</dt><dd>${Math.round(a.cloud_fraction * 100)}%</dd>
  <dt>Preproc.</dt><dd>${esc(a.preprocessing_version)}</dd><dt>Model</dt><dd>${esc(a.model_version)}</dd><dt>Data</dt><dd>${a.is_synthetic ? "Synthetic demo" : "Real product"}</dd></dl>
  <h3>Analyst review</h3><textarea id="note" rows="3" placeholder="Evidence, vessel reports, field notes…">${esc(a.analyst_note || "")}</textarea>
  <div class="actions"><button data-s="confirmed">Confirm</button><button class="no" data-s="rejected">Reject</button><button class="fc" data-s="field_check">Needs field check</button><button class="ghost" data-s="pending">Reset</button></div>`;
}
$("#right").addEventListener("click", async e => {
  const s = e.target.dataset.s; if (!s || !selected) return;
  await j(`/api/alerts/${selected}/review`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status: s, analyst_note: $("#note").value }) });
  await load(); select(selected);
});
$("#list").addEventListener("click", e => { const li = e.target.closest("li"); if (li) select(+li.dataset.id); });
["#f-kind", "#f-status", "#f-sort"].forEach(s => $(s).addEventListener("change", () => { selected = null; load(); }));
$("#f-conf").addEventListener("input", e => { $("#conf-val").textContent = e.target.value + "%"; selected = null; load(); });
$("#export").onclick = () => {
  if (!demo) return window.open(`${API}/api/export.geojson?min_confidence=${$("#f-conf").value / 100}`);
  const gj = { type: "FeatureCollection", features: alerts.map(({ polygon, ...props }) => ({ type: "Feature", geometry: polygon, properties: props })) };
  const l = Object.assign(document.createElement("a"), { href: URL.createObjectURL(new Blob([JSON.stringify(gj)], { type: "application/geo+json" })), download: "alerts.geojson" }); l.click();
};
$("#reset").onclick = async () => { await j("/api/demo/reset", { method: "POST" }); selected = null; load(); };
const ok = () => { $("#conn").hidden = true; };
const offline = e => { $("#list").innerHTML = ""; $("#conn").hidden = false; $("#err").textContent = e && e.message ? `(${e.message})` : ""; setTimeout(() => load().then(ok).catch(offline), 3000); };
// Country selector: country boundaries are loaded from Natural Earth GeoJSON.
function pointInRing(point, ring) { let inside=false; for(let i=0,j=ring.length-1;i<ring.length;j=i++){const xi=ring[i][0],yi=ring[i][1],xj=ring[j][0],yj=ring[j][1];const hit=((yi>point[1])!==(yj>point[1]))&&(point[0]<(xj-xi)*(point[1]-yi)/(yj-yi+1e-12)+xi);if(hit)inside=!inside;}return inside; }
function geometryContains(g, lon, lat) { if(!g)return false; const polys=g.type==='Polygon'?[g.coordinates]:g.type==='MultiPolygon'?g.coordinates:[]; return polys.some(poly=>pointInRing([lon,lat],poly[0])&&!poly.slice(1).some(r=>pointInRing([lon,lat],r))); }
function featureContains(f,lon,lat){return geometryContains(f.geometry,lon,lat);}
const countryControl=L.control({position:'topleft'});
countryControl.onAdd=()=>{const d=L.DomUtil.create('div','country-control');d.innerHTML=`<label for="country-select">Explore a country</label><select id="country-select"><option value="">Loading countries…</option></select><label for="radius-select">Click search radius</label><select id="radius-select"><option value="50">50 km</option><option value="100">100 km</option><option value="250" selected>250 km</option><option value="500">500 km</option><option value="1000">1,000 km</option></select><small>Choose a country or click any ocean location.</small>`;L.DomEvent.disableClickPropagation(d);return d;};
countryControl.addTo(map);
const countrySelect=()=>document.getElementById('country-select');
let countryFeatures=[];
fetch('https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson').then(r=>{if(!r.ok)throw new Error('Country boundary service unavailable');return r.json();}).then(gj=>{
 countryFeatures=gj.features||[];const sel=countrySelect();sel.innerHTML='<option value="">All countries / global view</option>'+countryFeatures.map((f,i)=>({f,i,n:f.properties.ADMIN||f.properties.NAME||'Country'})).sort((a,b)=>a.n.localeCompare(b.n)).map(x=>`<option value="${x.i}">${esc(x.n)}</option>`).join('');
}).catch(()=>{countrySelect().innerHTML='<option value="">Country list unavailable</option>';});
countrySelect().addEventListener('change',e=>{
 const idx=e.target.value;countryFeature=idx===''?null:countryFeatures[+idx];
 if(countryGeoLayer){map.removeLayer(countryGeoLayer);countryGeoLayer=null;}
 if(countryFeature){countryGeoLayer=L.geoJSON(countryFeature,{style:{color:'#56d6cf',weight:2,fillColor:'#56d6cf',fillOpacity:.06,dashArray:'5 4'}}).addTo(map);map.fitBounds(countryGeoLayer.getBounds(),{padding:[20,20]});}
 selected=null;load().catch(offline);
 const name=countryFeature?(countryFeature.properties.ADMIN||countryFeature.properties.NAME):'Global';
 $('#right').innerHTML=`<h3>${esc(name)} selected</h3><p class="mut">The map is filtered to candidate alerts whose coordinates fall inside this country's mapped boundary. Click an ocean location to inspect nearby records.</p>`;
});
map.on('click',async e=>{
 const lat=e.latlng.lat,lon=e.latlng.lng,radius=+document.getElementById('radius-select').value;
 if(inspectMarker)map.removeLayer(inspectMarker);if(inspectCircle)map.removeLayer(inspectCircle);
 inspectMarker=L.marker([lat,lon]).addTo(map).bindPopup(`<b>Area selected</b><br>${lat.toFixed(4)}, ${lon.toFixed(4)}<br>Search radius: ${radius} km`).openPopup();
 inspectCircle=L.circle([lat,lon],{radius:radius*1000,color:'#f4d06f',weight:1,fillColor:'#f4d06f',fillOpacity:.07,dashArray:'5 6'}).addTo(map);
 $('#right').innerHTML='<h3>Inspecting selected area…</h3><p class="mut">Searching the project alert catalogue for candidate records near this point.</p>';
 try{const result=await j(`/api/inspect?lat=${lat}&lon=${lon}&radius_km=${radius}`);const rows=result.alerts||[];
  $('#right').innerHTML=`<h3>Selected ocean area</h3><dl><dt>Latitude</dt><dd>${lat.toFixed(4)}</dd><dt>Longitude</dt><dd>${lon.toFixed(4)}</dd><dt>Search radius</dt><dd>${radius} km</dd><dt>Nearby records</dt><dd>${result.count}</dd></dl><div class="area-note">${rows.length?`<b>${rows.length} candidate alert(s) found</b><p>Choose a record below to inspect its footprint, sensor and review status.</p>`:'<b>No candidate alerts in this search radius</b><p>The current sample catalogue has no indexed observation here. This does not mean the water is pollution-free; this prototype does not yet query live global satellite products.</p>'}</div>${rows.map(a=>`<li class="${a.kind}" data-near="${a.id}"><b>${LABEL[a.kind]}</b><small>${esc(a.region)} · ${a.distance_km} km away · ${Math.round(a.confidence*100)}% screening score · ${a.is_synthetic?'synthetic sample':'record'}</small></li>`).join('')}<p class="mut">${esc(result.data_note||'')}</p>`;
 }catch(err){$('#right').innerHTML=`<h3>Area lookup failed</h3><p class="mut">${esc(err.message)}</p>`;}
});
$('#right').addEventListener('click',e=>{const li=e.target.closest('[data-near]');if(li)select(+li.dataset.near);});

load().then(ok).catch(offline);
$("#about").onclick = () => $("#aboutdlg").showModal();
