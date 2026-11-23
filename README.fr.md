# Outdoor Brief

[English](README.md) · **Français**

Le **résumé du jour pour ce qui se passe dehors**, dans Home Assistant. La version 0.2 couvre le littoral : les marées du jour, le marnage, le douzième de marée en cours et la prochaine grande marée, rassemblés dans un capteur de résumé affichés par une carte Lovelace et envoyés chaque matin sur votre téléphone, avec l'image du résumé, et si vous le souhaitez sur une montre connectée.

> **Statut : 0.3.1, début de développement.** La météo marine (0.4) et le profil potager (0.5) sont dans la [feuille de route](ROADMAP.md).

## D'où viennent les données

Outdoor Brief **ne récupère pas les marées sur Internet**. Il les lit dans l'intégration [Marées France](https://github.com/KipK/marees_france) (données du SHOM), à installer d'abord, au moyen de ses actions `marees_france.get_tides_data` et `marees_france.get_coefficients_data`. Tout le reste est calculé localement.

## Installation

1. Installez **Marées France** et ajoutez au moins un port.
2. Avec HACS (dépôt personnalisé) : ajoutez `https://github.com/systemedomotiqueresilient/ha-outdoor-brief`, catégorie *Intégration*, installez, redémarrez.
3. Ajoutez l'intégration **Outdoor Brief** : choisissez le profil, puis le port Marées France, puis les réglages. Une entrée par port.

## Entités (0.1)

| Entité | État | Attributs principaux |
|---|---|---|
| Résumé du jour | date du jour | `schema_version`, `port`, `tides` (4 marées : type, heure, hauteur, coefficient), `coefficients`, `tidal_range`, `tide_twelfth`, `next_tide`, `next_spring_tide`, `month_max` |
| Marnage | mètres, demi-marée en cours | |
| Douzième de marée | 1 à 6 | `trend`, `range_share`, `started_at`, `ends_at`, `duration_minutes` |
| Prochaine grande marée | date | `coefficient`, `threshold`, `upcoming` |
| Téléphone admin | cible de notification | `notify_service` (convention commune SDR) |
| Image du résumé | PNG (entité image) | pièce jointe des notifications |

Le marnage et le douzième sont recalculés toutes les 5 minutes ; Marées France est relue toutes les heures. Le **seuil des grandes marées** (100 par défaut) se règle dans les options : décembre 2026, par exemple, culmine à 99.

## Carte Lovelace

La carte `outdoor-brief-card` est livrée avec l'intégration et se charge toute seule. Ajoutez-la depuis *Ajouter une carte* (recherchez « Outdoor Brief »), ou en YAML :

```yaml
type: custom:outdoor-brief-card
entity: sensor.outdoor_brief_mon_port_resume_du_jour  # votre capteur « Résumé du jour »
compact: false
```

Elle affiche le sens de la marée et le douzième en cours, un tableau matin / après-midi des pleines et basses mers avec leurs coefficients, la prochaine grande marée et le plus fort coefficient du mois. `compact: true` ne garde que le tableau et la prochaine grande marée. Après une mise à jour, rechargez la page une fois si la carte affiche encore l'ancienne version.

## Notifications

À régler dans l'écran *Notifications* (aussi dans les options) :

- **Résumé du jour** : chaque jour, seulement les jours remarquables (coefficient du jour au seuil des grandes marées, ou grande marée dans les 2 jours), ou jamais ; à l'heure choisie (07:00 par défaut). Envoyé au **téléphone admin** (convention commune SDR), avec l'image du résumé quand la cible est un service `notify.mobile_app_*`.
- **Alerte de grande marée**, 2 jours avant, avec les heures des pleines mers du jour.
- **Montre connectée** (facultative, indépendante du téléphone) : *notification complète* (même texte, sans image, envoyée même sans téléphone) ou *court avis* envoyé seulement si la notification du téléphone est bien partie. Avec une **Apple Watch**, les notifications de l'iPhone s'y affichent déjà : laissez la montre désactivée. Avec **Wear OS**, choisissez le service notify propre à la montre.
- **Événements** `outdoor_brief_daily_summary` et `outdoor_brief_spring_tide_upcoming`, émis même si les notifications sont coupées, pour vos propres automatisations.
- **Plusieurs ports** : notification propre à chaque port, ou une seule notification regroupée (une ligne par port, tableaux empilés dans l'image), envoyée selon les réglages du plus ancien port regroupé.
- **Ouvrir au toucher** : chemin d'un tableau de bord, par exemple `/lovelace/0`.
- **Téléphone admin en entité notify** (`notify.iphone_…`) : Outdoor Brief envoie au service `notify.mobile_app_…` du même appareil, seul capable de joindre l'image.
- **Test** : l'action `outdoor_brief.send_summary` envoie le résumé tout de suite.

Une entrée créée avant la 0.3 n'envoie rien tant que vous n'avez pas choisi de fréquence dans ses options.

## À propos du profil potager

Cette intégration fournit uniquement des données astronomiques et météorologiques mesurables. Les calendriers lunaires de jardinage (lune montante/descendante, jours racines, feuilles, fleurs, fruits) reposent sur des conventions qui diffèrent selon les almanachs. Ils ne sont pas inclus, pour ne pas imposer l'une d'elles.

## Pour les développeurs

Outdoor Brief est fait pour qu'on construise dessus, par exemple un calendrier de jardinage lunaire.

- **Contrat stable** : l'`unique_id` de chaque entité (`<entry_id>_<clé>`) et les attributs listés plus haut. Le résumé porte un champ `schema_version`.
- **Versionnage** : sémantique. Un attribut n'est renommé ou supprimé qu'en version majeure, après au moins une version où il est signalé obsolète.
- **Événements** (0.3) : `outdoor_brief_daily_summary` (contenu du résumé et `entry_id`) et `outdoor_brief_spring_tide_upcoming` (`date`, `coefficient`, `days_before`).
- **À venir** : la déclinaison et la longitude écliptique de la Lune (0.5), matière première de tout almanach de jardinage.

Une intégration de calendrier de jardinage lunaire peut se construire au-dessus de celle-ci : ouvrez une issue pour qu'on la référence ici.

## Licence

MIT. Données de marée : SHOM, via Marées France. La police Roboto de `fonts/` est sous licence SIL Open Font License 1.1 (`fonts/OFL.txt`).
