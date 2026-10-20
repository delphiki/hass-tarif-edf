"""Data update coordinator for the Tarif EDF integration."""
from __future__ import annotations

from datetime import timedelta, datetime, date
import calendar
import time
import re
from typing import Any
import json
import logging
import os
import requests
import csv

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import TimestampDataUpdateCoordinator
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    DEFAULT_REFRESH_INTERVAL,
    CONTRACT_TYPE_BASE,
    CONTRACT_TYPE_HPHC,
    CONTRACT_TYPE_TEMPO,
    TARIF_BASE_URL,
    TARIF_HPHC_URL,
    TARIF_TEMPO_URL,
    TEMPO_COLOR_API_URL,
    TEMPO_FORECAST_API_URL,
    TEMPO_COLORS_MAPPING,
    TEMPO_DAY_START_AT,
    TEMPO_TOMRROW_AVAILABLE_AT,
    TEMPO_OFFPEAK_HOURS,
    TEMPO_FORECAST_DAYS,
    BASE_FALLBACK_FILENAME,
    HPHC_FALLBACK_FILENAME,
    TEMPO_FALLBACK_FILENAME,
    AUTOPRODUCER_INJECTION_SURCHARGE_HT,
    SUBSCRIPTION_VAT_RATE,
    STORAGE_VERSION,
    STORAGE_KEY,
)

_LOGGER = logging.getLogger(__name__)

def get_remote_file(url: str):
    return requests.get(
        url,
        stream=True,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"
        },
    )

# --- Fonctions I/O bloquantes, destinées à être exécutées dans l'executor ---
# (jamais directement depuis l'event loop). Elles réalisent l'appel réseau ET
# la lecture/le décodage du corps de la réponse, car avec ``stream=True`` le
# corps n'est lu qu'au premier accès à ``.json()``/``.content`` : ces accès
# doivent donc rester hors de l'event loop.

def fetch_json(url: str):
    """Appel réseau + parsing JSON, exécutés dans l'executor."""
    response = get_remote_file(url)
    try:
        return response.json()
    finally:
        response.close()

def fetch_json_with_status(url: str):
    """Appel réseau : renvoie (status_code, json|None). Exécuté dans l'executor."""
    response = get_remote_file(url)
    try:
        status_code = response.status_code
        data = response.json() if status_code == 200 else None
        return status_code, data
    finally:
        response.close()

def fetch_csv_rows(url: str):
    """Appel réseau + décodage + parsing CSV, exécutés dans l'executor."""
    response = get_remote_file(url)
    try:
        return list(csv.reader(response.content.decode('utf-8').splitlines(), delimiter=';'))
    finally:
        response.close()

def read_csv_rows(path: str):
    """Lecture de fichier + parsing CSV, exécutés dans l'executor.

    Renvoie ``None`` si le fichier n'existe pas.
    """
    if not os.path.exists(path):
        return None
    with open(path, encoding='utf-8') as csv_file:
        return list(csv.reader(csv_file, delimiter=';'))

def str_to_time(str):
    return datetime.strptime(str, '%H:%M').time()

def time_in_between(now, start, end):
    if start <= end:
        return start <= now < end
    else:
        return start <= now or now < end

def get_tempo_color_from_code(code):
    return TEMPO_COLORS_MAPPING[code]


