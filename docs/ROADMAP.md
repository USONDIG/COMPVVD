# État du développement

## Développé et couvert par les tests

- Accès par rôle, compétitions, clubs, officiels, assistants et aires.
- Inscriptions en ligne, validation organisateur, import Excel avec exemple et contrôle avant import.
- Dau individuel et Vat : tableaux, rounds, pauses, prolongations, mort subite, repêchages et places de classement.
- Quyen et Quyen Arme : deux tours, trois notes au dixième, qualification et départages.
- Quyen synchro : composition des équipes et séparation seniors / moins de 18 ans, même notation Quyen.
- Dau équipe : composition, poule unique, confrontations individuelles, départages des rencontres et classement de poule.
- Corrections journalisées et blocage des corrections qui modifieraient des épreuves dépendantes commencées.
- Suivi public par code, filtre aire / tableau, arbres, notes, poules, classements et impression.
- Tests automatisés Python et parcours réels Chromium sur ordinateur et mobile.

## Avant mise en service réelle

- Remplacer le stockage temporaire de l’instance Render de test par une solution persistante, vérifier sauvegarde et restauration.
- Effectuer une répétition générale avec plusieurs postes, assistants et officiels sur une compétition fictive complète.
- Valider les cas sportifs encore ouverts dans DECISIONS.md, notamment les corrections tardives, forfaits Quyen et critères d’âge senior.
- Dimensionner l’hébergement pour les effectifs et le nombre de spectateurs attendus.

Le dépôt USONDIG/COMPVVD et le service compvvd-test sur Render sont configurés. La mise à jour de main déclenche le déploiement automatique.
