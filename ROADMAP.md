# Feuille de route

Validée par Mathieu le 2026-11-21 (cahier des charges « Outdoor Brief — Cahier des charges »).

## Fait
- **0.3.3** : module commun admin_phone 1.2.0 (Outdoor Brief reconnu comme intégration sœur).
- **0.3.2** : l'action de test n'envoie plus en double les ports regroupés.
- **0.3.1** : image envoyée aussi quand le téléphone admin est une entité notify ; notification regroupée pour plusieurs ports ; ouverture d'un tableau de bord au toucher.
- **0.3.0** : image du résumé, notifications (résumé quotidien, grande marée J-2), montre (complète ou avis), événements, action de test.
- **0.2.2** : l'éditeur de la carte ne propose plus que les résumés du jour ; message d'erreur lisible.
- **0.2.1** : hauteur de la carte libre dans les sections, message clair si le capteur choisi n'est pas un résumé du jour.
- **0.2.0** : carte Lovelace `outdoor-brief-card` (ligne d'état, tableau matin / après-midi, prochaine grande marée et plus fort coefficient du mois, éditeur visuel).
- **0.1.0** : profil littoral, lecture de Marées France, marnage, douzièmes, prochaine grande marée, capteur résumé du jour, téléphone admin.

## Prévu
1. **0.4** : Open-Meteo Marine (houle) sur un écran distinct, **désactivé par défaut** ; indicateur de surcote ; créneau de pêche à pied.
2. **0.5** : calcul lunaire local (Python pur), profil potager (gel, pluie, lune), déclinaison et longitude écliptique exposées.
3. **0.6** : courbe de marée dans la carte, lignes météo et lune dans le tableau, contrat développeurs publié.
4. **1.0** : contrat gelé, publication HACS et Marketplace.

## Pistes
- **Port secondaire** (décalage horaire et facteur de hauteur) : seulement sur demande, Marées France couvrant déjà les petits ports.
- **Module commun 1.3.0** (décidé par Mathieu le 2026-11-23) : reconnaissance ouverte des sœurs et envoi enrichi vers une entité notify mobile_app. À sa sortie, recopier le module, utiliser `admin_sensor_attributes` et retirer le contournement local `rich_target`.
