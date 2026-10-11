import html
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

# Local database models & API routing
from app.database_models import Base, Segment, PlaceholderItem
from app.api_routes import router as offer_router
from app.services import DocumentService


app = FastAPI(
    title="WINDTRE Sintesi & Trasparenze Automation API",
    description="Backend service for automating pre-contract summaries (Sintesi) and AGCOM tariff transparency (Trasparenze) spreadsheets.",
    version="1.0.0"
)

# 1. Enable CORS middleware for seamless local frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In development, allow any local client origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the core offers endpoints under the standard API prefix
app.include_router(offer_router, prefix="/api")


# ============================================================================
# Local Database Initialization & Seeding on Startup
# ============================================================================
DATABASE_URL = "sqlite:///./pre_contratti.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@app.on_event("startup")
def on_startup():
    # Use an exclusive cross-process file lock to serialize database initialization across concurrent worker processes
    lock_file = None
    try:
        import fcntl
        lock_file = open("/app/pre_contratti_db_init.lock", "w")
        fcntl.flock(lock_file, fcntl.LOCK_EX)
    except Exception as e:
        # Fallback if fcntl is unavailable (e.g. Windows) or if there are unexpected permission limits
        print(f"Process locking bypassed or unavailable (falling back): {e}")

    try:
        # 1. Automatically create local SQLite tables for our ORM entities safely (handling concurrency from multiple workers)
        try:
            Base.metadata.create_all(bind=engine)
        except Exception as e:
            print(f"Database creation already handled by another worker process: {e}")
        
        # 2. Seed default segments if empty to satisfy foreign key validations
        db = SessionLocal()
        try:
            existing_segments = db.scalars(select(Segment)).all()
            if not existing_segments:
                segments_seed = [
                    Segment(id="W3_MOB_GA_CNS", name="WINDTRE Mobile GA Consumer", description="Windtre Mobile Generazione Attiva Consumer"),
                    Segment(id="W3_MOB_CB_CNS", name="WINDTRE Mobile CB Consumer", description="Windtre Mobile Customer Base Consumer"),
                    Segment(id="W3_MOB_GA_MB", name="WINDTRE Mobile GA Microbusiness", description="Windtre Mobile Generazione Attiva Microbusiness"),
                    Segment(id="W3_FIX_GA_CNS", name="WINDTRE Fisso GA Consumer", description="Windtre Fisso Generazione Attiva Consumer/Cross Selling"),
                    Segment(id="W3_FIX_CB_CNS", name="WINDTRE Fisso CB Consumer", description="Windtre Fisso Customer Base Consumer"),
                    Segment(id="W3_FIX_GA_MB", name="WINDTRE Fisso GA Microbusiness", description="Windtre Fisso Generazione Attiva Microbusiness/Cross Selling"),
                    Segment(id="W3_FIX_CB_MB", name="WINDTRE Fisso CB Microbusiness", description="Windtre Fisso Customer Base Microbusiness"),
                    Segment(id="W3_ETN_CNS", name="WINDTRE Etnico Consumer", description="Windtre Etnico Consumer GA/CB"),
                    Segment(id="VERY_MOBILE", name="Very Mobile", description="Very Mobile Commercial Segment")
                ]
                db.add_all(segments_seed)
                db.commit()

            # 3. Seed default offers and dynamic tables if none exist to make the demo portal look premium instantly
            from app.database_models import Offer, DynamicTable
            import uuid
            from datetime import date
            from decimal import Decimal

            existing_offers = db.scalars(select(Offer)).all()
            if not existing_offers:
                offers_seed_data = [
                    {
                        "id": uuid.UUID("342ec6f4-ec8a-40a2-944d-57ff638b9bb8"),
                        "segment_id": "W3_MOB_CB_CNS",
                        "commercial_name": "Windtre Super Mobile Unlimited",
                        "technology_type": "5G",
                        "base_price": Decimal("29.99"),
                        "po_code": None,
                        "status": "APERTA",
                        "current_agcom_code": "COD1234567",
                        "date_start": date(2026, 6, 1),
                        "tables": {
                            "PREZZO": {
                                "max_rows_limit": 15,
                                "rows": [
                                    { "id": "p_abbonamento", "type": "padre", "label": "Canone mensile offerta", "value": "29,99 euro/mese", "children": [] },
                                    { "id": "p_attivazione", "type": "padre", "label": "Costo di attivazione una tantum", "value": "9,99 euro", "children": [] }
                                ]
                            },
                            "COSTI": {
                                "max_rows_limit": 10,
                                "rows": [
                                    { "id": "p_costo_recesso", "type": "padre", "label": "Costo disattivazione linea", "value": "ND", "children": [] },
                                    { "id": "p_sim", "type": "padre", "label": "Costo SIM fisica", "value": "10,00 euro", "children": [] }
                                ]
                            },
                            "SERVIZI": {
                                "max_rows_limit": 15,
                                "rows": [
                                    { "id": "p_voce", "type": "padre", "label": "Minuti di conversazione nazionali", "value": "Illimitati", "children": [] },
                                    { "id": "p_sms", "type": "padre", "label": "SMS nazionali inclusi", "value": "500 SMS", "children": [] },
                                    { "id": "p_giga", "type": "padre", "label": "Giga di traffico Internet inclusi", "value": "Illimitati $Bollino$", "children": [] }
                                ]
                            },
                            "DURATA": {
                                "max_rows_limit": 10,
                                "rows": [
                                    { "id": "p_durata", "type": "padre", "label": "Durata minima contrattuale", "value": "24 mesi", "children": [] }
                                ]
                            }
                        }
                    },
                    {
                        "id": uuid.UUID("bc88a531-ee0a-4fcb-84a1-b4f0b2f671c6"),
                        "segment_id": "W3_FIX_GA_CNS",
                        "commercial_name": "Super Fibra Casa Premium",
                        "technology_type": "FTTH",
                        "base_price": Decimal("26.99"),
                        "po_code": None,
                        "status": "APERTA",
                        "current_agcom_code": "COD3234567",
                        "date_start": date(2026, 6, 1),
                        "tables": {
                            "PREZZO": {
                                "max_rows_limit": 12,
                                "rows": [
                                    { "id": "p_fibra", "type": "padre", "label": "Abbonamento Fibra Casa", "value": "26,99 euro", "children": [] }
                                ]
                            }
                        }
                    },
                    {
                        "id": uuid.UUID("7498cbe1-df8c-4bc9-98da-cdb2e592fba2"),
                        "segment_id": "VERY_MOBILE",
                        "commercial_name": "Very 4.99 Flash Promo",
                        "technology_type": "4G",
                        "base_price": Decimal("4.99"),
                        "po_code": "PO778844",
                        "status": "APERTA",
                        "current_agcom_code": "COD4234567",
                        "date_start": date(2026, 6, 1),
                        "tables": {
                            "PREZZO": {
                                "max_rows_limit": 3,
                                "rows": [
                                    { "id": "p_cost_mensile", "type": "padre", "label": "Canone Mensile", "value": "4,99 euro", "children": [] }
                                ]
                            }
                        }
                    }
                ]

                for offer_data in offers_seed_data:
                    is_fixed = "FIX" in offer_data["segment_id"] or offer_data["technology_type"] in ("FTTH", "FTTC")
                    pay_method = "abbonamento" if is_fixed else "credito_residuo"

                    db_offer = Offer(
                        id=offer_data["id"],
                        segment_id=offer_data["segment_id"],
                        commercial_name=offer_data["commercial_name"],
                        technology_type=offer_data["technology_type"],
                        base_price=offer_data["base_price"],
                        po_code=offer_data["po_code"],
                        status=offer_data["status"],
                        current_agcom_code=offer_data["current_agcom_code"],
                        date_start=offer_data["date_start"],
                        payment_method=pay_method
                    )
                    db.add(db_offer)
                    
                    # Seed tables for this offer
                    default_identifiers = ["PREZZO", "COSTI", "SERVIZI", "DURATA"]
                    for idx, identifier in enumerate(default_identifiers):
                        struct = offer_data["tables"].get(identifier, {"max_rows_limit": 15, "rows": []})
                        db_table = DynamicTable(
                            offer_id=db_offer.id,
                            table_identifier=identifier,
                            sequence_order=idx,
                            title=f"Tabella {identifier.title()}",
                            structural_content=struct,
                            note_links={"links": []}
                        )
                        db.add(db_table)
                db.commit()
        except Exception as e:
            db.rollback()
            # Cleanly ignore if tables are already seeded or have integrity conflicts from concurrent runs
            if "UNIQUE constraint failed" in str(e) or "already exists" in str(e):
                print("Database already seeded by another worker process.")
            else:
                print(f"Database seeding already handled by another worker process: {e}")
        finally:
            db.close()

        # 4. Create the compilation workspace folder locally if it doesn't exist
        os.makedirs("/tmp/compilation_workspace", exist_ok=True)

    finally:
        # Always release file lock and close the lock file safely
        if lock_file:
            try:
                import fcntl
                fcntl.flock(lock_file, fcntl.LOCK_UN)
                lock_file.close()
            except Exception:
                pass


