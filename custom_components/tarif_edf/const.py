"""Constants for the Tarif EDF integration."""

from homeassistant.const import Platform

DOMAIN = "tarif_edf"

CONTRACT_TYPE_BASE="base"
CONTRACT_TYPE_HPHC="hphc"
CONTRACT_TYPE_TEMPO="tempo"

TARIF_BASE_URL="https://www.data.gouv.fr/fr/datasets/r/c13d05e5-9e55-4d03-bf7e-042a2ade7e49"
TARIF_HPHC_URL="https://www.data.gouv.fr/fr/datasets/r/f7303b3a-93c7-4242-813d-84919034c416"
TARIF_TEMPO_URL="https://www.data.gouv.fr/fr/datasets/r/0c3d1d36-c412-4620-8566-e5cbb4fa2b5a"

TEMPO_COLOR_API_URL="https://www.api-couleur-tempo.fr/api/jourTempo"
TEMPO_COLORS_MAPPING={
    0: "indéterminé",
    1: "bleu",
    2: "blanc",
    3: "rouge"
}
TEMPO_DAY_START_AT="06:00"
TEMPO_TOMRROW_AVAILABLE_AT="11:00"
TEMPO_OFFPEAK_HOURS="22:00-06:00"

DEFAULT_REFRESH_INTERVAL=1

PLATFORMS = [Platform.SENSOR]
