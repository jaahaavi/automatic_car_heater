/*
 * Automatic Car Heater Timer — Lovelace card + visual editor
 *
 * Companion UI for the `car_heater` custom integration. All logic runs
 * server-side in the integration; this card only reads its entities and calls
 * standard Home Assistant services.
 *
 * The integration auto-registers this file as a frontend resource, so no manual
 * resource setup is needed. Add via the dashboard card picker ("Automatic Car
 * Heater Timer") or in YAML:
 *
 *   type: custom:car-heater-card
 *   # prefix: car_heater_garage   # optional — auto-detected if omitted
 *   # name: Garage car heater     # optional title override
 */

const WEEKDAYS = [
  { key: "mon", label: "Mon" },
  { key: "tue", label: "Tue" },
  { key: "wed", label: "Wed" },
  { key: "thu", label: "Thu" },
  { key: "fri", label: "Fri" },
  { key: "sat", label: "Sat" },
  { key: "sun", label: "Sun" },
];

/** Find all car_heater instances present in hass.states. */
function detectInstances(hass) {
  const out = [];
  const states = hass ? hass.states : {};
  for (const id of Object.keys(states)) {
    if (!id.startsWith("binary_sensor.")) continue;
    const attrs = states[id].attributes || {};
    if (attrs.integration === "car_heater" && attrs.prefix) {
      out.push({ prefix: attrs.prefix, name: attrs.device_name || attrs.prefix });
    }
  }
  return out;
}

class CarHeaterCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._built = false;
    this._expanded = false;
    this._config = {};
  }

  setConfig(config) {
    this._config = config || {};
  }

  getCardSize() {
    return this._expanded ? 7 : 4;
  }

  static getConfigElement() {
    return document.createElement("car-heater-card-editor");
  }

  static getStubConfig(hass) {
    const found = detectInstances(hass);
    return found.length ? { prefix: found[0].prefix } : {};
  }

  set hass(hass) {
    this._hass = hass;
    this._resolvePrefix();
    if (!this._built) this._build();
    this._update();
  }

  // ------------------------------------------------------------------
  // Entity resolution
  // ------------------------------------------------------------------
  _resolvePrefix() {
    if (this._config.prefix) {
      this._prefix = this._config.prefix;
      return;
    }
    const found = detectInstances(this._hass);
    this._prefix = found.length ? found[0].prefix : null;
  }

  _entities() {
    const p = this._prefix;
    return {
      status: `binary_sensor.${p}_heating`,
      nextReady: `sensor.${p}_next_ready`,
      nextStart: `sensor.${p}_next_start`,
      schedule: `switch.${p}_schedule`,
      manual: `switch.${p}_manual`,
      readyTime: `time.${p}_ready_time`,
      weekdays: `text.${p}_weekdays`,
    };
  }

  _statusAttrs() {
    const st = this._hass.states[this._entities().status];
    return st ? st.attributes || {} : {};
  }

  // ------------------------------------------------------------------
  // Rendering (build once, update on every hass push)
  // ------------------------------------------------------------------
  _build() {
    const style = document.createElement("style");
    style.textContent = `
      ha-card { padding: 16px; }
      .title { font-size: 1.3rem; font-weight: 600; margin-bottom: 12px; }
      .status {
        display: flex; align-items: center; gap: 14px; margin-bottom: 14px;
      }
      .status ha-icon { --mdc-icon-size: 40px; }
      .status.on ha-icon { color: var(--state-active-color, #ff9800); }
      .status.off ha-icon { color: var(--disabled-text-color, #9e9e9e); }
      .status .headline { font-size: 1.25rem; font-weight: 600; }
      .status .sub { color: var(--secondary-text-color); font-size: 0.9rem; }
      .rows { display: grid; gap: 8px; margin-bottom: 14px; }
      .row { display: flex; justify-content: space-between; gap: 12px; }
      .row .k { color: var(--secondary-text-color); }
      .row .v { font-weight: 500; text-align: right; }
      .actions { display: flex; gap: 10px; flex-wrap: wrap; }
      button.btn {
        flex: 1 1 auto; min-width: 130px; cursor: pointer;
        border: none; border-radius: 12px; padding: 12px 14px;
        font-size: 0.95rem; font-weight: 600;
        background: var(--secondary-background-color); color: var(--primary-text-color);
      }
      button.btn.primary { background: var(--primary-color); color: var(--text-primary-color, #fff); }
      button.btn.active { background: var(--state-active-color, #ff9800); color: #fff; }
      .panel {
        margin-top: 14px; padding-top: 14px;
        border-top: 1px solid var(--divider-color);
        display: none;
      }
      .panel.open { display: block; }
      .panel h3 { margin: 0 0 8px; font-size: 1rem; }
      .days { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 16px; }
      .day {
        cursor: pointer; border: 1px solid var(--divider-color);
        border-radius: 999px; padding: 8px 12px; font-weight: 600;
        background: transparent; color: var(--primary-text-color);
      }
      .day.sel { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: var(--primary-color); }
      .field { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; gap: 12px; }
      .field label { color: var(--secondary-text-color); }
      .schedule-row {
        border-top: 1px solid var(--divider-color);
        padding-top: 12px;
      }
      input[type="time"] {
        font-size: 1rem; padding: 8px; border-radius: 8px;
        border: 1px solid var(--divider-color);
        background: var(--card-background-color); color: var(--primary-text-color);
      }
      .warn { color: var(--error-color); padding: 8px 0; }
      .switch { position: relative; width: 46px; height: 26px; }
      .switch input { opacity: 0; width: 0; height: 0; }
      .slider {
        position: absolute; inset: 0; cursor: pointer; border-radius: 26px;
        background: var(--disabled-text-color, #9e9e9e); transition: 0.2s;
      }
      .slider::before {
        content: ""; position: absolute; height: 20px; width: 20px; left: 3px; top: 3px;
        background: #fff; border-radius: 50%; transition: 0.2s;
      }
      .switch input:checked + .slider { background: var(--primary-color); }
      .switch input:checked + .slider::before { transform: translateX(20px); }
    `;

    const card = document.createElement("ha-card");
    card.innerHTML = `
      <div class="content">
        <div class="title" id="title"></div>
        <div class="warn" id="warn" style="display:none"></div>
        <div class="status" id="status">
          <ha-icon id="statusIcon"></ha-icon>
          <div>
            <div class="headline" id="statusText"></div>
            <div class="sub" id="statusSub"></div>
          </div>
        </div>
        <div class="rows">
          <div class="row"><span class="k">Next ready</span><span class="v" id="nextReady">—</span></div>
          <div class="row"><span class="k">Heating starts</span><span class="v" id="nextStart">—</span></div>
        </div>
        <div class="field schedule-row">
          <label for="scheduleToggle">Schedule enabled</label>
          <span class="switch">
            <input type="checkbox" id="scheduleToggle" />
            <span class="slider" id="scheduleSlider"></span>
          </span>
        </div>
        <div class="actions">
          <button class="btn" id="manualBtn"></button>
          <button class="btn" id="configBtn">Configure leaving time</button>
        </div>
        <div class="panel" id="panel">
          <h3>Days the car must be ready</h3>
          <div class="days" id="days"></div>
          <div class="field">
            <label for="readyInput">Ready by</label>
            <input type="time" id="readyInput" />
          </div>
        </div>
      </div>
    `;

    this.shadowRoot.append(style, card);

    this._el = {
      title: card.querySelector("#title"),
      warn: card.querySelector("#warn"),
      status: card.querySelector("#status"),
      statusIcon: card.querySelector("#statusIcon"),
      statusText: card.querySelector("#statusText"),
      statusSub: card.querySelector("#statusSub"),
      nextReady: card.querySelector("#nextReady"),
      nextStart: card.querySelector("#nextStart"),
      manualBtn: card.querySelector("#manualBtn"),
      configBtn: card.querySelector("#configBtn"),
      panel: card.querySelector("#panel"),
      days: card.querySelector("#days"),
      readyInput: card.querySelector("#readyInput"),
      scheduleToggle: card.querySelector("#scheduleToggle"),
    };

    for (const d of WEEKDAYS) {
      const chip = document.createElement("button");
      chip.className = "day";
      chip.textContent = d.label;
      chip.dataset.key = d.key;
      chip.addEventListener("click", () => this._toggleDay(d.key));
      this._el.days.appendChild(chip);
    }

    this._el.configBtn.addEventListener("click", () => {
      this._expanded = !this._expanded;
      this._el.panel.classList.toggle("open", this._expanded);
    });
    this._el.manualBtn.addEventListener("click", () => this._toggleManual());
    this._el.readyInput.addEventListener("change", (e) =>
      this._setReadyTime(e.target.value)
    );
    this._el.scheduleToggle.addEventListener("change", (e) =>
      this._setSchedule(e.target.checked)
    );

    this._built = true;
  }

  _update() {
    if (!this._el) return;
    const e = this._el;

    e.title.textContent =
      this._config.name || this._statusAttrs().device_name || "Car heater timer";

    if (!this._prefix || !this._hass.states[this._entities().status]) {
      e.warn.style.display = "block";
      e.warn.textContent =
        "No car heater instance found. Set up the 'Automatic Car Heater Timer' integration, or set `prefix:` in the card config.";
      return;
    }
    e.warn.style.display = "none";

    const ent = this._entities();
    const a = this._statusAttrs();
    const on = this._hass.states[ent.status].state === "on";

    e.status.classList.toggle("on", on);
    e.status.classList.toggle("off", !on);
    e.statusIcon.setAttribute("icon", on ? "mdi:car-defrost-front" : "mdi:car");
    e.statusText.textContent = on ? "Heating" : "Idle";

    const temp = a.outside_temperature;
    const dur = a.heating_duration;
    const parts = [];
    if (temp !== null && temp !== undefined) parts.push(`${temp}°C outside`);
    if (a.heating_needed !== false && dur) parts.push(`${dur} min heating`);
    if (a.manual_active) parts.push("manual heating");
    e.statusSub.textContent = parts.join(" · ");

    if (!a.schedule_enabled) {
      e.nextReady.textContent = "Schedule off";
      e.nextStart.textContent = "—";
    } else {
      e.nextReady.textContent = this._fmt(a.next_ready);
      e.nextStart.textContent =
        a.heating_needed === false
          ? "Not needed — warm enough"
          : this._fmt(a.next_start);
    }

    if (a.manual_active) {
      e.manualBtn.textContent = `Stop heating (${this._remaining(a.manual_until)})`;
      e.manualBtn.classList.add("active");
      e.manualBtn.classList.remove("primary");
    } else {
      e.manualBtn.textContent = "Manual heating 2 h";
      e.manualBtn.classList.add("primary");
      e.manualBtn.classList.remove("active");
    }

    const days = a.weekdays || [];
    for (const chip of e.days.querySelectorAll(".day")) {
      chip.classList.toggle("sel", days.includes(chip.dataset.key));
    }
    if (document.activeElement !== e.readyInput && a.ready_time) {
      e.readyInput.value = a.ready_time;
    }
    if (document.activeElement !== e.scheduleToggle) {
      e.scheduleToggle.checked = !!a.schedule_enabled;
    }
    e.panel.classList.toggle("open", this._expanded);
  }

  // ------------------------------------------------------------------
  // Actions
  // ------------------------------------------------------------------
  _toggleManual() {
    const ent = this._entities();
    const on = this._statusAttrs().manual_active;
    this._hass.callService("switch", on ? "turn_off" : "turn_on", {
      entity_id: ent.manual,
    });
  }

  _toggleDay(key) {
    const current = new Set(this._statusAttrs().weekdays || []);
    if (current.has(key)) current.delete(key);
    else current.add(key);
    const ordered = WEEKDAYS.filter((d) => current.has(d.key)).map((d) => d.key);
    this._hass.callService("text", "set_value", {
      entity_id: this._entities().weekdays,
      value: ordered.join(","),
    });
  }

  _setReadyTime(value) {
    if (!value) return;
    const time = value.length === 5 ? `${value}:00` : value;
    this._hass.callService("time", "set_value", {
      entity_id: this._entities().readyTime,
      time,
    });
  }

  _setSchedule(enabled) {
    this._hass.callService("switch", enabled ? "turn_on" : "turn_off", {
      entity_id: this._entities().schedule,
    });
  }

  // ------------------------------------------------------------------
  // Formatting helpers
  // ------------------------------------------------------------------
  _localeCode() {
    return (this._hass && this._hass.locale && this._hass.locale.language) || undefined;
  }

  _hour12() {
    // Honor the user's Home Assistant time-format profile setting.
    // HA stores this as "24" / "12" (enum values), not the member names.
    const tf = this._hass && this._hass.locale && this._hass.locale.time_format;
    if (tf === "24" || tf === "twenty_four") return false;
    if (tf === "12" || tf === "am_pm") return true;
    return undefined; // 'language' / 'system' — let the locale decide
  }

  _fmt(iso) {
    if (!iso) return "—";
    const d = new Date(iso);
    if (isNaN(d)) return "—";
    const loc = this._localeCode();
    const timeOpts = { hour: "2-digit", minute: "2-digit" };
    const h12 = this._hour12();
    if (h12 !== undefined) timeOpts.hour12 = h12;
    const now = new Date();
    const sameDay = d.toDateString() === now.toDateString();
    const time = d.toLocaleTimeString(loc, timeOpts);
    const day = sameDay
      ? "Today"
      : d.toLocaleDateString(loc, { weekday: "short", day: "numeric", month: "short" });
    return `${day} ${time} (${this._remaining(iso)})`;
  }

  _remaining(iso) {
    if (!iso) return "";
    const diffMs = new Date(iso).getTime() - Date.now();
    if (isNaN(diffMs)) return "";
    const past = diffMs < 0;
    let mins = Math.round(Math.abs(diffMs) / 60000);
    const h = Math.floor(mins / 60);
    mins = mins % 60;
    const txt = h > 0 ? `${h} h ${mins} min` : `${mins} min`;
    return past ? `${txt} ago` : `in ${txt}`;
  }
}

