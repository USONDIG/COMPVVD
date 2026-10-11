# Cahier des charges COMPVVD
Dernière consolidation : 9 octobre 2026. Ce document conserve les décisions exprimées par l’organisateur. Les règles spécifiques à cette compétition priment sur les règlements fédéraux.

## 1. Produit
Application web hébergée en ligne, en français, utilisable sur ordinateur, tablette et téléphone. Plusieurs compétitions indépendantes. Authentification par identifiant et mot de passe pour les espaces de gestion. Une aire accueille un tableau à la fois et possède sa propre table de saisie. Plusieurs aires peuvent fonctionner simultanément.

Disciplines : Combat individuel, Kata, Lutte, Kata Arme, Combat équipe et Kata synchro. L’organisateur peut ouvrir et fermer les inscriptions séparément pour chacune. Un participant peut s’inscrire à toutes les disciplines auxquelles il est éligible, sans plafond de nombre.

## 2. Utilisateurs
- **Administrateur** : crée les comptes et la liste des clubs.
- **Organisateur de compétition** : approuve ou refuse les inscriptions, gère sa compétition, les officiels, aires, catégories et tableaux. Lui seul modifie une inscription approuvée ou un résultat validé.
- **Responsable de club connecté** : inscrit les participants de son club via le formulaire en ligne. Les inscriptions nécessitent l’approbation de l’organisateur. Aucune auto-inscription publique ni auto-création de compte.
- **Assistant de table** : compte affecté à une aire ; lance manuellement les rounds, manipule les chronomètres et saisit toutes les notes, scores et décisions.
- **Spectateur** : consulte les résultats et classements en direct avec un code généré pour la compétition, sans compte utilisateur.

Les équipes multiclubs sont constituées par l’organisateur. Les juges ne saisissent pas sur des appareils personnels.

## 3. Participants, catégories et grades
Informations utiles : identité, date de naissance, sexe, club, grade, poids déclaré, disciplines. La pesée le jour de la compétition n’est pas obligatoire.

Ordre des grades, du moins au plus élevé :
1. Ceinture blanche
2. Premier cap
3. Deuxième cap
4. Troisième cap
5. Ceinture bleue
6. Ceinture noire

Combat et Lutte : répartition **sexe → catégorie d’âge → poids**.
Kata et Kata Arme : **sexe → catégorie d’âge**, sans poids.
Kata synchro et Combat équipe : règles collectives ci-dessous.

Base d’âge du karaté FFK, déterminée par année de naissance et saison :
| Catégorie | Âge de référence |
|---|---|
| Mini-poussins | 4–5 ans |
| Poussins | 6–7 ans |
| Pupilles | 8–9 ans |
| Benjamins | 10–11 ans |
| Minimes | 12–13 ans |
| Cadets | 14–15 ans |
| Juniors | 16–17 ans |
| Seniors | 18 ans et plus |

