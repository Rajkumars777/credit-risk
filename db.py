import pyodbc
import json, os

# configuration file for database connection parameters
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "db_config.json")
DEFAULT_CONFIG = {
    "server": "TEST-DB",
    "database": "dbAAFS_MAFS",
    "user": "jaccsadmin",
    "password": "J@ccs@admin",
    "driver": "{ODBC Driver 17 for SQL Server}",
}

def load_config():
    """Return the current database configuration, loading from disk if present."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(cfg: dict):
    """Persist a configuration dictionary to disk."""
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump(cfg, f, indent=4)
    except Exception:
        # silently ignore write errors, caller can handle if needed
        pass


def get_connection(
    server=None,
    database=None,
    user=None,
    password=None,
    driver=None,
    # encrypt="yes",
    # trustservercertificate="yes",

    # local
    # server="localhost,1433",
    # database="scoringDB",
    # user="sa",
    # password="MyStrongPass123",
    # driver="{ODBC Driver 18 for SQL Server}",
):
    # fall back to values from config file when arguments are not supplied
    cfg = load_config()
    server = server or cfg.get("server")
    database = database or cfg.get("database")
    user = user or cfg.get("user")
    password = password or cfg.get("password")
    driver = driver or cfg.get("driver")

    conn_str = (
        f"DRIVER={driver};SERVER={server};DATABASE={database};"
        f"UID={user};PWD={password};"
        # f"Encrypt={encrypt};TrustServerCertificate={trustservercertificate};"
    )
    return pyodbc.connect(conn_str)

def fetch_ci_mock_crifv4(party_no: int, application_no: int, conn=None):
    """
    Calls: EXEC dbo.CIMockCrifv4 @party=?, @application=?
    Returns: a single row as {column: value} or None if nothing.
    """
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    try:
        with conn.cursor() as cur:
            cur.execute("EXEC dbo.CIMockCrifv4 @party = ?, @application = ?", party_no, application_no)
            columns = [c[0] for c in cur.description] if cur.description else []
            row = cur.fetchone()
            if not row:
                return None
            data = dict(zip(columns, row))
            return data
    finally:
        if close_conn:
            conn.close()
