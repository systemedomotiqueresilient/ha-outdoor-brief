# Feuille de route

Validée par Mathieu le 2026-11-21 (cahier des charges « Outdoor Brief — Cahier des charges »).

## Fait
- **0.1.0** : profil littoral, lecture de Marées France, marnage, douzièmes, prochaine grande marée, capteur résumé du jour, téléphone admin.

## Prévu
1. **0.2** : carte Lovelace `outdoor-brief-card` (tableau du jour, pied « prochaine grande marée » et plus fort coefficient du mois), livrée avec l'intégration.
2. **0.3** : entité image du résumé (PNG local) et notifications (résumé quotidien, grande marée à J-2), événements `outdoor_brief_*`.
3. **0.4** : Open-Meteo Marine (houle) sur un écran distinct, **désactivé par défaut** ; indicateur de surcote ; créneau de pêche à pied.
4. **0.5** : calcul lunaire local (Python pur), profil potager (gel, pluie, lune), déclinaison et longitude écliptique exposées.
5. **0.6** : courbe de marée dans la carte, contrat développeurs publié.
6. **1.0** : contrat gelé, publication HACS et Marketplace.

## Pistes
- **Port secondaire** (décalage horaire et facteur de hauteur) : seulement sur demande, Marées France couvrant déjà les petits ports.
- **SIBLING_PLATFORMS** : faire ajouter `outdoor_brief` au module commun dans `ha-sdr` (version 1.2.0), pour que les intégrations sœurs lisent aussi ce téléphone admin.
