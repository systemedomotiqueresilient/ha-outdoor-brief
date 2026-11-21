"""Constantes d'Outdoor Brief."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "outdoor_brief"
VERSION: Final = "0.1.0"  # identique à manifest.json et au fichier VERSION

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
