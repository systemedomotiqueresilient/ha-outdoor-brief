# Outdoor Brief

**English** · [Français](README.fr.md)

The **daily brief for what happens outdoors**, in Home Assistant. Version 0.2 covers the coast: today's tides, tidal range, the current tide twelfth and the next spring tide, gathered in a single summary sensor and shown by a Lovelace card. A phone notification comes next.

> **Status: 0.2.0, early development.** Visual notifications (0.3), marine weather (0.4) and the garden profile (0.5) are on the [roadmap](ROADMAP.md).

## Where the data comes from

Outdoor Brief **does not fetch tides from the Internet**. It reads them from the [Marées France](https://github.com/KipK/marees_france) integration (SHOM data), which must be installed first, through its actions `marees_france.get_tides_data` and `marees_france.get_coefficients_data`. Everything else is computed locally.

## Installation

1. Install **Marées France** and add at least one port.
2. With HACS (custom repository): add `https://github.com/systemedomotiqueresilient/ha-outdoor-brief`, category *Integration*, install, restart.
3. Add the **Outdoor Brief** integration: choose the profile, then the Marées France port, then the settings. Add one entry per port.

## Entities (0.1)

| Entity | State | Main attributes |
|---|---|---|
| Daily summary | today's date | `schema_version`, `port`, `tides` (4 tides: type, time, height, coefficient), `coefficients`, `tidal_range`, `tide_twelfth`, `next_tide`, `next_spring_tide`, `month_max` |
| Tidal range | metres, current half-tide | |
| Tide twelfth | 1 to 6 | `trend`, `range_share`, `started_at`, `ends_at`, `duration_minutes` |
| Next spring tide | date | `coefficient`, `threshold`, `upcoming` |
| Admin phone | notify target | `notify_service` (common SDR convention) |

The tidal range and the twelfth are recomputed every 5 minutes; Marées France is read again every hour. The **spring tide threshold** (100 by default) can be changed in the options: December 2026, for instance, peaks at 99.

## Lovelace card

The `outdoor-brief-card` card ships with the integration and loads automatically. Add it from *Add card* (search "Outdoor Brief"), or in YAML:

```yaml
type: custom:outdoor-brief-card
entity: sensor.outdoor_brief_my_port_daily_summary  # your "Daily summary" sensor
compact: false
```

It shows the tide trend and twelfth, a morning/afternoon table of high and low tides with coefficients, the next spring tide and the month's highest coefficient. `compact: true` keeps only the table and the next spring tide. After an update, reload the page once if the card still shows the previous version.

## About the garden profile

This integration only provides measurable astronomical and weather data. Lunar gardening calendars (ascending/descending moon, root, leaf, flower and fruit days) rely on conventions that differ from one almanac to another. They are not included, so as not to impose one of them.

## For developers

Outdoor Brief is meant to be built upon, for example by a lunar gardening calendar.

- **Stable contract**: the `unique_id` of each entity (`<entry_id>_<key>`) and the attributes listed above. The summary carries a `schema_version` field.
- **Versioning**: semantic versioning. An attribute is renamed or removed only in a major version, after at least one version where it is flagged as deprecated.
- **Coming**: the moon's declination and ecliptic longitude (0.5), the raw material of any gardening almanac, and events (`outdoor_brief_daily_summary`, `outdoor_brief_spring_tide_upcoming`…) from 0.3.

A lunar gardening calendar integration can be built on top of this one: open an issue so we can list it here.

## License

MIT. Tide data: SHOM, via Marées France.
