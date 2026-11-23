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
    },
}


@cache
def _font(size: int, medium: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    name = "Roboto-Medium.ttf" if medium else "Roboto-Regular.ttf"
    try:
        return ImageFont.truetype(str(FONTS / name), size)
    except OSError:  # police absente : repli lisible, sans accents
        return ImageFont.load_default(size=size)


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
    height = 168 + len(summaries) * section + 24 + 2 * 54 + 80
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
            draw.text((MARGIN, y), status, font=_font(36, medium=True), fill=colors["accent"])
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
        if multi:
            y += 28

    y += 24
    for line in footer_lines(first, lang):
        draw.text((MARGIN, y), line, font=f_small, fill=colors["text"])
        y += 54
    y += 10
    draw.text((MARGIN, y), lang["source"], font=_font(24), fill=colors["muted"])

    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
