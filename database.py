"""
=====================================================================
 database.py — Couche de persistance SQLite pour Marsa Maroc
---------------------------------------------------------------------
 Au premier lancement, crée le fichier marsa_maroc.db, initialise les
 tables et insère le jeu de données de démonstration (120 conteneurs
 + 7 navires). Aux lancements suivants, les données existantes sont
 conservées telles quelles.
 
 Pour réinitialiser : supprimer marsa_maroc.db puis relancer le serveur.
=====================================================================
"""

import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Chemin de la base (au même niveau que main.py) ─────────────────────
DB_PATH = Path(__file__).resolve().parent / "marsa_maroc.db"

# ── Constantes de seeding ──────────────────────────────────────────────
SEED = 2026
TARGET_STOCK = 120
FREE_DAYS = 5
STANDARD_END = 10

CARRIERS = [
    {"name": "Maersk",      "prefix": "MSKU", "weight": 26},
    {"name": "MSC",         "prefix": "MSCI", "weight": 24},
    {"name": "CMA CGM",     "prefix": "CMAC", "weight": 20},
    {"name": "Hapag-Lloyd",  "prefix": "HLAG", "weight": 12},
    {"name": "Evergreen",   "prefix": "EGHU", "weight": 10},
    {"name": "COSCO",       "prefix": "CSNU", "weight": 5},
    {"name": "ONE",         "prefix": "ONEU", "weight": 3},
]

ZONES_LIST = ["A-1", "A-2", "B-1", "B-2"]
ZONE_FILL  = {"A-1": 0.55, "A-2": 0.42, "B-1": 0.34, "B-2": 0.19}
BAYS   = [f"{i:02d}" for i in range(1, 11)]
ROWS   = [f"{i:02d}" for i in range(1, 5)]
TIERS  = ["1", "2"]
BASE_STATUSES  = ["En transit", "Dédouané", "Inspection", "Prêt à livrer"]
STATUS_WEIGHTS = [35, 40, 12, 13]


# =====================================================================
#  CONNEXION
# =====================================================================
def get_connection() -> sqlite3.Connection:
    """Retourne une connexion SQLite avec row_factory = sqlite3.Row."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Convertit un sqlite3.Row en dict standard (conteneur)."""
    d = dict(row)
    d["id"] = str(d["id"])          # le frontend attend un string
    d["paid"] = bool(d.get("paid", 0))
    return d


def _vessel_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Convertit un sqlite3.Row en dict standard (navire)."""
    return dict(row)


# =====================================================================
#  CREATION DES TABLES
# =====================================================================
def _create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS containers (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            number      TEXT    UNIQUE NOT NULL,
            size        INTEGER NOT NULL CHECK(size IN (20, 40)),
            owner       TEXT    NOT NULL,
            zone        TEXT    NOT NULL,
            bay         TEXT    NOT NULL,
            row         TEXT    NOT NULL,
            tier        TEXT    NOT NULL,
            base_status TEXT    NOT NULL DEFAULT 'En transit',
            entry_date  TEXT    NOT NULL,
            paid        INTEGER DEFAULT 0,
            vessel_id   TEXT,
            UNIQUE(zone, bay, row, tier),
            FOREIGN KEY(vessel_id) REFERENCES vessels(id)
        );

        CREATE TABLE IF NOT EXISTS vessels (
            id              TEXT PRIMARY KEY,
            name            TEXT NOT NULL,
            owner           TEXT NOT NULL,
            status          TEXT NOT NULL,
            eta             TEXT,
            etd             TEXT,
            berth           TEXT,
            teu_discharged  INTEGER DEFAULT 0,
            teu_loaded      INTEGER DEFAULT 0,
            image           TEXT
        );

        CREATE TABLE IF NOT EXISTS users (
            email           TEXT PRIMARY KEY,
            password        TEXT NOT NULL,
            role            TEXT NOT NULL,
            name            TEXT NOT NULL,
            company         TEXT
        );
    """)
    conn.commit()


