"""Penyimpanan akun, sesi, consent, dan riwayat analisis (SQLite; pengganti sementara PostgreSQL)."""
import hashlib
import json
import os
import secrets
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(os.environ.get("AGROGARLIC_DB", Path(__file__).parent / "data" / "agrogarlic.db"))


def koneksi():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init():
    with koneksi() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT, kontak TEXT UNIQUE NOT NULL,
            salt TEXT NOT NULL, hash TEXT NOT NULL,
            consent INTEGER NOT NULL DEFAULT 0, dibuat TEXT);
        CREATE TABLE IF NOT EXISTS sesi (
            token TEXT PRIMARY KEY, user_id INTEGER NOT NULL, dibuat TEXT);
        CREATE TABLE IF NOT EXISTS analisis (
            id TEXT PRIMARY KEY, user_id INTEGER, disimpan INTEGER NOT NULL DEFAULT 0,
            dibuat TEXT, hasil TEXT NOT NULL);
        """)


def _hash(sandi, salt):
    return hashlib.pbkdf2_hmac("sha256", sandi.encode(), salt.encode(), 100_000).hex()


def daftar(nama, kontak, sandi, consent):
    salt = secrets.token_hex(8)
    with koneksi() as con:
        try:
            cur = con.execute(
                "INSERT INTO users (nama, kontak, salt, hash, consent, dibuat) VALUES (?,?,?,?,?,?)",
                (nama, kontak.strip().lower(), salt, _hash(sandi, salt), int(consent), _now()))
        except sqlite3.IntegrityError:
            return None
        return cur.lastrowid


def masuk(kontak, sandi):
    with koneksi() as con:
        u = con.execute("SELECT * FROM users WHERE kontak=?", (kontak.strip().lower(),)).fetchone()
        if not u or _hash(sandi, u["salt"]) != u["hash"]:
            return None
        token = secrets.token_urlsafe(24)
        con.execute("INSERT INTO sesi VALUES (?,?,?)", (token, u["id"], _now()))
        return token


def keluar(token):
    with koneksi() as con:
        con.execute("DELETE FROM sesi WHERE token=?", (token,))


def user_dari_token(token):
    if not token:
        return None
    with koneksi() as con:
        u = con.execute("SELECT u.* FROM users u JOIN sesi s ON s.user_id=u.id WHERE s.token=?",
                        (token,)).fetchone()
        return dict(u) if u else None


def set_consent(user_id, consent):
    with koneksi() as con:
        con.execute("UPDATE users SET consent=? WHERE id=?", (int(consent), user_id))


def simpan_analisis(hasil, user_id=None):
    with koneksi() as con:
        con.execute("INSERT INTO analisis (id, user_id, dibuat, hasil) VALUES (?,?,?,?)",
                    (hasil["analysis_id"], user_id, _now(), json.dumps(hasil, ensure_ascii=False)))


def ambil_analisis(aid):
    with koneksi() as con:
        r = con.execute("SELECT * FROM analisis WHERE id=?", (aid,)).fetchone()
        return dict(r) if r else None


def tandai_disimpan(aid, user_id):
    with koneksi() as con:
        cur = con.execute("UPDATE analisis SET disimpan=1, user_id=? WHERE id=? AND (user_id IS NULL OR user_id=?)",
                          (user_id, aid, user_id))
        return cur.rowcount > 0


def hapus_riwayat(aid, user_id):
    with koneksi() as con:
        con.execute("UPDATE analisis SET disimpan=0 WHERE id=? AND user_id=?", (aid, user_id))


def riwayat(user_id):
    with koneksi() as con:
        rows = con.execute("SELECT * FROM analisis WHERE user_id=? AND disimpan=1 ORDER BY dibuat DESC",
                           (user_id,)).fetchall()
        return [json.loads(r["hasil"]) | {"disimpan_pada": r["dibuat"]} for r in rows]


def _now():
    return datetime.now().isoformat(timespec="seconds")