# ============================================================================
# Frontend Dashboard & Output File Server Routes
# ============================================================================

@app.get("/", response_class=HTMLResponse, tags=["Dashboard"])
def get_admin_portal():
    """
    Serves the premium single-page administration panel directly at the host root.
    Go to http://localhost:8000/ to view the portal.
    """
    project_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    html_path = os.path.join(project_root, "admin_dashboard.html")
    if not os.path.exists(html_path):
        return HTMLResponse(content="<h1>Admin Dashboard template not found!</h1>", status_code=404)
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/downloads/{filename}", tags=["Downloads"])
def download_compiled_file(filename: str):
    """
    Serves the compiled PDF, Word, or Excel document directly from the local compilation workspace.
    Returns a clear 404 when the document has not been compiled yet. It never fabricates
    placeholder files, which previously produced unopenable fake PDFs named '<file>.pdf'.
    """
    safe_name = os.path.basename(filename)
    file_path = os.path.join("/tmp/compilation_workspace", safe_name)

    def not_available_response(reason: str) -> HTMLResponse:
        escaped_name = html.escape(safe_name, quote=True)
        return HTMLResponse(
            content=(
                "<html><body style='font-family: sans-serif; padding: 40px;'>"
                "<h1>Documento non disponibile</h1>"
                f"<p>{reason}</p>"
                "<p>Clicca su <strong>&#x1F504; Rigenera</strong> nell'elenco delle offerte "
                "e riprova tra qualche secondo.</p>"
                f"<p style='color:#888; font-size: 12px;'>"
                f"File richiesto: <code>{escaped_name}</code></p>"
                "</body></html>"
            ),
            status_code=404,
        )

    if not os.path.exists(file_path):
        return not_available_response(
            "Il documento non &egrave; stato ancora compilato "
            "oppure la compilazione &egrave; fallita.",
        )

    if safe_name.lower().endswith(".pdf"):
        with open(file_path, "rb") as f:
            if f.read(5) != b"%PDF-":
                return not_available_response(
                    "Il file presente non &egrave; un PDF valido "
                    "(compilazione incompleta o corrotta).",
                )

    return FileResponse(file_path, filename=safe_name)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "service": "document-synthesis-service"}


@app.get("/api/placeholders", response_model=list[PlaceholderItem], tags=["Placeholders"])
@app.get("/api/v1/placeholders", response_model=list[PlaceholderItem], tags=["Placeholders"])
def get_root_placeholders():
    """
    Returns available template placeholders registry for autocomplete and document authoring.
    """
    return DocumentService.get_available_placeholders()

