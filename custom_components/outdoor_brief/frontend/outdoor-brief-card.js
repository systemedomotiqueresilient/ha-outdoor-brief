// Outdoor Brief : carte Lovelace du résumé du jour.
// JavaScript sans dépendance. Aucune valeur venant d'une entité n'est insérée en HTML :
// le gabarit est fixe et les données passent par textContent.

const CARD_VERSION = "0.4.0";

const TEXT = {
  fr: {
    title: "Outdoor Brief",
    morning: "Matin",
    afternoon: "Après-midi",
    high: "Pleine mer",
    low: "Basse mer",
    coefficient: "Coefficient",
    rising: "Marée montante",
    falling: "Marée descendante",
    twelfth: (n) => `${n === 1 ? "1er" : `${n}ᵉ`} douzième`,
    range: "marnage",
    nextLow: "BM",
    nextHigh: "PM",
    spring: "Prochaine grande marée",
    springNone: (t) => `Aucune grande marée (seuil ${t}) dans les données disponibles`,
    inDays: (n) => (n === 0 ? "aujourd'hui" : n === 1 ? "demain" : `dans ${n} j`),
    monthMax: "Plus fort coefficient du mois",
    monthMaxOn: (c, d) => `${c} le ${d}`,
    unavailable: "Résumé indisponible : vérifiez l'intégration Marées France.",
    notSummary: (e) => `« ${e} » n'est pas un capteur « Résumé du jour » d'Outdoor Brief : choisissez le bon capteur dans l'éditeur de la carte.`,
    notFound: (e) => `Entité introuvable : ${e}`,
    noEntity: "Choisissez le capteur « Résumé du jour » d'Outdoor Brief.",
    source: "Données SHOM via Marées France",
    editorEntity: "Capteur « Résumé du jour »",
    editorCompact: "Mode compact (sans ligne d'état ni plus fort coefficient du mois)",
    pickerName: "Outdoor Brief",
    pickerDesc: "Le résumé du jour : marées, coefficients et prochaine grande marée.",
    reportName: "Outdoor Brief — rapport du jour",
    reportDesc: "Le rapport de la notification, en temps réel : tous les ports regroupés.",
    noReport: "Aucun résumé Outdoor Brief n'est disponible pour l'instant.",
    updated: (t) => `Mis à jour à ${t}`,
    outdated: "Outdoor Brief a été mis à jour : rechargez la page.",
    reload: "Recharger",
    colon: " :",
    fishing: "Pêche à pied",
    fishingWindow: (s, e, t, c) => `${s}–${e} (BM ${t}, coef ${c})`,
    fishingNext: (d, s, e, c) => `prochain créneau ${d} ${s}–${e} (coef ${c})`,
    fishingNone: (t) => `aucun créneau à coef ${t} ou plus sur 7 jours`,
    sea: "Mer",
    waves: (v) => `vagues ${v} m`,
    swell: (d, v, p) => `houle ${d} ${v} m ${p} s`,
    water: (v) => `eau ${v} °C`,
    surge: (v) => (v >= 0 ? `surcote estimée +${v} cm` : `décote estimée ${v} cm`),
    compass: ["N", "NE", "E", "SE", "S", "SO", "O", "NO"],
    sourceMarine: "Données SHOM via Marées France · mer : Open-Meteo.com",
  },
  en: {
    title: "Outdoor Brief",
    morning: "Morning",
    afternoon: "Afternoon",
    high: "High tide",
    low: "Low tide",
    coefficient: "Coefficient",
    rising: "Rising tide",
    falling: "Falling tide",
    twelfth: (n) => `twelfth ${n}/6`,
    range: "range",
    nextLow: "LW",
    nextHigh: "HW",
    spring: "Next spring tide",
    springNone: (t) => `No spring tide (threshold ${t}) in the available data`,
    inDays: (n) => (n === 0 ? "today" : n === 1 ? "tomorrow" : `in ${n} d`),
    monthMax: "Highest coefficient this month",
    monthMaxOn: (c, d) => `${c} on ${d}`,
    unavailable: "Summary unavailable: check the Marées France integration.",
    notSummary: (e) => `“${e}” is not an Outdoor Brief “Daily summary” sensor: pick the right sensor in the card editor.`,
    notFound: (e) => `Entity not found: ${e}`,
    noEntity: "Choose the Outdoor Brief “Daily summary” sensor.",
    source: "SHOM data via Marées France",
    editorEntity: "“Daily summary” sensor",
    editorCompact: "Compact mode (no status line, no monthly highest coefficient)",
    pickerName: "Outdoor Brief",
    pickerDesc: "The daily brief: tides, coefficients and next spring tide.",
    reportName: "Outdoor Brief — daily report",
    reportDesc: "The notification report, live: every grouped port.",
    noReport: "No Outdoor Brief summary is available yet.",
    updated: (t) => `Updated at ${t}`,
    outdated: "Outdoor Brief was updated: reload the page.",
    reload: "Reload",
    colon: ":",
    fishing: "Shore fishing",
    fishingWindow: (s, e, t, c) => `${s}–${e} (LW ${t}, coef ${c})`,
    fishingNext: (d, s, e, c) => `next window ${d} ${s}–${e} (coef ${c})`,
    fishingNone: (t) => `no window at coef ${t} or more within 7 days`,
    sea: "Sea",
    waves: (v) => `waves ${v} m`,
    swell: (d, v, p) => `swell ${d} ${v} m ${p} s`,
    water: (v) => `water ${v} °C`,
    surge: (v) => (v >= 0 ? `estimated surge +${v} cm` : `estimated drop ${v} cm`),
    compass: ["N", "NE", "E", "SE", "S", "SW", "W", "NW"],
    sourceMarine: "SHOM data via Marées France · sea: Open-Meteo.com",
  },
};

