from app.database import Base, SessionLocal, engine
from app.services.seed import seed_definitions


def main() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_definitions(db)
    print("Seed completato.")


if __name__ == "__main__":
    main()
