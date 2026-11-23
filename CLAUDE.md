# Outdoor Brief : consignes pour les agents

Intégration Home Assistant (domaine `outdoor_brief`). Le résumé du jour pour ce qui se passe dehors : marées (0.1), puis carte, notifications visuelles, météo marine, lune et potager. Référence fonctionnelle : le cahier des charges « Outdoor Brief — Cahier des charges » (doc Claude de Mathieu) et `ROADMAP.md`.

## Règles
- **Données factuelles uniquement.** Pas de calendrier de jardinage lunaire (lune montante/descendante, jours racines/feuilles/fleurs/fruits) : on expose les grandeurs astronomiques, un tiers interprète.
- **Les marées viennent de Marées France**, par `marees_france.get_tides_data` et `get_coefficients_data`, **toujours avec `device_id`** : sans lui, l'action répond pour un port par défaut. On n'interroge jamais le SHOM directement.
- **Open-Meteo (0.4)** : écran de configuration distinct, désactivé par défaut ; désactivé = aucune requête, aucune entité houle.
- **On passe par l'appareil et le registre**, jamais par un `entity_id` de Marées France (renommable).
- **Les entités ne sont créées que pour le profil et les données choisis.** Une source absente rend indisponibles seulement les entités qui en dépendent.
- **Contrat public** : `unique_id` et attributs du résumé (`schema_version`). Un attribut n'est renommé ou supprimé qu'en version majeure, après une version où il est signalé obsolète.
- **Carte** : JavaScript sans dépendance ni étape de build ; l'innerHTML ne reçoit que le gabarit fixe, les données passent par textContent (un test le vérifie).
- **Aucune nouvelle dépendance Python.** Le calcul lunaire sera écrit en Python pur. L'image utilise Pillow, dépendance de HA core (confirmé : `Pillow==12.0.0` dans les requirements de HA 2026.2). Police Roboto (OFL) livrée dans `fonts/`, réduite aux caractères latins : la police par défaut de Pillow n'a pas d'accents, et Roboto n'a ni « ᵉ » ni flèches (écrire « 4e »).
- **Notifications** : téléphone = cible admin (entry.data) via `async_notify_admin` ; montre = option séparée (off / full / notice), « notice » seulement si le téléphone a reçu. Entrée sans option de fréquence = « never » (pas de surprise après mise à jour). Anti-doublon dans un `Store` par entrée. Événements toujours émis.
- **Tests de minuterie** : `async_fire_time_changed(hass, dt_util.utcnow(), fire_all=True)` puis `async_block_till_done(wait_background_tasks=True)`, sinon les envois lancés par l'heure ne sont pas attendus.
- **Jamais de méthode `_context` sur une entité** : elle écrase `Entity._context`.
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
- **Version copiée** : 1.2.0 (77a8992, SHA-256 1d720150…545b), outdoor_brief dans SIBLING_PLATFORMS.
- **1.3.0 à venir** (décision de Mathieu du 2026-11-23) : reconnaissance ouverte des sœurs + envoi enrichi vers une entité notify mobile_app. À la recopie : utiliser `admin_sensor_attributes` dans le capteur, nouvelle forme de `find_admin_targets`, retirer `rich_target` d'alerts.py.
- **Synchronisation entre agents** : carnet Evernote « HA Intégrations – Synchro IA » (00 : protocole, 01 : spécification, 02 : journal, à compléter à la fin ; 15 : fiche Outdoor Brief).

## Versions
La version doit être identique dans `manifest.json`, `const.py` (`VERSION`), `VERSION` et `CARD_VERSION` en tête de `frontend/outdoor-brief-card.js`. Un test le vérifie. Tenir à jour `CHANGELOG.md` et `ROADMAP.md`.

## Vérifications
```bash
python3 -m pytest -q --cov=custom_components/outdoor_brief   # couverture ≥ 50 %
ruff check custom_components/
node --check custom_components/outdoor_brief/frontend/outdoor-brief-card.js
cd ../ha-core && python3 -m script.hassfest --action validate --integration-path ../ha-outdoor-brief/custom_components/outdoor_brief
```
