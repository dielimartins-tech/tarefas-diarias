#!/usr/bin/env python3
"""Monta o dashboard.html de distribuição de conteúdo da Espaço Humanidade.

Junta:
  - dados/*.csv: exportações diárias do Gerenciador (Fase 1 e Fase 2), lidas por csv_fases.py.
  - data_api.json: Instagram e Fase 3, gerado por fetch_api.py.

O HTML sai autocontido: os dados vão embutidos em JSON, e o filtro de datas,
a comparação com o período anterior e as tabelas rodam no navegador.

Uso: python3 build_dashboard.py
"""

import glob
import html
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DASHBOARD_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, SCRIPT_DIR)

import csv_fases  # noqa: E402


def carregar_csvs():
    """Une os CSVs da pasta dados/. Se o mesmo dia e anuncio aparecer em dois
    arquivos, vale o ultimo (ordem alfabetica do nome do arquivo)."""
    pasta = os.path.join(DASHBOARD_DIR, "dados")
    unidos = {}
    for caminho in sorted(glob.glob(os.path.join(pasta, "*.csv"))):
        for linha in csv_fases.ler_csv(caminho):
            unidos[(linha["dia"], linha["ad_id"])] = linha
    return list(unidos.values())


def carregar_api():
    caminho = os.path.join(DASHBOARD_DIR, "data_api.json")
    if not os.path.isfile(caminho):
        sys.exit("ERRO: data_api.json não encontrado. Rode fetch_api.py antes.")
    with open(caminho, encoding="utf-8") as arquivo:
        return json.load(arquivo)


def payload_json(obj):
    # Escapa "</" para um texto dentro de um anuncio nao fechar a tag <script>.
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


