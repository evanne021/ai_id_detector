import mysql.connector
from mysql.connector import Error
import bcrypt
from typing import Optional, Dict, List

# -----------------------------
# Database Connection
# -----------------------------
def get_connection():
    """Create and return a MySQL connection."""
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="09096558231pogi",  # Change if needed
            database="ai_id_detector"
        )
        return conn
    except Error as e:
        print(f"[ERROR] Could not connect to MySQL: {e}")
        return None

# -----------------------------
# User Management
# -----------------------------
def insert_user(name: str, role: str, username: str, password: str) -> bool:
    """Insert a new user with hashed password."""
    try:
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    except ValueError as e:
        print(f"[ERROR] Password hashing failed: {e}")
        return False

    conn = get_connection()
    if not conn:
        return False

    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO user (name, role, username, password) VALUES (%s, %s, %s, %s)",
                (name, role, username, hashed)
            )
            conn.commit()
        return True
    except Error as e:
        print(f"[ERROR] Failed to insert user: {e}")
        return False
    finally:
        conn.close()

def hash_plain_passwords():
    """Hash all existing plain-text passwords in the user table."""
    conn = get_connection()
    if not conn:
        return
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute("SELECT user_id, password FROM user")
            users = cur.fetchall()
            for u in users:
                pwd = u["password"]
                if not pwd.startswith("$2b$"):
                    hashed = bcrypt.hashpw(pwd.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                    cur.execute("UPDATE user SET password=%s WHERE user_id=%s", (hashed, u["user_id"]))
                    print(f"[INFO] Hashed password for user_id {u['user_id']}")
        conn.commit()
    except Error as e:
        print(f"[ERROR] Failed to hash plain passwords: {e}")
    finally:
        conn.close()

def verify_user(username: str, password: str) -> Optional[Dict]:
    """Verify user credentials. Returns user dict (without password) if valid."""
    conn = get_connection()
    if not conn:
        return None

    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(
                "SELECT user_id, name, role, username, password FROM user WHERE username=%s",
                (username,)
            )
            row = cur.fetchone()

        if row:
            stored = row["password"].encode("utf-8")
            if stored.startswith(b"$2b$") and bcrypt.checkpw(password.encode("utf-8"), stored):
                return {k: v for k, v in row.items() if k != "password"}
        return None
    except Error as e:
        print(f"[ERROR] Failed to verify user: {e}")
        return None
    finally:
        conn.close()

def get_users() -> List[Dict]:
    """Retrieve all users (without passwords)."""
    conn = get_connection()
    if not conn:
        return []
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute("SELECT user_id, name, role, username FROM user")
            return cur.fetchall()
    except Error as e:
        print(f"[ERROR] Failed to fetch users: {e}")
        return []
    finally:
        conn.close()

# -----------------------------
# Detection Management
# -----------------------------
def insert_detection(camera_id: int, confidence_score: float,
                     ai_result: str, image_path: str, timestamp: str) -> int:
    """
    Save a detection event.
    Returns the auto-generated detection_id (INT).
    """
    conn = get_connection()
    if not conn:
        return 0
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO detection
                (camera_id, confidence_score, ai_result, image_path, `timestamp`)
                VALUES (%s, %s, %s, %s, %s)""",
                (camera_id, confidence_score, ai_result, image_path, timestamp)
            )
            conn.commit()
            return cur.lastrowid
    except Error as e:
        print(f"[ERROR] Failed to insert detection: {e}")
        return 0
    finally:
        conn.close()

# -----------------------------
# Feedback / Incident Management
# -----------------------------
def insert_feedback(detection_id: int, user_id: int, category: str, notes: str) -> bool:
    """Save a feedback/incident record."""
    conn = get_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO feedback (detection_id, user_id, category, notes) VALUES (%s, %s, %s, %s)",
                (detection_id, user_id, category, notes)
            )
            conn.commit()
        return True
    except Error as e:
        print(f"[ERROR] Failed to insert feedback: {e}")
        return False
    finally:
        conn.close()

# -----------------------------
# MAIN BLOCK FOR ONE-TIME HASHING
# -----------------------------
if __name__ == "__main__":
    hash_plain_passwords()
    print("✅ All plain-text passwords are hashed. You can now run login.py safely.")
