# Changelog

Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/), versions selon [SemVer](https://semver.org/lang/fr/).

## [0.1.0] - 2026-11-21

Première version : profil littoral, à partir de l'intégration Marées France.

### Ajouté
- **Config flow en trois écrans** : profil (littoral seulement en 0.1), port (un appareil Marées France), réglages. Une entrée par port ; le même port ne peut pas être ajouté deux fois. Abandon expliqué si Marées France n'est pas installée.
- **Lecture de Marées France par ses actions** `get_tides_data` (8 jours) et `get_coefficients_data` (1 an), toujours avec le `device_id` du port, toutes les heures. Aucun appel Internet.
- **Capteurs** : résumé du jour (contrat `schema_version` 1), marnage, douzième de marée, prochaine grande marée. Marnage et douzième recalculés toutes les 5 minutes sans relire la source.
- **Seuil des grandes marées réglable** (100 par défaut, de 70 à 120) dans le config flow et les options.
- **Téléphone admin** : `admin_phone.py` MODULE_VERSION 1.1.0 copié tel quel depuis `ha-sdr` (SHA-256 `32b3619e…e1f9`, vérifié par un test). Capteur diagnostic `<entry_id>_admin_notify_target`, valeur dans `entry.data`. Aucune notification envoyée avant la 0.3.

### Formats Marées France gérés
- Nombres transmis en texte, `---` pour une valeur absente, `tide.none` / `--:--` les jours à trois marées, jours à un seul coefficient.
- Heures `HH:MM` locales sans fuseau : reconstruites avec le fuseau de Home Assistant.