CSS = """
:root {
  --bg-top: #0B2A4A; --bg-bottom: #07111F; --card: #0F1E33; --border: #1E3350;
  --accent: #4DA3E0; --text: #F1F5F9; --muted: #94A3B8;
  --ok: #34D399; --warn: #FBBF24; --late: #F87171; --surface-2: #132740;
  --radius: 12px;
  --font: Inter, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
}
* { box-sizing: border-box; }
html, body { margin: 0; }
body {
  min-height: 100vh;
  background: linear-gradient(180deg, var(--bg-top) 0%, var(--bg-bottom) 420px, var(--bg-bottom) 100%);
  background-attachment: fixed;
  color: var(--text); font-family: var(--font); font-size: 14px; line-height: 1.45;
  padding-block: 24px 40px;
  padding-inline: max(16px, env(safe-area-inset-left, 0px)) max(16px, env(safe-area-inset-right, 0px));
}
h1, h2, h3 { margin: 0; font-weight: 600; }
h1 { font-size: 26px; letter-spacing: -0.01em; }
h2 { font-size: 16px; }
.eyebrow { font-size: 12px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: var(--accent); margin-bottom: 6px; }
.muted { color: var(--muted); }
.num { font-variant-numeric: tabular-nums; }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
select, input[type="date"] {
  font: inherit; color: var(--text); background: var(--card); border: 1px solid var(--border);
  border-radius: 8px; padding: 8px 10px; min-width: 0; color-scheme: dark;
}
.card { background: var(--card); border: 1px solid var(--border); border-radius: var(--radius); padding: 18px; min-width: 0; }
.card-head { display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
.card-head .muted { font-size: 12px; }
.stack { display: grid; gap: 16px; }
.grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; align-items: start; }
.grid > .wide { grid-column: 1 / -1; }

.head { display: flex; align-items: flex-end; justify-content: space-between; flex-wrap: wrap; gap: 14px; margin-bottom: 18px; }
.toolbar { display: flex; flex-wrap: wrap; align-items: flex-end; gap: 12px 16px; margin-bottom: 16px; }
.field { display: grid; gap: 4px; font-size: 12px; color: var(--muted); }
.check { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--text); padding-bottom: 9px; }
.check input { width: 16px; height: 16px; margin: 0; accent-color: var(--accent); }
.range-label { width: 100%; margin: 0; font-size: 12.5px; color: var(--muted); }

.tabs { display: flex; gap: 4px; margin-bottom: 18px; border-bottom: 1px solid var(--border); overflow-x: auto; }
.tabs button {
  font: inherit; font-weight: 500; color: var(--muted); background: none; border: 0;
  padding: 10px 14px; cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -1px; white-space: nowrap;
}
.tabs button[aria-selected="true"] { color: var(--text); border-bottom-color: var(--accent); }
.tabs button:hover { color: var(--text); }
.panel[hidden] { display: none; }

.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }
.kpi { background: var(--surface-2); border: 1px solid var(--border); border-radius: var(--radius); padding: 12px 14px; min-width: 0; }
.kpi .label { font-size: 12px; color: var(--muted); }
.kpi .value { font-size: 24px; font-weight: 600; margin-top: 4px; font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
.kpi .sub { font-size: 11.5px; color: var(--muted); margin-top: 2px; }
.kpi--alert { border-color: var(--late); }
.delta { font-size: 12px; color: var(--muted); margin-top: 3px; }
.delta.up { color: var(--ok); }
.delta.down { color: var(--late); }
.delta:empty { display: none; }
.note { font-size: 12px; color: var(--muted); margin-top: 2px; }
.note:empty { display: none; }
.kpi--alert .note { color: var(--late); font-weight: 600; }

.phase-title { display: flex; align-items: center; gap: 8px; }
.dot { width: 9px; height: 9px; border-radius: 50%; background: var(--c); flex: none; display: inline-block; }
.phase-desc { margin: 4px 0 0; font-size: 13px; color: var(--muted); max-width: 70ch; }
.legend { display: flex; flex-wrap: wrap; gap: 6px 14px; font-size: 12px; color: var(--muted); margin-bottom: 12px; }
.legend span { display: inline-flex; align-items: center; gap: 6px; }

.split { display: flex; height: 12px; border-radius: 6px; overflow: hidden; background: var(--border); margin-top: 16px; }
.split i { display: block; height: 100%; }

.bars { display: flex; align-items: flex-end; gap: 6px; height: 180px; border-bottom: 1px solid var(--border); padding-top: 8px; }
.bars .slot { flex: 1; height: 100%; display: flex; flex-direction: column; justify-content: flex-end; min-width: 0; }
.bars .stk { display: flex; flex-direction: column; justify-content: flex-end; width: 100%; }
.bars .stk i { display: block; width: 100%; min-height: 2px; }
.bars .stk i:first-child { border-radius: 3px 3px 0 0; }
.axis { display: flex; justify-content: space-between; gap: 6px; margin-top: 6px; font-size: 11px; color: var(--muted); }

.seg { display: inline-flex; border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
.seg button { font: inherit; font-size: 13px; color: var(--muted); background: var(--card); border: 0; padding: 7px 12px; cursor: pointer; }
.seg button[aria-pressed="true"] { background: var(--accent); color: #07111F; font-weight: 600; }
.ads-head { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 10px; margin: 22px 0 10px; }
.ads-head h3 { margin: 0; font-size: 15px; }

.table-wrap { overflow-x: auto; margin-inline: -18px; padding-inline: 18px; }
table { width: 100%; border-collapse: collapse; min-width: 640px; }
th, td { text-align: left; padding: 9px 8px; border-bottom: 1px solid var(--border); vertical-align: middle; font-size: 13.5px; }
th { font-size: 11.5px; font-weight: 600; letter-spacing: .04em; text-transform: uppercase; color: var(--muted); white-space: nowrap; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
th .sort { font: inherit; font-size: inherit; letter-spacing: inherit; text-transform: inherit; color: inherit; background: none; border: 0; padding: 0; cursor: pointer; }
th[aria-sort="descending"] .sort::after { content: " ↓"; }
th[aria-sort="ascending"] .sort::after { content: " ↑"; }
td strong { font-weight: 600; }
.pill { display: inline-block; font-size: 11.5px; font-weight: 600; padding: 3px 9px; border-radius: 999px; white-space: nowrap; color: var(--c); background: color-mix(in srgb, var(--c) 18%, transparent); }
.pill--ok { --c: var(--ok); }
.pill--prod { --c: #94A3B8; }
.pill--warn { --c: var(--warn); }
.pill--late { --c: var(--late); }
.empty { color: var(--muted); font-size: 13px; padding: 18px 0; margin: 0; }

.aviso { border: 1px dashed var(--border); border-radius: var(--radius); padding: 18px; color: var(--muted); font-size: 13px; }
footer { margin-top: 24px; font-size: 12px; color: var(--muted); display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px; }

@media (max-width: 760px) {
  .grid { grid-template-columns: minmax(0, 1fr); }
}
"""