# =====================================================================
#  SEEDING INITIAL
# =====================================================================
def _entry(days_ago: int) -> str:
    return (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")


def _seed_containers(conn: sqlite3.Connection) -> None:
    """Insère 120 conteneurs de démonstration (graine fixe = reproductible)."""
    rng = random.Random(SEED)

    # 1. Tirage des emplacements, zone par zone.
    slots: list = []
    for zone in ZONES_LIST:
        every_slot = [(zone, bay, row, tier)
                      for bay in BAYS for row in ROWS for tier in TIERS]
        wanted = round(len(every_slot) * ZONE_FILL[zone])
        slots.extend(rng.sample(every_slot, wanted))

    rng.shuffle(slots)
    slots = slots[:TARGET_STOCK]

    # 2. Constitution des conteneurs.
    carrier_pool = [c for c in CARRIERS for _ in range(c["weight"])]
    used_numbers: set = set()

    for zone, bay, row, tier in slots:
        carrier = rng.choice(carrier_pool)

        while True:
            number = f"{carrier['prefix']}{rng.randint(1000000, 9999999)}"
            if number not in used_numbers:
                used_numbers.add(number)
                break

        bucket = rng.choices(["court", "moyen", "long"], weights=[58, 24, 18])[0]
        if bucket == "court":
            days_ago = rng.randint(0, FREE_DAYS)
        elif bucket == "moyen":
            days_ago = rng.randint(FREE_DAYS + 1, STANDARD_END)
        else:
            days_ago = rng.randint(STANDARD_END + 1, 25)

        size = 20 if (zone != "B-1" and rng.random() < 0.38) else 40
        base_status = rng.choices(BASE_STATUSES, weights=STATUS_WEIGHTS)[0]
        paid = 1 if rng.random() < (0.55 if days_ago <= STANDARD_END else 0.15) else 0

        owner_name = carrier["name"]
        vessel_id = None
        if owner_name == "Maersk":
            vessel_id = "v3"
        elif owner_name == "MSC":
            vessel_id = "v1" if rng.random() < 0.5 else "v6"
        elif owner_name == "CMA CGM":
            vessel_id = "v2"
        elif owner_name == "Hapag-Lloyd":
            vessel_id = "v4"
        elif owner_name == "Evergreen":
            vessel_id = "v5"
        elif owner_name == "COSCO":
            vessel_id = "v6"
        elif owner_name == "ONE":
            vessel_id = "v7"

        conn.execute(
            "INSERT INTO containers (number, size, owner, zone, bay, row, tier, "
            "base_status, entry_date, paid, vessel_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (number, size, owner_name, zone, bay, row, tier,
             base_status, _entry(days_ago), paid, vessel_id),
        )

    conn.commit()


