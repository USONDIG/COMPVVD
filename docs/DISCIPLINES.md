# Tester les nouvelles disciplines

## Préparation commune

1. Ouvrir les inscriptions de la discipline dans Préparation.
2. Faire inscrire les participants par leurs responsables de club, individuellement ou par Excel.
3. Approuver les inscriptions en tant qu’organisateur.
4. Pour les disciplines collectives, ouvrir Équipes et composer chaque équipe parmi les membres approuvés. Tous les inscrits collectifs doivent être affectés avant génération.
5. Fermer les inscriptions, générer les catégories, fusionner si nécessaire les catégories individuelles compatibles, puis effectuer le tirage.
6. Affecter l’aire, son assistant et les officiels ; ouvrir le tableau et le lancer.

Les équipes sont mixtes et peuvent réunir plusieurs clubs. Un participant appartient au plus à une équipe par discipline. Une composition devient verrouillée après génération. Retirer un membre d’une équipe avant de modifier son inscription.

## Quyen, Quyen Arme et Quyen synchro

Trois juges distincts, sans arbitre central. Chaque passage est lancé manuellement, puis la table saisit les trois notes entre 6,0 et 10,0 au dixième. Les valeurs sont stockées en dixièmes entiers pour éviter les faux écarts d’arrondi.

- Plus de cinq inscrits : le tour 1 sélectionne cinq finalistes. Le tour 2 seul détermine les places finales.
- Deux à cinq inscrits : tous passent deux fois ; les deux totaux sont additionnés.
- Une égalité à cheval sur la cinquième place déclenche un passage de départage pour les concurrents concernés. Les égalités entièrement parmi les qualifiés n’imposent pas de passage supplémentaire au premier tour.
- Les égalités finales sont départagées par une nouvelle série de trois notes indépendante des tours précédents. Une nouvelle égalité fait recommencer le départage. Les groupes initialement à égalité sont départagés séparément.
- Le bouton de validation du tour calcule la suite ou clôture le tableau. Le classement général est alors actualisé pour les épreuves individuelles.

Les Quyen individuels sont regroupés par sexe et catégorie d’âge, sans poids. Quyen synchro : 2 à 6 membres, groupes seniors et moins de 18 ans séparés, aucune contribution aux classements individuels et clubs.

## Dau équipe

3 à 6 seniors par équipe. La catégorie senior suit le calcul par année de saison existant ; le contrôle de 18 ans révolus au jour de l’événement reste à valider.

Le tirage produit une poule unique : chaque paire d’équipes se rencontre une fois. Les rencontres et compositions des confrontations sont tirées au sort. Le nombre de confrontations égale le plus grand effectif ; les membres de la plus petite équipe peuvent combattre deux fois au maximum.

L’assistant lance manuellement la rencontre puis chaque round. Chaque confrontation suit les règles Dau : trois juges, cumul des points, pauses, deux prolongations de 15 secondes, puis mort subite à la majorité des juges. Les durées sont réglées pour le tableau.

Valider la rencontre compare les combats gagnés puis le cumul des points. En cas d’égalité, le système tire au sort un combattant éligible de chaque équipe pour une confrontation supplémentaire. Ceux ayant déjà combattu deux fois sont exclus. Si la plus petite équipe n’a plus de membre éligible, elle gagne.

Le classement compare les rencontres gagnées. À égalité entre exactement deux équipes, leur rencontre directe prime. Pour trois équipes ou plus à égalité, l’implémentation compare les combats gagnés, puis les points cumulés, et conserve les ex æquo restants. Elle ne réapplique pas la rencontre directe à un sous-groupe obtenu après ce départage (choix provisoire documenté dans DECISIONS.md).

Les équipes ne rapportent pas de points au classement général individuel ni au classement des clubs.

## Corrections et suivi

Les notes et scores peuvent être corrigés uniquement par l’organisateur ou l’administrateur. Une correction Quyen revient à la série concernée si les suivantes n’ont pas commencé. Une correction Dau équipe est bloquée lorsqu’une rencontre suivante ou un départage dépendant a commencé. Les validations sont consignées dans l’historique.

Un combattant engagé en Dau/Vat ne peut pas commencer simultanément un passage Quyen, y compris comme membre d’une équipe synchro. Une aire ne reçoit qu’un tableau actif ; les officiels ne peuvent pas être affectés simultanément à deux tableaux actifs.

Le spectateur utilise le code de compétition puis sélectionne l’aire ou le tableau. Il voit les notes et qualifications Quyen, les rencontres et classements de poule, ainsi que les arbres des épreuves individuelles. Les dates de naissance, poids, comptes et qualifications d’officiels ne sont pas affichés publiquement.

## Arbres et impressions Dau/Vat

Les rencontres sont présentées en blocs de deux concurrents, avec scores et vainqueurs, puis reliées jusqu’à la finale. Les tours futurs apparaissent en pointillés ; aucun adversaire repêché n’est inventé avant le calcul officiel. Les places 3 et 4 sont présentées séparément. Les clubs accompagnent les noms.

« Imprimer l’arbre / PDF » ouvre une page d’impression dédiée, sans contrôles de saisie. Le format par défaut est A4 paysage ; un lien permet de choisir A3 paysage pour les grands tableaux. L’arbre est vectoriel et peut être agrandi dans le PDF. Les classements du tableau et les classements généraux ont leurs propres liens d’impression.

La page publique actualise les résultats toutes les cinq secondes, sans navigation complète. Les choix d’aire et de tableau, la position de défilement et les détails ouverts sont conservés. En cas de perte réseau, le dernier état reste visible avec une indication de déconnexion ; les tentatives reprennent automatiquement. L’actualisation est suspendue pendant l’impression et quand l’onglet est masqué.
