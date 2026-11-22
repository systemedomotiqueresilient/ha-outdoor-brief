# Changelog

Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/), versions selon [SemVer](https://semver.org/lang/fr/).

## [0.2.1] - 2026-11-22

Tirée du premier essai de la carte sur l'instance de Mathieu.

### Corrigé
- **Bas de la carte coupé dans la vue en sections** (visible en mode édition) : la carte n'impose plus de hauteur à la grille, elle prend celle de son contenu.
- **Heure et hauteur coupées sur deux lignes** quand la carte est étroite : les cases du tableau ne passent plus à la ligne.
- **Message trompeur avec un mauvais capteur** : choisir « Prochaine grande marée » au lieu de « Résumé du jour » affichait « Résumé indisponible : vérifiez l'intégration Marées France ». La carte dit maintenant que ce capteur n'est pas un résumé du jour, et réserve le premier message à un résumé réellement indisponible.

## [0.2.0] - 2026-11-22

### Ajouté
- **Carte Lovelace `outdoor-brief-card`**, livrée avec l'intégration et chargée automatiquement : aucune ressource à déclarer, ni second dépôt.
  - Ligne d'état : sens de la marée, douzième en cours, marnage, heure de la prochaine pleine ou basse mer.
  - Tableau du jour en deux colonnes, matin et après-midi : pleines mers, basses mers, coefficients. Une case vide affiche « — » les jours à trois marées.
  - Pied : prochaine grande marée (date, coefficient, nombre de jours) et plus fort coefficient du mois.
  - Éditeur visuel : choix du capteur « Résumé du jour » et mode compact. La carte apparaît dans la liste « Ajouter une carte ».
  - Textes en français ou en anglais selon la langue de Home Assistant ; heures dans le fuseau de l'installation.
  - JavaScript sans dépendance ; aucune donnée d'entité n'est insérée en HTML.
- **Résumé du jour** : attributs `port` et `tide_twelfth`. Ajouts seulement, `schema_version` reste à 1.

### Modifié
- Le manifest dépend de `http` et se charge après `frontend`, pour servir la carte.

## [0.1.0] - 2026-11-21

Première version : profil littoral, à partir de l'intégration Marées France.

### Ajouté
- **Config flow en trois écrans** : profil (littoral seulement en 0.1), port (un appareil Marées France), réglages. Une entrée par port ; le même port ne peut pas être ajouté deux fois. Abandon expliqué si Marées France n'est pas installée.
- **Lecture de Marées France par ses actions** `get_tides_data` (8 jours) et `get_coefficients_data` (1 an), toujours avec le `device_id` du port, toutes les heures. Aucun appel Internet.
- **Capteurs** : résumé du jour (contrat `schema_version` 1), marnage, douzième de marée, prochaine grande marée. Marnage et douzième recalculés toutes les 5 minutes sans relire la source.
- **Seuil des grandes marées réglable** (100 par défaut, de 70 à 120) dans le config flow et les options.
- **Téléphone admin** : `admin_phone.py` MODULE_VERSION 1.1.0 copié tel quel depuis `ha-sdr` (SHA-256 `32b3619e…e1f9`, vérifié par un test). Capteur diagnostic `<entry_id>_admin_notify_target`, valeur dans `entry.data`. Aucune notification envoyée avant la 0.3.

### Publication
- Icônes de marque (`brand/icon.png`, `brand/icon@2x.png`) et catégorie Marketplace `weather_alerts.forecasts`, exigées par les contrôles HACS et Marketplace.

### Formats Marées France gérés
- Nombres transmis en texte, `---` pour une valeur absente, `tide.none` / `--:--` les jours à trois marées, jours à un seul coefficient.
- Heures `HH:MM` locales sans fuseau : reconstruites avec le fuseau de Home Assistant.
