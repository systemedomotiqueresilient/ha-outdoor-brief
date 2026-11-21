# Outdoor Brief : consignes pour les agents

Intégration Home Assistant (domaine `outdoor_brief`). Le résumé du jour pour ce qui se passe dehors : marées (0.1), puis carte, notifications visuelles, météo marine, lune et potager. Référence fonctionnelle : le cahier des charges « Outdoor Brief — Cahier des charges » (doc Claude de Mathieu) et `ROADMAP.md`.

## Règles
- **Données factuelles uniquement.** Pas de calendrier de jardinage lunaire (lune montante/descendante, jours racines/feuilles/fleurs/fruits) : on expose les grandeurs astronomiques, un tiers interprète.
- **Les marées viennent de Marées France**, par `marees_france.get_tides_data` et `get_coefficients_data`, **toujours avec `device_id`** : sans lui, l'action répond pour un port par défaut. On n'interroge jamais le SHOM directement.
- **Open-Meteo (0.4)** : écran de configuration distinct, désactivé par défaut ; désactivé = aucune requête, aucune entité houle.
- **On passe par l'appareil et le registre**, jamais par un `entity_id` de Marées France (renommable).
- **Les entités ne sont créées que pour le profil et les données choisis.** Une source absente rend indisponibles seulement les entités qui en dépendent.
- **Contrat public** : `unique_id` et attributs du résumé (`schema_version`). Un attribut n'est renommé ou supprimé qu'en version majeure, après une version où il est signalé obsolète.
- **Aucune nouvelle dépendance Python.** Le calcul lunaire sera écrit en Python pur ; l'image utilisera Pillow, déjà présent dans HA (à confirmer en 0.3).
- **Aucune donnée personnelle dans le dépôt public** (ni coordonnées GPS réelles, ni identifiants d'appareil). Commits avec l'adresse GitHub noreply.
- **Mathieu pousse lui-même les commits** (à partir d'un patch ou d'un bundle).

## Formats Marées France (relevés le 2026-11-21)
- Marées : `{date: [[type, "HH:MM", hauteur, coefficient], …]}`, type `tide.high` / `tide.low` / `tide.none` ; heure locale sans fuseau ; nombres en texte ; `---` = absent.
- Coefficients : `{date: [c1, c2]}` sur un an, parfois un seul par jour.
- Entités : heures en UTC, `maree_actuelle` en anglais (`falling` / `rising`). Voir l'annexe du cahier des charges.
- `tests/fixtures/` contient un relevé réel (Port-Louis, 20 au 27 novembre 2026, coefficients sur un an).

## Module commun `admin_phone.py`
- **Référence** : dépôt privé `systemedomotiqueresilient/ha-sdr`. Copié **tel quel**, jamais modifié ici. Le test `test_module_copy_and_versions` vérifie son SHA-256.
- **Convention** : capteur diagnostic `<entry_id>_admin_notify_target`, valeur dans `entry.data["admin_notify_target"]`, envoi par `async_notify_admin`.
- **À faire dans ha-sdr** : ajouter `outdoor_brief` à `SIBLING_PLATFORMS` (1.2.0).
- **Synchronisation entre agents** : carnet Evernote « HA Intégrations – Synchro IA » (00 : protocole, 01 : spécification, 02 : journal, à compléter à la fin ; 15 : fiche Outdoor Brief).

## Versions
La version doit être identique dans `manifest.json`, `const.py` (`VERSION`) et `VERSION`. Un test le vérifie. Tenir à jour `CHANGELOG.md` et `ROADMAP.md`.

## Vérifications
```bash
python3 -m pytest -q --cov=custom_components/outdoor_brief   # couverture ≥ 50 %
ruff check custom_components/
cd ../ha-core && python3 -m script.hassfest --action validate --integration-path ../ha-outdoor-brief/custom_components/outdoor_brief
```
