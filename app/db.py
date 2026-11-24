"""
Penyimpanan akun, sesi, consent, dan riwayat analisis.

- Bila variabel lingkungan DATABASE_URL / POSTGRES_URL ada (mis. database Neon/Supabase
  yang dihubungkan di Vercel) -> PostgreSQL, data permanen.
- Bila tidak ada -> SQLite lokal (file app/data/agrogarlic.db), cocok untuk dijalankan di laptop.
"""
import hashlib
import json
import os
import secrets
import sqlite3
from datetime import datetime
from pathlib import Path

DB_URL = next((os.environ[k] for k in ("DATABASE_URL", "POSTGRES_URL", "POSTGRES_PRISMA_URL")
               if os.environ.get(k)), None)
PG = bool(DB_URL)
DB_PATH = Path(os.environ.get("AGROGARLIC_DB", Path(__file__).parent / "data" / "agrogarlic.db"))

if PG:
    import psycopg
    from psycopg.rows import dict_row
    IntegrityError = psycopg.IntegrityError
else:
    IntegrityError = sqlite3.IntegrityError


def _q(sql, params=(), satu=False, semua=False, jumlah=False):
    """Jalankan satu query; '?' otomatis diganti '%s' untuk PostgreSQL."""
    if PG:
        with psycopg.connect(DB_URL, row_factory=dict_row, autocommit=True) as con:
            cur = con.execute(sql.replace("?", "%s"), params)
            if satu:
                return cur.fetchone()
            if semua:
                return cur.fetchall()
            return cur.rowcount if jumlah else None
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        with con:
            cur = con.execute(sql, params)
            if satu:
                r = cur.fetchone()
                return dict(r) if r else None
            if semua:
                return [dict(r) for r in cur.fetchall()]
            return cur.rowcount if jumlah else None
    finally:
        con.close()


def init():
    auto = "SERIAL PRIMARY KEY" if PG else "INTEGER PRIMARY KEY AUTOINCREMENT"
    for sql in (
        f"""CREATE TABLE IF NOT EXISTS users (
            id {auto}, nama TEXT, kontak TEXT UNIQUE NOT NULL,
            salt TEXT NOT NULL, hash TEXT NOT NULL,
            consent INTEGER NOT NULL DEFAULT 0, dibuat TEXT)""",
        """CREATE TABLE IF NOT EXISTS sesi (
            token TEXT PRIMARY KEY, user_id INTEGER NOT NULL, dibuat TEXT)""",
        """CREATE TABLE IF NOT EXISTS analisis (
            id TEXT PRIMARY KEY, user_id INTEGER, disimpan INTEGER NOT NULL DEFAULT 0,
            dibuat TEXT, hasil TEXT NOT NULL)""",
    ):
        _q(sql)


def _hash(sandi, salt):
    return hashlib.pbkdf2_hmac("sha256", sandi.encode(), salt.encode(), 100_000).hex()


def daftar(nama, kontak, sandi, consent):
    salt = secrets.token_hex(8)
    try:
        _q("INSERT INTO users (nama, kontak, salt, hash, consent, dibuat) VALUES (?,?,?,?,?,?)",
           (nama, kontak.strip().lower(), salt, _hash(sandi, salt), int(consent), _now()))
    except IntegrityError:
        return None
    return _q("SELECT id FROM users WHERE kontak=?", (kontak.strip().lower(),), satu=True)["id"]


def masuk(kontak, sandi):
    u = _q("SELECT * FROM users WHERE kontak=?", (kontak.strip().lower(),), satu=True)
    if not u or _hash(sandi, u["salt"]) != u["hash"]:
        return None
    token = secrets.token_urlsafe(24)
    _q("INSERT INTO sesi VALUES (?,?,?)", (token, u["id"], _now()))
    return token


def keluar(token):
    _q("DELETE FROM sesi WHERE token=?", (token,))


def user_dari_token(token):
    if not token:
        return None
    return _q("SELECT u.* FROM users u JOIN sesi s ON s.user_id=u.id WHERE s.token=?", (token,), satu=True)


def set_consent(user_id, consent):
    _q("UPDATE users SET consent=? WHERE id=?", (int(consent), user_id))


def simpan_analisis(hasil, user_id=None):
    _q("INSERT INTO analisis (id, user_id, dibuat, hasil) VALUES (?,?,?,?)",
       (hasil["analysis_id"], user_id, _now(), json.dumps(hasil, ensure_ascii=False)))


def ambil_analisis(aid):
    return _q("SELECT * FROM analisis WHERE id=?", (aid,), satu=True)


def tandai_disimpan(aid, user_id):
    return _q("UPDATE analisis SET disimpan=1, user_id=? WHERE id=? AND (user_id IS NULL OR user_id=?)",
              (user_id, aid, user_id), jumlah=True) > 0


def hapus_riwayat(aid, user_id):
    _q("UPDATE analisis SET disimpan=0 WHERE id=? AND user_id=?", (aid, user_id))


def riwayat(user_id):
    rows = _q("SELECT * FROM analisis WHERE user_id=? AND disimpan=1 ORDER BY dibuat DESC", (user_id,), semua=True)
    return [json.loads(r["hasil"]) | {"disimpan_pada": r["dibuat"]} for r in rows]


def _now():
    return datetime.now().isoformat(timespec="seconds")