def _seed_vessels(conn: sqlite3.Connection) -> None:
    """Insère les 7 navires de démonstration."""
    now = datetime.now()
    vessels = [
        ("v1", "MSC AMELIA", "MSC", "À quai",
         now.strftime("%Y-%m-%d %H:%M"),
         (now + timedelta(days=2)).strftime("%Y-%m-%d %H:%M"),
         "Poste 1", 2450, 1800, "/static/images/ship_msc.jpg"),
        ("v2", "CMA CGM ANTOINE DE SAINT EXUPERY", "CMA CGM", "En attente",
         (now + timedelta(hours=14)).strftime("%Y-%m-%d %H:%M"),
         (now + timedelta(days=3)).strftime("%Y-%m-%d %H:%M"),
         "Poste 2", 1890, 1200, "/static/images/ship_cma.jpg"),
        ("v3", "MAERSK MC-KINNEY MOLLER", "Maersk", "En attente",
         (now + timedelta(days=2)).strftime("%Y-%m-%d %H:%M"),
         (now + timedelta(days=5)).strftime("%Y-%m-%d %H:%M"),
         "Poste 1", 3100, 2500, "/static/images/ship_maersk.jpg"),
        ("v4", "HAPAG-LLOYD BERLIN EXPRESS", "Hapag-Lloyd", "À quai",
         now.strftime("%Y-%m-%d %H:%M"),
         (now + timedelta(days=3)).strftime("%Y-%m-%d %H:%M"),
         "Poste 3", 1950, 1400, "/static/images/ship_hapag.jpg"),
        ("v5", "EVERGREEN EVER GIVEN", "Evergreen", "En attente",
         (now + timedelta(days=1)).strftime("%Y-%m-%d %H:%M"),
         (now + timedelta(days=4)).strftime("%Y-%m-%d %H:%M"),
         "Poste 2", 2200, 1600, "/static/images/ship_evergreen.jpg"),
        ("v6", "COSCO SHIPPING UNIVERSE", "COSCO", "À quai",
         (now - timedelta(hours=8)).strftime("%Y-%m-%d %H:%M"),
         (now + timedelta(days=1)).strftime("%Y-%m-%d %H:%M"),
         "Poste 4", 1780, 1100, "/static/images/ship_cosco.jpg"),
        ("v7", "ONE COLUMBA", "ONE", "En attente",
         (now + timedelta(days=3)).strftime("%Y-%m-%d %H:%M"),
         (now + timedelta(days=6)).strftime("%Y-%m-%d %H:%M"),
         "Poste 1", 2800, 2100, "/static/images/ship_one.jpg"),
    ]
    for v in vessels:
        conn.execute(
            "INSERT INTO vessels (id, name, owner, status, eta, etd, berth, "
            "teu_discharged, teu_loaded, image) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", v,
        )
    conn.commit()


def _seed_users(conn: sqlite3.Connection) -> None:
    """Insère les utilisateurs de démonstration pour chaque armateur du système."""
    users = [
        ("agent@marsamaroc.ma", "agent", "Agent Portuaire", "Wissal - Agent Portuaire", None),
        ("maersk@armateur.com", "maersk", "Armateur B2B", "Maersk Operations", "Maersk"),
        ("msc@armateur.com", "msc", "Armateur B2B", "MSC Operations", "MSC"),
        ("cma@armateur.com", "cma", "Armateur B2B", "CMA CGM Operations", "CMA CGM"),
        ("hapag@armateur.com", "hapag", "Armateur B2B", "Hapag-Lloyd Operations", "Hapag-Lloyd"),
        ("evergreen@armateur.com", "evergreen", "Armateur B2B", "Evergreen Operations", "Evergreen"),
        ("cosco@armateur.com", "cosco", "Armateur B2B", "COSCO Operations", "COSCO"),
        ("one@armateur.com", "one", "Armateur B2B", "ONE Operations", "ONE"),
        ("zim@armateur.com", "zim", "Armateur B2B", "ZIM Operations", "ZIM"),
    ]
    for u in users:
        conn.execute(
            "INSERT OR IGNORE INTO users (email, password, role, name, company) VALUES (?, ?, ?, ?, ?)", u
        )
    conn.commit()


def init_db() -> None:
    """Point d'entrée : crée les tables et insère les données si la base est vide.

    L'ordre d'insertion importe : chaque conteneur porte un `vessel_id`
    contraint par une clé étrangère vers `vessels`. Les navires doivent
    donc exister avant les conteneurs, sinon SQLite rejette l'insertion
    avec « FOREIGN KEY constraint failed ».
    """
    conn = get_connection()
    _create_tables(conn)

    # 1. Navires — aucune dépendance
    count = conn.execute("SELECT COUNT(*) FROM vessels").fetchone()[0]
    if count == 0:
        _seed_vessels(conn)
        print("[DB] 7 navires de démonstration insérés.")

    # 2. Conteneurs — dépendent des navires ci-dessus
    count = conn.execute("SELECT COUNT(*) FROM containers").fetchone()[0]
    if count == 0:
        _seed_containers(conn)
        print(f"[DB] {TARGET_STOCK} conteneurs de démonstration insérés.")

    # 3. Utilisateurs — aucune dépendance
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if count == 0:
        _seed_users(conn)
        print("[DB] Utilisateurs de démonstration insérés.")

    conn.close()
    print(f"[DB] Base SQLite prête : {DB_PATH}")


