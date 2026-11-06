import pyodbc
import json, os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),'../..')))

import hashlib
import secrets
from base64 import b64encode, b64decode


# Sensitive fields that should be encrypted
SENSITIVE_FIELDS = {"password", "user"}

def _get_config_path() -> str:
    """Get path to db_config.json.
    
    PyInstaller bundles database/ at root of _MEIPASS.
    For development, use the src/backend/data/database directory.
    Subsequent writes go to user's home directory.
    """
    try:
        if getattr(sys, "frozen", False):
            # First check if bundled database config exists (read-only template)
            bundled_config = os.path.join(sys._MEIPASS, "database", "db_config.json")  # type: ignore[attr-defined]
            if os.path.exists(bundled_config):
                return bundled_config
            
            # Otherwise use user writable location
            app_dir = os.path.join(os.path.expanduser("~"), ".jaccs_credit_app")
            config_dir = os.path.join(app_dir, "config")
            os.makedirs(config_dir, exist_ok=True)
            return os.path.join(config_dir, "db_config.json")
        else:
            # Development mode
            config_dir = os.path.join(os.path.dirname(__file__), "data", "database")
            os.makedirs(config_dir, exist_ok=True)
            return os.path.join(config_dir, "db_config.json")
    except Exception as e:
        print(f"[DB] Warning: Failed to resolve config path ({e}). Using temp location.")
        import tempfile
        return os.path.join(tempfile.gettempdir(), "db_config.json")

CONFIG_PATH = _get_config_path()

DEFAULT_CONFIG = {
    "server": "",
    "database": "",
    "user": "",
    "password": "",
    "driver": "{ODBC Driver 17 for SQL Server}",
}

def _derive_encryption_key(salt: str) -> str:
    """Derive a simple encryption key from salt using SHA256."""
    return hashlib.sha256((salt + "DB_CONFIG_SECRET").encode('utf-8')).hexdigest()[:32]

def _simple_encrypt(value: str, salt: str) -> str:
    """Encrypt value using XOR with derived key."""
    key = _derive_encryption_key(salt)
    encrypted = bytes([ord(c) ^ ord(key[i % len(key)]) for i, c in enumerate(value)])
    return b64encode(encrypted).decode('utf-8')

def _simple_decrypt(encrypted_value: str, salt: str) -> str:
    """Decrypt value using XOR with derived key."""
    try:
        key = _derive_encryption_key(salt)
        encrypted = b64decode(encrypted_value.encode('utf-8'))
        decrypted = bytes([b ^ ord(key[i % len(key)]) for i, b in enumerate(encrypted)])
        return decrypted.decode('utf-8')
    except Exception:
        return ""

def load_config():
    """Return the current database configuration, loading from disk if present and decrypting sensitive fields."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                cfg = json.load(f)
                # Extract salt and decrypt sensitive fields
                salt = cfg.get("_salt", "")
                if salt:
                    for field in SENSITIVE_FIELDS:
                        if field in cfg and cfg[field].startswith("ENC:"):
                            encrypted_val = cfg[field][4:]  # Remove "ENC:" prefix
                            cfg[field] = _simple_decrypt(encrypted_val, salt)
                    # Remove the salt from the returned config
                    cfg.pop("_salt", None)
                return cfg
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(cfg: dict):
    """Persist a configuration dictionary to disk with encrypted sensitive fields."""
    try:
        # Create a copy to avoid modifying the original
        cfg_to_save = dict(cfg)
        
        # Generate a salt for encryption
        salt = secrets.token_hex(16)
        cfg_to_save["_salt"] = salt
        
        # Encrypt sensitive fields
        for field in SENSITIVE_FIELDS:
            if field in cfg_to_save:
                original_value = cfg_to_save[field]
                encrypted_value = _simple_encrypt(original_value, salt)
                cfg_to_save[field] = f"ENC:{encrypted_value}"
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        
        with open(CONFIG_PATH, "w") as f:
            json.dump(cfg_to_save, f, indent=4)
        print(f"Config saved to: {CONFIG_PATH}")
    except Exception as e:
        print(f"[DB] Warning: Failed to save config ({e}).")
        raise

def _resolve_driver(driver_name=None):
    installed = pyodbc.drivers()
    preferred = [
        "ODBC Driver 18 for SQL Server",
        "ODBC Driver 17 for SQL Server",
        "SQL Server Native Client 11.0",
        "SQL Server",
    ]
    if driver_name:
        return driver_name
    for name in preferred:
        if name in installed:
            return name
    return installed[0] if installed else "ODBC Driver 17 for SQL Server"


def _server_candidates(server=None):
    raw = [
        server,
        os.getenv("SQL_SERVER"),
        r"LEGION\SQLEXPRESS",
        r"localhost\SQLEXPRESS",
        r"(local)\SQLEXPRESS",
        r"127.0.0.1",
        r"localhost",
        r"(local)",
    ]
    seen = set()
    out = []
    for item in raw:
        if not item:
            continue
        norm = item.strip()
        if norm not in seen:
            seen.add(norm)
            out.append(norm)
    return out


# --- For Developer Testing --- #
def get_connection_local(server=None, database=None, user=None, password=None, driver=None, encrypt="yes", trustservercertificate="yes"):
    database = database or "ltid"
    driver = _resolve_driver(driver)
    last_error = None

    for srv in _server_candidates(server):
        auth = f"UID={user};PWD={password};" if user and password else "Trusted_Connection=yes;"
        conn_str = (
            f"DRIVER={{{driver}}};SERVER={srv};DATABASE={database};{auth}"
            f"Encrypt={encrypt};TrustServerCertificate={trustservercertificate};"
        )
        try:
            return pyodbc.connect(conn_str, timeout=10)
        except Exception as exc:
            last_error = exc
            print(f"Local connection attempt failed for {srv}: {exc}")

    raise RuntimeError(f"Could not connect locally. Last error: {last_error}")


def get_connection(
    server=None,
    database=None,
    user=None,
    password=None,
    driver=None,
    # encrypt="yes",
    # trustservercertificate="yes",
):
    # fall back to values from config file when arguments are not supplied
    cfg = load_config()
    server = server or cfg.get("server")
    database = database or cfg.get("database")
    user = user or cfg.get("user")
    password = password or cfg.get("password")
    driver = driver or cfg.get("driver")

    missing = [
        name for name, value in (
            ("server", server),
            ("database", database),
            ("user", user),
            ("password", password),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(
            "Database configuration is incomplete. Set the missing values in "
            f"{CONFIG_PATH}: {', '.join(missing)}"
        )

    conn_str = (
        f"DRIVER={driver};SERVER={server};DATABASE={database};"
        f"UID={user};PWD={password};"
        # f"Encrypt={encrypt};TrustServerCertificate={trustservercertificate};"
        # f"Trusted_Connection=yes;Encrypt=no;"
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

            # --- For Testing --- #
            # cur.execute(
            #     """
            #     SELECT * FROM customer
            #     WHERE [Party No] = ?
            #     AND [Application No] = ?
            #     """, party_no, application_no,
            # )
            
            columns = [c[0] for c in cur.description] if cur.description else []
            row = cur.fetchone()
            if not row:
                return None
            data = dict(zip(columns, row))
            return data
    finally:
        if close_conn:
            conn.close()
