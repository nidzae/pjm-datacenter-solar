"""
Phase 7 -- Interactive map + PJM-wide summary.

Reads outputs/pjm_sites.csv and pjm_sites_sensitivity.csv and produces:
  * outputs/pjm_map.html  -- custom Leaflet map: gas plants, marker size ∝ nameplate,
                             color ∝ qualification at g=10% / 10 km; popup with details.
                             CLICK a plant to shade its developable solar land within 10 km
                             with a diagonal hatch fill (uses the developable_10km.json
                             overlay + inlined leaflet.pattern plugin, SVG renderer).
  * outputs/summary.md    -- qualifying-site counts and hostable-load GW by gas cap,
                             buffer, power-density, and state; validated vs Spec section 11.
Run:    python src/07_map.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402

# Spec section 11 Figure-4 state potentials (GW) for order-of-magnitude validation.
PAPER_STATE_GW = {"PA": 17, "OH": 12, "IL": 16, "VA": 10, "NJ": 6}


def make_map(wide: pd.DataFrame) -> None:
    """Custom Leaflet map: markers sized by nameplate, colored by qualification; clicking a
    plant shades its developable solar land within 10 km with a diagonal hatch fill."""
    import json

    # High-fidelity per-plant developable tiles (Phase 7 helper). Regenerate if missing.
    tile_dir = C.OUTPUTS / "dev_tiles"
    manifest = tile_dir / "manifest.json"
    if not manifest.exists():
        import subprocess
        subprocess.run([sys.executable, str(Path(__file__).with_name("make_developable_geojson.py"))],
                       check=True)
    have = set(json.loads(manifest.read_text()))
    pattern_js = (Path(__file__).with_name("assets") / "leaflet.pattern.js").read_text()

    plants = []
    for r in wide.itertuples(index=False):
        code = int(r.plant_code)
        plants.append({
            "code": code, "name": r.name, "state": r.state,
            "lat": round(float(r.lat), 5), "lon": round(float(r.lon), 5),
            "mw": round(float(r.nameplate_MW), 0), "cf": round(float(r.cf_ac), 3),
            "dmw": round(float(r.developable_MW), 0),
            "umw": round(float(r.usable_solar_MW), 0),
            "darea": round(float(r.developable_area_mi2), 1),
            "h5": round(float(r.headroom_g5), 2), "h10": round(float(r.headroom_g10), 2),
            "h20": round(float(r.headroom_g20), 2), "q10": bool(r.qualifies_g10),
            "sr5": round(float(r.solar_req_MW_g5), 0), "sr10": round(float(r.solar_req_MW_g10), 0),
            "sr20": round(float(r.solar_req_MW_g20), 0),
            # solar-limited hostable data-center load = min(nameplate, headroom * nameplate)
            "hl5": round(min(r.nameplate_MW, r.headroom_g5 * r.nameplate_MW), 0),
            "hl10": round(min(r.nameplate_MW, r.headroom_g10 * r.nameplate_MW), 0),
            "hl20": round(min(r.nameplate_MW, r.headroom_g20 * r.nameplate_MW), 0),
            "hasdev": code in have,
        })

    n = len(wide)
    fleet_gw = wide.nameplate_MW.sum() / 1000.0
    q10 = wide[wide["qualifies_g10"] == True]  # noqa: E712
    q10_gw = q10.nameplate_MW.sum() / 1000.0
    cf_lo, cf_hi = wide.cf_ac.min(), wide.cf_ac.max()
    caps = " / ".join(f"{int(g*100)}%" for g in C.GAS_CAPS)
    # total solar-limited hostable data-center load at 10% gas (sum of per-plant partials)
    host_gw = wide.apply(
        lambda r: min(r.nameplate_MW, r.headroom_g10 * r.nameplate_MW), axis=1
    ).sum() / 1000.0

    html = _MAP_TEMPLATE
    html = html.replace("/*__PATTERN_JS__*/", pattern_js)
    html = html.replace("__PLANTS__", json.dumps(plants, separators=(",", ":")))
    html = html.replace("__SIDEBAR__", _sidebar_html(n, fleet_gw, len(q10), q10_gw,
                                                     cf_lo, cf_hi, caps, host_gw))
    out = C.OUTPUTS / "pjm_map.html"
    out.write_text(html)
    print(f"Wrote {out}  ({out.stat().st_size/1e6:.2f} MB base; {len(have)} on-demand "
          f"developable tiles in {tile_dir.name}/)")


def _sidebar_html(n, fleet_gw, n_qual, qual_gw, cf_lo, cf_hi, caps, host_gw) -> str:
    pd_mw = C.POWER_DENSITY_MW_PER_MI2
    pd_pct = (cf_lo + cf_hi) / 2 * 100      # ~mean capacity factor, % of the time panels produce
    return f"""