Les grilles de poids sont celles du karaté par défaut, modifiables par compétition, y compris pour la Lutte. La base de référence vérifiée est le [règlement FFK 2026–2027, pages 16–17](https://www.ffkarate.fr/wp-content/uploads/2026/09/REGLEMENT-COMPETITION-KARATE_2026.pdf). Ne pas confondre ces valeurs par défaut avec les règles sportives propres à COMPVVD.

Si une catégorie n’a qu’un participant, l’organisateur peut la fusionner manuellement avec une autre. Il n’y a pas d’attribution automatique de la première place demandée.

## 4. Combat individuel
### Tirage
Premier tour aléatoire, en évitant autant que possible les rencontres entre membres du même club. Aucune modification manuelle des confrontations après le tirage.

### Premier tour impair
Exemple à sept inscrits : trois combats sont organisés. Le septième participant attend, puis affronte le meilleur perdant de ces trois combats. Le vainqueur de ce combat complémentaire rejoint le deuxième tour. Ce n’est pas une qualification automatique de l’inscrit isolé.

### Repêchage des tours suivants
Si le nombre de qualifiés pour le tour suivant est impair, on repêche **un perdant du tour concerné** selon :
1. Plus petit écart final de points, prolongations comprises.
2. Grade le moins élevé.
3. Participant le plus jeune.
4. Tirage au sort si tous les critères sont identiques.

Un participant peut être repêché plusieurs fois. La finale n’engendre pas de repêchage parce qu’il ne reste qu’un vainqueur.

### Rounds et scores
Valeurs par défaut : **2 rounds de 60 secondes**, avec **30 secondes de pause**. Nombre et durée des rounds et durée des pauses modifiables par tableau avant son lancement. Chaque round est lancé manuellement par l’assistant.

À la fin de chaque round, chacun des trois juges attribue ses points aux deux combattants. La table dispose de **six champs par round** (trois par combattant), avec aides à la saisie +1, +2, +3 et correction avant validation.

Le score final cumule les points des trois juges sur tous les rounds et les prolongations. On ne classe pas au nombre de rounds gagnés.

### Égalité
Une prolongation de 15 secondes, puis une seconde de 15 secondes si l’égalité persiste, puis mort subite. Le premier point de mort subite doit être accordé par au moins deux des trois juges.

### Forfait, abandon, disqualification
L’adversaire gagne. Le participant concerné n’est pas éligible au repêchage à partir de ce combat.

### Places 3 à 5
Les deux perdants des demi-finales s’affrontent pour les places 3 et 4. La 5e place revient au meilleur perdant des quarts de finale, suivant les critères de repêchage.

## 5. Lutte
Élimination directe et fonctionnement des tableaux comparable au Combat individuel.

Mise à jour du 11 octobre 2026 : la Lutte utilise les mêmes rounds que le Combat (nombre, durée et pauses configurables, départ manuel, cumul des scores). L’arbitre central seul annonce les scores, saisis par l’assistant en fin de round. En cas d’égalité : deux prolongations de 15 secondes, puis premier point en mort subite sans limite de temps.

Critères de repêchage et de meilleure 5e place :
1. Perdant ayant combattu le plus longtemps.
2. Grade le moins élevé.
3. Plus jeune.
4. Tirage au sort si égalité complète.

Le chronomètre mesure la durée réellement combattue : les interruptions sont exclues. Combat de classement pour les places 3 et 4. Le temps effectif cumule les rounds et prolongations, hors pauses, interruptions et délai de saisie après la fin du round.

## 6. Kata, Kata Arme et Kata synchro
Mêmes règles de notation pour ces trois disciplines.

Trois juges donnent chacun une note **de 6,0 à 10,0 au dixième**. Trois champs de saisie par participant ou équipe, à chaque tour. La somme des trois notes constitue le total du passage.

### Plus de cinq participants / équipes
Premier tour éliminatoire : sélection des cinq meilleurs.
Deuxième tour : classement final basé **uniquement sur les notes du deuxième tour**.

### Cinq participants / équipes ou moins
Deux tours pour tous. Le classement utilise **la somme des deux tours**.

### Égalités
Nouveau passage des concurrents concernés, noté par les trois juges. Ces notes sont indépendantes des tours précédents et servent uniquement à départager les places concernées. Les passages se répètent jusqu’au départage.

Il faut traiter les égalités à la limite des cinq qualifiés comme celles affectant une place finale.

## 7. Kata synchro
- **2 à 6 membres** par équipe.
- Équipes multiclubs et mixtes autorisées.
- Deux groupes : **seniors** et **moins de 18 ans**.
- **Interdiction de mélanger seniors et moins de 18 ans dans une équipe**.
- Dans le groupe moins de 18 ans, différentes catégories d’âge peuvent être réunies.
- Classement propre à l’épreuve ; aucun point au classement général individuel ni au classement des clubs.

## 8. Combat équipe
- **3 à 6 membres**.
- Réservé aux **seniors (18 ans et plus)** : ne pas confondre avec le classement général « adultes » dès 12 ans.
- Équipes mixtes et multiclubs autorisées.
- Confrontations libres entre seniors, sans contrainte de sexe ni de poids.
- **Poule unique : chaque équipe rencontre toutes les autres. Aucun tableau à élimination directe ni repêchage.**

### Rencontre entre deux équipes
Nombre de combats égal à l’effectif de la plus grande équipe.
Un membre peut combattre deux fois au maximum, uniquement si son équipe a moins de membres que l’équipe adverse.
Exemple : 3 contre 5 = cinq combats, deux membres de la petite équipe passent deux fois.
Ordre de passage aléatoire retenu après que l’organisateur a indiqué ne pas avoir de préférence.

Chaque combat applique les scores cumulés, les deux prolongations de 15 secondes et la mort subite du Combat individuel.

### Équipe gagnante
1. Plus grand nombre de combats gagnés.
2. Cumul des points marqués dans la rencontre.
3. Si égalité persistante : combat supplémentaire, un combattant tiré au sort dans chaque équipe.
4. Les combattants ayant déjà combattu deux fois sont exclus du tirage.
5. Si la petite équipe n’a plus aucun combattant éligible (notamment 3 contre 6), **la plus petite équipe gagne**.

### Classement de la poule
1. Nombre de rencontres remportées.
2. Pour deux équipes à égalité : résultat de leur confrontation directe.
3. Pour une égalité circulaire à trois : nombre total de combats individuels gagnés dans la poule.
4. Total des points marqués dans la poule.
5. Équipes ex æquo si l’égalité persiste.

Aucun point au classement général individuel ni au classement des clubs.

## 9. Classements
Indépendants pour chaque compétition, sans cumul entre compétitions.

| Place | Points |
|---|---:|
| 1re | 5 |
| 2e | 5 |
| 3e | 3 |
| 4e | 2 |
| 5e | 1 |

Les deux premières places rapportent bien le même nombre de points : barème explicitement confirmé.

Chaque participant cumule ses points de **Combat individuel, Lutte, Kata et Kata Arme**.
Deux classements généraux **mixtes** :
- Enfants : moins de 12 ans.
- « Adultes » : 12 ans et plus.

Départage individuel : points, puis moins gradé, puis plus jeune. À points, grade et date de naissance identiques : ex æquo.

Classement des clubs : addition des points individuels de tous les participants du club, enfants et adultes confondus. Les clubs à égalité restent ex æquo.

Les résultats en cours sont visibles en direct. La proposition de calcul consolide les points lorsqu’un tableau est clôturé pour ne pas attribuer prématurément des places.

## 10. Aires, officiels et chronomètres
Par tableau :
- Combat : trois juges et un arbitre central.
- Kata / Kata Arme / Kata synchro : trois juges.
- Lutte : un arbitre central, sans juges d’aire.
- Un assistant de saisie par table / aire.

Enregistrer les informations des officiels et leurs affectations. Lancer le tableau ouvre un chronomètre global jusqu’à sa clôture. Les chronomètres des combats et pauses sont séparés.

L’assistant peut suspendre et reprendre un combat sur interruption décidée par l’arbitre. Les chronomètres doivent rester cohérents après rechargement ou reconnexion.

Bloquer le lancement d’un passage ou combat lorsqu’un participant concerné est déjà engagé sur une autre aire, y compris comme membre d’équipe.

## 11. Consultation et exports
Code généré par compétition pour accès spectateurs aux résultats en direct.
Écran public par aire : noms, scores et chronomètre, utilisable sur télévision.
Exports :
- tableaux et classements en PDF ;
- listes d’inscrits en Excel.

## 12. Hébergement et fonctionnement
Application hébergée sur le Web. Pas d’ordinateur serveur obligatoire dans la salle. Les postes utilisent le Wi-Fi avec accès Internet. Le besoin initial de fonctionnement sans Internet a été remplacé par la demande explicite d’application hébergée.

Les mots de passe, dates de naissance et données d’inscription ne doivent pas être publiés dans les dépôts, journaux publics ou vues spectateurs.

