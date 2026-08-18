# Marsa Maroc — Gestion du stockage des conteneurs

Application web de gestion d'un terminal à conteneurs : suivi du stock, détection
automatique de l'overstay, facturation des surestaries, planning des escales navires
et assistant IA intégré.

**Stack** : FastAPI (Python) · JavaScript vanilla · Bootstrap Icons

---

## Installation

```bash
git clone https://github.com/wissalfaquih-dotcom/marsa_maroc_port.git
cd marsa_maroc_port

python -m venv venv
# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload
```

L'application est disponible sur **http://127.0.0.1:8000**
La documentation interactive de l'API sur **http://127.0.0.1:8000/docs**

---

## Comptes de démonstration

| Profil | Identifiant | Mot de passe |
|---|---|---|
| Agent portuaire | `agent@marsamaroc.ma` | `agent` |
| Armateur Maersk | `maersk@armateur.com` | `maersk` |
| Armateur MSC | `msc@armateur.com` | `msc` |

---

## Barème de stockage

| Période | Tarif |
|---|---|
| Jours 1 à 5 | Franchise — gratuit |
| Jours 6 à 10 | 500 MAD / jour |
| Jour 11 et au-delà | 1 500 MAD / jour (overstay) |

Un conteneur est marqué **Overstay** dès le 11ᵉ jour de séjour. Le statut métier
(En transit, Dédouané, Inspection) est conservé séparément et reste consultable.

---

## Cartographie du quai

Chaque emplacement est identifié par `ZONE-TRAVÉE-RANGÉE-NIVEAU` (ex. `A-1-02-03-1`).

| Élément | Valeurs | Nombre |
|---|---|---|
| Zones | A-1, A-2, B-1, B-2 | 4 |
| Travées (bays) | 01 à 10 | 10 |
| Rangées (rows) | 01 à 04 | 4 |
| Niveaux (tiers) | 1 à 2 | 2 |

**Capacité totale : 320 emplacements** (80 par zone), calculée dynamiquement
depuis cette structure. Le système refuse toute affectation sur un emplacement
déjà occupé ou hors grille.

Deux conteneurs superposés n'occupent pas le même emplacement : ils occupent deux
emplacements distincts, différenciés par leur niveau de gerbage (`tier`). C'est ce
qui permet à un cariste de savoir quelle boîte aller chercher.

---

## Stock de démonstration

Le stock initial est produit par la fonction `build_initial_stock()` plutôt que
saisi en dur, afin d'obtenir un terminal réaliste : **120 conteneurs sur 320
emplacements, soit 37,5 % d'occupation**.

Règles de génération :

- **Graine aléatoire fixe** (`SEED = 2026`) — le jeu de données est identique à
  chaque démarrage, la démonstration est donc reproductible.
- **Répartition par armateur pondérée** selon des parts de présence plausibles
  (Maersk 26 %, MSC 24 %, CMA CGM 20 %, etc.) plutôt qu'uniforme.
- **Taux de remplissage inégal par zone** (A-1 à 55 %, B-2 à 19 %) pour faire
  apparaître des zones sous tension et des zones disponibles.
- **Durées de séjour déséquilibrées vers les séjours courts** (58 % en franchise,
  24 % en stockage standard, 18 % en overstay), ce qui couvre les trois paliers
  du barème.
- Numéros ISO uniques, emplacements uniques, conteneurs 40 pieds majoritaires en
  zone frigorifique.

---

## API

### Authentification
| Méthode | Route | Description |
|---|---|---|
| POST | `/api/login` | Connexion, renvoie le rôle et la société rattachée |

### Conteneurs
| Méthode | Route | Description |
|---|---|---|
| GET | `/api/conteneurs` | Liste — filtres `?owner=`, `?zone=`, `?overstay=` |
| GET | `/api/conteneurs/{id}` | Détail d'un conteneur |
| POST | `/api/conteneurs` | Création avec contrôle d'emplacement |
| PUT | `/api/conteneurs/{id}` | Modification |
| DELETE | `/api/conteneurs/{id}` | Suppression |

### Quai et indicateurs
| Méthode | Route | Description |
|---|---|---|
| GET | `/api/quai` | Plan d'occupation complet, slot par slot |
| GET | `/api/kpis` | Indicateurs du terminal |
| GET | `/api/referentiel` | Zones, statuts, barème |

