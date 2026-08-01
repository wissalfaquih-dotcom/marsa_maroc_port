import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import os
from typing import List, Optional

app = FastAPI(
    title="Marsa Maroc - Container Storage Management",
    description="Backend API for managing container stock, vessels, billing, and AI Assistant.",
    version="1.0.0"
)

# Mock databases
USERS = {
    "agent@marsamaroc.ma": {"password": "agent", "role": "Agent Portuaire", "name": "Wissal - Agent Portuaire"},
    "maersk@armateur.com": {"password": "maersk", "role": "Armateur B2B", "name": "Maersk Operations"},
    "msc@armateur.com": {"password": "msc", "role": "Armateur B2B", "name": "MSC Operations"}
}

# Initial Containers Mock Data
containers_db = [
    {
        "id": "1",
        "number": "MSKU9876543",
        "size": 40,
        "owner": "Maersk",
        "zone": "A-1",
        "bay": "02",
        "row": "03",
        "tier": "1",
        "status": "En transit",
        "entry_date": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"),
        "days": 3
    },
    {
        "id": "2",
        "number": "MSKU1234567",
        "size": 20,
        "owner": "Maersk",
        "zone": "A-1",
        "bay": "02",
        "row": "03",
        "tier": "2",
        "status": "Overstay",
        "entry_date": (datetime.now() - timedelta(days=12)).strftime("%Y-%m-%d"),
        "days": 12
    },
    {
        "id": "3",
        "number": "MSCI8889991",
        "size": 40,
        "owner": "MSC",
        "zone": "A-2",
        "bay": "05",
        "row": "01",
        "tier": "1",
        "status": "Dédouané",
        "entry_date": (datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d"),
        "days": 4
    },
    {
        "id": "4",
        "number": "MSCI4445552",
        "size": 20,
        "owner": "MSC",
        "zone": "B-1",
        "bay": "01",
        "row": "04",
        "tier": "1",
        "status": "Overstay",
        "entry_date": (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d"),
        "days": 15
    },
    {
        "id": "5",
        "number": "CMAC7776662",
        "size": 40,
        "owner": "CMA CGM",
        "zone": "B-2",
        "bay": "03",
        "row": "02",
        "tier": "1",
        "status": "Inspection",
        "entry_date": (datetime.now() - timedelta(days=8)).strftime("%Y-%m-%d"),
        "days": 8
    },
    {
        "id": "6",
        "number": "CMAC1112223",
        "size": 40,
        "owner": "CMA CGM",
        "zone": "A-1",
        "bay": "04",
        "row": "01",
        "tier": "1",
        "status": "Dédouané",
        "entry_date": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
        "days": 2
    },
    {
        "id": "7",
        "number": "MSKU5554443",
        "size": 20,
        "owner": "Maersk",
        "zone": "B-1",
        "bay": "08",
        "row": "02",
        "tier": "1",
        "status": "En transit",
        "entry_date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
        "days": 1
    },
    {
        "id": "8",
        "number": "HLAG9990001",
        "size": 40,
        "owner": "Hapag-Lloyd",
        "zone": "A-2",
        "bay": "01",
        "row": "02",
        "tier": "1",
        "status": "Overstay",
        "entry_date": (datetime.now() - timedelta(days=18)).strftime("%Y-%m-%d"),
        "days": 18
    }
]

# Vessel Mock Data
vessels_db = [
    {
        "id": "v1",
        "name": "MSC AMELIA",
        "owner": "MSC",
        "status": "À quai",
        "eta": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "etd": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d %H:%M"),
        "berth": "Poste 1",
        "teu_discharged": 2450,
        "teu_loaded": 1800,
        "image": "/static/images/ship_msc.jpg"
    },
    {
        "id": "v2",
        "name": "CMA CGM ANTOINE DE SAINT EXUPERY",
        "owner": "CMA CGM",
        "status": "En attente",
        "eta": (datetime.now() + timedelta(hours=14)).strftime("%Y-%m-%d %H:%M"),
        "etd": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d %H:%M"),
        "berth": "Poste 2",
        "teu_discharged": 1890,
        "teu_loaded": 1200,
        "image": "/static/images/ship_cma.jpg"
    },
    {
        "id": "v3",
        "name": "MAERSK MC-KINNEY MOLLER",
        "owner": "Maersk",
        "status": "En attente",
        "eta": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d %H:%M"),
        "etd": (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d %H:%M"),
        "berth": "Poste 1",
        "teu_discharged": 3100,
        "teu_loaded": 2500,
        "image": "/static/images/ship_maersk.jpg"
    },
    {
        "id": "v4",
        "name": "HAPAG-LLOYD BERLIN EXPRESS",
        "owner": "Hapag-Lloyd",
        "status": "À quai",
        "eta": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "etd": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d %H:%M"),
        "berth": "Poste 3",
        "teu_discharged": 1950,
        "teu_loaded": 1400,
        "image": "/static/images/ship_hapag.jpg"
    },
    {
        "id": "v5",
        "name": "EVERGREEN EVER GIVEN",
        "owner": "Evergreen",
        "status": "En attente",
        "eta": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M"),
        "etd": (datetime.now() + timedelta(days=4)).strftime("%Y-%m-%d %H:%M"),
        "berth": "Poste 2",
        "teu_discharged": 2200,
        "teu_loaded": 1600,
        "image": "/static/images/ship_evergreen.jpg"
    },
    {
        "id": "v6",
        "name": "COSCO SHIPPING UNIVERSE",
        "owner": "COSCO",
        "status": "À quai",
        "eta": (datetime.now() - timedelta(hours=8)).strftime("%Y-%m-%d %H:%M"),
        "etd": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M"),
        "berth": "Poste 4",
        "teu_discharged": 1780,
        "teu_loaded": 1100,
        "image": "/static/images/ship_msc.jpg"
    },
    {
        "id": "v7",
        "name": "ONE COLUMBA",
        "owner": "ONE",
        "status": "En attente",
        "eta": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d %H:%M"),
        "etd": (datetime.now() + timedelta(days=6)).strftime("%Y-%m-%d %H:%M"),
        "berth": "Poste 1",
        "teu_discharged": 2800,
        "teu_loaded": 2100,
        "image": "/static/images/ship_cma.jpg"
    }
]

# Models
class LoginRequest(BaseModel):
    email: str
    password: str

class ContainerModel(BaseModel):
    id: Optional[str] = None
    number: str = Field(..., example="MSKU9999999")
    size: int = Field(..., ge=20, le=40, example=40)
    owner: str = Field(..., example="Maersk")
    zone: str = Field(..., example="A-1")
    bay: str = Field(..., example="01")
    row: str = Field(..., example="01")
    tier: str = Field(..., example="1")
    status: str = Field(..., example="En transit")
    entry_date: str = Field(..., example="2026-07-20")
    days: int = Field(..., ge=0, example=5)

class AIChatRequest(BaseModel):
    message: str

# Helper to calculate overstay fees
def calculate_fees(days: int) -> float:
    # Jours 1-5: gratuit
    # Jours 6-10: 500 MAD/jour
    # Jours >10: 1500 MAD/jour (Overstay)
    if days <= 5:
        return 0.0
    elif days <= 10:
        return (days - 5) * 500.0
    else:
        # 5 jours gratuits + 5 jours à 500 + (days - 10) à 1500
        return (5 * 500.0) + (days - 10) * 1500.0

# API Routes

@app.post("/api/login")
def login(req: LoginRequest):
    user = USERS.get(req.email)
    if not user or user["password"] != req.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants incorrects"
        )
    return {
        "status": "success",
        "role": user["role"],
        "name": user["name"],
        "email": req.email
    }

@app.get("/api/conteneurs", response_model=List[ContainerModel])
def get_containers():
    # Recalculate days based on entry_date for realism
    for c in containers_db:
        try:
            entry_dt = datetime.strptime(c["entry_date"], "%Y-%m-%d")
            diff = datetime.now() - entry_dt
            c["days"] = max(0, diff.days)
            # Update status to Overstay automatically if days > 10
            if c["days"] > 10:
                c["status"] = "Overstay"
        except Exception:
            pass
    return containers_db

@app.post("/api/conteneurs", status_code=status.HTTP_201_CREATED)
def create_container(c: ContainerModel):
    # Verify slot availability
    for existing in containers_db:
        if (
            existing["zone"] == c.zone
            and existing["bay"] == c.bay
            and existing["row"] == c.row
            and existing["tier"] == c.tier
            and existing["id"] != c.id
        ):
            raise HTTPException(
                status_code=400,
                detail=f"Emplacement {c.zone}-{c.bay}-{c.row}-{c.tier} déjà occupé par {existing['number']}"
            )
            
    # Auto-generate ID if not provided
    c_id = str(max([int(x["id"]) for x in containers_db]) + 1) if containers_db else "1"
    
    # Calculate days based on entry date
    try:
        entry_dt = datetime.strptime(c.entry_date, "%Y-%m-%d")
        days = max(0, (datetime.now() - entry_dt).days)
    except Exception:
        days = c.days
        
    new_c = {
        "id": c_id,
        "number": c.number,
        "size": c.size,
        "owner": c.owner,
        "zone": c.zone,
        "bay": c.bay,
        "row": c.row,
        "tier": c.tier,
        "status": "Overstay" if days > 10 else c.status,
        "entry_date": c.entry_date,
        "days": days
    }
    containers_db.append(new_c)
    return new_c

@app.put("/api/conteneurs/{c_id}")
def update_container(c_id: str, c: ContainerModel):
    # Find container
    target = None
    for item in containers_db:
        if item["id"] == c_id:
            target = item
            break
            
    if not target:
        raise HTTPException(status_code=404, detail="Conteneur introuvable")
        
    # Verify slot availability
    for existing in containers_db:
        if (
            existing["zone"] == c.zone
            and existing["bay"] == c.bay
            and existing["row"] == c.row
            and existing["tier"] == c.tier
            and existing["id"] != c_id
        ):
            raise HTTPException(
                status_code=400,
                detail=f"Emplacement {c.zone}-{c.bay}-{c.row}-{c.tier} déjà occupé par {existing['number']}"
            )
            
    try:
        entry_dt = datetime.strptime(c.entry_date, "%Y-%m-%d")
        days = max(0, (datetime.now() - entry_dt).days)
    except Exception:
        days = c.days

    target["number"] = c.number
    target["size"] = c.size
    target["owner"] = c.owner
    target["zone"] = c.zone
    target["bay"] = c.bay
    target["row"] = c.row
    target["tier"] = c.tier
    target["status"] = "Overstay" if days > 10 else c.status
    target["entry_date"] = c.entry_date
    target["days"] = days
    
    return target

@app.delete("/api/conteneurs/{c_id}")
def delete_container(c_id: str):
    global containers_db
    target = None
    for item in containers_db:
        if item["id"] == c_id:
            target = item
            break
            
    if not target:
        raise HTTPException(status_code=404, detail="Conteneur introuvable")
        
    containers_db = [x for x in containers_db if x["id"] != c_id]
    return {"status": "success", "message": f"Conteneur {target['number']} supprimé avec succès"}

@app.get("/api/navires")
def get_vessels():
    return vessels_db

@app.get("/api/factures")
def get_invoices():
    invoices = []
    for c in containers_db:
        days = c["days"]
        fees = calculate_fees(days)
        invoices.append({
            "container_id": c["id"],
            "number": c["number"],
            "owner": c["owner"],
            "entry_date": c["entry_date"],
            "days": days,
            "fees": fees,
            "status": "Overstay" if days > 10 else ("À payer" if fees > 0 else "Gratuit"),
            "paid": fees == 0.0 or c["id"] in ["1", "3", "7"]  # Simulating some paid
        })
    return invoices

@app.post("/api/ia/assistant")
def ai_assistant(req: AIChatRequest):
    msg = req.message.lower()
    
    # Analyze live port statistics to generate precise answers
    total = len(containers_db)
    overstay_count = sum(1 for x in containers_db if x["days"] > 10)
    overstay_pct = (overstay_count / total * 100) if total > 0 else 0
    
    # 20 slots per zone (A-1, A-2, B-1, B-2) = 80 slots total
    capacity = 80
    occupied = len(containers_db)
    free_slots = capacity - occupied
    
    # Total penalties
    total_penalties = sum(calculate_fees(x["days"]) for x in containers_db)
    
    # Intelligent response matching
    if "overstay" in msg or "délai dépassé" in msg or "retard" in msg:
        response = (
            f"Actuellement, Marsa Maroc compte **{overstay_count} conteneurs en Overstay** "
            f"sur un total de {total} conteneurs stockés, soit un taux d'overstay de **{overstay_pct:.1f}%**. "
            f"Les pénalités associées s'élèvent à un montant cumulé de **{total_penalties:,.2f} MAD**."
        )
    elif "place" in msg or "libre" in msg or "quai" in msg or "capacité" in msg or "remplissage" in msg:
        response = (
            f"Le terminal portuaire a une capacité maximale de **{capacity} slots**. "
            f"Actuellement, **{occupied} slots** sont occupés et **{free_slots} slots sont disponibles** "
            f"pour accueillir de nouveaux conteneurs (taux d'occupation : **{(occupied/capacity*100):.1f}%**).\n\n"
            f"Zones de stockage actives :\n"
            f"- Zone A-1 : {sum(1 for x in containers_db if x['zone']=='A-1')} occupés\n"
            f"- Zone A-2 : {sum(1 for x in containers_db if x['zone']=='A-2')} occupés\n"
            f"- Zone B-1 : {sum(1 for x in containers_db if x['zone']=='B-1')} occupés\n"
            f"- Zone B-2 : {sum(1 for x in containers_db if x['zone']=='B-2')} occupés"
        )
    elif "facture" in msg or "pénalité" in msg or "tarif" in msg or "frais" in msg:
        response = (
            f"Le barème de facturation de stockage de Marsa Maroc est appliqué comme suit :\n"
            f"- **Jours 1 à 5** : Gratuit.\n"
            f"- **Jours 6 à 10** : Tarif standard de **500 MAD/jour**.\n"
            f"- **Jours > 10** : Tarif Overstay critique de **1 500 MAD/jour**.\n\n"
            f"Les pénalités globales calculées s'élèvent à **{total_penalties:,.2f} MAD** pour l'ensemble des conteneurs en dépassement."
        )
    elif "navire" in msg or "scale" in msg or "bateau" in msg:
        active_ships = [s for s in vessels_db if s["status"] == "À quai"]
        coming_ships = [s for s in vessels_db if s["status"] == "En attente"]
        response = (
            f"Nous gérant actuellement **{len(vessels_db)} escales de navires** :\n"
            f"- À quai : {', '.join([s['name'] for s in active_ships]) if active_ships else 'Aucun'}\n"
            f"- En attente : {', '.join([s['name'] for s in coming_ships]) if coming_ships else 'Aucun'}.\n"
            f"Le volume total à décharger prévu s'élève à **{sum(s['teu_discharged'] for s in vessels_db):,} TEU**."
        )
    else:
        response = (
            "Bonjour ! Je suis l'assistant IA intelligent de **Marsa Maroc**.\n\n"
            "Je peux répondre à vos questions opérationnelles concernant :\n"
            "1. **Le taux d'overstay** des conteneurs.\n"
            "2. **La capacité du quai** et les places libres.\n"
            "3. **Les tarifs et pénalités** de stockage.\n"
            "4. **Le planning des navires** et des escales."
        )
        
    return {"response": response}

# Mount static files & fallback routes for simple client routing
app.mount("/static", StaticFiles(directory="C:\\Users\\PC\\.gemini\\antigravity\\scratch\\marsa_maroc_port\\static"), name="static")

@app.get("/")
def get_index():
    return FileResponse("C:\\Users\\PC\\.gemini\\antigravity\\scratch\\marsa_maroc_port\\static\\index.html")

@app.get("/dashboard")
def get_dashboard():
    return FileResponse("C:\\Users\\PC\\.gemini\\antigravity\\scratch\\marsa_maroc_port\\static\\dashboard.html")

@app.get("/conteneurs")
def get_conteneurs():
    return FileResponse("C:\\Users\\PC\\.gemini\\antigravity\\scratch\\marsa_maroc_port\\static\\conteneurs.html")

@app.get("/navires")
def get_navires():
    return FileResponse("C:\\Users\\PC\\.gemini\\antigravity\\scratch\\marsa_maroc_port\\static\\navires.html")

@app.get("/facturation")
def get_facturation():
    return FileResponse("C:\\Users\\PC\\.gemini\\antigravity\\scratch\\marsa_maroc_port\\static\\facturation.html")

@app.get("/espace_client")
def get_espace_client():
    return FileResponse("C:\\Users\\PC\\.gemini\\antigravity\\scratch\\marsa_maroc_port\\static\\espace_client.html")

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
