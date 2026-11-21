# Outdoor Brief

[English](README.md) · **Français**

Le **résumé du jour pour ce qui se passe dehors**, dans Home Assistant. La version 0.1 couvre le littoral : les marées du jour, le marnage, le douzième de marée en cours et la prochaine grande marée, rassemblés dans un capteur de résumé qu'une carte Lovelace et une notification sur téléphone afficheront dans les versions suivantes.

> **Statut : 0.1.0, début de développement.** La carte (0.2), les notifications visuelles (0.3), la météo marine (0.4) et le profil potager (0.5) sont dans la [feuille de route](ROADMAP.md).

## D'où viennent les données

Outdoor Brief **ne récupère pas les marées sur Internet**. Il les lit dans l'intégration [Marées France](https://github.com/KipK/marees_france) (données du SHOM), à installer d'abord, au moyen de ses actions `marees_france.get_tides_data` et `marees_france.get_coefficients_data`. Tout le reste est calculé localement.

## Installation

1. Installez **Marées France** et ajoutez au moins un port.
2. Avec HACS (dépôt personnalisé) : ajoutez `https://github.com/systemedomotiqueresilient/ha-outdoor-brief`, catégorie *Intégration*, installez, redémarrez.
3. Ajoutez l'intégration **Outdoor Brief** : choisissez le profil, puis le port Marées France, puis les réglages. Une entrée par port.

## Entités (0.1)

| Entité | État | Attributs principaux |
|---|---|---|
| Résumé du jour | date du jour | `schema_version`, `tides` (4 marées : type, heure, hauteur, coefficient), `coefficients`, `tidal_range`, `next_tide`, `next_spring_tide`, `month_max` |
| Marnage | mètres, demi-marée en cours | |
| Douzième de marée | 1 à 6 | `trend`, `range_share`, `started_at`, `ends_at`, `duration_minutes` |
| Prochaine grande marée | date | `coefficient`, `threshold`, `upcoming` |
| Téléphone admin | cible de notification | `notify_service` (convention commune SDR) |

Le marnage et le douzième sont recalculés toutes les 5 minutes ; Marées France est relue toutes les heures. Le **seuil des grandes marées** (100 par défaut) se règle dans les options : décembre 2026, par exemple, culmine à 99.

## À propos du profil potager

Cette intégration fournit uniquement des données astronomiques et météorologiques mesurables. Les calendriers lunaires de jardinage (lune montante/descendante, jours racines, feuilles, fleurs, fruits) reposent sur des conventions qui diffèrent selon les almanachs. Ils ne sont pas inclus, pour ne pas imposer l'une d'elles.

## Pour les développeurs

Outdoor Brief est fait pour qu'on construise dessus, par exemple un calendrier de jardinage lunaire.

- **Contrat stable** : l'`unique_id` de chaque entité (`<entry_id>_<clé>`) et les attributs listés plus haut. Le résumé porte un champ `schema_version`.
- **Versionnage** : sémantique. Un attribut n'est renommé ou supprimé qu'en version majeure, après au moins une version où il est signalé obsolète.
- **À venir** : la déclinaison et la longitude écliptique de la Lune (0.5), matière première de tout almanach de jardinage, et des événements (`outdoor_brief_daily_summary`, `outdoor_brief_spring_tide_upcoming`…) à partir de la 0.3.

Une intégration de calendrier de jardinage lunaire peut se construire au-dessus de celle-ci : ouvrez une issue pour qu'on la référence ici.

## Licence

MIT. Données de marée : SHOM, via Marées France.
