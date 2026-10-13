# Sauvegarde avant les arbres imprimables — 13 octobre 2026

Version sauvegardée et vérifiée avant toute modification des arbres :

- Dépôt : USONDIG/COMPVVD.
- Branche : `backup/2026-10-13-avant-arbres-imprimables`.
- Commit exact : `4628620316860bbc9a7b1b4650e79eb094714ab5`.
- Version en ligne correspondante : déploiement Render `dep-db6s96ijnfac73ea2c7g`, service `srv-db4u5enlot8c73d1gm6g`.
- Cette version comprend les six disciplines, les inscriptions Excel et les parcours validés par 72 tests et Chromium.

## Revenir au code précédent

Les modifications d’arbre sont livrées dans une PR distincte. Après sa fusion par squash, utiliser **Revert** sur cette PR dans GitHub et fusionner la PR de retour arrière après vérification. Cela conserve l’historique et déclenche le redéploiement automatique de main sur Render. Ne pas supprimer ni réécrire la branche de sauvegarde.

Autre possibilité : redéployer le commit sauvegardé depuis le tableau de bord Render. Vérifier ensuite le commit servi, `/health`, la connexion et les pages des six disciplines. Désactiver ou ajuster le déploiement automatique si un rollback Render temporaire doit être conservé alors que main contient toujours le nouveau code.

## Portée de la sauvegarde

Cette sauvegarde protège **le code et ses dépendances déclarées**, pas la base SQLite de l’instance de test. Un retour arrière du code ne restaure pas les inscriptions ni les scores. Le service actuel conserve SQLite dans un stockage temporaire : un redémarrage ou redéploiement peut effacer ces données. Une base persistante et une sauvegarde/restauration des données restent nécessaires avant utilisation réelle.

La nouvelle présentation ne change ni le schéma des compétitions ni les règles sportives : les rencontres futures dessinées sont une projection en lecture seule, jamais enregistrée comme résultat ou tirage.
