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
TEMPO_FORECAST_API_URL="https://open-dpe.fr/assets/tempo_days_lite.json"
TEMPO_COLORS_MAPPING={
    0: "indéterminé",
    1: "bleu",
    2: "blanc",
    3: "rouge"
}
TEMPO_FORECAST_DAYS=9
# Fichiers de secours contenant des grilles tarifaires officielles déjà connues
# mais pas encore publiées sur data.gouv.fr (une par type de contrat, même
# format que le jeu de données correspondant). Ils sont utilisés
# automatiquement tant que data.gouv.fr n'a pas publié une grille au moins
# aussi récente, puis ignorés sans intervention (voir coordinator.py).
BASE_FALLBACK_FILENAME="base_fallback.csv"
HPHC_FALLBACK_FILENAME="hphc_fallback.csv"
TEMPO_FALLBACK_FILENAME="tempo_fallback.csv"
TEMPO_DAY_START_AT="06:00"
TEMPO_TOMRROW_AVAILABLE_AT="11:00"
TEMPO_OFFPEAK_HOURS="22:00-06:00"

# Majoration annuelle de l'abonnement pour les auto-producteurs individuels
# avec injection (grille Tarif Bleu au 01/08/2026 : 9,84 €/an HT).
# La TVA à 20 % s'applique à l'abonnement.
AUTOPRODUCER_INJECTION_SURCHARGE_HT=9.84
SUBSCRIPTION_VAT_RATE=0.20

DEFAULT_REFRESH_INTERVAL=1

# Storage constants
STORAGE_VERSION = 1
STORAGE_KEY = "tarif_edf_tempo_cache"

PLATFORMS = [Platform.SENSOR]
