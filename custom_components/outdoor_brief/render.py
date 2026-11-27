"""Image PNG du résumé du jour, dessinée localement avec Pillow (fourni par Home Assistant).

Même contenu que la carte Lovelace : ligne d'état, tableau matin / après-midi,
prochaine grande marée et plus fort coefficient du mois. Aucune ressource externe :
la police Roboto (SIL OFL 1.1, réduite aux caractères latins) est livrée dans fonts/,
car la police par défaut de Pillow n'a pas les lettres accentuées.
"""

from __future__ import annotations

from datetime import date, datetime
from functools import cache
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

FONTS = Path(__file__).parent / "fonts"
WIDTH = 1080
MARGIN = 56

THEMES = {
    "light": {
        "bg": (255, 255, 255),
        "text": (33, 33, 33),
        "muted": (110, 110, 110),
        "line": (224, 224, 224),
        "accent": (3, 132, 199),
        "band": (159, 225, 203),
        "sun": (239, 159, 39),
    },
    "dark": {
        "bg": (17, 38, 48),
        "text": (240, 244, 245),
        "muted": (160, 180, 186),
        "line": (45, 72, 84),
        "accent": (159, 225, 203),
        "band": (93, 202, 165),
        "sun": (239, 159, 39),
    },
}

TEXT = {
    "fr": {
        "days": ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"),
        "months": (
            "janv.",
            "févr.",
            "mars",
            "avr.",
            "mai",
            "juin",
            "juil.",
            "août",
            "sept.",
            "oct.",
            "nov.",
            "déc.",
        ),
        "morning": "Matin",
        "afternoon": "Après-midi",
        "high": "Pleine mer",
        "low": "Basse mer",
        "coefficient": "Coefficient",
        "rising": "Marée montante",
        "falling": "Marée descendante",
        "twelfth": "{n}e douzième",
        "first": "1er douzième",
        "range": "marnage {v} m",
        "next_high": "PM {t}",
        "next_low": "BM {t}",
        "spring": "Prochaine grande marée : {d}, coef {c} ({n})",
        "spring_none": "Aucune grande marée (seuil {t}) dans les données disponibles",
        "today": "aujourd'hui",
        "tomorrow": "demain",
        "in_days": "dans {n} j",
        "month_max": "Plus fort coefficient du mois : {c} le {d}",
        "source": "Données SHOM via Marées France",
        "source_marine": "Données SHOM via Marées France · mer : Open-Meteo.com",
        "fishing": "Pêche à pied : {w}",
        "fishing_window": "{s}–{e} (BM {t}, coef {c})",
        "fishing_next": "Pêche à pied : prochain créneau {d} {s}–{e} (coef {c})",
        "fishing_none": "Pêche à pied : aucun créneau à coef {t} ou plus sur 7 jours",
        "sea": "Mer : {v}",
        "waves": "vagues {v} m",
        "swell": "houle {d} {v} m {p} s",
        "water": "eau {v} °C",
        "surge": "surcote estimée +{v} cm",
        "drop": "décote estimée {v} cm",
        "compass": ("N", "NE", "E", "SE", "S", "SO", "O", "NO"),
    },
    "en": {
        "days": ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"),
        "months": (
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ),
        "morning": "Morning",
        "afternoon": "Afternoon",
        "high": "High tide",
        "low": "Low tide",
        "coefficient": "Coefficient",
        "rising": "Rising tide",
        "falling": "Falling tide",
        "twelfth": "twelfth {n}/6",
        "first": "twelfth 1/6",
        "range": "range {v} m",
        "next_high": "HW {t}",
        "next_low": "LW {t}",
        "spring": "Next spring tide: {d}, coef {c} ({n})",
        "spring_none": "No spring tide (threshold {t}) in the available data",
        "today": "today",
        "tomorrow": "tomorrow",
        "in_days": "in {n} d",
        "month_max": "Highest coefficient this month: {c} on {d}",
        "source": "SHOM data via Marées France",
        "source_marine": "SHOM data via Marées France · sea: Open-Meteo.com",
        "fishing": "Shore fishing: {w}",
        "fishing_window": "{s}–{e} (LW {t}, coef {c})",
        "fishing_next": "Shore fishing: next window {d} {s}–{e} (coef {c})",
        "fishing_none": "Shore fishing: no window at coef {t} or more within 7 days",
        "sea": "Sea: {v}",
        "waves": "waves {v} m",
        "swell": "swell {d} {v} m {p} s",
        "water": "water {v} °C",
        "surge": "estimated surge +{v} cm",
        "drop": "estimated drop {v} cm",
        "compass": ("N", "NE", "E", "SE", "S", "SW", "W", "NW"),
    },
}