JS = r"""
(function () {
  "use strict";
  var P = JSON.parse(document.getElementById("payload").textContent);
  var $ = function (id) { return document.getElementById(id); };
  var CFG = P.config;

  var NF = {
    brl0: new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }),
    brl2: new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 2 }),
    int: new Intl.NumberFormat("pt-BR"),
    compact: new Intl.NumberFormat("pt-BR", { notation: "compact", maximumFractionDigits: 1 }),
    pct: new Intl.NumberFormat("pt-BR", { style: "percent", maximumFractionDigits: 2 }),
    pct1: new Intl.NumberFormat("pt-BR", { style: "percent", maximumFractionDigits: 1 }),
    dec: new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 }),
    delta: new Intl.NumberFormat("pt-BR", { style: "percent", maximumFractionDigits: 1 })
  };

  function esc(s) { return String(s === null || s === undefined ? "" : s).replace(/[&<>"']/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function iso(d) { return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0"); }
  function parse(s) { var p = s.split("-").map(Number); return new Date(p[0], p[1] - 1, p[2]); }
  function addDays(d, n) { var x = new Date(d); x.setDate(x.getDate() + n); return x; }
  function diff(a, b) { return Math.round((b - a) / 864e5); }
  function br(s) { var p = s.split("-"); return p[2] + "/" + p[1] + "/" + p[0]; }
  function days(from, to) { var out = []; for (var d = new Date(from); d <= to; d = addDays(d, 1)) out.push(iso(d)); return out; }

  var ALL = P.csv.map(function (r) { return r.dia; }).concat(P.api.fase3_anuncios_dia.map(function (r) { return r.dia; }))
    .concat(Object.keys(P.api.gasto_conta_por_dia || {})).concat(Object.keys(P.api.instagram.seguidores_por_dia || {}));
  ALL.sort();
  var MIN = ALL.length ? ALL[0] : iso(new Date());
  var TODAY = iso(new Date());
  if (TODAY < MIN) MIN = TODAY;
  var LAST = ALL.length ? ALL[ALL.length - 1] : TODAY;
  var TODAY_D = parse(LAST);

  // Linhas por fase, todas com a mesma forma: dia, ad_id, anuncio, campanha, gasto, alcance, impressoes, cliques, extras.
  var F1 = [], F2 = [], F3 = [];
  P.csv.forEach(function (r) {
    var base = { dia: r.dia, ad_id: r.ad_id, anuncio: r.anuncio, campanha: r.campanha, status: r.status,
      gasto: r.gasto, seguidores: r.seguidores, visitas: r.visitas, alcance: r.alcance, impressoes: r.impressoes,
      cliques: r.cliques_link };
    (r.fase === "fase1" ? F1 : F2).push(base);
  });
  P.api.fase3_anuncios_dia.forEach(function (r) {
    F3.push({ dia: r.dia, ad_id: r.ad_id, anuncio: r.anuncio, campanha: r.campanha, status: null, gasto: r.gasto,
      alcance: r.alcance, impressoes: r.impressoes, cliques: r.cliques, reacoes: r.reacoes, comentarios: r.comentarios,
      salvamentos: r.salvamentos, compartilhamentos: r.compartilhamentos, video_p25: r.video_p25,
      video_p50: r.video_p50, video_p100: r.video_p100 });
  });

  function inRange(dia, from, to) { return dia >= from && dia <= to; }
  function sumRows(rows, from, to) {
    var t = { gasto: 0, seguidores: 0, visitas: 0, alcance: 0, impressoes: 0, cliques: 0, n: 0 };
    rows.forEach(function (r) { if (inRange(r.dia, from, to)) {
      t.gasto += r.gasto || 0; t.seguidores += r.seguidores || 0; t.visitas += r.visitas || 0;
      t.alcance += r.alcance || 0; t.impressoes += r.impressoes || 0; t.cliques += r.cliques || 0; t.n++; } });
    return t;
  }
  function sumKeyed(obj, from, to) {
    var s = 0; Object.keys(obj || {}).forEach(function (d) { if (inRange(d, from, to)) s += obj[d]; }); return s;
  }
  function sumIg(from, to) {
    var seg = P.api.instagram.seguidores_por_dia || {}, alc = P.api.instagram.alcance_por_dia || {};
    return { seguidores: sumKeyed(seg, from, to), alcance: sumKeyed(alc, from, to) };
  }
  function totals(from, to) {
    var a = sumRows(F1, from, to), b = sumRows(F2, from, to);
    var c = sumRows(F3, from, to);
    var ig = sumIg(from, to);
    return {
      investimento: a.gasto + b.gasto + c.gasto,
      f1: a, f2: b, f3: c, ig: ig,
      // Seguidores da conta já incluem os que vieram dos anúncios; não somar de novo.
      seguidores_total: ig.seguidores,
      cps: (a.seguidores + b.seguidores) ? (a.gasto + b.gasto) / (a.seguidores + b.seguidores) : NaN
    };
  }

  // ---------- Formatos ----------
  function fmtKind(kind, n) {
    if (!isFinite(n)) return "—";
    if (kind === "brl") return (n >= 100 ? NF.brl0 : NF.brl2).format(n);
    if (kind === "pct") return NF.pct1.format(n);
    if (kind === "dec") return NF.dec.format(n);
    return n >= 10000 ? NF.compact.format(n) : NF.int.format(Math.round(n));
  }
  function deltaHtml(cur, prev, good) {
    if (!isFinite(cur) || !isFinite(prev) || prev === 0) return { cls: "delta", txt: "" };
    var pct = (cur - prev) / Math.abs(prev);
    var better = good === "down" ? pct < 0 : pct > 0;
    return { cls: "delta" + (pct === 0 ? "" : better ? " up" : " down"),
      txt: (pct > 0 ? "▲ " : pct < 0 ? "▼ " : "") + NF.delta.format(Math.abs(pct)) + " vs. anterior" };
  }

  // ---------- Estado do filtro ----------
  var state = { from: null, to: null, compare: true, live: { f1: true, f2: true, f3v: true, f3s: true } };
  var sort = { f1: { k: "seguidores", d: -1 }, f2: { k: "seguidores", d: -1 }, f3v: { k: "reacoes", d: -1 }, f3s: { k: "reacoes", d: -1 } };

  function presetRange(v) {
    if (v === "month") return [new Date(TODAY_D.getFullYear(), TODAY_D.getMonth(), 1), TODAY_D];
    if (v === "prev-month") return [new Date(TODAY_D.getFullYear(), TODAY_D.getMonth() - 1, 1), new Date(TODAY_D.getFullYear(), TODAY_D.getMonth(), 0)];
    if (v === "custom") return null;
    return [addDays(TODAY_D, -(Number(v) - 1)), TODAY_D];
  }

  function render() {
    var from = $("from").value, to = $("to").value;
    if (!from || !to || from > to) { $("range").textContent = "Escolha um período válido."; return; }
    state.from = from; state.to = to;
    var len = diff(parse(from), parse(to)) + 1;
    var pTo = iso(addDays(parse(from), -1)), pFrom = iso(addDays(parse(pTo), -(len - 1)));
    var canCompare = $("compare").checked && pFrom >= MIN;
    var cur = totals(from, to), prev = canCompare ? totals(pFrom, pTo) : null;

    var label = br(from) + " a " + br(to);
    if ($("compare").checked) label += canCompare ? " · comparado com " + br(pFrom) + " a " + br(pTo) : " · sem dados do período anterior";
    $("range").textContent = label;

    renderKpis(cur, prev);
    renderAvisos();
    renderPhaseBar(cur);
    renderCharts(from, to);
    renderInstagram(from, to, cur, prev);
    renderAdsTables(from, to);
  }

  // ---------- Visão geral ----------
  function kpi(label, value, sub, prevVal, curVal, good, extraClass) {
    var d = prevVal === null ? { cls: "delta", txt: "" } : deltaHtml(curVal, prevVal, good);
    return '<div class="kpi' + (extraClass || "") + '"><div class="label">' + label + '</div><div class="value num">' + value +
      '</div><div class="' + d.cls + '">' + d.txt + '</div><div class="sub">' + (sub || "") + '</div></div>';
  }

  function renderKpis(cur, prev) {
    var p = prev, cs = null, ps = null;
    var cps = cur.cps, pcps = p ? p.cps : null;
    var html = "";
    html += kpi("Investimento total", fmtKind("brl", cur.investimento), "soma das Fases 1, 2 e 3", p ? p.investimento : null, cur.investimento, "down");
    html += kpi("Seguidores", fmtKind("int", cur.seguidores_total), "ganhos na conta do Instagram, no período", p ? p.seguidores_total : null, cur.seguidores_total, "up");
    html += kpi("Custo por seguidor", fmtKind("brl", cps), "Fase 1 + Fase 2", p ? pcps : null, cps, "down");
    html += kpi("Alcance Instagram", fmtKind("int", cur.ig.alcance), "contas alcançadas no dia, somadas", p ? p.ig.alcance : null, cur.ig.alcance, "up");
    $("kpis").innerHTML = html;

    var fases = "";
    fases += kpi("Fase 1 · Aquisição", fmtKind("brl", cur.f1.gasto), fmtKind("int", cur.f1.seguidores) + " seguidores",
      p ? p.f1.gasto : null, cur.f1.gasto, "down");
    fases += kpi("Fase 2 · Recuperação", fmtKind("brl", cur.f2.gasto), fmtKind("int", cur.f2.seguidores) + " seguidores",
      p ? p.f2.gasto : null, cur.f2.gasto, "down");
    fases += kpi("Fase 3 · Engajamento", fmtKind("brl", cur.f3.gasto), fmtKind("int", cur.f3.reacoes) + " reações (vídeos e estáticos)",
      p ? p.f3.gasto : null, cur.f3.gasto, "down");
    $("kpis-fases").innerHTML = fases;
  }

  function renderAvisos() {
    var cur = state.from;
    var noDataFb = "Facebook: ainda sem coleta automática (precisa de token de Página).";
    $("aviso-fb").textContent = noDataFb;
  }

  function renderPhaseBar(cur) {
    var t = cur.investimento || 0;
    var parts = [["f1", "Fase 1", cur.f1.gasto], ["f2", "Fase 2", cur.f2.gasto], ["f3", "Fase 3", cur.f3.gasto]];
    $("split").innerHTML = parts.map(function (p) {
      var share = t ? p[2] / t : 0;
      return '<i title="' + p[1] + ': ' + NF.pct1.format(share) + '" style="width:' + (share * 100).toFixed(2) + '%;background:' + COLORS[p[0]] + '"></i>';
    }).join("");
    $("split-legend").innerHTML = parts.map(function (p) {
      var share = t ? p[2] / t : 0;
      return '<span><i class="dot" style="--c:' + COLORS[p[0]] + '"></i>' + p[1] + ' · ' + NF.pct1.format(share) + '</span>';
    }).join("");
  }

  var COLORS = { f1: "#4DA3E0", f2: "#FBBF24", f3: "#34D399" };

  // ---------- Gráfico diário por fase ----------
  function stackBars(id, axisId, labels, series) {
    var totals = labels.map(function (_, i) { return series.reduce(function (a, s) { return a + s.values[i]; }, 0); });
    var max = Math.max.apply(null, [1].concat(totals));
    $(id).style.gap = labels.length > 40 ? "1px" : "6px";
    $(id).innerHTML = labels.map(function (l, i) {
      return '<div class="slot" title="' + esc(l) + ': ' + fmtKind("brl", totals[i]) + '"><div class="stk">' +
        series.map(function (s) { return '<i style="height:' + (s.values[i] / max * 100).toFixed(2) + '%;background:' + s.color + '"></i>'; }).join("") +
        '</div></div>';
    }).join("");
    $(axisId).innerHTML = labels.length ? "<span>" + esc(labels[0]) + "</span><span>" + esc(labels[labels.length - 1]) + "</span>" : "";
  }

  function renderCharts(from, to) {
    var ds = days(from, to);
    var labels = ds.map(br);
    var gasto = function (rows) { var m = {}; rows.forEach(function (r) { m[r.dia] = (m[r.dia] || 0) + (r.gasto || 0); }); return m; };
    var m1 = gasto(F1), m2 = gasto(F2), m3 = gasto(F3);
    stackBars("chart-fases", "chart-fases-axis", labels, [
      { values: ds.map(function (d) { return m1[d] || 0; }), color: COLORS.f1 },
      { values: ds.map(function (d) { return m2[d] || 0; }), color: COLORS.f2 },
      { values: ds.map(function (d) { return m3[d] || 0; }), color: COLORS.f3 }
    ]);
  }

  // ---------- Instagram ----------
  function renderInstagram(from, to, cur, prev) {
    var ig = P.api.instagram;
    var ds = days(from, to);
    $("ig-seg-total").textContent = fmtKind("int", ig.seguidores_atuais || 0) + " seguidores hoje";
    $("ig-kpis").innerHTML =
      kpi("Seguidores ganhos", fmtKind("int", cur.ig.seguidores), "no período", prev ? prev.ig.seguidores : null, cur.ig.seguidores, "up") +
      kpi("Alcance", fmtKind("int", cur.ig.alcance), "contas alcançadas (soma diária)", prev ? prev.ig.alcance : null, cur.ig.alcance, "up") +
      kpi("Visualizações (acumulado)", fmtKind("int", (ig.periodo_total || {}).views || 0), "desde " + br(P.api.periodo.inicio), null, 0, "up") +
      kpi("Visitas ao perfil (acumulado)", fmtKind("int", (ig.periodo_total || {}).profile_views || 0), "desde " + br(P.api.periodo.inicio), null, 0, "up") +
      kpi("Toques no link (acumulado)", fmtKind("int", (ig.periodo_total || {}).website_clicks || 0), "desde " + br(P.api.periodo.inicio), null, 0, "up");
    var seg = ig.seguidores_por_dia || {}, alc = ig.alcance_por_dia || {};
    stackBars("ig-seg-bars", "ig-seg-axis", ds.map(br), [{ values: ds.map(function (d) { return seg[d] || 0; }), color: "#4DA3E0" }]);
    stackBars("ig-alc-bars", "ig-alc-axis", ds.map(br), [{ values: ds.map(function (d) { return alc[d] || 0; }), color: "#4DA3E0" }]);
  }

  // ---------- Tabelas por anuncio ----------
  function agregaPorAnuncio(rows, from, to) {
    var out = {};
    rows.forEach(function (r) {
      if (!inRange(r.dia, from, to)) return;
      var k = r.ad_id;
      var o = out[k] || (out[k] = { ad_id: k, anuncio: r.anuncio, campanha: r.campanha, dias: [], status: null,
        gasto: 0, seguidores: 0, visitas: 0, alcance: 0, impressoes: 0, cliques: 0,
        reacoes: 0, comentarios: 0, salvamentos: 0, compartilhamentos: 0, video_p25: 0, video_p50: 0, video_p100: 0 });
      o.dias.push(r.dia);
      ["gasto", "seguidores", "visitas", "alcance", "impressoes", "cliques", "reacoes", "comentarios", "salvamentos",
       "compartilhamentos", "video_p25", "video_p50", "video_p100"].forEach(function (c) { o[c] += r[c] || 0; });
    });
    return Object.keys(out).map(function (k) { return out[k]; });
  }
  function ultimoDia(o) { return o.dias.length ? o.dias.slice().sort().pop() : null; }
  function ativoHoje(rows, ad_id) {
    var hoje = LAST;
    return rows.some(function (r) { return r.ad_id === ad_id && r.dia === hoje && (r.status ? r.status === "active" : r.gasto > 0); });
  }
  function metrica(o, k) {
    var g = function (x) { return o[x] || 0; };
    var r = function (a, b) { return b ? a / b : NaN; };
    var eng = g("reacoes") + g("comentarios") + g("salvamentos") + g("compartilhamentos");
    switch (k) {
      case "cps": return r(g("gasto"), g("seguidores"));
      case "conv": return r(g("seguidores"), g("visitas"));
      case "cpm": return r(g("gasto"), g("impressoes")) * 1000;
      case "ctr": return r(g("cliques"), g("impressoes"));
      case "freq": return r(g("impressoes"), g("alcance"));
      case "eng": return eng;
      case "cpe": return r(g("gasto"), eng);
      case "r25": return g("video_p25");
      case "r100": return r(g("video_p100"), g("video_p25"));
      default: return g(k);
    }
  }
  var COLS = {
    f1: [["anuncio", "Anúncio"], ["status", "Status"], ["gasto", "Investimento", "brl"], ["seguidores", "Seguidores", "int"],
      ["cps", "Custo por seguidor", "brl", "down"], ["visitas", "Visitas ao perfil", "int"], ["conv", "Visitas que viraram seguidores", "pct"],
      ["alcance", "Alcance", "int"], ["ctr", "CTR", "pct"], ["link", "Abrir"]],
    f2: [["anuncio", "Anúncio"], ["status", "Status"], ["gasto", "Investimento", "brl"], ["seguidores", "Seguidores", "int"],
      ["cps", "Custo por seguidor", "brl", "down"], ["alcance", "Alcance", "int"], ["freq", "Frequência", "dec", "down", "freq"],
      ["cpm", "CPM", "brl", "down"], ["link", "Abrir"]],
    f3v: [["anuncio", "Anúncio"], ["status", "Status"], ["gasto", "Investimento", "brl"], ["eng", "Engajamento real", "int"],
      ["cpe", "Custo por engajamento", "brl", "down"], ["reacoes", "Reações", "int"], ["comentarios", "Comentários", "int"],
      ["salvamentos", "Salvamentos", "int"], ["compartilhamentos", "Compartilhamentos", "int"], ["alcance", "Alcance", "int"],
      ["freq", "Frequência", "dec", "down"], ["ctr", "CTR", "pct"], ["r25", "Reprodução 25%", "int"], ["r100", "Reprodução 100% (de 25%)", "pct"], ["link", "Abrir"]],
    f3s: [["anuncio", "Anúncio"], ["status", "Status"], ["gasto", "Investimento", "brl"], ["eng", "Engajamento real", "int"],
      ["cpe", "Custo por engajamento", "brl", "down"], ["reacoes", "Reações", "int"], ["comentarios", "Comentários", "int"],
      ["salvamentos", "Salvamentos", "int"], ["compartilhamentos", "Compartilhamentos", "int"], ["alcance", "Alcance", "int"],
      ["freq", "Frequência", "dec", "down"], ["ctr", "CTR", "pct"], ["link", "Abrir"]]
  };

  function renderTable(key, tbodyId, theadId, rows, all) {
    var cols = COLS[key];
    var st = sort[key];
    var lista = agregaPorAnuncio(rows.data, rows.from, rows.to).filter(function (o) {
      return state.live[key] ? ativoHoje(rows.data, o.ad_id) : true;
    });
    lista.forEach(function (o) { o.status = ativoHoje(rows.data, o.ad_id) ? "active" : "inactive"; });
    var sv = function (o) {
      if (st.k === "anuncio") return o.anuncio || "";
      var v = metrica(o, st.k); return isFinite(v) ? v : -Infinity;
    };
    lista.sort(function (a, b) { var x = sv(a), y = sv(b); return (typeof x === "string" ? x.localeCompare(y) : x - y) * st.d; });

    $(theadId).innerHTML = "<tr>" + cols.map(function (c) {
      var num = c[2] ? ' class="num"' : "";
      if (c[0] === "anuncio" || c[0] === "status" || c[0] === "link") return "<th" + num + ">" + c[1] + "</th>";
      var aria = st.k === c[0] ? (st.d < 0 ? "descending" : "ascending") : "none";
      return '<th' + num + ' aria-sort="' + aria + '"><button type="button" class="sort" data-table="' + key + '" data-sort="' + c[0] + '">' + c[1] + "</button></th>";
    }).join("") + "</tr>";

    if (!lista.length) {
      $(tbodyId).innerHTML = '<tr><td colspan="' + cols.length + '" class="muted">' +
        (state.live[key] ? "Nenhum anúncio ativo hoje nesta tabela." : "Nenhum anúncio com dados no período.") + "</td></tr>";
      return;
    }
    $(tbodyId).innerHTML = lista.map(function (o) {
      return "<tr>" + cols.map(function (c) {
        if (c[0] === "anuncio") return "<td><strong>" + esc(o.anuncio) + '</strong><div class="muted" style="font-size:11.5px">' + esc(o.campanha) + "</div></td>";
        if (c[0] === "status") return '<td><span class="pill ' + (o.status === "active" ? "pill--ok" : "pill--prod") + '">' + (o.status === "active" ? "Ativo" : "Inativo") + "</span></td>";
        if (c[0] === "link") return '<td><a href="https://adsmanager.facebook.com/adsmanager/manage/ads?act=' + esc(CFG.ad_account_id.replace("act_", "")) + "&selected_ad_ids=" + esc(o.ad_id) + '" target="_blank" rel="noopener">Gerenciador</a></td>';
        var v = c[0] === "conv" ? metrica(o, "conv") : metrica(o, c[0]);
        var kind = c[2] || "int";
        var txt = c[0] === "freq" ? fmtKind("dec", v) : fmtKind(kind, v);
        var cls = c[4] === "freq" && isFinite(v) && v > CFG.frequencia_alerta_fase2 && key === "f2" ? ' style="color:var(--late);font-weight:600"' : "";
        return '<td class="num"' + cls + ">" + txt + "</td>";
      }).join("") + "</tr>";
    }).join("");
  }

  function renderAdsTables(from, to) {
    renderTable("f1", "f1-ads", "f1-head", { data: F1, from: from, to: to });
    renderTable("f2", "f2-ads", "f2-head", { data: F2, from: from, to: to });
    renderTable("f3v", "f3v-ads", "f3v-head", { data: F3.filter(isVideo), from: from, to: to });
    renderTable("f3s", "f3s-ads", "f3s-head", { data: F3.filter(function (r) { return !isVideo(r); }), from: from, to: to });
    renderPosts(from, to);
  }
  // Fase 3 separa vídeo de estático pelo nome da campanha (VIDEO / CARROSSEL).
  function isVideo(r) { return /v[ií]deo|reel/i.test(r.campanha || "") && !/carross|est[aá]tic/i.test(r.campanha || ""); }

  function renderPosts(from, to) { /* reservado: tabela de publicações do Instagram */ }

  // ---------- Eventos ----------
  var presetBtns = document.querySelectorAll("#preset");
  $("preset").addEventListener("change", function (e) {
    var r = presetRange(e.target.value);
    if (r) { $("from").value = iso(r[0]); $("to").value = iso(r[1]); }
    render();
  });
  ["from", "to"].forEach(function (id) {
    $(id).addEventListener("change", function () { $("preset").value = "custom"; render(); });
  });
  $("compare").addEventListener("change", render);

  document.addEventListener("click", function (e) {
    var b = e.target.closest("button.sort");
    if (b) {
      var st = sort[b.dataset.table];
      if (st.k === b.dataset.sort) st.d = -st.d; else { st.k = b.dataset.sort; st.d = -1; }
      render(); return;
    }
    var l = e.target.closest("[data-live]");
    if (l) {
      var key = l.dataset.live, on = l.dataset.on === "1";
      state.live[key] = on;
      document.querySelectorAll('[data-live="' + key + '"]').forEach(function (x) {
        x.setAttribute("aria-pressed", String(x.dataset.on === (on ? "1" : "0")));
      });
      render();
    }
  });

  var tabs = [].slice.call(document.querySelectorAll('[role="tab"]'));
  function showTab(tab) {
    tabs.forEach(function (t) {
      var on = t === tab;
      t.setAttribute("aria-selected", on);
      t.tabIndex = on ? 0 : -1;
      $(t.getAttribute("aria-controls")).hidden = !on;
    });
    tab.focus();
  }
  tabs.forEach(function (t, i) {
    t.addEventListener("click", function () { showTab(t); });
    t.addEventListener("keydown", function (e) {
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
      showTab(tabs[(i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length]);
    });
  });

  // Período padrão: últimos 30 dias até o último dia com dados.
  $("from").min = MIN; $("to").min = MIN; $("from").max = LAST; $("to").max = LAST;
  var ini = presetRange("30");
  $("from").value = iso(ini[0]); $("to").value = iso(ini[1]);
  render();
})();
"""


