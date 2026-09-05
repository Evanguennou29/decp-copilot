# Spécification — `decp-copilot`

**Projet B du portfolio : recherche augmentée sur les marchés publics français, avec évaluation chiffrée.**
Document à donner tel quel à Claude Code. Chaque lot correspond à une PR.

---

## 1. Problème et périmètre

### La question

> **Une PME veut répondre à un appel d'offres. Combien ont coûté les marchés comparables déjà attribués, à qui, et où ?**

La donnée existe : toutes les collectivités et administrations françaises sont légalement tenues de publier les données essentielles de leurs marchés attribués. Mais le fichier consolidé est trop volumineux pour un tableur, les intitulés sont en texte libre, et deux marchés identiques peuvent être décrits de dix façons différentes. Personne ne peut y répondre sans outil.

### Ce que le dépôt prouve

| Compétence | Où elle est visible |
|---|---|
| Recherche hybride, filtres structurés plus similarité sémantique | `src/decp/retrieval/` |
| Génération ancrée avec citations vérifiables | `src/decp/answer/` |
| **Évaluation chiffrée de la qualité de retrieval** | `eval/` plus tableau dans le README |
| API propre, mode dégradé sans clé | `src/decp/api/` |
| Interface soignée, pas un formulaire par défaut | `web/` déployé |
| Outillage agent moderne | `mcp/` (lot 6) |

Le point différenciant est la ligne en gras. Il existe des milliers de dépôts « chatbot RAG sur mes documents ». Il en existe très peu qui mesurent leur retrieval sur un jeu de questions de référence et publient les scores. C'est ce qui fera la différence en entretien, pas la stack.

### Dans le périmètre

- Marchés attribués depuis 2024, à partir du fichier DECP consolidé publié sur data.gouv.fr au format Parquet.
- Recherche hybride : filtres structurés sur montant, acheteur, code CPV, département, date, plus similarité sémantique sur l'objet du marché.
- Réponse en langage naturel citant systématiquement les marchés sources, avec leur identifiant et leur montant.
- Jeu d'évaluation d'au moins quarante questions annotées à la main, et scores publiés.
- Interface web sur mesure, déployée.

### Hors périmètre, à écrire dans le README

- Pas de conseil juridique ni de prédiction du prix d'attribution. L'outil restitue et compare, il ne recommande pas.
- Pas de concessions ni de contrats antérieurs à 2024 (schéma réglementaire différent).
- Pas d'entraînement de modèle. Les embeddings viennent d'un modèle ouvert pris tel quel.
- Pas de collecte de données personnelles, pas de scraping. Uniquement le fichier officiel.

### Source et licence

- Jeu de données : données essentielles de la commande publique consolidées, format tabulaire, sur data.gouv.fr. Publié en Parquet et CSV, mis à jour quotidiennement.
- Licence : Licence Ouverte version 2.0 (Etalab). À vérifier sur la page du jeu de données au lot 1 et citer précisément dans le README, avec le lien.
- Aucune clé d'API nécessaire pour la donnée.

### Budget modèles

- Embeddings : modèle multilingue léger exécuté en local sur CPU. L'indexation d'un corpus réduit doit tenir en quelques minutes, pas en heures.
- Génération : palier gratuit d'un fournisseur au choix, avec repli sur un modèle local via Ollama.
- **Obligation : l'application doit rester utile sans aucune clé.** Sans clé, elle renvoie les marchés comparables, leurs montants et les statistiques associées, sans rédaction. C'est un mode nominal documenté, pas une panne.

---

## 2. Architecture

```mermaid
flowchart TD
    A[DECP consolide<br/>Parquet data.gouv.fr] -->|telechargement + filtrage| B[(DuckDB<br/>marches)]
    B -->|embeddings CPU| C[Index vectoriel<br/>persiste sur disque]
    D[Question utilisateur] --> E[Extraction de filtres<br/>montant, CPV, departement, date]
    E --> F[Recherche hybride]
    B --> F
    C --> F
    F --> G{Cle LLM presente ?}
    G -->|oui| H[Reponse redigee<br/>avec citations]
    G -->|non| I[Liste de marches<br/>+ statistiques]
    H --> J[API FastAPI]
    I --> J
    J --> K[Frontend React<br/>deploye]
    J --> L[Serveur MCP<br/>lot 6]
    M[eval/ jeu de reference] -.->|recall@k, MRR| F
```

