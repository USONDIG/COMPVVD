# Plan de développement

## Lot 1 — Parcours complet Dau individuel
Statut : développement en cours, non livré.

### Infrastructure et accès
- Serveur web et base de données persistante.
- Comptes créés par l’administrateur, autorisations côté serveur, sessions et protection CSRF.
- Clubs, compétitions et affectation des organisateurs.
- Historique des validations et corrections.

### Inscriptions et catégories
- Formulaire pour responsables de club.
- Validation par l’organisateur, modification après validation réservée à l’organisateur.
- Génération sexe / âge / poids, catégories FFK modifiables, fusion avant tirage.
- Tirage définitif sans édition manuelle, évitement des duels intra-club.

### Déroulement
- Une table par aire, configuration des officiels et assistant.
- Rounds lancés manuellement, chronomètres persistants côté serveur.
- Six saisies par round, prolongations et votes de mort subite.
- Premier tour impair, repêchages répétés, finale et places 3–5.
- Corrections par l’organisateur avec gestion explicite des tours dépendants.

### Résultats et exports
- Classements mixtes enfants / adultes et clubs.
- Consultation par code de compétition, affichage par aire.
- Export Excel et impression PDF.

### Critères de recette
- Deux responsables de club ne peuvent pas consulter ou modifier leurs données privées respectives.
- Un assistant ne peut pas opérer l’aire d’un autre.
- Une double validation ne doit pas ajouter deux fois les scores.
- Une requête fondée sur une révision périmée est refusée.
- Tester tous les effectifs de 2 à 32, notamment 3, 5, 7 et 9.
- Tester égalités complètes, repêchages multiples, exclusions et dau complémentaire.
- Vérifier les classements après correction.
- Tester le parcours sur ordinateur, tablette et téléphone.
- Vérifier les sauvegardes, le redémarrage et la protection des pages publiques.

## Lot 2 — Vat
Rounds, pauses et prolongations comme en Dau ; scores de l’arbitre central, repêchage sur durée effective cumulée et classement.

## Lot 3 — Quyens
Quyen, Quyen Arme, notes au dixième, deux modes selon effectif, égalités à la qualification et au classement final, passages indépendants de départage.

## Lot 4 — Équipes
Constitution par l’organisateur, équipes multiclubs, Quyen synchro par groupe senior/non-senior, poule unique Dau équipe, effectifs asymétriques et départages.

## Lot 5 — Répétition générale et mise en service
Compétition fictive complète, postes simultanés, écran public, sauvegarde/restauration, validation avec officiels et assistants.

Le dépôt GitHub et l’hébergement de l’application sont deux livraisons distinctes. Aucun hébergement public n’a encore été configuré.

