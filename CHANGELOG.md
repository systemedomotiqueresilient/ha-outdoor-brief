# Changelog

Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/), versions selon [SemVer](https://semver.org/lang/fr/).

## [0.4.0] - 2026-11-27

### Ajouté
- **Pêche à pied** : capteur « Prochain créneau de pêche à pied » (horodatage du début, créneaux suivants en attributs). Un créneau va de 2 h avant à 1 h après une basse mer dont le coefficient atteint le seuil (réglage, 70 par défaut) ; la basse mer prend le plus fort coefficient des pleines mers voisines. Option « de jour seulement » (activée par défaut, lever et coucher du soleil au lieu de HA).
- **Surcote estimée** (cm, effet de baromètre inverse : 1 cm par hPa sous 1013,25 hPa, vent non compté). Pression d'un capteur local ou d'une entité météo choisis dans les réglages, sinon d'Open-Meteo. Entité créée seulement s'il y a une source de pression ; recalcul dès que le capteur change.
- **Open-Meteo, écran distinct et désactivé par défaut** (5e écran de configuration et entrée « Conditions de mer » des options) : vagues, houle (hauteur, période, direction), température de l'eau et pression au niveau de la mer, relues toutes les heures au point choisi. Désactivé : aucune requête, aucune entité de mer. Requête d'essai à l'activation (erreurs « injoignable » et « pas de données de vagues pour ce point »). Un échec ne rend indisponibles que les entités de mer.
- **Résumé du jour** : blocs `fishing`, `marine` et `surge` (ajouts seulement, `schema_version` reste à 1).
- **Carte, tableau de bord et image** : lignes « Pêche à pied » et « Mer » sous le tableau de chaque port ; source Open-Meteo citée quand elle est utilisée. Texte détaillé des notifications : créneaux de pêche du jour.

## [0.3.5] - 2026-11-25

### Ajouté
- **Tableau de bord dédié `/outdoor-brief`** (panneau « Outdoor Brief » de la barre latérale, ouvert à tous les utilisateurs, pensé pour le téléphone) : la reproduction **en temps réel** du rapport de la notification. Mêmes ports, même ordre, même contenu : ligne d'état, tableau matin / après-midi, prochaine grande marée, plus fort coefficient du mois. Avec `?entry=<id>`, un seul port.
- **Cible prédéfinie du toucher** : si « Ouvrir au toucher » est vide, la notification ouvre ce tableau de bord : le rapport regroupé, ou le port seul pour une notification propre à un port.
- **Carte `custom:outdoor-brief-report-card`** : le même rapport, à placer dans n'importe quel tableau de bord (option `entry` pour un seul port).
- **Résumé du jour** : attribut `report` (`entry_id`, `rank`, `grouped`), pour reproduire l'ordre et le regroupement de la notification. Ajout seulement, `schema_version` reste à 1.
- **Rechargement automatique** du tableau de bord après une mise à jour (une fois, puis un bandeau « Recharger »), comme le panneau de Package Keeper.

### Modifié
- Le manifest se charge aussi après `panel_custom`.

## [0.3.4] - 2026-11-24

Demandée par Mathieu après la première notification regroupée du matin.

### Ajouté
- **Texte de la notification : court ou détaillé** (court par défaut). Le texte court (« Coef 90-93 · prochaine BM 10:06 », ou « Coef 90-93 · 3 ports, détails dans l'image ») n'est utilisé **que si l'image du résumé est réellement jointe**. Une cible qui ne reçoit pas l'image garde le texte détaillé, pour ne rien perdre.
- **Destinataires supplémentaires** : n'importe quels services ou entités notify, en plus du téléphone admin (un autre téléphone Companion, Telegram, Signal, ntfy, Gotify, e-mail…). Les téléphones Companion reçoivent l'image, le tag et le lien ; les autres canaux reçoivent seulement le titre et le texte détaillé, sans `data` qu'ils pourraient refuser. Résumé du jour et alerte de grande marée.

### Corrigé
- **Ligne d'état coupée à droite dans l'image** quand elle est longue (« … · BM 10:0 ») : sa taille de police s'ajuste maintenant à la largeur.

## [0.3.3] - 2026-11-23

### Modifié
- **Module commun `admin_phone.py` 1.2.0**, recopié tel quel depuis `ha-sdr` (commit 77a8992, SHA-256 `1d720150…545b`, vérifié par un test). Outdoor Brief fait désormais partie des intégrations sœurs : le téléphone choisi ici est proposé à l'installation des autres intégrations SDR. Aucun autre changement. Le contournement local `rich_target` reste en place jusqu'à la 1.3.0 du module, qui l'intégrera pour toutes les intégrations.

## [0.3.2] - 2026-11-23

### Corrigé
- **Action `outdoor_brief.send_summary` sans port précisé, avec des ports regroupés** : elle envoyait la notification regroupée et, en plus, celle de chaque port secondaire. Les ports secondaires sont maintenant ignorés, puisqu'ils figurent déjà dans la notification regroupée. Précisé, un port secondaire envoie toujours son propre résumé, pour tester. Le passage quotidien n'était pas concerné.

## [0.3.1] - 2026-11-23

Tirée du premier essai des notifications sur l'iPhone de Mathieu.

### Corrigé
- **Image absente quand le téléphone admin est une entité notify** (`notify.iphone_…`). Le module commun passe alors par `notify.send_message`, qui ne transmet ni image, ni tag, ni lien. Pour une entité notify de l'app Companion, Outdoor Brief envoie maintenant au service `notify.mobile_app_…` du même appareil. Même chose pour la montre.

### Ajouté
- **Plusieurs ports : notification propre ou regroupée.** Les ports réglés sur « regroupée » partagent une seule notification : une ligne par port, et une image où leurs tableaux sont empilés. Elle suit les réglages (heure, fréquence, téléphone, montre) du plus ancien port regroupé ; les autres n'y ajoutent que leurs marées. L'alerte de grande marée est regroupée de la même façon. Les événements restent émis pour chaque port.
- **Ouvrir au toucher** : chemin d'un tableau de bord (par exemple `/lovelace/0`), transmis en `url` (iOS) et `clickAction` (Android).

## [0.3.0] - 2026-11-23

### Ajouté
- **Image du résumé** : entité `image` (`<entry_id>_summary_image`), PNG de 1080 px de large dessiné localement avec Pillow (fourni par Home Assistant), même contenu que la carte, thème clair ou sombre. Redessinée seulement quand le résumé change.
- **Notifications sur le téléphone admin** (convention SDR) :
  - résumé du jour à l'heure choisie (07:00 par défaut), chaque jour, seulement les jours remarquables, ou jamais. Jour remarquable en 0.3 : coefficient du jour au seuil des grandes marées, ou grande marée dans les 2 jours ;
  - alerte de grande marée 2 jours avant, avec les heures des pleines mers du jour (sauf « Jamais ») ;
  - l'image du résumé est jointe quand la cible est un service `notify.mobile_app_*` (une entité notify ne transporte pas de pièce jointe).
- **Montre** (facultative, indépendante du téléphone) : cible notify à part, et trois modes : désactivée, notification complète (même texte, sans image, envoyée même sans téléphone), ou court avis envoyé seulement si la notification du téléphone est bien partie.
- **Anti-doublon persistant** : un même envoi ne part qu'une fois par jour (ou par grande marée), même après un redémarrage.
- **Événements** `outdoor_brief_daily_summary` (contenu du résumé) et `outdoor_brief_spring_tide_upcoming` (J-2), émis même si les notifications sont coupées.
- **Action `outdoor_brief.send_summary`** : envoie le résumé tout de suite, pour tester (réponse : port → envoyé ou non).
- **Écran « Notifications »** à l'installation ; les options deviennent un menu (Réglages / Notifications).
- **Police Roboto** (SIL OFL 1.1, réduite aux caractères latins, 2 × 32 Ko) livrée dans `fonts/` : la police par défaut de Pillow n'a pas les lettres accentuées.

### Modifié
- **Une entrée créée avant la 0.3 n'envoie rien** tant que la fréquence n'a pas été choisie dans les options : pas de notification surprise après la mise à jour.

## [0.2.2] - 2026-11-22

### Corrigé
- **L'éditeur de la carte ne propose plus que les capteurs « Résumé du jour »**. Il proposait aussi « Prochaine grande marée », de même classe (date), avec lequel la carte ne peut rien afficher.
- **Message lisible** quand le capteur choisi n'est pas un résumé : il cite le nom du capteur au lieu de son identifiant, et passe à la ligne au lieu de déborder de la carte.

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
