# Tarif EDF integration for Home Assistant

Provides current electricity rates for French EDF contracts (Base, HP/HC, Tempo) with automatic tariff updates from official data.gouv.fr sources.

## Installation

### Using HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=divers33&repository=hass-tarif-edf&category=integration)

### Manual install

Copy the `tarif_edf` folder from latest release to the `custom_components` folder in your `config` folder.

## Configuration

[![Open your Home Assistant instance and add the integration via the UI.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=tarif_edf)

During setup, you'll be asked to:
1. Select your contract type (Base, HP/HC, or Tempo)
2. Select your subscribed power (kVA)
3. For HP/HC contracts: enter your off-peak hours (e.g., `22:30-06:30` or `01:30-07:30,12:30-14:30`)

## Available Entities

### Common Entities (All Contracts)

| Entity | Description | Unit |
|--------|-------------|------|
| `sensor.puissance_souscrite_[type]_[power]kva` | Subscribed power | kVA |
| `sensor.tarif_actuel_[type]_[power]kva_ttc` | Current applicable rate | EUR/kWh |

### Base Contract

| Entity | Description | Unit |
|--------|-------------|------|
| `sensor.tarif_base_ttc` | Base rate | EUR/kWh |
| `sensor.tarif_abonnement_base_ttc` | Monthly subscription | EUR/month |

### HP/HC Contract (Peak/Off-Peak)

**Important:** For HP/HC contracts, you must configure your off-peak hours during setup. Enter them as shown on your electricity bill using the format `HH:MM-HH:MM`. For multiple periods, separate with commas (e.g., `01:30-07:30,12:30-14:30`).

| Entity | Description | Unit |
|--------|-------------|------|
| `sensor.tarif_heures_creuses_ttc` | Off-peak hours rate | EUR/kWh |
| `sensor.tarif_heures_pleines_ttc` | Peak hours rate | EUR/kWh |
| `sensor.tarif_abonnement_hphc_ttc` | Monthly subscription | EUR/month |
| `binary_sensor.heures_creuses_hphc_[power]kva` | Off-peak hours indicator | on/off |

### Tempo Contract

| Entity | Description | Unit |
|--------|-------------|------|
| `sensor.tarif_tempo_couleur` | Current Tempo color | - |
| `sensor.tarif_tempo_couleur_hier` | Yesterday's Tempo color | - |
| `sensor.tarif_tempo_couleur_aujourdhui` | Today's Tempo color | - |
| `sensor.tarif_tempo_couleur_demain` | Tomorrow's Tempo color | - |
| `sensor.tarif_tempo_heures_creuses_ttc` | Current off-peak rate | EUR/kWh |
| `sensor.tarif_tempo_heures_pleines_ttc` | Current peak rate | EUR/kWh |
| `sensor.tarif_bleu_tempo_heures_creuses_ttc` | Blue days off-peak rate | EUR/kWh |
| `sensor.tarif_bleu_tempo_heures_pleines_ttc` | Blue days peak rate | EUR/kWh |
| `sensor.tarif_blanc_tempo_heures_creuses_ttc` | White days off-peak rate | EUR/kWh |
| `sensor.tarif_blanc_tempo_heures_pleines_ttc` | White days peak rate | EUR/kWh |
| `sensor.tarif_rouge_tempo_heures_creuses_ttc` | Red days off-peak rate | EUR/kWh |
| `sensor.tarif_rouge_tempo_heures_pleines_ttc` | Red days peak rate | EUR/kWh |
| `sensor.tarif_abonnement_tempo_ttc` | Monthly subscription | EUR/month |
| `binary_sensor.heures_creuses_tempo_[power]kva` | Off-peak hours indicator | on/off |

## Off-Peak Hours Binary Sensor

The `binary_sensor.heures_creuses_*` entity is `on` when currently in off-peak hours, useful for automations:

```yaml
automation:
  - alias: "Start dishwasher during off-peak"
    trigger:
      - platform: state
        entity_id: binary_sensor.heures_creuses_hphc_6kva
        to: "on"
    action:
      - service: switch.turn_on
        entity_id: switch.dishwasher
```