class TarifEdfDataUpdateCoordinator(TimestampDataUpdateCoordinator):
    """Data update coordinator for the Tarif EDF integration."""

    config_entry: ConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name=entry.title,
            update_interval=timedelta(minutes=1),
        )
        self.config_entry = entry
        self.tempo_prices: dict[str, dict] = {}
        self._store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry.entry_id}")
        self._tempo_cache_loaded = False
        self._forecast_cache: list = []
        self._forecast_cache_time = None

    async def _async_load_tempo_cache(self) -> None:
        """Charge le cache Tempo depuis le stockage persistant."""
        if self._tempo_cache_loaded:
            return

        stored_data = await self._store.async_load()
        if stored_data:
            self.logger.info("Chargement du cache Tempo depuis le stockage persistant")
            if self.data is None:
                self.data = {}
            # Restaurer les couleurs Tempo sauvegardées
            if 'tempo_demain_date' in stored_data:
                self.data['tempo_demain_date'] = stored_data.get('tempo_demain_date')
                self.data['tempo_couleur_demain'] = stored_data.get('tempo_couleur_demain')
                self.logger.info(
                    f"Cache Tempo restauré: demain={self.data.get('tempo_couleur_demain')} "
                    f"pour le {self.data.get('tempo_demain_date')}"
                )
            if 'tempo_aujourdhui_date' in stored_data:
                self.data['tempo_aujourdhui_date'] = stored_data.get('tempo_aujourdhui_date')
                self.data['tempo_couleur_aujourdhui'] = stored_data.get('tempo_couleur_aujourdhui')
                self.logger.info(
                    f"Cache Tempo restauré: aujourd'hui={self.data.get('tempo_couleur_aujourdhui')} "
                    f"pour le {self.data.get('tempo_aujourdhui_date')}"
                )
        self._tempo_cache_loaded = True

    async def _async_save_tempo_cache(self) -> None:
        """Sauvegarde le cache Tempo dans le stockage persistant."""
        if self.data is None:
            return

        cache_data = {
            'tempo_demain_date': self.data.get('tempo_demain_date'),
            'tempo_couleur_demain': self.data.get('tempo_couleur_demain'),
            'tempo_aujourdhui_date': self.data.get('tempo_aujourdhui_date'),
            'tempo_couleur_aujourdhui': self.data.get('tempo_couleur_aujourdhui'),
        }
        await self._store.async_save(cache_data)
        self.logger.debug(f"Cache Tempo sauvegardé: {cache_data}")

    async def get_tempo_day(self, date):
        date_str = date.strftime('%Y-%m-%d')
        now = dt_util.now().time()
        check_limit = str_to_time(TEMPO_TOMRROW_AVAILABLE_AT)

        cached = self.tempo_prices.get(date_str)
        if cached is not None:
            codeJour = cached['codeJour']
            # Use cache if color is known, or if indéterminé and before the recheck limit
            if codeJour in [1, 2, 3] or (codeJour == 0 and now < check_limit):
                return cached

        url = f"{TEMPO_COLOR_API_URL}/{date_str}"
        response_json = await self.hass.async_add_executor_job(fetch_json, url)

        # Only overwrite cache if new result has a known color, or no cache exists
        if cached is None or response_json.get('codeJour', 0) in [1, 2, 3]:
            self.tempo_prices[date_str] = response_json

        return response_json

    async def get_tempo_forecast(self) -> list:
        """Récupère les prévisions Tempo depuis open-dpe.fr (mis en cache 1h)."""
        now = dt_util.now()
        if self._forecast_cache and self._forecast_cache_time and \
                (now - self._forecast_cache_time).total_seconds() < 3600:
            return self._forecast_cache

        try:
            status_code, forecast_data = await self.hass.async_add_executor_job(
                fetch_json_with_status, TEMPO_FORECAST_API_URL
            )
            if status_code == 200:
                if not isinstance(forecast_data, list):
                    self.logger.warning(
                        f"Réponse prévisions Tempo inattendue (type={type(forecast_data).__name__})"
                    )
                    return []
                self.logger.debug(f"Prévisions Tempo récupérées: {len(forecast_data)} jours")
                self._forecast_cache = forecast_data
                self._forecast_cache_time = now
                return forecast_data
            else:
                self.logger.warning(
                    f"Erreur lors de la récupération des prévisions Tempo: {status_code}"
                )
                return self._forecast_cache or []
        except Exception as e:
            self.logger.error(f"Exception lors de la récupération des prévisions Tempo: {e}")
            return self._forecast_cache or []

    async def _apply_tariff_fallback(self, contract_type: str, official_effective_date: str | None, power: str) -> None:
        """Applique une grille tarifaire de secours si nécessaire.

        Chaque type de contrat (Base, HP/HC, Tempo) dispose d'un fichier de
        secours (livré avec l'intégration, même format que le jeu de données
        data.gouv.fr correspondant) contenant une grille officielle déjà connue
        mais pas encore présente sur data.gouv.fr. La grille de secours n'est
        appliquée que si :

        - sa date de début est plus récente que celle de la grille officielle
          actuellement active sur data.gouv.fr, ET
        - cette date de début est déjà atteinte (grille en vigueur).

        Dès que data.gouv.fr publie une grille dont la date de début est au moins
        aussi récente que celle du fichier de secours, ce dernier est ignoré
        automatiquement : aucune mise à jour de l'intégration n'est nécessaire.
        """
        self.data['tarifs_secours'] = False

        filename = {
            CONTRACT_TYPE_BASE: BASE_FALLBACK_FILENAME,
            CONTRACT_TYPE_HPHC: HPHC_FALLBACK_FILENAME,
            CONTRACT_TYPE_TEMPO: TEMPO_FALLBACK_FILENAME,
        }.get(contract_type)
        if filename is None:
            return

        # La lecture du fichier (existence + open + parsing CSV) est déportée
        # dans l'executor pour ne pas bloquer l'event loop.
        fallback_path = os.path.join(os.path.dirname(__file__), filename)
        try:
            fallback_rows = await self.hass.async_add_executor_job(read_csv_rows, fallback_path)
        except OSError as err:
            self.logger.warning(f"Lecture du fichier de secours {filename} impossible: {err}")
            return
        if fallback_rows is None:
            return

        # Nombre minimal de colonnes attendu selon le type de contrat
        min_cols = {
            CONTRACT_TYPE_BASE: 6,
            CONTRACT_TYPE_HPHC: 8,
            CONTRACT_TYPE_TEMPO: 16,
        }[contract_type]

        fallback_row = None
        for row in fallback_rows:
            if len(row) > min_cols and row[1] == '' and row[2] == power:
                fallback_row = row
                break
        if fallback_row is None:
            return

        try:
            fallback_date = datetime.strptime(fallback_row[0].strip(), '%d/%m/%Y').date()
        except ValueError:
            self.logger.warning(f"Date de la grille de secours {filename} invalide: {fallback_row[0]!r}")
            return

        official_date = None
        if official_effective_date:
            try:
                official_date = datetime.strptime(official_effective_date.strip(), '%d/%m/%Y').date()
            except ValueError:
                official_date = None

        today = dt_util.now().date()

        # Grille de secours pas encore en vigueur
        if today < fallback_date:
            return

        # data.gouv.fr propose déjà une grille au moins aussi récente : on la garde
        if official_date is not None and official_date >= fallback_date:
            self.logger.info(
                f"Grille officielle {contract_type} du {official_date.strftime('%d/%m/%Y')} disponible "
                f"sur data.gouv.fr, fichier de secours ignoré"
            )
            return

        # Appliquer les tarifs de secours (colonnes TTC identiques au fichier officiel)
        def _val(index):
            return float(fallback_row[index].replace(",", "."))

        if contract_type == CONTRACT_TYPE_BASE:
            self.data['base_fixe_ttc'] = _val(4)
            self.data['base_variable_ttc'] = _val(6)
        elif contract_type == CONTRACT_TYPE_HPHC:
            self.data['hphc_fixe_ttc'] = _val(4)
            self.data['hphc_variable_hc_ttc'] = _val(6)
            self.data['hphc_variable_hp_ttc'] = _val(8)
        elif contract_type == CONTRACT_TYPE_TEMPO:
            self.data['tempo_fixe_ttc'] = _val(4)
            self.data['tempo_variable_hc_bleu_ttc'] = _val(6)
            self.data['tempo_variable_hp_bleu_ttc'] = _val(8)
            self.data['tempo_variable_hc_blanc_ttc'] = _val(10)
            self.data['tempo_variable_hp_blanc_ttc'] = _val(12)
            self.data['tempo_variable_hc_rouge_ttc'] = _val(14)
            self.data['tempo_variable_hp_rouge_ttc'] = _val(16)

        self.data['tarifs_secours'] = True
        self.data['last_refresh_at'] = dt_util.now()
        official_str = official_date.strftime('%d/%m/%Y') if official_date else "aucune"
        self.logger.warning(
            f"Tarifs {contract_type} de secours appliqués (grille du {fallback_date.strftime('%d/%m/%Y')}) : "
            f"data.gouv.fr n'a pas encore publié cette grille "
            f"(dernière grille officielle active: {official_str})"
        )

    def _apply_autoproducer_surcharge(self, contract_type: str) -> None:
        """Ajoute la majoration d'abonnement « auto-producteur avec injection ».

        Activable via l'option ``autoproducteur_injection`` de la configuration.
        Le montant de la grille Tarif Bleu (9,84 €/an HT) est converti en TTC
        (TVA 20 % sur l'abonnement) puis ajouté au prix de l'abonnement annuel
        du contrat concerné. Appelée après le calcul de l'abonnement (officiel ou
        de secours), une seule fois par rafraîchissement des tarifs.
        """
        fixe_key = {
            CONTRACT_TYPE_BASE: 'base_fixe_ttc',
            CONTRACT_TYPE_HPHC: 'hphc_fixe_ttc',
            CONTRACT_TYPE_TEMPO: 'tempo_fixe_ttc',
        }.get(contract_type)

        enabled = bool(self.config_entry.options.get("autoproducteur_injection", False))
        self.data['autoproducteur_injection'] = enabled

        if not enabled or fixe_key is None or self.data.get(fixe_key) is None:
            return

        surcharge_ttc = round(
            AUTOPRODUCER_INJECTION_SURCHARGE_HT * (1 + SUBSCRIPTION_VAT_RATE), 2
        )
        self.data[fixe_key] = round(self.data[fixe_key] + surcharge_ttc, 2)
        self.logger.info(
            f"Majoration auto-producteur avec injection appliquée: "
            f"+{surcharge_ttc} €/an TTC sur {fixe_key}"
        )

    def _update_hourly_subscription(self, contract_type: str) -> None:
        """Calcule le prix de l'abonnement en €/h pour le mois en cours.

        L'abonnement annuel TTC est ramené à un coût mensuel (÷ 12), puis réparti
        sur le nombre réel d'heures du mois courant (28, 29, 30 ou 31 jours × 24 h),
        avec 6 décimales de précision.

        Ainsi, un capteur d'intégration (somme de Riemann, unité €/h → €) branché
        sur cette valeur accumule exactement le coût de l'abonnement : 1/12 de
        l'annuel sur chaque mois, et le montant annuel complet sur douze mois,
        quelle que soit la longueur des mois.
        """
        fixe_key = {
            CONTRACT_TYPE_BASE: 'base_fixe_ttc',
            CONTRACT_TYPE_HPHC: 'hphc_fixe_ttc',
            CONTRACT_TYPE_TEMPO: 'tempo_fixe_ttc',
        }.get(contract_type)

        annual_ttc = self.data.get(fixe_key) if fixe_key else None
        if annual_ttc is None:
            self.data['abonnement_horaire_ttc'] = None
            return

        now = dt_util.now()
        days_in_month = calendar.monthrange(now.year, now.month)[1]
        monthly_ttc = annual_ttc / 12
        self.data['abonnement_horaire_ttc'] = round(monthly_ttc / (days_in_month * 24), 6)

    async def _async_update_data(self) -> dict[Platform, dict[str, Any]]:
        """Get the latest data from Tarif EDF and updates the state."""
        data = self.config_entry.data
        previous_data = None if self.data is None else self.data.copy()

        # Charger le cache Tempo depuis le stockage persistant au premier démarrage
        if data['contract_type'] == CONTRACT_TYPE_TEMPO:
            await self._async_load_tempo_cache()

        if previous_data is None:
            # Préserver les données du cache si elles existent
            cached_tempo_demain_date = self.data.get('tempo_demain_date') if self.data else None
            cached_tempo_couleur_demain = self.data.get('tempo_couleur_demain') if self.data else None
            cached_tempo_aujourdhui_date = self.data.get('tempo_aujourdhui_date') if self.data else None
            cached_tempo_couleur_aujourdhui = self.data.get('tempo_couleur_aujourdhui') if self.data else None

            self.data = {
                "contract_power": data['contract_power'],
                "contract_type": data['contract_type'],
                "last_refresh_at": None,
                "tarif_actuel_ttc": None
            }

            # Restaurer les données du cache
            if cached_tempo_demain_date:
                self.data['tempo_demain_date'] = cached_tempo_demain_date
                self.data['tempo_couleur_demain'] = cached_tempo_couleur_demain
            if cached_tempo_aujourdhui_date:
                self.data['tempo_aujourdhui_date'] = cached_tempo_aujourdhui_date
                self.data['tempo_couleur_aujourdhui'] = cached_tempo_couleur_aujourdhui

        fresh_data_limit = dt_util.now() - timedelta(days=self.config_entry.options.get("refresh_interval", DEFAULT_REFRESH_INTERVAL))

        tarif_needs_update = self.data['last_refresh_at'] is None or self.data['last_refresh_at'] < fresh_data_limit

        self.logger.info('EDF tarif_needs_update '+('yes' if tarif_needs_update else 'no'))

        if tarif_needs_update:
            if data['contract_type'] == CONTRACT_TYPE_BASE:
                url = TARIF_BASE_URL
            elif data['contract_type'] == CONTRACT_TYPE_HPHC:
                    url = TARIF_HPHC_URL
            elif data['contract_type'] == CONTRACT_TYPE_TEMPO:
                    url = TARIF_TEMPO_URL

            # Appel réseau + décodage + parsing CSV entièrement dans l'executor.
            rows = await self.hass.async_add_executor_job(fetch_csv_rows, url)

            # Date de début de la grille officielle active (utilisée pour décider
            # si la grille de secours Tempo doit s'appliquer)
            official_effective_date = None

            for row in rows:
                if row[1] == '' and row[2] == data['contract_power']:
                    if data['contract_type'] == CONTRACT_TYPE_BASE:
                        self.data['base_fixe_ttc'] = float(row[4].replace(",", "." ))
                        self.data['base_variable_ttc'] = float(row[6].replace(",", "." ))
                    elif data['contract_type'] == CONTRACT_TYPE_HPHC:
                        self.data['hphc_fixe_ttc'] = float(row[4].replace(",", "." ))
                        self.data['hphc_variable_hc_ttc'] = float(row[6].replace(",", "." ))
                        self.data['hphc_variable_hp_ttc'] = float(row[8].replace(",", "." ))
                    elif data['contract_type'] == CONTRACT_TYPE_TEMPO:
                        self.data['tempo_fixe_ttc'] = float(row[4].replace(",", "." ))
                        self.data['tempo_variable_hc_bleu_ttc'] = float(row[6].replace(",", "." ))
                        self.data['tempo_variable_hp_bleu_ttc'] = float(row[8].replace(",", "." ))
                        self.data['tempo_variable_hc_blanc_ttc'] = float(row[10].replace(",", "." ))
                        self.data['tempo_variable_hp_blanc_ttc'] = float(row[12].replace(",", "." ))
                        self.data['tempo_variable_hc_rouge_ttc'] = float(row[14].replace(",", "." ))
                        self.data['tempo_variable_hp_rouge_ttc'] = float(row[16].replace(",", "." ))

                    official_effective_date = row[0]
                    self.data['last_refresh_at'] = dt_util.now()

                    break

            # Grille tarifaire de secours : appliquée uniquement tant que
            # data.gouv.fr n'a pas publié une grille au moins aussi récente.
            await self._apply_tariff_fallback(data['contract_type'], official_effective_date, data['contract_power'])

            # Majoration abonnement auto-producteur avec injection (option)
            self._apply_autoproducer_surcharge(data['contract_type'])

        # Abonnement en €/h pour le mois en cours (recalculé à chaque cycle pour
        # suivre les changements de mois : 28/29/30/31 jours)
        self._update_hourly_subscription(data['contract_type'])

        if data['contract_type'] == CONTRACT_TYPE_TEMPO:
            today = dt_util.now().date()
            yesterday = today - timedelta(days=1)
            tomorrow = today + timedelta(days=1)
            today_str = today.strftime('%Y-%m-%d')

            try:
                tempo_yesterday = await self.get_tempo_day(yesterday)
                tempo_today = await self.get_tempo_day(today)
                tempo_tomorrow = await self.get_tempo_day(tomorrow)
            except Exception as e:
                self.logger.error(f"Erreur lors de la récupération des couleurs Tempo: {e}")
                tempo_yesterday = {'codeJour': 0}
                tempo_today = {'codeJour': 0}
                tempo_tomorrow = {'codeJour': 0}

            yesterday_color = get_tempo_color_from_code(tempo_yesterday['codeJour'])
            today_color = get_tempo_color_from_code(tempo_today['codeJour'])
            tomorrow_color = get_tempo_color_from_code(tempo_tomorrow['codeJour'])
            tomorrow_str = tomorrow.strftime('%Y-%m-%d')

            # Si la couleur d'aujourd'hui est indéterminée, essayer de la résoudre
            # depuis les caches (couleur de demain de la veille, ou couleur déjà résolue)
            if today_color == "indéterminé":
                # D'abord vérifier si on a déjà résolu la couleur d'aujourd'hui
                if self.data.get('tempo_aujourdhui_date') == today_str:
                    cached_today_color = self.data.get('tempo_couleur_aujourdhui')
                    if cached_today_color and cached_today_color != "indéterminé":
                        self.logger.info(f"Réutilisation de la couleur d'aujourd'hui déjà résolue: {cached_today_color}")
                        today_color = cached_today_color
                # Sinon vérifier la couleur de demain connue la veille
                elif self.data.get('tempo_demain_date') == today_str:
                    previous_tomorrow_color = self.data.get('tempo_couleur_demain')
                    if previous_tomorrow_color and previous_tomorrow_color != "indéterminé":
                        self.logger.info(f"Réutilisation de la couleur de demain connue la veille: {previous_tomorrow_color}")
                        today_color = previous_tomorrow_color

            # Si la couleur de demain est indéterminée mais qu'on l'avait déjà
            # récupérée et qu'elle est valide, on réutilise cette valeur du cache
            if tomorrow_color == "indéterminé" and self.data.get('tempo_demain_date') == tomorrow_str:
                cached_tomorrow_color = self.data.get('tempo_couleur_demain')
                if cached_tomorrow_color and cached_tomorrow_color != "indéterminé":
                    self.logger.info(f"Réutilisation de la couleur de demain déjà connue: {cached_tomorrow_color}")
                    tomorrow_color = cached_tomorrow_color

            self.data['tempo_couleur_hier'] = yesterday_color if yesterday_color != "indéterminé" else None
            # Ne stocker que les couleurs réelles (pas "indéterminé") pour que les capteurs
            # soient "indisponibles" plutôt que d'afficher une valeur incorrecte
            self.data['tempo_couleur_aujourdhui'] = today_color if today_color != "indéterminé" else None
            # Sauvegarder la couleur résolue d'aujourd'hui pour les mises à jour suivantes
            self.data['tempo_aujourdhui_date'] = today_str
            self.data['tempo_couleur_demain'] = tomorrow_color if tomorrow_color != "indéterminé" else None
            # Stocker la date de demain pour pouvoir la réutiliser après minuit
            self.data['tempo_demain_date'] = tomorrow_str

            # Sauvegarder le cache Tempo sur disque pour survivre aux redémarrages
            save_cache = False
            if tomorrow_color != "indéterminé":
                save_cache = True
            if today_color != "indéterminé":
                save_cache = True
            if save_cache:
                await self._async_save_tempo_cache()
            else:
                self.logger.debug("Cache Tempo non sauvegardé: couleurs indéterminées")

            if dt_util.now().time() >= str_to_time(TEMPO_DAY_START_AT):
                self.logger.info("Using today's tempo prices")
                current_color = today_color
            else:
                self.logger.info("Using yesterday's tempo prices")
                current_color = yesterday_color

            if current_color != "indéterminé":
                self.data['tempo_couleur'] = current_color
                self.data['tempo_variable_hp_ttc'] = self.data[f"tempo_variable_hp_{current_color}_ttc"]
                self.data['tempo_variable_hc_ttc'] = self.data[f"tempo_variable_hc_{current_color}_ttc"]
                self.data['last_refresh_at'] = dt_util.now()
            else:
                # Couleur inconnue : vider les clés pour éviter d'afficher des données périmées
                self.data['tempo_couleur'] = None
                self.data['tempo_variable_hp_ttc'] = None
                self.data['tempo_variable_hc_ttc'] = None

            # Initialiser les clés de prévision avec des valeurs par défaut
            # pour garantir que les capteurs sont toujours disponibles
            for i in range(TEMPO_FORECAST_DAYS):
                day_num = i + 1
                if f'tempo_prevision_j{day_num}_couleur' not in self.data:
                    self.data[f'tempo_prevision_j{day_num}_couleur'] = 'indéterminé'
                    self.data[f'tempo_prevision_j{day_num}_probabilite'] = 0
                    self.data[f'tempo_prevision_j{day_num}_date'] = ''

            # Récupérer les prévisions Tempo (J+1 à J+9)
            try:
                forecast_data = await self.get_tempo_forecast()
                if forecast_data:
                    for i, forecast in enumerate(forecast_data[:TEMPO_FORECAST_DAYS]):
                        day_num = i + 1
                        self.data[f'tempo_prevision_j{day_num}_couleur'] = forecast.get('couleur', 'indéterminé')
                        self.data[f'tempo_prevision_j{day_num}_probabilite'] = round(forecast.get('probability', 0) * 100)
                        self.data[f'tempo_prevision_j{day_num}_date'] = forecast.get('date', '')
                    self.logger.info(f"Prévisions Tempo mises à jour pour {len(forecast_data)} jours")
                else:
                    self.logger.warning("Aucune donnée de prévision Tempo récupérée")
            except Exception as e:
                self.logger.error(f"Erreur lors du traitement des prévisions Tempo: {e}")

        default_offpeak_hours = None
        if data['contract_type'] == CONTRACT_TYPE_TEMPO:
            default_offpeak_hours = TEMPO_OFFPEAK_HOURS
        off_peak_hours_ranges = self.config_entry.options.get("off_peak_hours_ranges", default_offpeak_hours)

        if data['contract_type'] == CONTRACT_TYPE_BASE:
            self.data['tarif_actuel_ttc'] = self.data['base_variable_ttc']
        elif data['contract_type'] in [CONTRACT_TYPE_HPHC, CONTRACT_TYPE_TEMPO] and off_peak_hours_ranges is not None:
            contract_type_key = 'hphc' if data['contract_type'] == CONTRACT_TYPE_HPHC else 'tempo'
            tarif_actuel = self.data.get(contract_type_key+'_variable_hp_ttc')
            if tarif_actuel is None:
                # Couleur indéterminée ou données tarifaires pas encore chargées
                return self.data
            now = dt_util.now().time()
            for hour_range in off_peak_hours_ranges.split(','):
                if not re.match(r'([0-1]?[0-9]|2[0-3]):[0-5][0-9]-([0-1]?[0-9]|2[0-3]):[0-5][0-9]', hour_range):
                    continue

                hours = hour_range.split('-')
                start_at = str_to_time(hours[0])
                end_at = str_to_time(hours[1])

                if time_in_between(now, start_at, end_at):
                    tarif_actuel = self.data[contract_type_key+'_variable_hc_ttc']
                    break

            self.data['tarif_actuel_ttc'] = tarif_actuel

        self.logger.info('EDF Tarif')
        self.logger.info(self.data)

        return self.data
