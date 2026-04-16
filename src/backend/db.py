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
    "server": "TEST-DB",
    "database": "dbAAFS_MAFS",
    "user": "jaccsadmin",
    "password": "J@ccs@admin",
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
        # silently ignore write errors
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
