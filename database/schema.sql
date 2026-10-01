-- ==============================================================================
-- DATABASE SCHEMA: DISCORD BOT TOKEN REFRESHER
-- ==============================================================================

-- 1. Tabel Akun Bot Growtopia
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_label TEXT NOT NULL,                     -- Label bot (misal: 'Bot_Google_01')
    account_type TEXT NOT NULL DEFAULT 'GOOGLE',     -- Tipe login: 'GOOGLE', 'LEGACY', 'UBISOFT'
    email_or_growid TEXT NOT NULL,                   -- Email Gmail atau GrowID
    password_encrypted TEXT NOT NULL,                -- Password akun (Terenkripsi AES/Fernet)
    recovery_encrypted TEXT,                         -- Recovery email / phone (opsional, terenkripsi)
    mac TEXT NOT NULL DEFAULT '02:00:00:00:00:00',   -- Hardware MAC address
    rid TEXT NOT NULL DEFAULT '00000000000000000000000000000000', -- Device RID
    current_ltoken TEXT UNIQUE,                      -- LToken aktif saat ini
    previous_ltoken TEXT,                            -- LToken sebelumnya (grace period / cadangan)
    assigned_user_id INTEGER,                        -- ID Discord buyer yang menyewa akun (opsional)
    expires_at TIMESTAMP,                            -- Tanggal kedaluwarsa sewa akun
    token_updated_at TIMESTAMP,                      -- Terakhir kali token di-refresh
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index pencarian cepat berdasarkan token & kepemilikan user
CREATE INDEX IF NOT EXISTS idx_accounts_current_token ON accounts(current_ltoken);
CREATE INDEX IF NOT EXISTS idx_accounts_previous_token ON accounts(previous_ltoken);
CREATE INDEX IF NOT EXISTS idx_accounts_assigned_user ON accounts(assigned_user_id);

-- 2. Tabel Catatan / Riwayat Refresh Token
CREATE TABLE IF NOT EXISTS refresh_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    old_ltoken TEXT,
    new_ltoken TEXT,
    status TEXT NOT NULL,                            -- 'SUCCESS' atau 'FAILED'
    error_message TEXT,
    ip_or_source TEXT DEFAULT 'DISCORD',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
);