Deux décisions à justifier dans le README : la recherche hybride plutôt que purement sémantique (un montant ou un département sont des filtres exacts, les vectoriser les dégrade), et le mode dégradé sans clé (un recruteur qui teste sans configurer quoi que ce soit doit voir quelque chose fonctionner).

---

## 3. Arborescence

```
decp-copilot/
├── README.md
├── LICENSE
├── pyproject.toml
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── .gitignore
├── Makefile
├── src/
│   └── decp/
│       ├── config.py
│       ├── ingest/
│       │   ├── download.py        # recuperation du Parquet consolide
│       │   └── normalize.py       # typage, nettoyage, filtrage du perimetre
│       ├── index/
│       │   ├── embed.py           # encodage CPU par lots
│       │   └── store.py           # index vectoriel persiste
│       ├── retrieval/
│       │   ├── filters.py         # extraction de filtres depuis la question
│       │   ├── hybrid.py          # fusion des scores lexical/vectoriel
│       │   └── search.py
│       ├── answer/
│       │   ├── prompt.py
│       │   ├── generate.py        # appel LLM, repli Ollama
│       │   └── degraded.py        # mode sans cle
│       ├── api/
│       │   └── app.py             # FastAPI
│       └── cli.py
├── eval/
│   ├── questions.jsonl            # jeu de reference annote a la main
│   ├── run.py                     # calcule recall@k, MRR, latence
│   └── results.md                 # sortie d'une execution reelle, datee
├── mcp/
│   └── server.py                  # lot 6
├── web/                           # frontend, voir section 5
├── tests/
│   └── fixtures/
├── docs/
└── .github/workflows/ci.yml
```

---

## 4. Direction visuelle du frontend

Contrainte explicite : **l'interface ne doit pas ressembler à un composant par défaut.** C'est ce que regarde un lead technique en trente secondes, et c'est ce qui distingue ce dépôt du précédent.

- **Stack** : React avec Vite, TypeScript, Tailwind. Pas de bibliothèque de composants clé en main qui impose son identité visuelle.
- **Typographie** : une seule famille à caractère, pas la police système par défaut. Une graisse forte pour les montants, une graisse fine pour les métadonnées. Les chiffres en variante tabulaire pour que les colonnes s'alignent.
- **Palette** : sobre, deux couleurs plus des neutres. Les montants sont l'information principale, ils portent la seule couleur d'accent. Fond légèrement teinté plutôt que blanc pur.
- **Densité** : c'est un outil de comparaison, donc la densité prime sur l'espacement généreux. Un résultat tient sur une ligne dense et lisible, pas sur une carte de deux cents pixels de haut.
- **États** : chargement, aucun résultat, erreur, et mode dégradé sans clé doivent tous être traités visuellement. Un écran vide non géré ruine l'impression.
- **Responsive** : doit rester utilisable sur mobile, un recruteur ouvrira peut-être le lien depuis son téléphone.
- **Accessibilité** : contrastes conformes, navigation clavier fonctionnelle, libellés sur les champs.

Déploiement : Vercel ou Netlify pour le frontend, palier gratuit. API sur Hugging Face Spaces en Docker, ou Fly.io. Le frontend doit gérer proprement le réveil de l'API si elle est mise en veille.

---

## 5. Plan du README, en anglais

1. Title plus one line pitch.
2. Demo GIF plus live link, immediately after the pitch.
3. **Evaluation results** — the scores table, right at the top. This is the section that sets the repo apart, it does not belong at the bottom.
4. The problem, in three sentences.
5. How it works — the diagram plus the hybrid retrieval rationale.
6. Quickstart, three commands, and an explicit note that it runs without any API key.
7. Data source, licence, refresh cadence, scope filter applied.
8. Evaluation methodology — how the reference set was built, what recall at k and MRR mean here, how to reproduce with one command.
9. Known limitations.
10. Licence.