// Capteurs « Résumé du jour » : seuls à porter schema_version et le tableau des marées.
const summaryEntities = (hass) =>
  Object.keys(hass?.states || {}).filter((id) => {
    const a = hass.states[id].attributes || {};
    return id.startsWith("sensor.") && a.schema_version !== undefined && Array.isArray(a.tides);
  });

const lang = (hass) => (String(hass?.locale?.language || hass?.language || "en").startsWith("fr") ? "fr" : "en");
const t = (hass) => TEXT[lang(hass)];

// --- Lignes de la 0.4 : pêche à pied et mer (communes à la carte et au rapport) ---------------
const hhmm = (hass, iso) =>
  new Date(iso).toLocaleTimeString(lang(hass), { hour: "2-digit", minute: "2-digit", timeZone: hass?.config?.time_zone });
const num = (hass, v, d) =>
  v === null || v === undefined ? "—" : Number(v).toLocaleString(lang(hass), { minimumFractionDigits: d, maximumFractionDigits: d });

const fishingText = (hass, a) => {
  const tx = t(hass);
  const block = a.fishing;
  if (!block) return null;
  if (block.today && block.today.length) {
    return block.today.map((w) => tx.fishingWindow(hhmm(hass, w.start), hhmm(hass, w.end), hhmm(hass, w.low_tide), w.coefficient)).join(" · ");
  }
  const n = block.next;
  if (n) {
    const day = new Date(n.low_tide).toLocaleDateString(lang(hass), { weekday: "short", day: "numeric", month: "short", timeZone: hass?.config?.time_zone });
    return tx.fishingNext(day, hhmm(hass, n.start), hhmm(hass, n.end), n.coefficient);
  }
  return tx.fishingNone(block.threshold ?? 70);
};

const seaText = (hass, a) => {
  const tx = t(hass);
  const parts = [];
  const m = a.marine;
  if (m) {
    if (m.wave_height !== null && m.wave_height !== undefined) parts.push(tx.waves(num(hass, m.wave_height, 1)));
    if (m.swell_height !== null && m.swell_height !== undefined) {
      const dir = m.swell_direction === null || m.swell_direction === undefined ? "" : tx.compass[Math.round((m.swell_direction % 360) / 45) % 8];
      parts.push(tx.swell(dir, num(hass, m.swell_height, 1), num(hass, m.swell_period, 0)).replace("  ", " "));
    }
    if (m.sea_temperature !== null && m.sea_temperature !== undefined) parts.push(tx.water(num(hass, m.sea_temperature, 1)));
  }
  if (a.surge && a.surge.height_cm !== null && a.surge.height_cm !== undefined) parts.push(tx.surge(a.surge.height_cm));
  return parts.length ? parts.join(" · ") : null;
};

