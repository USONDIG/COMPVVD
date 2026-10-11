# COMPVVD

Application web de gestion des compétitions d’arts martiaux de l’USON.

## État du projet

Cadrage fonctionnel validé. Première version **en cours de développement**, centrée sur le parcours complet du Combat individuel. Le code exécutable et ses tests seront publiés après vérification ; ce dépôt ne contient pas encore de version utilisable en compétition.

## Objectif de la première version

- Comptes créés par un administrateur, avec rôles organisateur, responsable de club et assistant de table.
- Compétitions multiples, clubs et inscriptions en ligne soumises à validation.
- Catégories sexe / âge / poids, fusion manuelle avant tirage.
- Tableaux Combat, tirage aléatoire, repêchages, chronomètres et saisie des trois juges.
- Une table de saisie par aire ; accès spectateurs par code de compétition.
- Classements individuels et clubs, exports PDF et Excel.

Les cinq autres disciplines (Lutte, Kata, Kata Arme, Combat équipe, Kata synchro) feront l’objet des étapes suivantes. Toutes les règles convenues sont conservées dans [le cahier des charges](docs/CAHIER_DES_CHARGES.md).

## Hébergement

L’application doit être hébergée en ligne avec authentification et base de données persistante. La publication du code sur GitHub ne met pas l’application en ligne. Un hébergement de serveur web sera nécessaire ; GitHub Pages seul ne convient pas.

Voir [le plan de développement](docs/ROADMAP.md) et [les décisions restant à préciser](docs/DECISIONS.md).