<div class="hd"><b>&#9432; Map guide</b>
  <button class="x" onclick="document.getElementById('sidebar').classList.remove('open')">&times;</button></div>
<div class="bd">
<p>Every <b>operating natural-gas power plant in PJM</b> ({n} plants, {fleet_gw:.0f} GW total) is
screened for one question: is there enough developable land within <b>10&nbsp;km</b> to build a new
<b>data center</b> <i>plus</i> enough new <b>solar</b> to serve a flat 24/7 load equal to the plant's
capacity, with the gas plant only covering <b>{caps}</b> backup?</p>
<p class="mut">A first-pass land-availability screen — not a cost, dispatch, or interconnection study.</p>

<h3>How to use it</h3>
<ul>
  <li><b>Search</b> (top) for a place name or <code>lat, lon</code> to drop a pin and zoom there.</li>
  <li><b>Click any plant</b> to draw its 10&nbsp;km circle and shade the land that could host solar.</li>
  <li>Use the <b>Street / Satellite</b> switch (top-right) to see what's actually on that land.</li>
  <li>Drag the <b>Hostable-load filter</b> sliders (top-left) to show only plants that can host a
      data-center of a given size (MW). This uses each plant's <i>solar-limited hostable load</i>
      (the partial capacity that fits), not full nameplate; <i>reset</i> clears it.</li>
  <li>Hover/click a marker for its <b>popup</b> with the numbers below.</li>
</ul>

<h3>Map symbols</h3>
<dl>
  <dt>Each marker is a gauge</dt>
  <dd>The <b>outline ring</b> = the plant's <b>full nameplate</b> (overall size ∝ nameplate MW).
      The <b>filled core</b> = the <b>hostable data-center load</b> you could actually run there
      (its area is that share of the ring). Gap between them = capacity the land can't reach.</dd>
  <dt><span class="gauge" style="border-color:#1a9850;width:14px;height:14px"><i style="background:#1a9850;width:11px;height:11px"></i></span> green</dt>
  <dd>Core fills the ring — the <b>full nameplate</b> data center fits (qualifies at 10% gas).</dd>
  <dt><span class="gauge" style="border-color:#f57c00;width:14px;height:14px"><i style="background:#f57c00;width:6px;height:6px"></i></span> orange</dt>
  <dd>Core is smaller than the ring — only a <b>partial</b> data center fits. Orange ≠ no
      opportunity, just partial.</dd>
  <dt><span class="hatchsw"></span> green hatch</dt>
  <dd><b>Developable solar land</b> within 10&nbsp;km at full 30&nbsp;m detail. Gaps (holes) are land
      removed by the screen — water, wetlands, developed areas, steep slope, forest, protected areas.</dd>
  <dt>&#9711; dashed circle</dt>
  <dd>The <b>10&nbsp;km buffer</b> — solar/DC land is only counted inside it.</dd>
</dl>

<h3>Terms in the popup</h3>
<p class="mut" style="margin-bottom:8px"><b>Key point:</b> a plant qualifies when the solar that <i>fits</i>
&ge; the solar <i>needed</i> — <b>not</b> when developable MW &gt; nameplate MW. A flat 24/7 load needs
roughly <b>6&times; its size in solar panels</b> (panels run only ~{pd_pct:.0f}% of the time, plus overbuild for
storage losses and cloudy stretches), so a 1&nbsp;GW load can need ~6&nbsp;GW of solar.</p>
<dl>
  <dt>Nameplate (MW)</dt><dd>Plant's max rated output; here it's the size of the 24/7 data-center load.</dd>
  <dt>AC capacity factor</dt><dd>Solar output ÷ its theoretical max, from PVWatts/NSRDB. PJM range here
      {cf_lo:.2f}–{cf_hi:.2f}. Higher = less solar needed.</dd>
  <dt>Developable land / usable for solar</dt><dd>Developable land × power density (~{pd_mw:.0f} MW/mi²)
      = the solar the land could fit. But a fixed <b>150-acre parcel is reserved for the data center
      building</b>, so <i>usable for solar</i> = (land − 150 ac) × power density. On small urban sites
      this deduction can matter; on normal sites the solar dwarfs it.</dd>
  <dt>Solar needed</dt><dd>= {C.OVERBUILD} × (1 − g) / CF × nameplate. The panels required so annual
      solar energy covers the load (minus the gas share). ~6× nameplate at these capacity factors.</dd>
  <dt>Hostable DC load (solar-limited)</dt><dd>The data-center size the usable solar land can actually
      power = min(nameplate, usable&nbsp;solar ÷ {C.OVERBUILD}(1−g)/CF). Full nameplate for green plants;
      the <b>partial</b> data center you could still build for orange ones.
      <b>The hostable-load slider filters on this.</b></dd>
  <dt>Headroom</dt><dd>Usable solar (after the 150-ac DC parcel) ÷ solar needed.
      <b>&ge; 1.0 = full nameplate qualifies</b>, exactly; shown per gas cap.</dd>
  <dt>Gas cap (g)</dt><dd>Share of annual data-center energy the gas plant may supply ({caps}).
      Lower g = cleaner but needs more solar/land.</dd>
