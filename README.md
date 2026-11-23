# Outdoor Brief

**English** · [Français](README.fr.md)

The **daily brief for what happens outdoors**, in Home Assistant. Version 0.2 covers the coast: today's tides, tidal range, the current tide twelfth and the next spring tide, gathered in a single summary sensor shown by a Lovelace card and sent each morning to your phone, with the summary image, and optionally to a smartwatch.

> **Status: 0.3.2, early development.** Marine weather (0.4) and the garden profile (0.5) are on the [roadmap](ROADMAP.md).

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
| Summary image | PNG (image entity) | used as notification attachment |

The tidal range and the twelfth are recomputed every 5 minutes; Marées France is read again every hour. The **spring tide threshold** (100 by default) can be changed in the options: December 2026, for instance, peaks at 99.

## Lovelace card

The `outdoor-brief-card` card ships with the integration and loads automatically. Add it from *Add card* (search "Outdoor Brief"), or in YAML:

```yaml
type: custom:outdoor-brief-card
entity: sensor.outdoor_brief_my_port_daily_summary  # your "Daily summary" sensor
compact: false
```

It shows the tide trend and twelfth, a morning/afternoon table of high and low tides with coefficients, the next spring tide and the month's highest coefficient. `compact: true` keeps only the table and the next spring tide. After an update, reload the page once if the card still shows the previous version.

## Notifications

Set in the *Notifications* screen (also in the options):

- **Daily brief**: every day, only on remarkable days (today's coefficient reaches the spring tide threshold, or a spring tide within 2 days), or never; at the time you choose (07:00 by default). Sent to the **admin phone** (common SDR convention), with the summary image when the target is a `notify.mobile_app_*` service.
- **Spring tide alert**, 2 days before, with the high tide times of that day.
- **Smartwatch** (optional, independent of the phone): *full notification* (same text, no image, sent even without a phone) or *short notice* sent only when the phone notification went through. With an **Apple Watch**, iPhone notifications already appear on the watch: leave the watch off. With **Wear OS**, choose the watch's own notify service.
- **Events** `outdoor_brief_daily_summary` and `outdoor_brief_spring_tide_upcoming` are fired even when notifications are off, for your own automations.
- **Several ports**: one notification per port, or a single grouped notification (one line per port, stacked tables in the image), sent with the settings of the oldest grouped port.
- **Open on tap**: a dashboard path, e.g. `/lovelace/0`.
- **Admin phone set as a notify entity** (`notify.iphone_…`): Outdoor Brief sends to the device's `notify.mobile_app_…` service, the only one that carries the image.
- **Test**: action `outdoor_brief.send_summary` sends the brief right away.

An entry created before 0.3 sends nothing until you pick a frequency in its options.

## About the garden profile

This integration only provides measurable astronomical and weather data. Lunar gardening calendars (ascending/descending moon, root, leaf, flower and fruit days) rely on conventions that differ from one almanac to another. They are not included, so as not to impose one of them.

## For developers

Outdoor Brief is meant to be built upon, for example by a lunar gardening calendar.

- **Stable contract**: the `unique_id` of each entity (`<entry_id>_<key>`) and the attributes listed above. The summary carries a `schema_version` field.
- **Versioning**: semantic versioning. An attribute is renamed or removed only in a major version, after at least one version where it is flagged as deprecated.
- **Events** (0.3): `outdoor_brief_daily_summary` (the summary content plus `entry_id`) and `outdoor_brief_spring_tide_upcoming` (`date`, `coefficient`, `days_before`).
- **Coming**: the moon's declination and ecliptic longitude (0.5), the raw material of any gardening almanac.

A lunar gardening calendar integration can be built on top of this one: open an issue so we can list it here.

## License

MIT. Tide data: SHOM, via Marées France. The Roboto font in `fonts/` is under the SIL Open Font License 1.1 (`fonts/OFL.txt`).
