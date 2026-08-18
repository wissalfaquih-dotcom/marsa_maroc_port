"""
=====================================================================
 MARSA MAROC - Container Storage Management (Backend FastAPI)
---------------------------------------------------------------------
 Gestion du stock conteneurs, de l'overstay, de la facturation,
 des escales navires et de l'assistant IA.

 Lancement :
     pip install -r requirements.txt
     uvicorn main:app --reload
     -> http://127.0.0.1:8000
=====================================================================
"""

import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------
# CHEMINS PORTABLES
# Tous les chemins sont calculés à partir de l'emplacement de main.py.
# Le projet fonctionne donc depuis n'importe quel dossier, sur Windows,
# Linux ou macOS, et pour n'importe qui clonant le dépôt.
# ---------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="Marsa Maroc - Container Storage Management",
    description="Backend API for managing container stock, vessels, billing, and AI Assistant.",
    version="1.1.0",
)

# ---------------------------------------------------------------------
# CARTOGRAPHIE DU QUAI
# La capacité n'est plus une constante arbitraire : elle est calculée
# à partir de la structure réelle des zones de stockage.
# ---------------------------------------------------------------------
ZONES: Dict[str, Dict[str, Any]] = {
    "A-1": {"label": "Zone A-1 · Import sec", "quai": "Quai Nord"},
    "A-2": {"label": "Zone A-2 · Export sec", "quai": "Quai Nord"},
    "B-1": {"label": "Zone B-1 · Reefer / Frigo", "quai": "Quai Sud"},
    "B-2": {"label": "Zone B-2 · Transbordement", "quai": "Quai Sud"},
}

BAYS = [f"{i:02d}" for i in range(1, 11)]   # 10 travées par zone
ROWS = [f"{i:02d}" for i in range(1, 5)]    # 4 rangées par travée
TIERS = ["1", "2"]                          # 2 niveaux de gerbage

SLOTS_PER_ZONE = len(BAYS) * len(ROWS) * len(TIERS)     # 80
TOTAL_CAPACITY = SLOTS_PER_ZONE * len(ZONES)            # 320

# ---------------------------------------------------------------------
# BAREME DE STOCKAGE
#   Jours 1 à 5   : franchise (gratuit)
#   Jours 6 à 10  : tarif standard
#   Jours 11 et + : surcoût overstay
# ---------------------------------------------------------------------
FREE_DAYS = 5
STANDARD_END = 10
STANDARD_RATE = 500.0
OVERSTAY_RATE = 1500.0
VAT_RATE = 0.20   # TVA marocaine applicable aux prestations portuaires




import database

# Initialisation de la base de données SQLite
database.init_db()



# ---------------------------------------------------------------------
# MODELES
# ---------------------------------------------------------------------
class LoginRequest(BaseModel):
    email: str
    password: str


class ContainerModel(BaseModel):
    id: Optional[str] = None
    number: str = Field(..., examples=["MSKU9999999"])
    size: int = Field(..., ge=20, le=40, examples=[40])
    owner: str = Field(..., examples=["Maersk"])
    zone: str = Field(..., examples=["A-1"])
    bay: str = Field(..., examples=["01"])
    row: str = Field(..., examples=["01"])
    tier: str = Field(..., examples=["1"])
    status: str = Field(..., examples=["En transit"])
    entry_date: str = Field(..., examples=["2026-07-20"])
    days: int = Field(0, ge=0, examples=[5])


class PaymentRequest(BaseModel):
    paid: bool = True


class AIChatRequest(BaseModel):
    message: str
    role: Optional[str] = None
    company: Optional[str] = None


# ---------------------------------------------------------------------
# CALCULS METIER
# ---------------------------------------------------------------------
def calculate_fees(days: int) -> float:
    """Montant total de stockage pour un séjour de `days` jours."""
    if days <= FREE_DAYS:
        return 0.0
    if days <= STANDARD_END:
        return (days - FREE_DAYS) * STANDARD_RATE
    return ((STANDARD_END - FREE_DAYS) * STANDARD_RATE
            + (days - STANDARD_END) * OVERSTAY_RATE)