def tabela_vazia(id_thead, id_tbody):
    return (f'<div class="table-wrap"><table><thead id="{id_thead}"></thead>'
            f'<tbody id="{id_tbody}"></tbody></table></div>')


def bloco_ads_head(chave, titulo, rotulo):
    return (
        f'<div class="ads-head"><h3>{html.escape(titulo)}</h3>'
        f'<div class="seg" role="group" aria-label="{html.escape(rotulo)}">'
        f'<button type="button" data-live="{chave}" data-on="1" aria-pressed="true">Ativos hoje</button>'
        f'<button type="button" data-live="{chave}" data-on="0" aria-pressed="false">Ativos no período</button>'
        f'</div></div>'
    )


def montar_html(config, csv_rows, api):
    payload = {"config": config, "csv": csv_rows, "api": api}
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="claude:viewport-fit-sides" content="cover">
<title>Espaço Humanidade · Distribuição de Conteúdo</title>
<style>{CSS}</style>
</head>
<body>
<header class="head">
  <div>
    <p class="eyebrow">Espaço Humanidade · Distribuição de conteúdo</p>
    <h1>Distribuição de conteúdo</h1>
  </div>
</header>

<section class="toolbar card" aria-label="Filtro de período">
  <label class="field">Período
    <select id="preset">
      <option value="7">Últimos 7 dias</option>
      <option value="14">Últimos 14 dias</option>
      <option value="30" selected>Últimos 30 dias</option>
      <option value="month">Este mês</option>
      <option value="prev-month">Mês anterior</option>
      <option value="custom">Personalizado</option>
    </select>
  </label>
  <label class="field">De <input type="date" id="from"></label>
  <label class="field">Até <input type="date" id="to"></label>
  <label class="check"><input type="checkbox" id="compare" checked> Comparar com período anterior</label>
  <p class="range-label" id="range" aria-live="polite"></p>