### Facturation
| Méthode | Route | Description |
|---|---|---|
| GET | `/api/factures` | Factures — filtre `?owner=` |
| POST | `/api/factures/{id}/paiement` | Encaissement d'une facture |
| GET | `/api/factures/simuler?days=` | Simulateur du calculateur d'overstay |
| GET | `/api/factures/{id}/pdf` | Facture imprimable (impression → PDF) |

### Navires et portail client
| Méthode | Route | Description |
|---|---|---|
| GET | `/api/navires` | Escales — filtre `?owner=` |
| GET | `/api/client/{société}` | Périmètre d'un armateur, filtré côté serveur |

### Assistant IA
| Méthode | Route | Description |
|---|---|---|
| POST | `/api/ia/assistant` | Répond sur l'overstay, la capacité, les tarifs, les escales et les prévisions |

---

## Structure du projet

```
marsa_maroc_port/
├── main.py              # Backend FastAPI (API + service des pages)
├── database.py          # Schéma SQLite, accès aux données et seeding
├── marsa_maroc.db       # Base créée au 1er démarrage (non versionnée)
├── requirements.txt
├── README.md
├── .gitignore
└── static/
    ├── index.html          # Connexion
    ├── dashboard.html      # Tableau de bord
    ├── conteneurs.html     # Cartographie du quai et CRUD
    ├── navires.html        # Planning des escales
    ├── facturation.html    # Facturation et overstay
    ├── espace_client.html  # Portail B2B armateurs
    ├── css/style.css
    ├── js/ai-widget.js     # Assistant IA flottant
    └── images/
```

---

## Persistance des données

Les données sont stockées dans une **base SQLite** (`marsa_maroc.db`), créée
automatiquement au premier démarrage par `database.py`. Les modifications
survivent au redémarrage du serveur : un encaissement, un ajout ou un
déplacement de conteneur est écrit en base.

**Schéma** — trois tables :

| Table | Contenu | Contraintes |
|---|---|---|
| `containers` | Parc conteneurs | `number` unique · `(zone, bay, row, tier)` unique · clé étrangère vers `vessels` |
| `vessels` | Escales navires | — |
| `users` | Comptes d'accès | `email` en clé primaire |

Les clés étrangères sont activées (`PRAGMA foreign_keys=ON`), et l'unicité de
l'emplacement est garantie par la base elle-même : deux conteneurs ne peuvent
pas occuper le même slot, même en cas de requêtes concurrentes.

**Réinitialiser la base** : supprimer `marsa_maroc.db` et relancer le serveur.
Le jeu de démonstration est régénéré à l'identique grâce à la graine fixe.

Le fichier n'est pas versionné (`*.db` dans `.gitignore`) : il est recréé à
la demande et n'a pas sa place dans l'historique Git.

---

## Modélisation des escales

Un porte-conteneurs ne transporte pas uniquement les boîtes de sa propre
compagnie. Deux mécanismes du métier l'expliquent : les **alliances
maritimes**, dont les membres exploitent leurs navires en commun, et le
**slot chartering**, l'achat d'emplacements sur le navire d'un tiers.

Le jeu de démonstration reproduit ce comportement : 65 % des conteneurs
voyagent sur un navire de leur compagnie, 25 % chez un partenaire d'alliance,
10 % sur n'importe quel navire. Les alliances modélisées sont Gemini
(Maersk, Hapag-Lloyd), Ocean Alliance (CMA CGM, COSCO, Evergreen, ONE) et
Premier (ONE, Hapag-Lloyd). MSC opère seul, sans alliance — ses navires
transportent donc essentiellement ses propres conteneurs.

La page Escales affiche pour chaque navire la répartition par compagnie des
conteneurs déchargés.

---

## Limites connues

Ces points sont assumés dans le cadre d'un projet académique et documentés
plutôt que masqués :

- **L'API n'est pas authentifiée.** Le contrôle d'accès par rôle est appliqué
  côté navigateur : un client ne peut pas atteindre les pages d'exploitation.
  Mais un appel direct à `/api/conteneurs` reste possible sans jeton. Une mise
  en production exigerait un jeton signé (JWT) vérifié à chaque requête.
- **Les mots de passe sont stockés en clair** dans la table `users`. En
  production, ils seraient hachés avec bcrypt ou argon2.
- **Le tableau des conteneurs n'est pas paginé** : les 120 lignes sont rendues
  d'un coup. Acceptable à cette volumétrie, à revoir au-delà du millier.