const STYLE = `
  ha-card { padding: 16px; }
  .head { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
  .title { font-size: 1.15em; font-weight: 500; }
  .port { color: var(--secondary-text-color); font-size: .9em; text-align: right; }
  .status { margin: 8px 0 12px; color: var(--primary-text-color); }
  .status .arrow { color: var(--primary-color); font-weight: 600; }
  table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
  th, td { padding: 6px 4px; text-align: left; border-bottom: 1px solid var(--divider-color); }
  th { color: var(--secondary-text-color); font-weight: 500; font-size: .85em; }
  td { white-space: nowrap; }
  td.label { color: var(--secondary-text-color); }
  td.strong { font-weight: 600; }
  tr:last-child td { border-bottom: none; }
  .foot { margin-top: 12px; display: grid; gap: 4px; font-size: .95em; }
  .foot .k { color: var(--secondary-text-color); }
  .source { margin-top: 10px; font-size: .75em; color: var(--secondary-text-color); }
  .warn { color: var(--warning-color, #c77700); overflow-wrap: anywhere; }
  [hidden] { display: none !important; }
`;

const TEMPLATE = `
  <ha-card>
    <div class="head"><span class="title"></span><span class="port"></span></div>
    <div class="warn" hidden></div>
    <div class="body">
      <div class="status"><span class="arrow"></span> <span class="status-text"></span></div>
      <table>
        <thead><tr><th></th><th class="h-am"></th><th class="h-pm"></th></tr></thead>
        <tbody>
          <tr class="r-high"><td class="label"></td><td></td><td></td></tr>
          <tr class="r-low"><td class="label"></td><td></td><td></td></tr>
          <tr class="r-coef"><td class="label"></td><td class="strong"></td><td class="strong"></td></tr>
        </tbody>
      </table>
      <div class="foot">
        <div class="spring"><span class="k"></span> <span class="v"></span></div>
        <div class="month"><span class="k"></span> <span class="v"></span></div>
        <div class="fishing"><span class="k"></span> <span class="v"></span></div>
        <div class="sea"><span class="k"></span> <span class="v"></span></div>
      </div>
      <div class="source"></div>
    </div>
  </ha-card>
`;

class OutdoorBriefCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("outdoor-brief-card-editor");
  }

  static getStubConfig(hass) {
    return { entity: summaryEntities(hass)[0] || "" };
  }

  setConfig(config) {
    if (!config || typeof config !== "object") throw new Error("Invalid configuration");
    this._config = { compact: false, ...config };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return this._config?.compact ? 4 : 6;
  }

  getGridOptions() {
    // Pas de « rows » : la hauteur suit le contenu, sinon le bas est coupé dans les sections.
    return { columns: 12, min_columns: 6 };
  }

  _build() {
    if (this._root) return;
    this._root = this.attachShadow({ mode: "open" });
    const style = document.createElement("style");
    style.textContent = STYLE;
    const tpl = document.createElement("template");
    tpl.innerHTML = TEMPLATE; // gabarit fixe, aucune donnée
    this._root.append(style, tpl.content.cloneNode(true));
    this._$ = (sel) => this._root.querySelector(sel);
  }

  _time(iso) {
    const tz = this._hass?.config?.time_zone;
    return new Date(iso).toLocaleTimeString(lang(this._hass), { hour: "2-digit", minute: "2-digit", timeZone: tz });
  }

  _hour(iso) {
    const tz = this._hass?.config?.time_zone;
    return Number(new Date(iso).toLocaleString("en-GB", { hour: "2-digit", hour12: false, timeZone: tz }));
  }

  _num(value, digits) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
    return Number(value).toLocaleString(lang(this._hass), { minimumFractionDigits: digits, maximumFractionDigits: digits });
  }

  _date(isoDate, opts) {
    // Une date seule (AAAA-MM-JJ) est lue à midi pour ne pas changer de jour selon le fuseau.
    return new Date(`${isoDate}T12:00:00`).toLocaleDateString(lang(this._hass), opts);
  }

  _days(fromIso, toIso) {
    return Math.round((new Date(`${toIso}T12:00:00`) - new Date(`${fromIso}T12:00:00`)) / 86400000);
  }

  _warn(message) {
    this._$(".warn").hidden = !message;
    this._$(".warn").textContent = message || "";
    this._$(".body").hidden = Boolean(message);
  }

  _render() {
    if (!this._config || !this._hass) return;
    this._build();
    const tx = t(this._hass);
    this._$(".title").textContent = tx.title;

    const entityId = this._config.entity;
    if (!entityId) return this._warn(tx.noEntity);
    const state = this._hass.states[entityId];
    if (!state) return this._warn(tx.notFound(entityId));
    const a = state.attributes || {};
    if (state.state === "unavailable" || state.state === "unknown") return this._warn(tx.unavailable);
    if (a.schema_version === undefined || !Array.isArray(a.tides)) return this._warn(tx.notSummary(a.friendly_name || entityId));
    this._warn("");

    this._$(".port").textContent = a.port || "";

    // Ligne d'état : sens de la marée, douzième, marnage, prochain extrême
    const status = this._$(".status");
    status.hidden = Boolean(this._config.compact) || !a.next_tide;
    if (a.next_tide) {
      const rising = a.next_tide.type === "high";
      const parts = [rising ? tx.rising : tx.falling];
      if (a.tide_twelfth) parts.push(tx.twelfth(a.tide_twelfth));
      if (a.tidal_range !== null && a.tidal_range !== undefined) parts.push(`${tx.range} ${this._num(a.tidal_range, 2)} m`);
      parts.push(`${rising ? tx.nextHigh : tx.nextLow} ${this._time(a.next_tide.time)}`);
      this._$(".arrow").textContent = rising ? "↗" : "↘";
      this._$(".status-text").textContent = parts.join(" · ");
    }

    // Tableau : matin (avant midi) / après-midi
    this._$(".h-am").textContent = tx.morning;
    this._$(".h-pm").textContent = tx.afternoon;
    const half = { high: [null, null], low: [null, null] };
    for (const tide of a.tides) {
      if (!half[tide.type]) continue;
      const col = this._hour(tide.time) < 12 ? 0 : 1;
      if (!half[tide.type][col]) half[tide.type][col] = tide;
    }
    const fill = (row, label, cells) => {
      const tds = this._$(row).querySelectorAll("td");
      tds[0].textContent = label;
      cells.forEach((text, i) => (tds[i + 1].textContent = text));
    };
    const cell = (tide) => (tide ? `${this._time(tide.time)} · ${this._num(tide.height, 2)} m` : "—");
    fill(".r-high", tx.high, half.high.map(cell));
    fill(".r-low", tx.low, half.low.map(cell));
    fill(".r-coef", tx.coefficient, half.high.map((tide) => (tide?.coefficient ?? "—").toString()));

    // Pied : prochaine grande marée et plus fort coefficient du mois
    const spring = a.next_spring_tide;
    this._$(".spring .k").textContent = `${tx.spring} :`;
    this._$(".spring .v").textContent = spring
      ? `${this._date(spring.date, { weekday: "short", day: "numeric", month: "short" })}, coef ${spring.coefficient} (${tx.inDays(this._days(a.date, spring.date))})`
      : tx.springNone(a.spring_tide_threshold ?? 100);
    const month = a.month_max;
    this._$(".month").hidden = Boolean(this._config.compact) || !month;
    if (month) {
      this._$(".month .k").textContent = `${tx.monthMax} :`;
      this._$(".month .v").textContent = tx.monthMaxOn(month.coefficient, this._date(month.date, { day: "numeric", month: "short" }));
    }
    // 0.4 : pêche à pied, puis mer (Open-Meteo) et surcote
    for (const [sel, label, text] of [
      [".fishing", tx.fishing, fishingText(this._hass, a)],
      [".sea", tx.sea, seaText(this._hass, a)],
    ]) {
      this._$(sel).hidden = !text;
      this._$(`${sel} .k`).textContent = `${label}${tx.colon}`;
      this._$(`${sel} .v`).textContent = text || "";
    }
    this._$(".source").textContent = a.marine ? tx.sourceMarine : tx.source;
  }
}

class OutdoorBriefCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { ...config };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.addEventListener("value-changed", (ev) => {
        this._config = { ...this._config, ...ev.detail.value };
        this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config }, bubbles: true, composed: true }));
      });
      this.appendChild(this._form);
    }
    const tx = t(this._hass);
    this._form.hass = this._hass;
    this._form.data = this._config;
    this._form.schema = [
      {
        name: "entity",
        required: true,
        selector: { entity: { include_entities: summaryEntities(this._hass), filter: { integration: "outdoor_brief", domain: "sensor" } } },
      },
      { name: "compact", selector: { boolean: {} } },
    ];
    this._form.computeLabel = (s) => (s.name === "entity" ? tx.editorEntity : tx.editorCompact);
  }
}

