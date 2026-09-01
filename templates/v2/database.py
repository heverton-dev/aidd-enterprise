import os, sqlite3

class Database:
    def __init__(self, db_url=None):
        self.db_url = db_url or os.getenv("DATABASE_URL", "sqlite:///app.db")
        self.is_postgres = self.db_url.startswith("postgres://") or self.db_url.startswith("postgresql://")
        self._init_migration_tracker()

    def _init_migration_tracker(self):
        """Inicializa a tabela interna de controle de versões e migrações de schema."""
        if not self.is_postgres:
            db_path = self.db_url.replace("sqlite:///", "")
            conn = sqlite3.connect(db_path, timeout=10.0)
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS _schema_migrations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        module_name TEXT NOT NULL UNIQUE,
                        version INTEGER NOT NULL,
                        applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                conn.commit()
            finally:
                conn.close()

    def get_connection(self):
        if self.is_postgres:
            try:
                import psycopg2
                from psycopg2.extras import RealDictCursor
                conn = psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
                return conn
            except ImportError:
                raise RuntimeError("psycopg2 não instalado. Para PostgreSQL, instale: pip install psycopg2-binary")
        else:
            db_path = self.db_url.replace("sqlite:///", "")
            conn = sqlite3.connect(db_path, timeout=10.0)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA busy_timeout=5000;")
            conn.execute("PRAGMA foreign_keys=ON;")
            conn.row_factory = sqlite3.Row
            return conn

    def record_migration(self, module_name: str, version: int = 1):
        """Registra a aplicação idempotente de schema para um módulo."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO _schema_migrations (module_name, version, applied_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(module_name) DO UPDATE SET version = ?, applied_at = CURRENT_TIMESTAMP;
            """, (module_name, version, version))
            conn.commit()