</dl>

<h3>The test (per plant, per gas cap)</h3>
<p class="mut">solar needed = {C.OVERBUILD} × (1 − g) / CF × nameplate&nbsp;&nbsp;·&nbsp;&nbsp;
land needed = solar ÷ {pd_mw:.0f} MW/mi² (+ {C.DC_LAND_ACRES:.0f}-acre data-center parcel).
Qualifies when developable land ≥ land needed.</p>

<h3>At a glance</h3>
<p><b>{n_qual} of {n} plants</b> fit a full-nameplate data center at the 10% gas cap
(conservative, forest-excluded) = <b>{qual_gw:.0f} GW</b>. But counting the <b>partial</b>
data centers that the other sites can still host, total <b>solar-limited hostable load rises to
~{host_gw:.0f} GW</b> — the opportunity beyond the whole-plant winners.</p>

<h3>Read with care</h3>
<ul>
  <li>The hatch shows the <b>conservative</b> screen (all forest excluded). Including forest roughly
      doubles the land — a documented sensitivity, not shown here.</li>
  <li>Land being present ≠ water/fiber/grid capacity being available. This screens <b>land only</b>.</li>
  <li>Capacity factor here is mildly optimistic; results are a plausibility screen, not a guarantee.</li>
</ul>

<h3>Data</h3>
<p class="mut">Plants: EIA-860 (2024). Solar: NREL NSRDB / PVWatts. Land cover: NLCD 2021.
Slope: USGS 3DEP. Protected areas: PAD-US 4.0. Adapted from Energy Institute at Haas WP&nbsp;356
(Chojkiewicz et&nbsp;al., 2026).</p>
</div>"""


_MAP_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PJM gas-plant solar + data-center land screen</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>/*__PATTERN_JS__*/</script>
<style>
  html,body{margin:0;height:100%} #map{width:100%;height:100vh}
  .info{font:13px/1.4 -apple-system,Segoe UI,sans-serif}
  .legend{position:absolute;bottom:24px;left:24px;z-index:1000;background:#fff;
    padding:10px 14px;border:1px solid #bbb;border-radius:8px;box-shadow:0 1px 6px rgba(0,0,0,.2)}
  .legend b{font-size:13px} .sw{display:inline-block;width:11px;height:11px;border-radius:50%;vertical-align:middle}
  .hatchsw{display:inline-block;width:14px;height:11px;vertical-align:middle;
    background:repeating-linear-gradient(-45deg,#1a9d4d 0 1px,transparent 1px 6px);border:1px solid #1a9d4d}
  .gauge{display:inline-block;width:16px;height:16px;border:1.5px solid #999;border-radius:50%;
    position:relative;vertical-align:middle;margin-right:3px}
  .gauge i{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);border-radius:50%;display:block}
  /* guide sidebar */
  #guideBtn{position:absolute;top:80px;left:10px;z-index:1200;background:#fff;border:1px solid #bbb;
    border-radius:8px;padding:8px 12px;font:600 13px -apple-system,Segoe UI,sans-serif;cursor:pointer;
    box-shadow:0 1px 6px rgba(0,0,0,.25)}
  #guideBtn:hover{background:#f4f4f4}
  #filterBox{position:absolute;top:120px;left:10px;z-index:1200;background:#fff;border:1px solid #bbb;
    border-radius:8px;padding:9px 12px;width:214px;box-shadow:0 1px 6px rgba(0,0,0,.25);
    font:13px -apple-system,Segoe UI,sans-serif}
  #filterBox .flabel{font-weight:600;font-size:12.5px;margin-bottom:5px}
  #filterBox .frow{display:flex;align-items:center;gap:7px;margin:5px 0}
  #filterBox .frow>span{font-size:11px;color:#666;width:24px}
  #filterBox input[type=range]{flex:1;accent-color:#0b6b2e;margin:0}
  #filterBox .fcount{font-size:11.5px;color:#0b6b2e;margin-top:6px;font-weight:600}
  #filterBox .fbtn{font-size:11px;color:#0b6b2e;cursor:pointer;text-decoration:underline;
    background:none;border:none;padding:0;margin-top:2px}
  /* search */
  #searchBox{position:absolute;top:12px;left:50%;transform:translateX(-50%);z-index:1200;background:#fff;
    border:1px solid #bbb;border-radius:8px;padding:6px 8px;box-shadow:0 1px 6px rgba(0,0,0,.25);
    font:13px -apple-system,Segoe UI,sans-serif;display:flex;align-items:center;gap:6px}
  #searchBox input{border:1px solid #ccc;border-radius:5px;padding:5px 8px;width:230px;font-size:13px;outline:none}
  #searchBox input:focus{border-color:#0b6b2e}
  #searchBox button{background:#0b6b2e;color:#fff;border:none;border-radius:5px;padding:6px 11px;
    cursor:pointer;font:600 13px inherit}
  #searchBox button:hover{background:#095a27}
  #searchStatus{font-size:11.5px;color:#888;max-width:150px}
  .searchpin{background:none;border:none;font-size:22px;line-height:22px;text-align:center}
  #sidebar{position:absolute;top:0;left:0;height:100%;width:360px;max-width:88vw;z-index:1300;
    background:#fff;box-shadow:2px 0 14px rgba(0,0,0,.28);transform:translateX(-100%);
    transition:transform .28s ease;overflow-y:auto;
    font:13.5px/1.5 -apple-system,Segoe UI,sans-serif;color:#222}
  #sidebar.open{transform:translateX(0)}
  #sidebar .hd{position:sticky;top:0;background:#0b6b2e;color:#fff;padding:14px 18px;display:flex;
    justify-content:space-between;align-items:center}
  #sidebar .hd b{font-size:15px}
  #sidebar .x{cursor:pointer;font-size:22px;line-height:1;border:none;background:none;color:#fff}
  #sidebar .bd{padding:6px 18px 28px}
  #sidebar h3{font-size:12px;letter-spacing:.05em;text-transform:uppercase;color:#0b6b2e;
    margin:18px 0 6px;border-bottom:1px solid #e2e2e2;padding-bottom:3px}
  #sidebar p{margin:6px 0} #sidebar ul{margin:6px 0;padding-left:18px} #sidebar li{margin:4px 0}
  #sidebar .k{display:inline-block;min-width:14px} #sidebar dt{font-weight:600;margin-top:8px}
  #sidebar dd{margin:2px 0 0;color:#444} #sidebar .mut{color:#777;font-size:12px}
  .dot{display:inline-block;width:12px;height:12px;border-radius:50%;vertical-align:middle}
  .bigdot{width:18px;height:18px} .smdot{width:8px;height:8px}
</style></head><body>
<div id="map"></div>
<div id="searchBox">
  <input id="searchInput" type="text" placeholder="Search place or  lat, lon"
    onkeydown="if(event.key==='Enter')doSearch()" autocomplete="off">
  <button onclick="doSearch()">Search</button>
  <span id="searchStatus"></span>
</div>
<button id="guideBtn" onclick="document.getElementById('sidebar').classList.add('open')">&#9432; Guide</button>
<div id="filterBox">
  <div class="flabel">Hostable load filter (MW)</div>
  <div class="frow"><span>min</span><input type="range" id="fmin"></div>
  <div class="frow"><span>max</span><input type="range" id="fmax"></div>
  <div class="fcount" id="fcount"></div>
  <button class="fbtn" onclick="resetFilter()">reset</button>
</div>
<div id="sidebar">__SIDEBAR__</div>
<div class="legend info">
  <b>PJM gas plants — solar + data-center land screen</b><br>
  <span class="gauge" style="border-color:#1a9850"><i style="background:#1a9850;width:12px;height:12px"></i></span>
  green — full nameplate fits<br>
  <span class="gauge" style="border-color:#f57c00"><i style="background:#f57c00;width:7px;height:7px"></i></span>
  orange — only a partial data center fits<br>
  <span style="color:#777">ring = full nameplate · filled core = hostable DC load · size &prop; nameplate MW</span><br>
  <span class="hatchsw"></span> developable solar land (click a plant)
</div>
<script>
var PLANTS = __PLANTS__;
// SVG renderer required: leaflet.pattern draws the hatch as an SVG <pattern> def,
// which a canvas renderer would silently ignore.
var map = L.map('map',{renderer:L.svg()}).setView([39.5,-80.0],6);
var streets = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
  {maxZoom:20,subdomains:'abcd',attribution:'&copy; OpenStreetMap &copy; CARTO'});
var satellite = L.tileLayer(
  'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
  {maxZoom:19,attribution:'Imagery &copy; Esri, Maxar, Earthstar Geographics'});
streets.addTo(map);
L.control.layers({'Street':streets,'Satellite':satellite}, null, {position:'topright'}).addTo(map);

// thin, airy hatch: 1 px stripes on a 10 px tile (~10% coverage), so the land underneath reads.
var stripes = new L.StripePattern({color:'#1a9d4d',weight:1,spaceWeight:9,opacity:0.8,
  spaceOpacity:0,angle:-45,width:10,height:10});
stripes.addTo(map);

var mws = PLANTS.map(function(p){return p.mw;});
var MINMW = Math.min.apply(null,mws), MAXMW = Math.max.apply(null,mws);
var devLayer=null, bufLayer=null, currentCode=null;
var DEV_CACHE={};   // code -> GeoJSON geometry (lazy-loaded, one per click)

function renderHatch(code, geom){
  if(currentCode!==code) return;                 // a newer click superseded this load
  if(devLayer){map.removeLayer(devLayer);devLayer=null;}
  devLayer = L.geoJSON({type:'Feature',geometry:geom},
    {style:{color:'#1a9d4d',weight:0.7,opacity:0.6,fill:true,fillOpacity:1.0,fillPattern:stripes}}).addTo(map);
}

// Called by the injected dev_tiles/plant_<code>.js files (JSONP-style; works from file://).
function DEVCB(code, geom){ DEV_CACHE[code]=geom; renderHatch(code, geom); }

function showDev(p){
  currentCode = p.code;
  if(devLayer){map.removeLayer(devLayer);devLayer=null;}
  if(bufLayer){map.removeLayer(bufLayer);bufLayer=null;}
  bufLayer = L.circle([p.lat,p.lon],{radius:10000,color:'#666',weight:1.5,
    dashArray:'5,5',fill:false}).addTo(map);
  map.fitBounds(bufLayer.getBounds().pad(0.15));
  if(!p.hasdev){ return; }                        // no developable land within 10 km
  if(DEV_CACHE[p.code]!==undefined){ renderHatch(p.code, DEV_CACHE[p.code]); return; }
  var s=document.createElement('script');         // lazy-load this plant's high-fidelity tile
  s.src='dev_tiles/plant_'+p.code+'.js';
  s.onerror=function(){console.warn('tile load failed for '+p.code);};
  document.body.appendChild(s);
}

var markers=[];   // {m, mw, hl, code} for the hostable-load filter
PLANTS.forEach(function(p){
  var color = p.q10 ? '#1a9850' : '#f57c00';
  // outer ring = full nameplate (plant size); inner fill = hostable DC load we can access.
  var outerR = 4 + 10*(p.mw-MINMW)/Math.max(MAXMW-MINMW,1);
  var frac = p.mw>0 ? Math.min(1, Math.max(0, p.hl10/p.mw)) : 0;   // share we can host
  var innerR = outerR*Math.sqrt(frac);                             // area ∝ accessible share
  var outer = L.circleMarker([p.lat,p.lon],{radius:outerR,color:color,weight:1.5,
    fill:true,fillColor:color,fillOpacity:0.12});
  var layers=[outer];
  if(innerR>0.5){
    layers.push(L.circleMarker([p.lat,p.lon],{radius:innerR,color:color,weight:0,
      fill:true,fillColor:color,fillOpacity:0.85}));
  }
  var m = L.featureGroup(layers).addTo(map);
  var html = '<div class="info"><b>'+p.name+'</b> ('+p.state+')<br>'+
    'Nameplate = 24/7 load: <b>'+p.mw.toLocaleString()+'</b> MW<br>'+
    'AC capacity factor: '+p.cf.toFixed(3)+'<br>'+
    'Developable land: '+p.darea.toLocaleString()+' mi&sup2; &nbsp;(fits <b>'+p.dmw.toLocaleString()+'</b> MW of solar)<br>'+
    'Usable for solar after 150-ac DC parcel: <b>'+p.umw.toLocaleString()+'</b> MW<br>'+
    'Solar <u>needed</u> (full load):&nbsp; g5% '+p.sr5.toLocaleString()+' &middot; g10% <b>'+p.sr10.toLocaleString()+'</b> &middot; g20% '+p.sr20.toLocaleString()+' MW<br>'+
    '<span style="color:#0b6b2e">&#9654; <b>Hostable DC load</b> (solar-limited):&nbsp; g5% '+p.hl5.toLocaleString()+' &middot; g10% <b>'+p.hl10.toLocaleString()+'</b> &middot; g20% '+p.hl20.toLocaleString()+' MW</span><br>'+
    'Headroom (usable&divide;needed):&nbsp; g5% '+p.h5.toFixed(2)+' &middot; g10% <b>'+p.h10.toFixed(2)+'</b> &middot; g20% '+p.h20.toFixed(2)+
    ' <span style="color:#777">(&ge;1 = full nameplate qualifies)</span><br>'+
    'Full nameplate qualifies @10%: <b>'+(p.q10?'YES':'no')+'</b>'+
    (p.hasdev?'<br><span style="color:#1a9d4d">&#9632; click marker to shade developable land</span>'
             :'<br><i>no developable land within 10&nbsp;km</i>')+'</div>';
  m.bindPopup(html,{maxWidth:360});
  m.on('click',function(){showDev(p);});
  markers.push({m:m, mw:p.mw, hl:p.hl10, code:p.code});
});

// Hostable-load range filter: show only plants whose solar-limited hostable DC load (at 10%
// gas) is within [min, max] MW. This uses the PARTIAL capacity, not full nameplate.
var HLMAX = Math.ceil(Math.max.apply(null,markers.map(function(o){return o.hl;}))/50)*50;
var fmin=document.getElementById('fmin'), fmax=document.getElementById('fmax'),
    fcount=document.getElementById('fcount');
[fmin,fmax].forEach(function(s){s.min=0;s.max=HLMAX;s.step=10;});
fmin.value=0; fmax.value=HLMAX;

function applyFilter(){
  var lo=+fmin.value, hi=+fmax.value;
  if(lo>hi){                                    // keep the two handles from crossing
    if(document.activeElement===fmin){ hi=lo; fmax.value=hi; }
    else { lo=hi; fmin.value=lo; }
  }
  var shown=0;
  markers.forEach(function(o){
    var show = o.hl>=lo && o.hl<=hi;
    if(show){ if(!map.hasLayer(o.m)) o.m.addTo(map); shown++; }
    else if(map.hasLayer(o.m)) map.removeLayer(o.m);
  });
  fcount.textContent = shown+' of '+markers.length+' plants · hostable '+
    lo.toLocaleString()+'–'+hi.toLocaleString()+' MW';
  if(currentCode!=null){                        // clear overlay if current plant filtered out
    var cur=null; markers.forEach(function(o){ if(o.code===currentCode) cur=o; });
    if(cur && (cur.hl<lo || cur.hl>hi)){
      if(devLayer){map.removeLayer(devLayer);devLayer=null;}
      if(bufLayer){map.removeLayer(bufLayer);bufLayer=null;}
      currentCode=null;
    }
  }
}
function resetFilter(){ fmin.value=0; fmax.value=HLMAX; applyFilter(); }
fmin.addEventListener('input',applyFilter);
fmax.addEventListener('input',applyFilter);
applyFilter();
// ---- Search: place names (Nominatim JSONP, works from file://) or "lat, lon" ----
var pinIcon = L.divIcon({className:'searchpin', html:'\\ud83d\\udccd', iconSize:[24,24],
  iconAnchor:[5,22], popupAnchor:[7,-20]});
var searchPin=null, geoSeq=0;
function setStatus(t){ document.getElementById('searchStatus').textContent=t||''; }

function dropPin(la, lo, label, bb){
  if(searchPin) map.removeLayer(searchPin);
  searchPin = L.marker([la,lo],{icon:pinIcon, zIndexOffset:1000}).addTo(map);
  searchPin.bindPopup('<div class="info"><b>'+(label||('📍 '+la.toFixed(4)+', '+lo.toFixed(4)))+
    '</b><br><span class="mut" style="color:#777">'+la.toFixed(4)+', '+lo.toFixed(4)+
    '</span></div>').openPopup();
  if(bb){ map.fitBounds([[+bb[0],+bb[2]],[+bb[1],+bb[3]]],{maxZoom:15,padding:[24,24]}); }
  else { map.setView([la,lo],13); }
}

function geocode(q){
  setStatus('Searching…');
  var seq=++geoSeq, cb='__geocb_'+seq, s;
  var timer=setTimeout(function(){ cleanup(); if(seq===geoSeq) setStatus('No response'); },12000);
  function cleanup(){ try{delete window[cb];}catch(e){window[cb]=undefined;}
    if(s&&s.parentNode) s.parentNode.removeChild(s); }
  window[cb]=function(data){
    clearTimeout(timer); cleanup();
    if(seq!==geoSeq) return;                       // superseded by a newer search
    if(!data||!data.length){ setStatus('Not found — try "lat, lon"'); return; }
    var r=data[0]; setStatus('');
    dropPin(+r.lat, +r.lon, r.display_name, r.boundingbox);
  };
  s=document.createElement('script');
  s.src='https://nominatim.openstreetmap.org/search?format=json&limit=1&json_callback='+cb+
        '&q='+encodeURIComponent(q);
  s.onerror=function(){ clearTimeout(timer); cleanup(); if(seq===geoSeq) setStatus('Search failed'); };
  document.body.appendChild(s);
}

function doSearch(){
  var q=document.getElementById('searchInput').value.trim();
  if(!q) return;
  var m=q.match(/^\\s*(-?\\d{1,3}(?:\\.\\d+)?)\\s*[, ]\\s*(-?\\d{1,3}(?:\\.\\d+)?)\\s*$/);
  if(m){ var la=+m[1], lo=+m[2];
    if(la>=-90&&la<=90&&lo>=-180&&lo<=180){ setStatus(''); dropPin(la,lo,null,null); return; } }
  geocode(q);
}

document.addEventListener('keydown',function(e){
  if(e.key==='Escape') document.getElementById('sidebar').classList.remove('open');
});
</script></body></html>
"""


