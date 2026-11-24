"""Constantes d'Outdoor Brief."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "outdoor_brief"
VERSION: Final = "0.3.4"  # identique à manifest.json et au fichier VERSION

# Carte Lovelace (servie par l'intégration elle-même)
FRONTEND_URL: Final = "/outdoor_brief_static"
CARD_FILE: Final = "outdoor-brief-card.js"

# Contrat public : à monter à chaque changement incompatible des attributs exposés
SCHEMA_VERSION: Final = 1

# Profils (le potager arrive en 0.5.0)
CONF_PROFILE: Final = "profile"
PROFILE_COASTAL: Final = "coastal"
PROFILES_AVAILABLE: Final = (PROFILE_COASTAL,)

# Source des marées : l'intégration Marées France (SHOM), jamais interrogée sur Internet ici
MAREES_DOMAIN: Final = "marees_france"
SERVICE_TIDES: Final = "get_tides_data"
SERVICE_COEFFICIENTS: Final = "get_coefficients_data"
CONF_PORT_DEVICE: Final = "port_device_id"

# Réglages
CONF_SPRING_THRESHOLD: Final = "spring_tide_threshold"
DEFAULT_SPRING_THRESHOLD: Final = 100
MIN_SPRING_THRESHOLD: Final = 70
MAX_SPRING_THRESHOLD: Final = 120

# Rythmes : les données Marées France sont relues toutes les heures ;
# le marnage et le douzième en cours sont recalculés toutes les 5 minutes.
REFRESH_INTERVAL: Final = timedelta(hours=1)
RECOMPUTE_INTERVAL: Final = timedelta(minutes=5)

UPCOMING_SPRING_TIDES: Final = 5

# Notifications (0.3)
CONF_NOTIFY_FREQUENCY: Final = "notify_frequency"
FREQ_DAILY: Final = "daily"
FREQ_REMARKABLE: Final = "remarkable"
FREQ_NEVER: Final = "never"
FREQUENCIES: Final = (FREQ_DAILY, FREQ_REMARKABLE, FREQ_NEVER)
DEFAULT_NEW_FREQUENCY: Final = FREQ_DAILY  # proposé à l'installation
# Entrée créée avant la 0.3 (option absente) : rien n'est envoyé tant qu'on n'a pas choisi.
FALLBACK_FREQUENCY: Final = FREQ_NEVER

CONF_NOTIFY_TIME: Final = "notify_time"
DEFAULT_NOTIFY_TIME: Final = "07:00:00"

CONF_IMAGE_THEME: Final = "image_theme"
THEMES: Final = ("light", "dark")
DEFAULT_IMAGE_THEME: Final = "light"

# Montre : seconde cible, indépendante du téléphone admin
CONF_WATCH_TARGET: Final = "watch_notify_target"
CONF_WATCH_MODE: Final = "watch_mode"
WATCH_OFF: Final = "off"
WATCH_FULL: Final = "full"  # même texte que le téléphone, sans image, même sans téléphone
WATCH_NOTICE: Final = "notice"  # court avis, seulement si le téléphone a bien reçu
WATCH_MODES: Final = (WATCH_OFF, WATCH_FULL, WATCH_NOTICE)

SPRING_TIDE_NOTICE_DAYS: Final = 2

# Regroupement (0.3.1) : une notification pour tous les ports regroupés, envoyée selon
# les réglages du premier port regroupé (le « port principal », le plus ancien).
CONF_GROUPING: Final = "notify_grouping"
GROUPING_OWN: Final = "own"
GROUPING_GROUPED: Final = "grouped"
GROUPINGS: Final = (GROUPING_OWN, GROUPING_GROUPED)

# Texte de la notification (0.3.4) : court quand l'image est jointe, sinon toujours détaillé
CONF_MESSAGE_STYLE: Final = "message_style"
STYLE_SHORT: Final = "short"
STYLE_DETAILED: Final = "detailed"
MESSAGE_STYLES: Final = (STYLE_SHORT, STYLE_DETAILED)

# Destinataires supplémentaires (0.3.4) : n'importe quels services ou entités notify
CONF_EXTRA_TARGETS: Final = "extra_notify_targets"

# Ouverture au toucher (0.3.1) : chemin d'un tableau de bord, ex. /lovelace/0
CONF_TAP_URL: Final = "tap_url"

EVENT_DAILY_SUMMARY: Final = f"{DOMAIN}_daily_summary"
EVENT_SPRING_TIDE: Final = f"{DOMAIN}_spring_tide_upcoming"
SERVICE_SEND_SUMMARY: Final = "send_summary"
