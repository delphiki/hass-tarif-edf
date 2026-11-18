"""Constants for the Tarif EDF integration."""

from homeassistant.const import Platform

DOMAIN = "tarif_edf"

# Config entry keys
CONF_CONTRACT_TYPE = "contract_type"
CONF_CONTRACT_POWER = "contract_power"
CONF_REFRESH_INTERVAL = "refresh_interval"
CONF_OFF_PEAK_HOURS_RANGES = "off_peak_hours_ranges"

# Contract types
CONTRACT_TYPE_BASE = "base"
CONTRACT_TYPE_HPHC = "hphc"
CONTRACT_TYPE_TEMPO = "tempo"

# Data.gouv.fr CSV sources
TARIF_BASE_URL = "https://www.data.gouv.fr/fr/datasets/r/c13d05e5-9e55-4d03-bf7e-042a2ade7e49"
TARIF_HPHC_URL = "https://www.data.gouv.fr/fr/datasets/r/f7303b3a-93c7-4242-813d-84919034c416"
TARIF_TEMPO_URL = "https://www.data.gouv.fr/fr/datasets/r/0c3d1d36-c412-4620-8566-e5cbb4fa2b5a"

# Tempo API
TEMPO_COLOR_API_URL = "https://www.api-couleur-tempo.fr/api/jourTempo"
TEMPO_COLORS_MAPPING = {
    0: "indéterminé",
    1: "bleu",
    2: "blanc",
    3: "rouge",
}
TEMPO_DAY_START_AT = "06:00"
TEMPO_TOMRROW_AVAILABLE_AT = "11:00"
TEMPO_OFFPEAK_HOURS = "22:00-06:00"

# Refresh
DEFAULT_REFRESH_INTERVAL = 1  # days – how often to re-download the tariff CSV
DEFAULT_UPDATE_INTERVAL_MINUTES = 5  # minutes – coordinator polling interval

# HTTP
HTTP_TIMEOUT = 30  # seconds
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"
)

# Timezone for Tempo day boundaries (Europe/Paris)
TEMPO_TIMEZONE = "Europe/Paris"

PLATFORMS = [Platform.SENSOR]