if (!customElements.get("car-heater-card")) {
  customElements.define("car-heater-card", CarHeaterCard);
}

/* ------------------------------------------------------------------ */
/* Visual editor                                                       */
/* ------------------------------------------------------------------ */
class CarHeaterCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { ...config };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _schema() {
    const instances = detectInstances(this._hass);
    const options = [
      { value: "", label: "Auto-detect (first instance)" },
      ...instances.map((i) => ({ value: i.prefix, label: `${i.name} (${i.prefix})` })),
    ];
    return [
      {
        name: "prefix",
        selector: {
          select: { options, mode: "dropdown", custom_value: true },
        },
      },
      { name: "name", selector: { text: {} } },
    ];
  }

  _labels(schema) {
    return { prefix: "Car heater instance", name: "Title (optional)" }[schema.name];
  }

  _render() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (s) => this._labels(s);
      this._form.addEventListener("value-changed", (e) => this._valueChanged(e));
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.schema = this._schema();
    // ha-form works best with defined keys.
    this._form.data = {
      prefix: this._config.prefix || "",
      name: this._config.name || "",
    };
  }

  _valueChanged(ev) {
    ev.stopPropagation();
    const value = ev.detail.value || {};
    const config = { type: "custom:car-heater-card" };
    if (value.prefix) config.prefix = value.prefix;
    if (value.name) config.name = value.name;
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config },
        bubbles: true,
        composed: true,
      })
    );
  }
}

if (!customElements.get("car-heater-card-editor")) {
  customElements.define("car-heater-card-editor", CarHeaterCardEditor);
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: "car-heater-card",
  name: "Automatic Car Heater Timer",
  description:
    "Schedule and monitor an automatic car heater; heating time adapts to the outside temperature.",
  preview: false,
  documentationURL: "https://github.com/your-name/automatic_car_heater",
});

console.info(
  "%c CAR-HEATER-CARD %c 1.2.2 ",
  "color: white; background: #ff9800; font-weight: 700;",
  "color: #ff9800; background: white; font-weight: 700;"
);
