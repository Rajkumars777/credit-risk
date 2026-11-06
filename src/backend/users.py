import csv, os, secrets, hashlib, sys
from typing import List, Dict, Optional
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),'../..')))

def _get_users_csv_path() -> str:
    """Get path to users.csv in a writable location.
    
    PyInstaller bundles users.csv at root of _MEIPASS.
    For development, use the src/backend directory.
    Subsequent writes go to user's home directory.
    """
    try:
        if getattr(sys, "frozen", False):
            # First check if bundled users.csv exists (read-only template)
            bundled_path = os.path.join(sys._MEIPASS, "users.csv")  # type: ignore[attr-defined]
            if os.path.exists(bundled_path):
                return bundled_path
            
            # Otherwise use user writable location
            app_dir = os.path.join(os.path.expanduser("~"), ".jaccs_credit_app")
            os.makedirs(app_dir, exist_ok=True)
            return os.path.join(app_dir, "users.csv")
        else:
            # Development mode
            return os.path.join(os.path.dirname(__file__), "users.csv")
    except Exception as e:
        print(f"[Users] Warning: Failed to resolve users.csv path ({e}). Using temp location.")
        import tempfile
        return os.path.join(tempfile.gettempdir(), "users.csv")

USERS_CSV = _get_users_csv_path()

def _hash_password(password: str, salt: Optional[str] = None):
    """
    Adding salt to password increases uniqueness of the password, for each user in case if similar password is choosen.
    """
    salt = salt or secrets.token_hex(16)
    new_hash_pass = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()
    return salt, new_hash_pass

def ensure_user_store():
    """
    User access credential.
    """
    if os.path.exists(USERS_CSV):
        return
    initial_password = os.getenv("JACCS_DEFAULT_ADMIN_PASSWORD")
    if not initial_password:
        initial_password = secrets.token_urlsafe(16)
        print(
            "[Users] Generated a temporary admin password. "
            "Set JACCS_DEFAULT_ADMIN_PASSWORD to choose one explicitly."
        )
    add_user("admin@example.com", initial_password, role="admin")

def _read_all() -> List[Dict[str,str]]:
    if not os.path.exists(USERS_CSV):
        return []
    with open(USERS_CSV, newline="", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        return list(rdr)

def _write_all(rows: List[Dict[str,str]]):
    with open(USERS_CSV, 'w', newline='', encoding='utf-8')as f:
        w = csv.DictWriter(f, fieldnames=["email", "role", "salt", "password_hash"])
        w.writeheader()
        w.writerows(rows)

def list_users() -> List[Dict[str, str]]:
    rows = _read_all()
    # Don't expose salt/hash to the UI
    return [{"email": r["email"], "role": r["role"]} for r in rows]

def get_user(email: str) -> Optional[Dict[str, str]]:
    for r in _read_all():
        if r["email"].lower() == email.lower():
            return r
    return None

def add_user(email: str, password: str, role: str = "user") -> None:
    if get_user(email):
        raise ValueError("User already exists.")
    salt, ph = _hash_password(password)
    rows = _read_all()
    rows.append({"email": email, "role": role, "salt": salt, "password_hash": ph})
    _write_all(rows)

def delete_user(email: str) -> None:
    rows = [r for r in _read_all() if r["email"].lower() != email.lower()]
    _write_all(rows)

def set_role(email: str, role: str) -> None:
    rows = _read_all()
    changed = False
    for r in rows:
        if r["email"].lower() == email.lower():
            r["role"] = role
            changed = True
            break
    if not changed:
        raise ValueError("User not found.")
    _write_all(rows)

def update_password(email: str, new_password: str) -> None:
    rows = _read_all()
    changed = False
    for r in rows:
        if r["email"].lower() == email.lower():
            salt, ph = _hash_password(new_password)
            r["salt"] = salt
            r["password_hash"] = ph
            changed = True
            break
    if not changed:
        raise ValueError("User not found.")
    _write_all(rows)

def authenticate(email: str, password: str) -> Optional[str]:
    """Return role if ok, else None."""
    r = get_user(email)
    if not r:
        return None
    salt = r["salt"]; ph = r["password_hash"]
    _, test = _hash_password(password, salt=salt)
    return r["role"] if test == ph else None

if __name__ == "__main__":
    ensure_user_store()
    print(_hash_password('123',salt='4b9ab5b3e4393a196e055ff0458f6cd9'))
