# COMPVVD

Application web de gestion des compétitions d’arts martiaux de l’USON, déployée pour les essais sur https://compvvd-test.onrender.com.

## Fonctionnalités

- Six disciplines : **Dau, Vat, Quyen, Quyen Arme, Quyen synchro et Dau équipe**.
- Comptes administrateur, organisateur, responsable de club, assistant affecté à une aire.
- Inscriptions manuelles ou import Excel avec modèle, prévisualisation et validation par l’organisateur.
- Catégories sexe / âge / poids pour Dau et Vat ; sexe / âge pour les Quyen individuels ; fusion manuelle avant tirage.
- Dau et Vat : élimination directe, repêchages, rounds, pauses, prolongations, mort subite, scores et arbres des confrontations.
- Quyen : trois notes au dixième par passage, deux tours, sélection des cinq finalistes au-delà de cinq inscrits, passages de départage indépendants.
- Équipes composées par l’organisateur, mixtes et multiclubs. Quyen synchro : groupes seniors / moins de 18 ans. Dau équipe : poule unique et rencontres de tous contre tous.
- Chronomètres, contrôle des engagements simultanés, corrections journalisées, protection contre les validations concurrentes.
- Résultats en direct avec code spectateur, choix de l’aire / du tableau, notes, poules, arbres et classements.
- Classements individuels et clubs : 5 / 5 / 3 / 2 / 1 points ; les épreuves collectives n’y contribuent pas.

## Développement

Python 3.12 ou 3.13 :

```sh
pip install -r requirements.txt
flask --app app.web:create_app create-admin
COOKIE_SECURE=false flask --app app.web:create_app run
python -m unittest discover -s tests -v
```

Configurer `DATABASE_PATH`, `SECRET_KEY` et conserver `COOKIE_SECURE=true` en HTTPS. Le démarrage Render est documenté dans les fichiers de déploiement. Ne jamais committer de secrets ni de bases contenant des données personnelles.

## Essais et limites

Les tests de règles, d’accès et les parcours Chromium sont exécutés dans GitHub Actions. Une recette sportive avec les organisateurs reste nécessaire avant une compétition réelle.

L’instance Render de test utilise actuellement SQLite dans `/tmp` : ses données ne survivent pas aux redéploiements et redémarrages. La persistance et la restauration restent à traiter avant la mise en service réelle.

Voir le [cahier des charges](docs/CAHIER_DES_CHARGES.md), le [plan de développement](docs/ROADMAP.md), les [cas à préciser](docs/DECISIONS.md) et le [guide des disciplines](docs/DISCIPLINES.md).