</section>

<nav class="tabs" role="tablist" aria-label="Seções">
  <button role="tab" aria-selected="true" aria-controls="p-geral" id="t-geral">Visão geral</button>
  <button role="tab" aria-selected="false" aria-controls="p-fb" id="t-fb" tabindex="-1">Facebook</button>
  <button role="tab" aria-selected="false" aria-controls="p-ig" id="t-ig" tabindex="-1">Instagram</button>
  <button role="tab" aria-selected="false" aria-controls="p-ads" id="t-ads" tabindex="-1">Anúncios</button>
</nav>

<section class="panel stack" id="p-geral" role="tabpanel" aria-labelledby="t-geral">
  <div class="kpis" id="kpis"></div>
  <div class="card">
    <div class="card-head"><h2>Investimento por fase</h2><span class="muted">Período selecionado</span></div>
    <div class="kpis" id="kpis-fases"></div>
    <div class="split" id="split" role="img" aria-label="Divisão do investimento entre as fases"></div>
    <div class="legend" id="split-legend" style="margin: 10px 0 0"></div>
  </div>
  <div class="card">
    <div class="card-head"><h2>Investimento por dia</h2><span class="muted">Período selecionado</span></div>
    <div class="legend">
      <span><i class="dot" style="--c:#4DA3E0"></i>Fase 1 · Aquisição</span>
      <span><i class="dot" style="--c:#FBBF24"></i>Fase 2 · Recuperação</span>
      <span><i class="dot" style="--c:#34D399"></i>Fase 3 · Engajamento</span>
    </div>
    <div class="bars" id="chart-fases" role="img" aria-label="Investimento por dia, separado por fase"></div>
    <div class="axis" id="chart-fases-axis"></div>
  </div>