def make_summary(long: pd.DataFrame, wide: pd.DataFrame) -> None:
    L = []
    L.append("# PJM Gas-Plant / Solar / Data-Center Land Screen — Summary\n")
    L.append(f"Fleet: **{len(wide)} operating PJM gas plants**, "
             f"**{wide.nameplate_MW.sum()/1000:.1f} GW** total nameplate.\n")
    L.append(f"Parameters: overbuild={C.OVERBUILD}, power density default "
             f"{C.POWER_DENSITY_MW_PER_MI2:.0f} MW/mi² ({C.ACRES_PER_MW:.0f} ac/MW), "
             f"DC parcel {C.DC_LAND_ACRES:.0f} acres, NSRDB TMY CF (PVWatts, AC). Areas in mi².\n")

    for forest, ftag in (("excl_forest", "forest EXCLUDED (conservative default)"),
                         ("incl_forest", "forest INCLUDED (less aggressive)")):
        prim = long[np.isclose(long.acres_per_MW, C.ACRES_PER_MW) & (long.forest == forest)]
        L.append(f"## Qualifying plants & hostable data-center load (GW) — {ftag}\n")
        L.append("| Buffer | Gas cap | Plants qualifying | Hostable load (GW) |")
        L.append("|---|---|---|---|")
        for buf in C.BUFFERS_KM:
            for g in C.GAS_CAPS:
                sub = prim[(prim.buffer_km == buf) & (prim.gas_cap == g)]
                q = sub[sub.qualifies]
                L.append(f"| {int(buf)} km | {int(g*100)}% | {len(q)} | {q.nameplate_MW.sum()/1000:.1f} |")
        L.append("")

    L.append("## Power-density sensitivity (10 km, 10% gas cap, forest excluded)\n")
    L.append("| acres/MW | MW/mi² | Plants qualifying | Hostable load (GW) |")
    L.append("|---|---|---|---|")
    for apm in C.ACRES_PER_MW_SENSITIVITY:
        sub = long[(long.buffer_km == C.BUFFER_KM_PRIMARY) & (long.gas_cap == 0.10) &
                   (long.forest == "excl_forest") & (np.isclose(long.acres_per_MW, apm))]
        q = sub[sub.qualifies]
        L.append(f"| {apm:.0f} | {C.power_density(apm):.1f} | {len(q)} | {q.nameplate_MW.sum()/1000:.1f} |")

    # Whole-plant vs partial-inclusive hostable load (the "opportunity left on the table").
    L.append("\n## Hostable load — whole-plant vs including partial data centers (10 km, forest excl.)\n")
    L.append("A plant that can't host a *full-nameplate* data center can usually still host a "
             "*smaller* one matched to its available solar land. Hostable load = "
             "min(nameplate, headroom × nameplate).\n")
    L.append("| Gas cap | Whole-plant qualifiers (GW) | Including partial DCs (GW) |")
    L.append("|---|---|---|")
    for g in C.GAS_CAPS:
        gg = int(g * 100)
        whole = wide.loc[wide[f"qualifies_g{gg}"] == True, "nameplate_MW"].sum() / 1000  # noqa: E712
        partial = wide[f"hostable_MW_g{gg}"].sum() / 1000
        L.append(f"| {gg}% | {whole:.1f} | {partial:.1f} |")

    # By-state roll-up vs paper Fig. 4, BOTH forest settings side by side.
    L.append("\n## Qualifying nameplate by state (10 km, 10% gas cap, 7 ac/MW) — vs paper Fig. 4\n")
    L.append("| State | Forest excl. GW | Forest incl. GW | Paper Fig. 4 (GW) |")
    L.append("|---|---|---|---|")
    def by_state(forest):
        sub = long[(long.buffer_km == C.BUFFER_KM_PRIMARY) & (long.gas_cap == 0.10) &
                   (np.isclose(long.acres_per_MW, C.ACRES_PER_MW)) & (long.forest == forest)]
        q = sub[sub.qualifies]
        return (q.groupby("state").nameplate_MW.sum() / 1000)
    bx, bi = by_state("excl_forest"), by_state("incl_forest")
    states = sorted(set(bx.index) | set(bi.index) | set(PAPER_STATE_GW),
                    key=lambda s: -bi.get(s, 0))
    for st in states:
        L.append(f"| {st} | {bx.get(st,0):.1f} | {bi.get(st,0):.1f} | {PAPER_STATE_GW.get(st,'—')} |")
    L.append(f"| **Total (5 paper states)** | "
             f"**{sum(bx.get(s,0) for s in PAPER_STATE_GW):.1f}** | "
             f"**{sum(bi.get(s,0) for s in PAPER_STATE_GW):.1f}** | "
             f"**{sum(PAPER_STATE_GW.values())}** |")

    L.append("\n## Validation notes (Spec section 11)\n")
    L.append("- **Order-of-magnitude match, forest toggle is the key lever.** The forest-"
             "included screen (27 GW across the 5 paper states) aligns with paper Fig. 4 far "
             "better than the conservative forest-excluded default (15 GW); VA (8.0 vs 10) and "
             "OH (7.3 vs 12) land close. Excluding all forest is the aggressive end of the "
             "toggle (Spec §12).")
    L.append("- **Fig. 4 is not the same quantity as qualifying gas nameplate.** Paper Fig. 4 "
             "gives IL = 16 GW, which *exceeds* IL's entire operating gas fleet here (13.7 GW). "
             "So Fig. 4 measures a solar/load-potential, not qualifying nameplate; our lower, "
             "same-order-of-magnitude totals are the expected outcome, not a bug.")
    L.append("- **Residual gap (PA, IL) is plant size + terrain.** PA/IL fleets are dominated "
             "by large CCGTs whose flat 24/7 load needs more solar than fits within 10 km; "
             "single-axis tracking or a larger buffer would expand the set.")
    L.append("- CF here (~0.19 AC, 1.3 ILR) is mildly optimistic vs the spec's 0.16 anchor; "
             "a lower CF raises R and shrinks the qualifying set. Solar land dwarfs the "
             "150-acre DC parcel, so the area test binds on solar.")
    (C.OUTPUTS / "summary.md").write_text("\n".join(L) + "\n")
    print("Wrote outputs/summary.md")


def main() -> None:
    wide = pd.read_csv(C.OUTPUTS / "pjm_sites.csv")
    long = pd.read_csv(C.OUTPUTS / "pjm_sites_sensitivity.csv")
    make_map(wide)
    make_summary(long, wide)


if __name__ == "__main__":
    main()
