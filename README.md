# Automatic Car Heater Timer

A Home Assistant **custom integration** + **Lovelace card** that turns a car
(block/cabin) heater on ahead of your leaving time, with the heating duration
scaled to the outside temperature.

The integration runs all logic **server-side**, so the heater switches on at the
right time whether or not any dashboard is open. The card is only the UI.

---

## Features

- Configured at setup: **outside temperature sensor** + **heater switch**.
- Optional parameters (with defaults): **min temp** `+5 °C`, **max temp** `-20 °C`,
  **min time** `30 min`, **max time** `120 min`, plus an **off delay** `15 min`.
- Card elements:
  - **Status** — heating / idle (plus outside temp and computed duration).
  - **Next ready** and **heating starts** times.
  - **Manual boost** — heat now for 2 hours, then auto-off.
  - **Configure leaving time** — weekday selection (Mon–Sun), a "ready by" time,
    and an enable/disable toggle (turn off for holidays).

### Heating time vs. temperature

| Outside temp | Heating time |
|---|---|
| ≥ +5 °C | 30 min (min time) |
| 0 °C | 48 min |
| −10 °C | 84 min |
| ≤ −20 °C | 120 min (max time, capped) |

Between `min_temp` and `max_temp` the time is interpolated linearly:

```
duration = min_time + (max_time − min_time) × (min_temp − temp) / (min_temp − max_temp)
```

Below `max_temp` the time stays at `max_time`. If the temperature sensor is
unavailable, the maximum time is used (fail-safe).

### Timing

- Heating turns **on** at `ready_time − duration`.
- Heating stays **on** until `ready_time + off_delay` (default 15 min) so a late
  start doesn't let the car refreeze.
- **Manual boost** forces heating on for 2 hours regardless of the schedule and
  works even when the schedule is disabled.

---

## Installation

### Via HACS (recommended)

1. HACS → ⋮ → **Custom repositories** → add this repo's URL, category **Integration**.
2. Install **Automatic Car Heater Timer**, then **restart Home Assistant**.
3. Continue with **Set up the integration** below.

The Lovelace card is bundled with the integration and **auto-registered as a
Lovelace resource** once you add an instance — you do not need to add a dashboard
resource manually. (In YAML-mode dashboards it is loaded via script injection
instead; add `/car_heater_frontend/car-heater-card.js` as a `module` resource in
your `lovelace:` config if you prefer.)

### Manual

Copy `custom_components/car_heater/` into your Home Assistant `config/custom_components/`
directory, so you end up with `config/custom_components/car_heater/manifest.json`,
then **restart Home Assistant**. The card is registered automatically as above.

### Set up the integration

Add it via **Settings → Devices & Services → Add Integration → "Automatic Car
Heater Timer"**. Pick the temperature sensor and the heater switch, adjust the
parameters if you like, and submit. Parameters can be changed later via the
integration's **Configure** button.

The integration creates these entities (prefix = `car_heater_<name>`, e.g.
`car_heater_garage`):

| Entity | Purpose |
|---|---|
| `binary_sensor.<prefix>_heating` | Status (carries all display data as attributes) |
| `sensor.<prefix>_next_ready` | Next ready-to-go time |
| `sensor.<prefix>_next_start` | Next heating start time |
| `switch.<prefix>_schedule` | Enable/disable the schedule (holiday toggle) |
| `switch.<prefix>_manual` | 2-hour manual boost |
| `time.<prefix>_ready_time` | "Ready by" time of day |
| `text.<prefix>_weekdays` | Selected weekdays (CSV, e.g. `mon,tue,wed,thu,fri`) |

### Add the card

Edit a dashboard → **Add card** → search **"Automatic Car Heater Timer"**. A
**visual editor** lets you pick the instance and an optional title. Or use YAML:

```yaml
type: custom:car-heater-card
# prefix: car_heater_garage   # optional — auto-detected if you have one instance
# name: Garage car heater     # optional title override
```

With a single instance the card auto-detects everything. For multiple cars, set
`prefix:` to the object-id prefix of the instance you want.

> The card is registered as a Lovelace resource when the integration starts, so
> it loads on every device (including the phone app). After first install, do one
> full refresh per device (close all HA tabs / restart the app) so the new
> resource is picked up. Remove any old manual resource pointing at
> `/local/car-heater-card.js` — that path is no longer used.

---

## Notes

- The heater is driven with `homeassistant.turn_on` / `homeassistant.turn_off`,
  so a `switch` or an `input_boolean` both work as the output.
- Runtime state (weekdays, ready time, schedule toggle, active boost) is persisted
  and survives restarts.
- The integration re-evaluates every 30 seconds and immediately on temperature or
  switch changes.
- Multiple cars: add the integration once per car (each gets its own entities and
  card).

---

## Publishing to HACS

This repo is set up as a **single HACS integration** that also ships the card, so
users install one thing. Checklist:

### Repository basics
- Public GitHub repository.
- A repo **description** and a few **topics** (e.g. `home-assistant`, `hacs`, `car-heater`).
- `README.md` in the root (this file).
- `hacs.json` in the root — already present (`name`, `content_in_root: false`,
  minimum `homeassistant` version).
- Not archived; issues enabled (used for `issue_tracker`).

### Integration requirements
- Code lives under `custom_components/car_heater/`.
- `manifest.json` includes the HACS/hassfest-required keys, with **`version`**
  (HACS needs it), `documentation`, `issue_tracker`, and `codeowners`
  (set `codeowners` to your GitHub handle, e.g. `["@your-name"]`).
- Keys after `domain`/`name` are alphabetical (hassfest requirement).

### Before you publish — replace placeholders
- In `manifest.json`: `documentation`, `issue_tracker` URLs and `codeowners`.
- In `custom_components/car_heater/frontend/car-heater-card.js`: `documentationURL`.

### Validation (CI)
`.github/workflows/validate.yml` runs the two checks HACS wants green:
- **hassfest** (`home-assistant/actions/hassfest`) — validates the manifest.
- **HACS Action** (`hacs/action` with `category: integration`) — validates repo
  structure.

### Releases
- Create a GitHub **release** with a version tag (e.g. `v1.0.0`) matching
  `manifest.json`'s `version`. HACS installs the latest release by default.
- Bump `version` in both `manifest.json` and `const.py` (`VERSION`, used for the
  card's cache-busting URL) on each release.

### Two ways users install
- **Now:** HACS → Custom repositories → add your URL as category *Integration*.
- **Later (optional):** to appear in the default HACS store without "custom
  repositories", submit a PR to [`hacs/default`](https://github.com/hacs/default)
  and add your integration's brand (icon/logo) to
  [`home-assistant/brands`](https://github.com/home-assistant/brands). Both must
  pass their PR checks; the brands entry is required for default-store integrations.

> Note: HACS treats each repo as **one** category. Because the card is bundled
> inside the integration and auto-registered, you don't need a second
> "plugin/dashboard" repo for it.