def fee_breakdown(days: int) -> Dict[str, Any]:
    """Détail ligne à ligne, utilisé par la facture et le simulateur."""
    free = min(days, FREE_DAYS)
    standard = max(0, min(days, STANDARD_END) - FREE_DAYS)
    over = max(0, days - STANDARD_END)
    total_ht = calculate_fees(days)
    vat = round(total_ht * VAT_RATE, 2)
    return {
        "days": days,
        "free_days": free,
        "standard_days": standard,
        "overstay_days": over,
        "standard_amount": standard * STANDARD_RATE,
        "overstay_amount": over * OVERSTAY_RATE,
        "total": total_ht,
        # Montants TTC calculés ici, et nulle part ailleurs, afin que
        # l'interface et le document imprimable affichent le même chiffre.
        "vat_rate": VAT_RATE,
        "vat_amount": vat,
        "total_ttc": round(total_ht + vat, 2),
        "is_overstay": over > 0,
        "next_day_cost": (OVERSTAY_RATE if days >= STANDARD_END
                          else (STANDARD_RATE if days >= FREE_DAYS else 0.0)),
        "days_before_billing": max(0, FREE_DAYS - days),
    }


def days_since(entry_date: str) -> int:
    try:
        return max(0, (datetime.now() - datetime.strptime(entry_date, "%Y-%m-%d")).days)
    except (ValueError, TypeError):
        return 0


def hydrate(c: Dict[str, Any]) -> Dict[str, Any]:
    """
    Renvoie une vue enrichie du conteneur SANS altérer les données stockées.
    `status` reste « Overstay » à l'affichage quand le seuil est franchi,
    mais `base_status` conserve le statut métier d'origine.
    """
    days = days_since(c["entry_date"])
    is_overstay = days > STANDARD_END
    view = dict(c)
    view["days"] = days
    view["base_status"] = c.get("base_status", c.get("status", "En transit"))
    view["status"] = "Overstay" if is_overstay else view["base_status"]
    view["slot"] = f"{c['zone']}-{c['bay']}-{c['row']}-{c['tier']}"
    view["fees"] = calculate_fees(days)
    view["is_overstay"] = is_overstay
    view["paid"] = bool(c.get("paid", False))
    return view


def all_containers() -> List[Dict[str, Any]]:
    return [hydrate(c) for c in database.get_all_containers()]


def find_container(c_id: str) -> Dict[str, Any]:
    c = database.get_container(c_id)
    if not c:
        raise HTTPException(status_code=404, detail="Conteneur introuvable")
    return c


