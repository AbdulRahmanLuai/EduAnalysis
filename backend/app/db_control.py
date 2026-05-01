import argparse
from sqlmodel import SQLModel
from app.db import engine


def drop_all_tables():
    """Drop all tables safely across DBs."""
    SQLModel.metadata.reflect(bind=engine)

    with engine.begin() as conn:
        if engine.dialect.name == "sqlite":
            conn.exec_driver_sql("PRAGMA foreign_keys = OFF")

        for table in reversed(SQLModel.metadata.sorted_tables):
            table.drop(bind=engine, checkfirst=True)

        if engine.dialect.name == "sqlite":
            conn.exec_driver_sql("PRAGMA foreign_keys = ON")

    print("✅ All tables dropped")


def create_all_tables():
    """Create all tables from models."""
    SQLModel.metadata.create_all(engine)
    print("✅ All tables created")


def reset_db():
    """Full reset: drop + create."""
    drop_all_tables()
    create_all_tables()
    print("🔄 Database reset complete")


def seed_db():
    """Optional seeding hook."""
    print("🌱 Seeding database...")
    # import and run your seed logic here
    # from app.seed import seed_all
    # seed_all()
    print("🌱 Done seeding")


def main():
    parser = argparse.ArgumentParser(description="DB management CLI")

    parser.add_argument(
        "command",
        choices=["drop", "create", "reset", "seed"],
        help="Database operation to run",
    )

    args = parser.parse_args()

    if args.command == "drop":
        drop_all_tables()

    elif args.command == "create":
        create_all_tables()

    elif args.command == "reset":
        reset_db()

    elif args.command == "seed":
        seed_db()


if __name__ == "__main__":
    main()