# =====================================================================
#  CRUD — CONTENEURS
# =====================================================================
def get_all_containers() -> List[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM containers ORDER BY id").fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_container(c_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM containers WHERE id = ?",
                       (int(c_id),)).fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def check_slot_conflict(zone: str, bay: str, row: str, tier: str,
                        ignore_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    if ignore_id:
        r = conn.execute(
            "SELECT * FROM containers "
            "WHERE zone=? AND bay=? AND row=? AND tier=? AND id!=?",
            (zone, bay, row, tier, int(ignore_id)),
        ).fetchone()
    else:
        r = conn.execute(
            "SELECT * FROM containers WHERE zone=? AND bay=? AND row=? AND tier=?",
            (zone, bay, row, tier),
        ).fetchone()
    conn.close()
    return _row_to_dict(r) if r else None


def check_number_exists(number: str, ignore_id: Optional[str] = None) -> bool:
    conn = get_connection()
    if ignore_id:
        r = conn.execute(
            "SELECT 1 FROM containers WHERE number=? AND id!=?",
            (number, int(ignore_id)),
        ).fetchone()
    else:
        r = conn.execute(
            "SELECT 1 FROM containers WHERE number=?", (number,),
        ).fetchone()
    conn.close()
    return r is not None


def insert_container(data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO containers "
        "(number, size, owner, zone, bay, row, tier, base_status, entry_date, paid, vessel_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (data["number"], data["size"], data["owner"], data["zone"],
         data["bay"], data["row"], data["tier"], data["base_status"],
         data["entry_date"], int(data.get("paid", False)), data.get("vessel_id")),
    )
    new_id = cursor.lastrowid
    conn.commit()
    row = conn.execute("SELECT * FROM containers WHERE id = ?",
                       (new_id,)).fetchone()
    conn.close()
    return _row_to_dict(row)


def update_container_fields(c_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_connection()
    conn.execute(
        "UPDATE containers SET number=?, size=?, owner=?, zone=?, bay=?, "
        "row=?, tier=?, base_status=?, entry_date=?, vessel_id=? WHERE id=?",
        (data["number"], data["size"], data["owner"], data["zone"],
         data["bay"], data["row"], data["tier"], data["base_status"],
         data["entry_date"], data.get("vessel_id"), int(c_id)),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM containers WHERE id = ?",
                       (int(c_id),)).fetchone()
    conn.close()
    return _row_to_dict(row)


def delete_container(c_id: str) -> bool:
    conn = get_connection()
    cursor = conn.execute("DELETE FROM containers WHERE id = ?", (int(c_id),))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def update_payment(c_id: str, paid: bool) -> None:
    conn = get_connection()
    conn.execute("UPDATE containers SET paid = ? WHERE id = ?",
                 (int(paid), int(c_id)))
    conn.commit()
    conn.close()


def get_distinct_owners() -> List[str]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT owner FROM containers ORDER BY owner"
    ).fetchall()
    conn.close()
    return [r["owner"] for r in rows]


# =====================================================================
#  CRUD — NAVIRES
# =====================================================================
def get_all_vessels() -> List[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM vessels ORDER BY id").fetchall()
    conn.close()
    return [_vessel_to_dict(r) for r in rows]


def get_vessels_by_owner(owner: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM vessels WHERE LOWER(owner) = LOWER(?) ORDER BY id",
        (owner,),
    ).fetchall()
    conn.close()
    return [_vessel_to_dict(r) for r in rows]


# =====================================================================
#  CRUD — UTILISATEURS
# =====================================================================
def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE LOWER(email) = LOWER(?)",
        (email.strip(),),
    ).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None