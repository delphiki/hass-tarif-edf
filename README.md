# Tarif EDF integration for Home Assistant

## Installation

### Using HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=delphiki&repository=hass-tarif-edf&category=integration)

### Manual install

Copy the `tarif_edf` folder from latest release to the `custom_components` folder in your `config` folder.

## Configuration

[![Open your Home Assistant instance and add the integration via the UI.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=tarif_edf)

## Available Sensors

### Common Sensors (All Contracts)
| Sensor | Description | Unit | Example |
|--------|-------------|------|---------|
| `sensor.tarif_actuel_[type]_[power]kva_ttc` | Current applicable rate | EUR/kWh | `sensor.tarif_actuel_base_6kva_ttc` |
| `sensor.tarif_actuel_[type]_[power]kva_ht` | Current applicable rate (excl. taxes) | EUR/kWh | `sensor.tarif_actuel_base_6kva_ht` |

### Base Contract
| Sensor | Description | Unit |
|--------|-------------|------|
| `sensor.tarif_base_ttc` | Base rate | EUR/kWh |
| `sensor.tarif_base_ht` | Base rate (excl. taxes) | EUR/kWh |

### HP/HC Contract (Peak/Off-Peak)
| Sensor | Description | Unit |
|--------|-------------|------|
| `sensor.tarif_heures_creuses_ttc` | Off-peak hours rate | EUR/kWh |
| `sensor.tarif_heures_creuses_ht` | Off-peak hours rate (excl. taxes) | EUR/kWh |
| `sensor.tarif_heures_pleines_ttc` | Peak hours rate | EUR/kWh |
| `sensor.tarif_heures_pleines_ht` | Peak hours rate (excl. taxes) | EUR/kWh |

### Tempo Contract
| Sensor | Description | Unit |
|--------|-------------|------|
| `sensor.tarif_tempo_couleur` | Current Tempo color | - |
| `sensor.tarif_tempo_couleur_hier` | Yesterday's Tempo color | - |
| `sensor.tarif_tempo_couleur_aujourd_hui` | Today's Tempo color | - |
| `sensor.tarif_tempo_couleur_demain` | Tomorrow's Tempo color | - |
| `sensor.tarif_tempo_heures_creuses_ttc` | Current off-peak hours rate | EUR/kWh |
| `sensor.tarif_tempo_heures_creuses_ht` | Current off-peak hours rate (excl. taxes) | EUR/kWh |
| `sensor.tarif_tempo_heures_pleines_ttc` | Current peak hours rate | EUR/kWh |
| `sensor.tarif_tempo_heures_pleines_ht` | Current peak hours rate (excl. taxes) | EUR/kWh |
| `sensor.tarif_bleu_tempo_heures_creuses_ttc` | Blue days off-peak rate | EUR/kWh |
| `sensor.tarif_bleu_tempo_heures_creuses_ht` | Blue days off-peak rate (excl. taxes) | EUR/kWh |
| `sensor.tarif_bleu_tempo_heures_pleines_ttc` | Blue days peak rate | EUR/kWh |
| `sensor.tarif_bleu_tempo_heures_pleines_ht` | Blue days peak rate (excl. taxes) | EUR/kWh |
| `sensor.tarif_blanc_tempo_heures_creuses_ttc` | White days off-peak rate | EUR/kWh |
| `sensor.tarif_blanc_tempo_heures_creuses_ht` | White days off-peak rate (excl. taxes) | EUR/kWh |
| `sensor.tarif_blanc_tempo_heures_pleines_ttc` | White days peak rate | EUR/kWh |
| `sensor.tarif_blanc_tempo_heures_pleines_ht` | White days peak rate (excl. taxes) | EUR/kWh |
| `sensor.tarif_rouge_tempo_heures_creuses_ttc` | Red days off-peak rate | EUR/kWh |
| `sensor.tarif_rouge_tempo_heures_creuses_ht` | Red days off-peak rate (excl. taxes) | EUR/kWh |
| `sensor.tarif_rouge_tempo_heures_pleines_ttc` | Red days peak rate | EUR/kWh |
| `sensor.tarif_rouge_tempo_heures_pleines_ht` | Red days peak rate (excl. taxes) | EUR/kWh |