Règle absolue du brief : chaque chiffre du README sort d'une exécution réelle et reproductible. Les scores d'évaluation sont datés et régénérables par `make eval`.

---

## 6. Découpage en lots

**Lot 0 — Squelette (½ j)**
Structure, licence MIT, ruff, pytest, CI verte, README stub.

**Lot 1 — Ingestion et normalisation (1 j)**
Téléchargement du Parquet consolidé, filtrage du périmètre, normalisation dans DuckDB. Vérifier et documenter la licence exacte. CLI `python -m decp ingest`. *Critère : le volume final tient sur une machine sans GPU et le temps de chargement est mesuré et noté.*

**Lot 2 — Indexation et recherche hybride (1,5 j)**
Encodage CPU par lots avec un modèle multilingue léger, index persisté. Extraction de filtres depuis la question. Fusion des scores lexical et vectoriel. *Critère : une recherche renvoie des résultats pertinents en moins d'une seconde sur le corpus retenu.*

**Lot 3 — API et génération (1 j)**
FastAPI, endpoint de recherche et endpoint de réponse. Génération avec citations obligatoires vers les identifiants de marché. Mode dégradé complet sans clé. *Critère : l'API démarre et répond correctement avec un fichier `.env` vide.*

**Lot 4 — Évaluation (1 j)** ← le lot qui donne sa valeur au dépôt
Construire à la main un jeu d'au moins quarante questions avec les marchés attendus. Calculer recall at k, MRR, latence. Publier `eval/results.md` daté. Comparer au minimum deux configurations, par exemple sémantique seule contre hybride, pour que le choix d'architecture soit justifié par un chiffre. *Critère : `make eval` reproduit les scores du README.*

**Lot 5 — Frontend (1,5 j)**
Interface React selon la section 4, déployée. Les cinq états visuels traités. *Critère : le lien public fonctionne en navigation privée, sur mobile comme sur desktop.*

**→ Le dépôt est publiable et épinglable à ce stade.**

**Lot 6 — Serveur MCP (½ j, bonus)**
Exposer la recherche et la consultation d'un marché comme outils MCP. Documenter la connexion depuis un client. C'est court, rare sur GitHub, et daté 2026.

**Lot 7 — Finition (½ j)**
README définitif, GIF, topics, épinglage, ligne CV.

**Total : 7,5 j-h**, soit sept à huit semaines à ton rythme, ou **cinq semaines pour l'état publiable au lot 5**. C'est plus lourd que le projet A, principalement à cause du frontend sur mesure et du jeu d'évaluation. Les deux sont justifiés, mais autant le savoir maintenant.

---

## 7. Tests et CI

- **Retrieval** : les fonctions de fusion de scores et d'extraction de filtres sont pures, donc testables directement. Une question contenant « moins de 50 000 euros dans le Finistère » doit produire les bons filtres.
- **API** : tests sur client FastAPI, y compris le chemin sans clé.
- **Génération** : les appels au modèle sont simulés, jamais réels. Un test vérifie qu'une réponse sans citation est rejetée.
- **Aucun appel réseau dans la suite de tests**, ni vers data.gouv.fr, ni vers un fournisseur de modèle.
- **CI** : lint, tests, et construction d'un index minuscule depuis des fixtures pour valider la chaîne complète.
- L'évaluation n'est pas dans la CI, elle est lancée à la main et son résultat est versionné.

---

## 8. Le prompt de démarrage pour Claude Code

> Tu implémentes le projet décrit dans `SPEC.md` à la racine. Lis-le entièrement avant d'écrire une ligne.
> Contraintes : Python 3.11, aucune dépendance payante, aucun appel réseau dans les tests, et l'application doit fonctionner sans clé d'API.
> Travaille uniquement sur le lot 0. Quand il est terminé et que la CI est verte, arrête-toi et fais un résumé. Ne commence pas le lot 1 sans mon accord.
> Commits atomiques et lisibles au fur et à mesure.

Copie ce document dans le dépôt sous le nom `SPEC.md` avant de lancer la session.