@cache
def _font(size: int, medium: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    name = "Roboto-Medium.ttf" if medium else "Roboto-Regular.ttf"
    try:
        return ImageFont.truetype(str(FONTS / name), size)
    except OSError:  # police absente : repli lisible, sans accents
        return ImageFont.load_default(size=size)


def _fit(draw: ImageDraw.ImageDraw, text: str, size: int) -> Any:
    """Police aussi grande que possible (jusqu'à `size`) pour tenir dans la largeur utile."""
    width = WIDTH - 2 * MARGIN
    while size > 24 and draw.textlength(text, font=_font(size, medium=True)) > width:
        size -= 1
    return _font(size, medium=True)


def _fit_small(draw: ImageDraw.ImageDraw, text: str) -> Any:
    """Police de 30 px au plus, réduite si la ligne dépasse la largeur utile."""
    size = 30
    while size > 20 and draw.textlength(text, font=_font(size)) > WIDTH - 2 * MARGIN:
        size -= 1
    return _font(size)


def texts(language: str | None) -> dict[str, Any]:
    return TEXT["fr" if str(language or "").lower().startswith("fr") else "en"]


def fmt_number(value: float | None, lang: dict[str, Any], digits: int = 2) -> str:
    if value is None:
        return "—"
    text = f"{value:.{digits}f}"
    return text.replace(".", ",") if lang is TEXT["fr"] else text


def fmt_time(iso: str) -> str:
    return datetime.fromisoformat(iso).strftime("%H:%M")


def fmt_day(day: date, lang: dict[str, Any], weekday: bool = True) -> str:
    month = lang["months"][day.month - 1]
    if lang is TEXT["fr"]:
        text = f"{day.day} {month}"
        return f"{lang['days'][day.weekday()][:3]}. {text}" if weekday else text
    text = f"{month} {day.day}"
    return f"{lang['days'][day.weekday()][:3]} {text}" if weekday else text


def fmt_full_day(day: date, lang: dict[str, Any]) -> str:
    name = lang["days"][day.weekday()]
    if lang is TEXT["fr"]:
        return f"{name} {day.day} {lang['months'][day.month - 1]}"
    return f"{name}, {lang['months'][day.month - 1]} {day.day}"


def in_days(days: int, lang: dict[str, Any]) -> str:
    if days == 0:
        return lang["today"]
    if days == 1:
        return lang["tomorrow"]
    return lang["in_days"].format(n=days)


def status_line(summary: dict[str, Any], lang: dict[str, Any]) -> str | None:
    """« Marée montante · 4e douzième · marnage 3,33 m · PM 14:46 »."""
    next_tide = summary.get("next_tide")
    if not next_tide:
        return None
    rising = next_tide["type"] == "high"
    parts = [lang["rising"] if rising else lang["falling"]]
    if n := summary.get("tide_twelfth"):
        parts.append(lang["first"] if n == 1 else lang["twelfth"].format(n=n))
    if summary.get("tidal_range") is not None:
        parts.append(lang["range"].format(v=fmt_number(summary["tidal_range"], lang)))
    key = "next_high" if rising else "next_low"
    parts.append(lang[key].format(t=fmt_time(next_tide["time"])))
    return " · ".join(parts)


def halves(summary: dict[str, Any]) -> dict[str, list[dict[str, Any] | None]]:
    """Pleines et basses mers rangées en matin (avant midi) et après-midi."""
    table: dict[str, list[dict[str, Any] | None]] = {"high": [None, None], "low": [None, None]}
    for tide in summary.get("tides", []):
        if tide["type"] not in table:
            continue
        col = 0 if datetime.fromisoformat(tide["time"]).hour < 12 else 1
        if table[tide["type"]][col] is None:
            table[tide["type"]][col] = tide
    return table


def compass(degrees: float | None, lang: dict[str, Any]) -> str:
    """Direction d'où vient la houle, en 8 points."""
    if degrees is None:
        return ""
    return lang["compass"][round(degrees % 360 / 45) % 8]


def fishing_line(summary: dict[str, Any], lang: dict[str, Any]) -> str | None:
    """« Pêche à pied : 08:32–11:32 (BM 10:32, coef 76) » ou le prochain créneau."""
    block = summary.get("fishing")
    if not block:
        return None
    if block.get("today"):
        return lang["fishing"].format(
            w=" · ".join(
                lang["fishing_window"].format(
                    s=fmt_time(w["start"]),
                    e=fmt_time(w["end"]),
                    t=fmt_time(w["low_tide"]),
                    c=w["coefficient"],
                )
                for w in block["today"]
            )
        )
    if nxt := block.get("next"):
        day = datetime.fromisoformat(nxt["low_tide"]).date()
        return lang["fishing_next"].format(
            d=fmt_day(day, lang),
            s=fmt_time(nxt["start"]),
            e=fmt_time(nxt["end"]),
            c=nxt["coefficient"],
        )
    return lang["fishing_none"].format(t=block.get("threshold", 70))


def sea_line(summary: dict[str, Any], lang: dict[str, Any]) -> str | None:
    """« Mer : vagues 1,4 m · houle O 1,2 m 11 s · eau 13,4 °C · surcote estimée +8 cm »."""
    parts = []
    if marine := summary.get("marine"):
        if marine.get("wave_height") is not None:
            parts.append(lang["waves"].format(v=fmt_number(marine["wave_height"], lang, 1)))
        if marine.get("swell_height") is not None:
            parts.append(
                lang["swell"]
                .format(
                    d=compass(marine.get("swell_direction"), lang),
                    v=fmt_number(marine["swell_height"], lang, 1),
                    p=fmt_number(marine.get("swell_period"), lang, 0),
                )
                .replace("  ", " ")
            )
        if marine.get("sea_temperature") is not None:
            parts.append(lang["water"].format(v=fmt_number(marine["sea_temperature"], lang, 1)))
    if (value := summary.get("surge")) and value.get("height_cm") is not None:
        cm = value["height_cm"]
        parts.append(lang["surge"].format(v=cm) if cm >= 0 else lang["drop"].format(v=cm))
    return lang["sea"].format(v=" · ".join(parts)) if parts else None


def port_lines(summary: dict[str, Any], lang: dict[str, Any]) -> list[str]:
    """Lignes propres à un port, sous son tableau (0.4)."""
    return [line for line in (fishing_line(summary, lang), sea_line(summary, lang)) if line]


def footer_lines(summary: dict[str, Any], lang: dict[str, Any]) -> list[str]:
    today = date.fromisoformat(summary["date"])
    lines = []
    if spring := summary.get("next_spring_tide"):
        day = date.fromisoformat(spring["date"])
        lines.append(
            lang["spring"].format(
                d=fmt_day(day, lang), c=spring["coefficient"], n=in_days((day - today).days, lang)
            )
        )
    else:
        lines.append(lang["spring_none"].format(t=summary.get("spring_tide_threshold", 100)))
    if best := summary.get("month_max"):
        day = date.fromisoformat(best["date"])
        lines.append(lang["month_max"].format(c=best["coefficient"], d=fmt_day(day, lang, False)))
    return lines


def render_png(summary: dict[str, Any], language: str | None, theme: str = "light") -> bytes:
    """Dessine le résumé d'un port ; la hauteur suit le contenu."""
    return render_summaries([summary], language, theme)


def render_summaries(
    summaries: list[dict[str, Any]], language: str | None, theme: str = "light"
) -> bytes:
    """Un ou plusieurs ports (notification regroupée) : tableaux empilés, pied commun."""
    lang = texts(language)
    colors = THEMES.get(theme, THEMES["light"])
    f_title, f_head = _font(56, medium=True), _font(36)
    f_label, f_value, f_small = _font(40), _font(40, medium=True), _font(30)
    multi = len(summaries) > 1
    first = summaries[0]

    section = (56 if multi else 0) + 70 + 48 + 3 * 84 + (28 if multi else 0)
    extra = sum(len(port_lines(summary, lang)) for summary in summaries) * 48
    height = 168 + len(summaries) * section + extra + 24 + 2 * 54 + 80
    image = Image.new("RGB", (WIDTH, height), colors["bg"])
    draw = ImageDraw.Draw(image)

    # Bandeau : petit soleil et vague aux couleurs SDR
    draw.rectangle([0, 0, WIDTH, 14], fill=colors["band"])
    draw.ellipse([WIDTH - MARGIN - 44, 40, WIDTH - MARGIN, 84], fill=colors["sun"])

    y = 34
    draw.text((MARGIN, y), "Outdoor Brief", font=f_title, fill=colors["text"])
    day = fmt_full_day(date.fromisoformat(first["date"]), lang)
    port = "" if multi else first.get("port") or ""
    y += 70
    draw.text((MARGIN, y), f"{port} · {day}" if port else day, font=f_head, fill=colors["muted"])
    y += 64

    def cell(tide: dict[str, Any] | None) -> str:
        if not tide:
            return "—"
        return f"{fmt_time(tide['time'])} · {fmt_number(tide.get('height'), lang)} m"

    def coef(tide: dict[str, Any] | None) -> str:
        return str(tide["coefficient"]) if tide and tide.get("coefficient") else "—"

    col_x = (MARGIN, MARGIN + 330, MARGIN + 660)
    for summary in summaries:
        if multi:
            draw.text(
                (MARGIN, y),
                summary.get("port") or "",
                font=_font(40, medium=True),
                fill=colors["text"],
            )
            y += 56
        if status := status_line(summary, lang):
            draw.text((MARGIN, y), status, font=_fit(draw, status, 36), fill=colors["accent"])
        y += 70
        draw.text((col_x[1], y), lang["morning"], font=f_small, fill=colors["muted"])
        draw.text((col_x[2], y), lang["afternoon"], font=f_small, fill=colors["muted"])
        y += 48
        table = halves(summary)
        for label, values in (
            (lang["high"], [cell(t) for t in table["high"]]),
            (lang["low"], [cell(t) for t in table["low"]]),
            (lang["coefficient"], [coef(t) for t in table["high"]]),
        ):
            draw.line([MARGIN, y, WIDTH - MARGIN, y], fill=colors["line"], width=2)
            y += 18
            draw.text((col_x[0], y), label, font=f_label, fill=colors["muted"])
            for x, value in zip(col_x[1:], values, strict=True):
                draw.text((x, y), value, font=f_value, fill=colors["text"])
            y += 66
        for line in port_lines(summary, lang):
            draw.text((MARGIN, y), line, font=_fit_small(draw, line), fill=colors["text"])
            y += 48
        if multi:
            y += 28

    y += 24
    for line in footer_lines(first, lang):
        draw.text((MARGIN, y), line, font=f_small, fill=colors["text"])
        y += 54
    y += 10
    source = lang["source_marine"] if any(x.get("marine") for x in summaries) else lang["source"]
    draw.text((MARGIN, y), source, font=_font(24), fill=colors["muted"])

    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