// --- Rapport du jour (0.3.5) : la reproduction en temps réel de la notification ------------
// Mêmes ports, même ordre et même contenu que l'image envoyée sur le téléphone :
// les ports « regroupés » s'il y en a au moins deux, sinon tous les ports (ou un seul,
// si l'adresse contient ?entry=<id>, comme le lien d'une notification propre à un port).

const REPORT_STYLE = `
  :host { display: block; }
  .report { font-variant-numeric: tabular-nums; }
  .r-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
  .r-title { font-size: 1.5em; font-weight: 500; }
  .r-sun { width: 18px; height: 18px; border-radius: 50%; background: #EF9F27; flex: none; }
  .r-date { color: var(--secondary-text-color); margin: 2px 0 8px; }
  .r-port { font-size: 1.1em; font-weight: 500; margin: 18px 0 4px; }
  .r-status { color: var(--primary-color); font-weight: 500; margin-bottom: 6px; }
  table { width: 100%; border-collapse: collapse; }
  th, td { padding: 8px 4px; text-align: left; border-bottom: 1px solid var(--divider-color); white-space: nowrap; }
  th { color: var(--secondary-text-color); font-weight: 400; font-size: .85em; }
  td.label { color: var(--secondary-text-color); }
  td.value { font-weight: 500; }
  tr:last-child td { border-bottom: none; }
  .r-foot { margin-top: 16px; display: grid; gap: 4px; }
  .r-extra { margin-top: 8px; font-size: .95em; }
  .r-source, .r-updated { margin-top: 10px; font-size: .8em; color: var(--secondary-text-color); }
  .r-empty { color: var(--secondary-text-color); }
`;

const el = (tag, attrs = {}, ...children) => {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "text") node.textContent = value;
    else if (key === "class") node.className = value;
    else node.setAttribute(key, value);
  }
  for (const child of children) if (child) node.append(child);
  return node;
};

// Résumés à afficher, dans l'ordre de la notification
const reportSummaries = (hass, onlyEntry) => {
  const all = summaryEntities(hass)
    .map((id) => hass.states[id].attributes)
    .filter((a) => a && a.report)
    .sort((a, b) => a.report.rank - b.report.rank);
  if (onlyEntry) return all.filter((a) => a.report.entry_id === onlyEntry);
  const grouped = all.filter((a) => a.report.grouped);
  return grouped.length >= 2 ? grouped : all;
};

const fmtTime = (hass, iso) =>
  new Date(iso).toLocaleTimeString(lang(hass), { hour: "2-digit", minute: "2-digit", timeZone: hass?.config?.time_zone });
const fmtNum = (hass, v, d = 2) =>
  v === null || v === undefined ? "—" : Number(v).toLocaleString(lang(hass), { minimumFractionDigits: d, maximumFractionDigits: d });
const fmtDay = (hass, iso, opts) => new Date(`${iso}T12:00:00`).toLocaleDateString(lang(hass), opts);
const hourOf = (hass, iso) =>
  Number(new Date(iso).toLocaleString("en-GB", { hour: "2-digit", hour12: false, timeZone: hass?.config?.time_zone }));

const statusText = (hass, a) => {
  const tx = t(hass);
  if (!a.next_tide) return "";
  const rising = a.next_tide.type === "high";
  const parts = [rising ? tx.rising : tx.falling];
  if (a.tide_twelfth) parts.push(tx.twelfth(a.tide_twelfth));
  if (a.tidal_range !== null && a.tidal_range !== undefined) parts.push(`${tx.range} ${fmtNum(hass, a.tidal_range)} m`);
  parts.push(`${rising ? tx.nextHigh : tx.nextLow} ${fmtTime(hass, a.next_tide.time)}`);
  return parts.join(" · ");
};