</section>

<section class="panel stack" id="p-fb" role="tabpanel" aria-labelledby="t-fb" hidden>
  <div class="aviso" id="aviso-fb"></div>
</section>

<section class="panel stack" id="p-ig" role="tabpanel" aria-labelledby="t-ig" hidden>
  <div class="card-head" style="padding:0"><h2>Instagram · conta</h2><span class="muted" id="ig-seg-total"></span></div>
  <div class="kpis" id="ig-kpis"></div>
  <div class="grid">
    <div class="card">
      <div class="card-head"><h2>Seguidores ganhos por dia</h2><span class="muted">Período selecionado</span></div>
      <div class="bars" id="ig-seg-bars" role="img" aria-label="Seguidores ganhos por dia"></div>
      <div class="axis" id="ig-seg-axis"></div>
    </div>
    <div class="card">
      <div class="card-head"><h2>Alcance por dia</h2><span class="muted">Período selecionado</span></div>
      <div class="bars" id="ig-alc-bars" role="img" aria-label="Alcance por dia"></div>
      <div class="axis" id="ig-alc-axis"></div>
    </div>
  </div>
</section>

<section class="panel stack" id="p-ads" role="tabpanel" aria-labelledby="t-ads" hidden>
  <div class="card">
    <div class="card-head"><h2 class="phase-title"><i class="dot" style="--c:#4DA3E0"></i>Fase 1 · Aquisição de seguidores</h2></div>
    <p class="phase-desc">Posts turbinados para atrair públicos frios. Seguidores, visitas e alcance vêm da planilha exportada do Gerenciador, por anúncio.</p>
    {bloco_ads_head("f1", "Anúncios da Fase 1", "Anúncios da Fase 1")}
    {tabela_vazia("f1-head", "f1-ads")}
  </div>

  <div class="card">
    <div class="card-head"><h2 class="phase-title"><i class="dot" style="--c:#FBBF24"></i>Fase 2 · Recuperação</h2></div>
    <p class="phase-desc">Criativos para público quente que viu ou interagiu e não segue. Frequência acima de 2 aparece em vermelho.</p>
    {bloco_ads_head("f2", "Anúncios da Fase 2", "Anúncios da Fase 2")}
    {tabela_vazia("f2-head", "f2-ads")}
  </div>

  <div class="card">
    <div class="card-head"><h2 class="phase-title"><i class="dot" style="--c:#34D399"></i>Fase 3 · Engajamento</h2></div>
    <p class="phase-desc">Conteúdos mais técnicos ou aprofundados. Duas campanhas: vídeos, e estáticos e carrosséis.</p>
    {bloco_ads_head("f3v", "Anúncios de vídeo", "Anúncios de vídeo")}
    {tabela_vazia("f3v-head", "f3v-ads")}
    {bloco_ads_head("f3s", "Anúncios estáticos e carrosséis", "Anúncios estáticos e carrosséis")}
    {tabela_vazia("f3s-head", "f3s-ads")}
  </div>
</section>

<footer>
  <span>Dados atualizados pela rotina automática (6h e 18h). Planilhas das Fases 1 e 2 são atualizadas quando chegam.</span>
  <span>Abrir no Gerenciador leva ao anúncio no Meta.</span>
</footer>

<script type="application/json" id="payload">{payload_json(payload)}</script>
<script>{JS}</script>
</body>
</html>
"""


def main():
    config_path = os.path.join(DASHBOARD_DIR, "config.json")
    with open(config_path, encoding="utf-8") as arquivo:
        config = json.load(arquivo)
    csv_rows = carregar_csvs()
    api = carregar_api()
    saida = os.path.join(DASHBOARD_DIR, "dashboard.html")
    with open(saida, "w", encoding="utf-8") as arquivo:
        arquivo.write(montar_html(config, csv_rows, api))
    print(f"OK: {len(csv_rows)} linhas de CSV e {len(api['fase3_anuncios_dia'])} linhas da Fase 3. Gravado em {saida}")


if __name__ == "__main__":
    main()