def slot_conflict(zone: str, bay: str, row: str, tier: str,
                  ignore_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    return database.check_slot_conflict(zone, bay, row, tier, ignore_id)


def validate_slot(zone: str, bay: str, row: str, tier: str) -> None:
    if zone not in ZONES:
        raise HTTPException(status_code=400,
                            detail=f"Zone inconnue. Valeurs acceptées : {', '.join(ZONES)}")
    if bay not in BAYS:
        raise HTTPException(status_code=400,
                            detail=f"Travée invalide. Valeurs acceptées : {BAYS[0]} à {BAYS[-1]}")
    if row not in ROWS:
        raise HTTPException(status_code=400,
                            detail=f"Rangée invalide. Valeurs acceptées : {ROWS[0]} à {ROWS[-1]}")
    if tier not in TIERS:
        raise HTTPException(status_code=400,
                            detail=f"Niveau invalide. Valeurs acceptées : {', '.join(TIERS)}")


def port_stats(company: Optional[str] = None) -> Dict[str, Any]:
    data = all_containers()
    if company:
        data = [c for c in data if c["owner"].lower() == company.lower().strip()]
    overstay = [c for c in data if c["is_overstay"]]
    occupied = len(data)
    zones = []
    for code, meta in ZONES.items():
        in_zone = [c for c in data if c["zone"] == code]
        zones.append({
            "zone": code,
            "label": meta["label"],
            "quai": meta["quai"],
            "capacity": SLOTS_PER_ZONE,
            "occupied": len(in_zone),
            "free": SLOTS_PER_ZONE - len(in_zone),
            "rate": round(len(in_zone) / SLOTS_PER_ZONE * 100, 1),
            "overstay": len([c for c in in_zone if c["is_overstay"]]),
        })
    vessels = database.get_all_vessels()
    if company:
        vessels = [v for v in vessels if v["owner"].lower() == company.lower().strip()]
    return {
        "total_containers": occupied,
        "capacity": TOTAL_CAPACITY,
        "free_slots": TOTAL_CAPACITY - occupied,
        "occupancy_rate": round(occupied / TOTAL_CAPACITY * 100, 1) if TOTAL_CAPACITY else 0,
        "overstay_count": len(overstay),
        "overstay_rate": round(len(overstay) / occupied * 100, 1) if occupied else 0,
        "total_fees": sum(c["fees"] for c in data),
        "overstay_fees": sum(fee_breakdown(c["days"])["overstay_amount"] for c in data),
        "unpaid": sum(c["fees"] for c in data if not c["paid"]),
        "daily_burn": sum(fee_breakdown(c["days"])["next_day_cost"] for c in data),
        "avg_stay": round(sum(c["days"] for c in data) / occupied, 1) if occupied else 0,
        "zones": zones,
        "vessels_at_berth": len([v for v in vessels if v["status"] == "À quai"]),
        "vessels_expected": len([v for v in vessels if v["status"] == "En attente"]),
    }


# ---------------------------------------------------------------------
# ROUTES API — AUTHENTIFICATION
# ---------------------------------------------------------------------
@app.post("/api/login")
def login(req: LoginRequest):
    user = database.get_user_by_email(req.email)
    if not user or user["password"] != req.password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Identifiants incorrects")
    return {
        "status": "success",
        "role": user["role"],
        "name": user["name"],
        "email": req.email,
        "company": user["company"],
    }


# ---------------------------------------------------------------------
# ROUTES API — CONTENEURS (CRUD)
# ---------------------------------------------------------------------
@app.get("/api/conteneurs")
def get_containers(
    owner: str = Query("", description="Filtre armateur (portail B2B)"),
    zone: str = Query("", description="Filtre zone de stockage"),
    overstay: Optional[bool] = Query(None, description="Filtre overstay"),
):
    data = all_containers()
    if owner:
        data = [c for c in data if c["owner"].lower() == owner.strip().lower()]
    if zone:
        data = [c for c in data if c["zone"] == zone.upper()]
    if overstay is not None:
        data = [c for c in data if c["is_overstay"] is overstay]
    return data


@app.get("/api/conteneurs/{c_id}")
def get_container(c_id: str):
    return hydrate(find_container(c_id))


@app.post("/api/conteneurs", status_code=status.HTTP_201_CREATED)
def create_container(c: ContainerModel):
    validate_slot(c.zone, c.bay, c.row, c.tier)

    conflict = slot_conflict(c.zone, c.bay, c.row, c.tier)
    if conflict:
        raise HTTPException(
            status_code=400,
            detail=f"Emplacement {c.zone}-{c.bay}-{c.row}-{c.tier} déjà occupé par {conflict['number']}",
        )

    number = c.number.strip().upper()
    if database.check_number_exists(number):
        raise HTTPException(status_code=400,
                            detail=f"Le conteneur {number} est déjà enregistré sur le terminal")

    new_c = {
        "number": number,
        "size": c.size,
        "owner": c.owner.strip(),
        "zone": c.zone,
        "bay": c.bay,
        "row": c.row,
        "tier": c.tier,
        "base_status": c.status,
        "entry_date": c.entry_date,
        "paid": False,
    }
    inserted = database.insert_container(new_c)
    return hydrate(inserted)


@app.put("/api/conteneurs/{c_id}")
def update_container(c_id: str, c: ContainerModel):
    target = find_container(c_id)
    validate_slot(c.zone, c.bay, c.row, c.tier)

    conflict = slot_conflict(c.zone, c.bay, c.row, c.tier, ignore_id=c_id)
    if conflict:
        raise HTTPException(
            status_code=400,
            detail=f"Emplacement {c.zone}-{c.bay}-{c.row}-{c.tier} déjà occupé par {conflict['number']}",
        )

    number = c.number.strip().upper()
    if database.check_number_exists(number, ignore_id=c_id):
        raise HTTPException(status_code=400,
                            detail=f"Le numéro {number} est déjà utilisé par un autre conteneur")

    updated_data = {
        "number": number,
        "size": c.size,
        "owner": c.owner.strip(),
        "zone": c.zone,
        "bay": c.bay,
        "row": c.row,
        "tier": c.tier,
        "entry_date": c.entry_date,
        "base_status": target["base_status"] if c.status == "Overstay" else c.status,
    }
    updated = database.update_container_fields(c_id, updated_data)
    return hydrate(updated)


@app.delete("/api/conteneurs/{c_id}")
def delete_container(c_id: str):
    target = find_container(c_id)
    database.delete_container(c_id)
    return {"status": "success",
            "message": f"Conteneur {target['number']} supprimé avec succès"}


# ---------------------------------------------------------------------
# ROUTES API — CARTOGRAPHIE DU QUAI
# ---------------------------------------------------------------------
@app.get("/api/quai")
def get_yard_map():
    """Plan d'occupation : chaque zone, chaque travée, avec ses conteneurs."""
    data = all_containers()
    index: Dict[str, Dict[str, Any]] = {c["slot"]: c for c in data}

    zones = []
    for code, meta in ZONES.items():
        bays = []
        for bay in BAYS:
            slots = []
            for row in ROWS:
                for tier in TIERS:
                    key = f"{code}-{bay}-{row}-{tier}"
                    occupant = index.get(key)
                    slots.append({
                        "slot": key,
                        "row": row,
                        "tier": tier,
                        "free": occupant is None,
                        "container": None if occupant is None else {
                            "id": occupant["id"],
                            "number": occupant["number"],
                            "owner": occupant["owner"],
                            "size": occupant["size"],
                            "days": occupant["days"],
                            "status": occupant["status"],
                            "is_overstay": occupant["is_overstay"],
                            "fees": occupant["fees"],
                        },
                    })
            bays.append({
                "bay": bay,
                "occupied": len([s for s in slots if not s["free"]]),
                "capacity": len(slots),
                "slots": slots,
            })
        occupied = sum(b["occupied"] for b in bays)
        zones.append({
            "zone": code,
            "label": meta["label"],
            "quai": meta["quai"],
            "capacity": SLOTS_PER_ZONE,
            "occupied": occupied,
            "free": SLOTS_PER_ZONE - occupied,
            "rate": round(occupied / SLOTS_PER_ZONE * 100, 1),
            "bays": bays,
        })

    return {"capacity": TOTAL_CAPACITY, "zones": zones,
            "structure": {"bays": BAYS, "rows": ROWS, "tiers": TIERS}}


@app.get("/api/kpis")
def get_kpis():
    return port_stats()


@app.get("/api/referentiel")
def get_reference():
    return {
        "zones": [{"code": k, **v} for k, v in ZONES.items()],
        "bays": BAYS,
        "rows": ROWS,
        "tiers": TIERS,
        "statuses": ["En transit", "Dédouané", "Inspection", "Prêt à livrer"],
        "owners": database.get_distinct_owners(),
        "tariff": {
            "free_days": FREE_DAYS,
            "standard_end": STANDARD_END,
            "standard_rate": STANDARD_RATE,
            "overstay_rate": OVERSTAY_RATE,
        },
    }


# ---------------------------------------------------------------------
# ROUTES API — NAVIRES
# ---------------------------------------------------------------------
@app.get("/api/navires")
def get_vessels(owner: str = Query("", description="Filtre armateur")):
    vessels = (database.get_vessels_by_owner(owner) if owner
               else database.get_all_vessels())

    # Chaque navire transporte des conteneurs de plusieurs compagnies
    # (alliances, slot chartering) : on joint le détail de son escale.
    mix = database.get_cargo_mix()
    for v in vessels:
        v["cargo_mix"] = mix.get(v["id"], [])
        v["containers_on_yard"] = sum(m["count"] for m in v["cargo_mix"])
    return vessels


# ---------------------------------------------------------------------
# ROUTES API — FACTURATION
# ---------------------------------------------------------------------
@app.get("/api/factures")
def get_invoices(owner: str = Query("", description="Filtre armateur")):
    invoices = []
    for c in all_containers():
        if owner and c["owner"].lower() != owner.strip().lower():
            continue
        detail = fee_breakdown(c["days"])
        invoices.append({
            "container_id": c["id"],
            "invoice_number": f"FA-{datetime.now().year}-{int(c['id']):04d}",
            "number": c["number"],
            "owner": c["owner"],
            "slot": c["slot"],
            "entry_date": c["entry_date"],
            "days": c["days"],
            "fees": detail["total"],
            "free_days": detail["free_days"],
            "standard_days": detail["standard_days"],
            "overstay_days": detail["overstay_days"],
            "standard_amount": detail["standard_amount"],
            "overstay_amount": detail["overstay_amount"],
            "vat_amount": detail["vat_amount"],
            "total_ttc": detail["total_ttc"],
            "next_day_cost": detail["next_day_cost"],
            "status": ("Overstay" if detail["is_overstay"]
                       else ("À payer" if detail["total"] > 0 else "Gratuit")),
            "paid": c["paid"],
        })
    return invoices


@app.post("/api/factures/{c_id}/paiement")
def set_payment(c_id: str, req: PaymentRequest):
    """Encaissement réel d'une facture (remplace la simulation en dur)."""
    target = find_container(c_id)
    database.update_payment(c_id, req.paid)
    updated = find_container(c_id)
    view = hydrate(updated)
    return {
        "status": "success",
        "message": (f"Facture du conteneur {target['number']} marquée "
                    f"{'payée' if req.paid else 'impayée'}"),
        "container_id": c_id,
        "paid": req.paid,
        "fees": view["fees"],
    }


@app.get("/api/factures/simuler")
def simulate_invoice(days: int = Query(12, ge=0, le=365)):
    """Simulateur du calculateur d'overstay."""
    detail = fee_breakdown(days)
    lines = []
    if detail["free_days"]:
        lines.append({"label": f"Franchise J1–J{FREE_DAYS}",
                      "days": detail["free_days"], "rate": 0.0, "amount": 0.0})
    if detail["standard_days"]:
        lines.append({"label": f"Stockage standard J{FREE_DAYS + 1}–J{STANDARD_END}",
                      "days": detail["standard_days"], "rate": STANDARD_RATE,
                      "amount": detail["standard_amount"]})
    if detail["overstay_days"]:
        lines.append({"label": f"Surcoût overstay J{STANDARD_END + 1} et +",
                      "days": detail["overstay_days"], "rate": OVERSTAY_RATE,
                      "amount": detail["overstay_amount"]})
    return {**detail, "lines": lines}


@app.get("/api/factures/{c_id}/pdf", response_class=HTMLResponse)
def invoice_document(c_id: str):
    """
    Facture imprimable. Le navigateur ouvre la boîte d'impression :
    « Enregistrer au format PDF » produit le document final, sans
    dépendance externe de génération PDF.
    """
    c = hydrate(find_container(c_id))
    d = fee_breakdown(c["days"])
    today = datetime.now()

    rows = ""
    if d["free_days"]:
        rows += (f"<tr><td>Franchise de stockage (J1–J{FREE_DAYS})</td>"
                 f"<td class='n'>{d['free_days']}</td><td class='n'>0,00</td>"
                 f"<td class='n'>0,00</td></tr>")
    if d["standard_days"]:
        rows += (f"<tr><td>Stockage standard (J{FREE_DAYS + 1}–J{STANDARD_END})</td>"
                 f"<td class='n'>{d['standard_days']}</td>"
                 f"<td class='n'>{STANDARD_RATE:,.2f}</td>"
                 f"<td class='n'>{d['standard_amount']:,.2f}</td></tr>")
    if d["overstay_days"]:
        rows += (f"<tr><td>Surcoût overstay (J{STANDARD_END + 1} et suivants)</td>"
                 f"<td class='n'>{d['overstay_days']}</td>"
                 f"<td class='n'>{OVERSTAY_RATE:,.2f}</td>"
                 f"<td class='n'>{d['overstay_amount']:,.2f}</td></tr>")
    if not rows:
        rows = ("<tr><td>Séjour dans la période de franchise</td>"
                "<td class='n'>0</td><td class='n'>0,00</td><td class='n'>0,00</td></tr>")

    warning = ""
    if d["is_overstay"]:
        warning = (f"<div class='warn'><b>Conteneur en situation d'overstay.</b> "
                   f"{d['overstay_days']} jour(s) au-delà du palier standard, facturés "
                   f"{OVERSTAY_RATE:,.2f} MAD/jour. Chaque jour supplémentaire ajoute "
                   f"{d['next_day_cost']:,.2f} MAD.</div>")

    paid_bg = "#dcfce7" if c["paid"] else "#fee2e2"
    paid_fg = "#166534" if c["paid"] else "#991b1b"
    paid_label = "Payée" if c["paid"] else "Impayée"

    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<title>Facture {c['number']} - Marsa Maroc</title>
<style>
  @page {{ size: A4; margin: 16mm; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #0f172a; margin: 0; }}
  .bar {{ height: 8px; background: linear-gradient(90deg,#0f172a,#0284c7,#38bdf8); }}
  header {{ display: flex; justify-content: space-between; padding: 26px 0 16px;
            border-bottom: 2px solid #0f172a; }}
  .brand {{ font-size: 22px; font-weight: 800; }}
  .brand span {{ color: #0284c7; }}
  .meta {{ text-align: right; font-size: 12px; color: #475569; line-height: 1.7; }}
  h1 {{ font-size: 18px; margin: 22px 0 14px; }}
  .refs {{ display: flex; flex-wrap: wrap; gap: 32px; font-size: 13px; margin-bottom: 20px; }}
  .refs b {{ display: block; font-size: 10px; text-transform: uppercase;
             letter-spacing: 1px; color: #64748b; margin-bottom: 2px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ background: #0f172a; color: #fff; text-align: left; padding: 10px;
        font-size: 10px; letter-spacing: 1px; text-transform: uppercase; }}
  td {{ padding: 10px; border-bottom: 1px solid #e2e8f0; }}
  .n {{ text-align: right; }}
  tfoot td {{ font-weight: 700; border: none; }}
  .ttc {{ background: #0f172a; color: #fff; font-size: 15px; }}
  .warn {{ margin-top: 20px; padding: 12px 14px; border-left: 4px solid #ef4444;
           background: #fef2f2; font-size: 12px; }}
  .paid {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 11px;
           font-weight: 700; text-transform: uppercase; letter-spacing: 1px;
           background: {paid_bg}; color: {paid_fg}; }}
  footer {{ margin-top: 36px; font-size: 10px; color: #64748b;
            border-top: 1px solid #e2e8f0; padding-top: 12px; line-height: 1.7; }}
  .print {{ position: fixed; top: 16px; right: 16px; background: #0284c7; color: #fff;
            border: 0; padding: 10px 18px; border-radius: 8px; cursor: pointer; }}
  @media print {{ .print {{ display: none; }} }}
</style></head><body>
<button class="print" onclick="window.print()">Imprimer / Enregistrer en PDF</button>
<div class="bar"></div>
<header>
  <div>
    <div class="brand">MARSA <span>MAROC</span></div>
    <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:1px">
      Terminal à conteneurs · Port de Casablanca</div>
  </div>
  <div class="meta">
    <b>FA-{today.year}-{int(c['id']):04d}</b><br>
    Émise le {today.strftime('%d/%m/%Y')}<br>
    Échéance : {(today + timedelta(days=30)).strftime('%d/%m/%Y')}<br>
    <span class="paid">{paid_label}</span>
  </div>
</header>
<h1>Facture de stockage et de surestarie (overstay)</h1>
<div class="refs">
  <div><b>Client</b>{c['owner']}</div>
  <div><b>Conteneur</b>{c['number']} · {c['size']} pieds</div>
  <div><b>Emplacement</b>{c['slot']}</div>
  <div><b>Entrée</b>{c['entry_date']}</div>
  <div><b>Séjour</b>{c['days']} jours</div>
  <div><b>Statut</b>{c['status']}</div>
</div>
<table>
  <thead><tr><th>Désignation</th><th class="n">Jours</th>
    <th class="n">P.U. (MAD)</th><th class="n">Montant (MAD)</th></tr></thead>
  <tbody>{rows}</tbody>
  <tfoot>
    <tr><td colspan="3" class="n">Total H.T.</td>
      <td class="n">{d['total']:,.2f}</td></tr>
    <tr><td colspan="3" class="n">TVA {int(VAT_RATE * 100)} %</td>
      <td class="n">{d['vat_amount']:,.2f}</td></tr>
    <tr class="ttc"><td colspan="3" class="n">TOTAL T.T.C. À RÉGLER</td>
      <td class="n">{d['total_ttc']:,.2f}</td></tr>
  </tfoot>
</table>
{warning}
<footer>
  Barème appliqué : franchise J1–J{FREE_DAYS} · stockage standard J{FREE_DAYS + 1}–J{STANDARD_END}
  ({STANDARD_RATE:,.2f} MAD/jour) · overstay J{STANDARD_END + 1}+ ({OVERSTAY_RATE:,.2f} MAD/jour).<br>
  Document généré par le système de gestion de stockage Marsa Maroc.
</footer>
</body></html>""")


# ---------------------------------------------------------------------
# ROUTES API — ESPACE CLIENT B2B
# ---------------------------------------------------------------------
@app.get("/api/client/{company}")
def client_space(company: str):
    """
    Périmètre d'un armateur, filtré côté serveur.
    Le portail B2B n'a plus besoin de télécharger tout le terminal
    pour n'en afficher qu'une partie.
    """
    key = company.strip().lower()
    containers = [c for c in all_containers() if c["owner"].lower() == key]
    if not containers:
        raise HTTPException(status_code=404,
                            detail=f"Aucun conteneur enregistré pour « {company} »")

    overstay = [c for c in containers if c["is_overstay"]]
    return {
        "company": containers[0]["owner"],
        "summary": {
            "containers": len(containers),
            "overstay": len(overstay),
            "in_free_period": len([c for c in containers if c["days"] <= FREE_DAYS]),
            "total_fees": sum(c["fees"] for c in containers),
            "unpaid": sum(c["fees"] for c in containers if not c["paid"]),
            "daily_burn": sum(fee_breakdown(c["days"])["next_day_cost"] for c in containers),
            "avg_stay": round(sum(c["days"] for c in containers) / len(containers), 1),
        },
        "containers": sorted(containers, key=lambda c: -c["days"]),
        "vessels": database.get_vessels_by_owner(key),
    }


# ---------------------------------------------------------------------
# ROUTES API — ASSISTANT IA
# ---------------------------------------------------------------------
@app.post("/api/ia/assistant")
def ai_assistant(req: AIChatRequest):
    msg = req.message.lower()
    stats = port_stats(req.company)
    data = all_containers()

    # Périmètre client : un armateur ne reçoit que ses propres chiffres.
    if req.company:
        scoped = [c for c in data if c["owner"].lower() == req.company.lower()]
    else:
        scoped = data

    if any(k in msg for k in ("overstay", "délai dépassé", "retard", "dépassement")):
        top = sorted([c for c in scoped if c["is_overstay"]], key=lambda c: -c["fees"])[:5]
        detail = "\n".join(
            f"- {c['number']} ({c['owner']}) — {c['slot']} — {c['days']} j — {c['fees']:,.2f} MAD"
            for c in top) or "- Aucun conteneur en overstay."
        response = (
            f"**{stats['overstay_count']} conteneurs en Overstay** sur "
            f"{stats['total_containers']} stockés, soit un taux de "
            f"**{stats['overstay_rate']}%**.\n\n"
            f"Pénalités overstay cumulées : **{stats['overstay_fees']:,.2f} MAD**. "
            f"Sans enlèvement, le terminal facturera **{stats['daily_burn']:,.2f} MAD "
            f"supplémentaires demain**.\n\n"
            f"Dossiers les plus coûteux :\n{detail}"
        )

    elif any(k in msg for k in ("place", "libre", "quai", "capacité", "remplissage", "emplacement")):
        zones = "\n".join(
            f"- {z['zone']} : {z['occupied']}/{z['capacity']} occupés "
            f"({z['free']} libres, {z['rate']}%)" for z in stats["zones"])
        response = (
            f"Le terminal dispose de **{stats['capacity']} emplacements** "
            f"({len(ZONES)} zones × {len(BAYS)} travées × {len(ROWS)} rangées × "
            f"{len(TIERS)} niveaux).\n\n"
            f"**{stats['total_containers']} occupés**, **{stats['free_slots']} libres** "
            f"(taux d'occupation : **{stats['occupancy_rate']}%**).\n\n"
            f"Détail par zone :\n{zones}"
        )

    elif any(k in msg for k in ("facture", "pénalité", "tarif", "frais", "impayé", "barème")):
        response = (
            f"Barème de stockage Marsa Maroc :\n"
            f"- **Jours 1 à {FREE_DAYS}** : franchise, gratuit.\n"
            f"- **Jours {FREE_DAYS + 1} à {STANDARD_END}** : **{STANDARD_RATE:,.0f} MAD/jour**.\n"
            f"- **Au-delà de J{STANDARD_END}** : overstay à **{OVERSTAY_RATE:,.0f} MAD/jour**.\n\n"
            f"Montant total facturable : **{stats['total_fees']:,.2f} MAD**, "
            f"dont **{stats['overstay_fees']:,.2f} MAD** de pénalités overstay.\n"
            f"Impayés en cours : **{stats['unpaid']:,.2f} MAD**."
        )

    elif any(k in msg for k in ("navire", "escale", "bateau", "accostage", "teu")):
        vessels = database.get_all_vessels()
        at_berth = [v for v in vessels if v["status"] == "À quai"]
        waiting = [v for v in vessels if v["status"] == "En attente"]
        response = (
            f"**{len(vessels)} escales** suivies actuellement :\n"
            f"- À quai : {', '.join(v['name'] for v in at_berth) if at_berth else 'Aucun'}\n"
            f"- En attente : {', '.join(v['name'] for v in waiting) if waiting else 'Aucun'}\n\n"
            f"Volume total déchargé : **{sum(v['teu_discharged'] for v in vessels):,} TEU**."
        )

    elif any(k in msg for k in ("prévision", "prevision", "combien", "coût", "cout", "projection")):
        base = stats["overstay_fees"]
        proj = "\n".join(
            f"- J+{j} : **{base + stats['daily_burn'] * j:,.2f} MAD**" for j in (1, 3, 7))
        response = (
            f"Projection des pénalités, en supposant qu'aucun conteneur n'est enlevé "
            f"(base : {stats['daily_burn']:,.2f} MAD/jour) :\n\n{proj}\n\n"
            f"Durée moyenne de séjour actuelle : **{stats['avg_stay']} jours** "
            f"pour une franchise de {FREE_DAYS} jours."
        )

    else:
        response = (
            "Bonjour ! Je suis l'assistant IA de **Marsa Maroc**.\n\n"
            "Je peux répondre sur :\n"
            "1. **Le taux d'overstay** et les dossiers critiques.\n"
            "2. **La capacité du quai** et les emplacements libres.\n"
            "3. **Les tarifs, pénalités et impayés**.\n"
            "4. **Le planning des navires**.\n"
            "5. **Les prévisions de pénalités** à 7 jours."
        )

    return {
        "response": response,
        "context": {
            "overstay_rate": stats["overstay_rate"],
            "free_slots": stats["free_slots"],
            "occupancy_rate": stats["occupancy_rate"],
        },
    }


# ---------------------------------------------------------------------
# GESTION D'ERREURS
# ---------------------------------------------------------------------
@app.exception_handler(HTTPException)
def http_error_handler(request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code,
                        content={"status": "error", "detail": exc.detail})


# ---------------------------------------------------------------------
# FICHIERS STATIQUES ET PAGES HTML
# ---------------------------------------------------------------------
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def serve(page: str) -> FileResponse:
    path = STATIC_DIR / page
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Page {page} introuvable")
    return FileResponse(path)


@app.get("/", include_in_schema=False)
def get_index():
    return serve("index.html")


@app.get("/dashboard", include_in_schema=False)
def get_dashboard():
    return serve("dashboard.html")


@app.get("/conteneurs", include_in_schema=False)
def get_conteneurs():
    return serve("conteneurs.html")


@app.get("/navires", include_in_schema=False)
def get_navires():
    return serve("navires.html")


@app.get("/facturation", include_in_schema=False)
def get_facturation():
    return serve("facturation.html")


@app.get("/espace_client", include_in_schema=False)
def get_espace_client():
    return serve("espace_client.html")


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)