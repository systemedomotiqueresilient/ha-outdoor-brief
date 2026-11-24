// Outdoor Brief : carte Lovelace du résumé du jour.
// JavaScript sans dépendance. Aucune valeur venant d'une entité n'est insérée en HTML :
// le gabarit est fixe et les données passent par textContent.

const CARD_VERSION = "0.3.4";

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
    this._$(".source").textContent = tx.source;
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

if (!customElements.get("outdoor-brief-card")) customElements.define("outdoor-brief-card", OutdoorBriefCard);
if (!customElements.get("outdoor-brief-card-editor")) customElements.define("outdoor-brief-card-editor", OutdoorBriefCardEditor);

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

console.info(`%c OUTDOOR-BRIEF-CARD %c v${CARD_VERSION} `, "color:#112630;background:#9FE1CB;font-weight:600", "color:#112630;background:#EF9F27");
