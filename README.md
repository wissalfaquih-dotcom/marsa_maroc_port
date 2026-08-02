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

## Note sur la persistance

Les données sont conservées en mémoire et réinitialisées à chaque redémarrage du
serveur — un choix adapté à la démonstration. Le passage en production suppose une
base de données (SQLite ou PostgreSQL via SQLAlchemy) et une authentification par
jeton signé.