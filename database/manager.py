import aiosqlite
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from utils.encryption import encrypt_credential, decrypt_credential

logger = logging.getLogger("TokenRefresher.Database")

class DatabaseManager:
    """
    Mengelola seluruh operasi database asinkron untuk akun Growtopia,
    riwayat refresh, dan token lookup.
    """

    def __init__(self, db_path: Path | str):
        self.db_path = str(db_path)

    async def init_db(self, schema_file: Optional[Path | str] = None) -> None:
        if schema_file is None:
            schema_file = Path(__file__).resolve().parent / "schema.sql"

        with open(schema_file, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON;")
            await db.executescript(schema_sql)
            await db.commit()
        logger.info(f"Database berhasil diinisialisasi pada: {self.db_path}")

    async def find_account_by_token(self, token_str: str) -> Optional[Dict[str, Any]]:
        """
        Mencari akun berdasarkan LToken yang diinputkan buyer.
        Mengecek current_ltoken DAN previous_ltoken (grace period).
        """
        clean_token = token_str.strip()
        if not clean_token:
            return None

        query = """
            SELECT id, account_label, account_type, email_or_growid, password_encrypted,
                   recovery_encrypted, mac, rid, current_ltoken, previous_ltoken,
                   assigned_user_id, expires_at, token_updated_at, created_at
            FROM accounts
            WHERE current_ltoken = ? OR previous_ltoken = ?
            LIMIT 1;
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, (clean_token, clean_token)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None

                data = dict(row)
                data["password"] = decrypt_credential(data["password_encrypted"])
                data["recovery"] = decrypt_credential(data["recovery_encrypted"] or "")
                return data

    async def update_account_token(self, account_id: int, new_token: str) -> bool:
        """
        Memperbarui token akun:
        previous_ltoken <- current_ltoken lama
        current_ltoken <- new_token baru
        """
        query = """
            UPDATE accounts
            SET previous_ltoken = current_ltoken,
                current_ltoken = ?,
                token_updated_at = CURRENT_TIMESTAMP
            WHERE id = ?;
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(query, (new_token, account_id))
            await db.commit()
            return cursor.rowcount > 0

    async def add_account(
        self,
        account_label: str,
        email_or_growid: str,
        password: str,
        account_type: str = "GOOGLE",
        recovery: str = "",
        mac: str = "02:00:00:00:00:00",
        rid: str = "00000000000000000000000000000000",
        initial_token: Optional[str] = None,
        assigned_user_id: Optional[int] = None,
        expires_at: Optional[str] = None
    ) -> int:
        """Menambahkan akun baru ke database dengan password terenkripsi."""
        query = """
            INSERT INTO accounts (
                account_label, account_type, email_or_growid, password_encrypted,
                recovery_encrypted, mac, rid, current_ltoken, assigned_user_id, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        enc_pass = encrypt_credential(password)
        enc_rec = encrypt_credential(recovery) if recovery else ""

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(query, (
                account_label, account_type.upper(), email_or_growid, enc_pass,
                enc_rec, mac, rid, initial_token, assigned_user_id, expires_at
            ))
            await db.commit()
            return cursor.lastrowid

    async def list_all_accounts(self) -> List[Dict[str, Any]]:
        """Melihat seluruh daftar akun untuk admin/owner."""
        query = """
            SELECT id, account_label, account_type, email_or_growid, mac, rid,
                   current_ltoken, assigned_user_id, expires_at, token_updated_at
            FROM accounts
            ORDER BY id ASC;
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def assign_account_user(self, account_id: int, user_id: Optional[int], expires_at: Optional[str] = None) -> bool:
        """Menugaskan akun ke buyer tertentu atau melepasnya."""
        query = "UPDATE accounts SET assigned_user_id = ?, expires_at = ? WHERE id = ?;"
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(query, (user_id, expires_at, account_id))
            await db.commit()
            return cursor.rowcount > 0

    async def log_refresh(
        self,
        account_id: int,
        user_id: int,
        old_token: str,
        new_token: Optional[str],
        status: str,
        error_message: Optional[str] = None
    ) -> None:
        """Mencatat aktivitas refresh ke riwayat audit."""
        query = """
            INSERT INTO refresh_logs (account_id, user_id, old_ltoken, new_ltoken, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?);
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(query, (account_id, user_id, old_token, new_token, status, error_message))
            await db.commit()
