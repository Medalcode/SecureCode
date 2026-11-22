from alembic.config import Config
from sqlalchemy import create_engine, inspect

from alembic import command
from securecode.adapters.postgres.models import Base


def test_service_acceptance_migration_upgrades_and_downgrades_on_sqlite(tmp_path, monkeypatch):
    database_path = tmp_path / "service_acceptance_migration.db"
    url = f"sqlite:///{database_path}"
    monkeypatch.setenv("DATABASE_URL", url)
    config = Config("alembic.ini")

    engine = create_engine(url)
    tables = [
        table for name, table in Base.metadata.tables.items()
        if name not in {"service_document_acceptances", "user_sessions"}
    ]
    Base.metadata.create_all(engine, tables=tables)
    engine.dispose()

    command.stamp(config, "e7b1c4d2a809")
    command.upgrade(config, "head")

    engine = create_engine(url)
    inspector = inspect(engine)
    assert "service_document_acceptances" in inspector.get_table_names()

    columns = {column["name"] for column in inspector.get_columns("service_document_acceptances")}
    assert {
        "id",
        "organization_id",
        "user_id",
        "package_id",
        "package_version",
        "document_id",
        "document_version",
        "document_sha256",
        "package_sha256",
        "source_path",
        "acceptance_type",
        "accepted_at",
    } <= columns

    indexes = {index["name"] for index in inspector.get_indexes("service_document_acceptances")}
    assert "ix_service_document_acceptances_org_accepted_at" in indexes
    assert "ix_service_document_acceptances_user_accepted_at" in indexes
    engine.dispose()

    command.downgrade(config, "e7b1c4d2a809")
    engine = create_engine(url)
    assert "service_document_acceptances" not in inspect(engine).get_table_names()
    engine.dispose()