const portTable = (hass, a) => {
  const tx = t(hass);
  const half = { high: [null, null], low: [null, null] };
  for (const tide of a.tides || []) {
    if (!half[tide.type]) continue;
    const col = hourOf(hass, tide.time) < 12 ? 0 : 1;
    if (!half[tide.type][col]) half[tide.type][col] = tide;
  }
  const cell = (tide) => (tide ? `${fmtTime(hass, tide.time)} · ${fmtNum(hass, tide.height)} m` : "—");
  const row = (label, values) =>
    el("tr", {}, el("td", { class: "label", text: label }), ...values.map((v) => el("td", { class: "value", text: v })));
  return el(
    "table",
    {},
    el("thead", {}, el("tr", {}, el("th"), el("th", { text: tx.morning }), el("th", { text: tx.afternoon }))),
    el(
      "tbody",
      {},
      row(tx.high, half.high.map(cell)),
      row(tx.low, half.low.map(cell)),
      row(tx.coefficient, half.high.map((tide) => String(tide?.coefficient ?? "—"))),
    ),
  );
};

// Construit tout le rapport ; aucune donnée n'est insérée en HTML (textContent seulement).
const buildReport = (hass, summaries) => {
  const tx = t(hass);
  const root = el("div", { class: "report" });
  root.append(el("div", { class: "r-head" }, el("span", { class: "r-title", text: tx.title }), el("span", { class: "r-sun" })));
  if (!summaries.length) {
    root.append(el("p", { class: "r-empty", text: tx.noReport }));
    return root;
  }
  const first = summaries[0];
  const multi = summaries.length > 1;
  const day = fmtDay(hass, first.date, { weekday: "long", day: "numeric", month: "long" });
  root.append(el("div", { class: "r-date", text: multi ? day : `${first.port} · ${day}` }));
  for (const a of summaries) {
    if (multi) root.append(el("div", { class: "r-port", text: a.port }));
    const status = statusText(hass, a);
    if (status) root.append(el("div", { class: "r-status", text: status }));
    root.append(portTable(hass, a));
    for (const [label, text] of [[tx.fishing, fishingText(hass, a)], [tx.sea, seaText(hass, a)]]) {
      if (text) root.append(el("div", { class: "r-extra", text: `${label}${tx.colon} ${text}` }));
    }
  }
  const foot = el("div", { class: "r-foot" });
  const spring = first.next_spring_tide;
  foot.append(
    el(
      "div",
      { text: spring
        ? `${tx.spring} : ${fmtDay(hass, spring.date, { weekday: "short", day: "numeric", month: "short" })}, coef ${spring.coefficient} (${tx.inDays(Math.round((new Date(`${spring.date}T12:00:00`) - new Date(`${first.date}T12:00:00`)) / 86400000))})`
        : tx.springNone(first.spring_tide_threshold ?? 100) },
    ),
  );
  if (first.month_max) {
    foot.append(el("div", { text: `${tx.monthMax} : ${tx.monthMaxOn(first.month_max.coefficient, fmtDay(hass, first.month_max.date, { day: "numeric", month: "short" }))}` }));
  }
  const source = summaries.some((a) => a.marine) ? tx.sourceMarine : tx.source;
  root.append(foot, el("div", { class: "r-source", text: source }));
  return root;
};

// Signature du contenu : on ne reconstruit le DOM que si le rapport a changé.
const signature = (hass, summaries) => JSON.stringify([lang(hass), summaries]);

class OutdoorBriefReportCard extends HTMLElement {
  static getStubConfig() {
    return {};
  }

  setConfig(config) {
    this._config = { ...(config || {}) };
    this._sig = null;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 10;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6 };
  }

  _render() {
    if (!this._hass || !this._config) return;
    if (!this._root) {
      this._root = this.attachShadow({ mode: "open" });
      const style = el("style", { text: REPORT_STYLE });
      this._card = el("ha-card");
      this._card.style.padding = "16px";
      this._root.append(style, this._card);
    }
    const summaries = reportSummaries(this._hass, this._config.entry);
    const sig = signature(this._hass, summaries);
    if (sig === this._sig) return;
    this._sig = sig;
    this._card.replaceChildren(buildReport(this._hass, summaries));
  }
}

// Panneau /outdoor-brief : tableau de bord dédié, pensé pour le téléphone.
class OutdoorBriefPanel extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  set narrow(value) {
    this._narrow = value;
    if (this._menu) this._menu.narrow = value;
  }

  set panel(value) {
    this._panel = value;
    this._checkVersion(value?.config?.version);
  }

  connectedCallback() {
    this._render();
  }

  // Après une mise à jour, le navigateur garde l'ancien module tant que la page n'est pas
  // rechargée : on recharge une fois tout seul, sinon un bandeau le propose.
  _checkVersion(serverVersion) {
    this._outdated = Boolean(serverVersion && serverVersion !== CARD_VERSION);
    if (!this._outdated) return;
    const key = `outdoor-brief-reloaded-${serverVersion}`;
    let tried = true;
    try {
      tried = sessionStorage.getItem(key) === "1";
      if (!tried) sessionStorage.setItem(key, "1");
    } catch (_err) {
      tried = true;
    }
    if (!tried) window.location.reload();
  }

  _render() {
    if (!this._hass) return;
    const tx = t(this._hass);
    if (!this._root) {
      this._root = this.attachShadow({ mode: "open" });
      const style = el("style", {
        text: `${REPORT_STYLE}
          :host { background: var(--primary-background-color); min-height: 100vh; color: var(--primary-text-color); }
          .bar { display: flex; align-items: center; gap: 4px; height: 56px; padding: 0 8px;
                 background: var(--app-header-background-color, var(--primary-color));
                 color: var(--app-header-text-color, white); font-size: 20px; }
          .page { max-width: 720px; margin: 0 auto; padding: 16px; }
          ha-card { padding: 16px; }
          .banner { background: var(--warning-color, #c77700); color: white; padding: 10px 16px; display: flex; justify-content: space-between; align-items: center; }
          .banner button { background: transparent; color: white; border: 1px solid white; border-radius: 6px; padding: 4px 10px; }
          [hidden] { display: none !important; }`,
      });
      this._menu = document.createElement("ha-menu-button");
      this._menu.narrow = this._narrow;
      this._banner = el("div", { class: "banner" });
      this._card = el("ha-card");
      this._updated = el("div", { class: "r-updated" });
      this._root.append(
        style,
        el("div", { class: "bar" }, this._menu, el("span", { text: "Outdoor Brief" })),
        this._banner,
        el("div", { class: "page" }, this._card, this._updated),
      );
    }
    this._menu.hass = this._hass;
    this._banner.hidden = !this._outdated;
    if (this._outdated && !this._banner.childNodes.length) {
      const button = el("button", { text: tx.reload });
      button.addEventListener("click", () => window.location.reload());
      this._banner.append(el("span", { text: tx.outdated }), button);
    }
    const entry = new URLSearchParams(window.location.search).get("entry");
    const summaries = reportSummaries(this._hass, entry);
    const sig = signature(this._hass, summaries);
    if (sig === this._sig) return;
    this._sig = sig;
    this._card.replaceChildren(buildReport(this._hass, summaries));
    this._updated.textContent = tx.updated(new Date().toLocaleTimeString(lang(this._hass), { hour: "2-digit", minute: "2-digit" }));
  }
}

if (!customElements.get("outdoor-brief-card")) customElements.define("outdoor-brief-card", OutdoorBriefCard);
if (!customElements.get("outdoor-brief-card-editor")) customElements.define("outdoor-brief-card-editor", OutdoorBriefCardEditor);
if (!customElements.get("outdoor-brief-report-card")) customElements.define("outdoor-brief-report-card", OutdoorBriefReportCard);
if (!customElements.get("outdoor-brief-panel")) customElements.define("outdoor-brief-panel", OutdoorBriefPanel);

window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "outdoor-brief-card")) {
  const tx = TEXT[String(navigator.language || "en").startsWith("fr") ? "fr" : "en"];
  window.customCards.push({
    type: "outdoor-brief-card",
    name: tx.pickerName,
    description: tx.pickerDesc,
    preview: true,
    documentationURL: "https://github.com/systemedomotiqueresilient/ha-outdoor-brief",
  });
}
if (!window.customCards.some((c) => c.type === "outdoor-brief-report-card")) {
  const tx = TEXT[String(navigator.language || "en").startsWith("fr") ? "fr" : "en"];
  window.customCards.push({
    type: "outdoor-brief-report-card",
    name: tx.reportName,
    description: tx.reportDesc,
    preview: true,
    documentationURL: "https://github.com/systemedomotiqueresilient/ha-outdoor-brief",
  });
}

console.info(`%c OUTDOOR-BRIEF-CARD %c v${CARD_VERSION} `, "color:#112630;background:#9FE1CB;font-weight:600", "color:#112630;background:#EF9F27");
