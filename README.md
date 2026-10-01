# 🔄 Growtopia LToken Auto Refresher (Discord Bot + Lucifer Worker)

Sistem bot Discord otomatis untuk me-refresh `ltoken` (Login Token) Growtopia yang kedaluwarsa (~6 jam).
Didesain khusus untuk toko/seller akun bot Growtopia, dengan konsep **Bearer Token as Lookup Key**:
> **Buyer cukup memasukkan LToken lama mereka ke bot Discord ➔ Sistem mencari kredensial akun di database ➔ Worker Lucifer login dan mengambil LToken baru ➔ LToken baru dikirimkan ke Buyer secara instan.**

---

## 🌟 Fitur Utama

1. **Auto Refresh via LToken Lama (`/refresh_ltoken <token>`):**
   - Buyer tidak perlu mengingat nomor pesanan atau username akun.
   - Cukup copy LToken dari executor ➔ tempel ke bot Discord ➔ terima LToken baru.
2. **Interactive Panel & Modal Pop-Up (`/refresh_panel`):**
   - Menampilkan embed tombol cantik yang bisa dipasang di channel Discord tokomu.
   - Tombol membuka Modal Pop-up Discord untuk input token yang rapi dan privat (*ephemeral*).
3. **Grace Period (Dukungan Token Sebelumnya):**
   - Menyimpan `previous_ltoken` sehingga jika buyer terlambat beberapa detik atau salah input token yang baru saja diperbarui, akun tidak akan terkunci.
4. **Enkripsi Kredensial Akun (AES / Fernet):**
   - Password dan data recovery akun disimpan dalam bentuk terenkripsi penuh di database SQLite.
5. **Lucifer Worker v2.86 Integration:**
   - Worker berjalan di executor Lucifer menggunakan `HttpServer` mini bawaan.
   - Mendukung **Google Login (`gmaillogin`)** dan **Legacy GrowID Login**.

---

## 📁 Struktur Folder Project

```text
Gabut 9 - Bot Discord Token Refresher/
├── cogs/
│   ├── admin.py          # Command admin: /add_account, /list_accounts, /worker_status
│   └── refresher.py      # Command user: /refresh_ltoken, /refresh_panel, Modal UI
├── database/
│   ├── manager.py        # Database manager asinkron (SQLite + Encryption)
│   └── schema.sql        # Skema tabel accounts & refresh_logs
├── services/
│   └── worker_client.py  # HTTP Client penghubung Discord Bot ke Worker Lucifer
├── utils/
│   └── encryption.py     # Modul enkripsi kredensial (Fernet / AES)
├── worker/
│   └── lucifer_worker.lua# Skrip Lucifer HTTP Server worker (login & capture token)
├── .env                  # Konfigurasi token & secret key
├── .env.example          # Contoh template konfigurasi
├── main.py               # Entry point bot Discord
├── requirements.txt      # Dependensi Python
└── README.md             # Dokumentasi panduan
```

---

## 🚀 Panduan Instalasi & Menjalankan

### Langkah 1: Persiapan Environment Python

1. Buka terminal di folder project ini:
   ```bash
   cd "c:\Users\MyBook Z Series\Documents\Learn\Gabut 9 - Bot Discord Token Refresher"
   ```
2. Buat dan aktifkan Virtual Environment (opsional tapi disarankan):
   ```bash
   python -m venv venv
   # Di Windows PowerShell:
   .\venv\Scripts\Activate.ps1
   ```
3. Install dependensi yang dibutuhkan:
   ```bash
   pip install -r requirements.txt
   ```

### Langkah 2: Konfigurasi `.env`

Edit file `.env`:
```ini
DISCORD_BOT_TOKEN=masukkan_token_bot_discord_kamu
DISCORD_GUILD_ID=1328644003100622941
OWNER_IDS=925562642989457500
SECRET_KEY=3vTYPpQgPk0np8fRj8tLuhcLdEDx1rFE3fWYyIyN2bc=
LUCIFER_WORKER_URL=http://127.0.0.1:8081
WORKER_SECRET_TOKEN=lucifer_token_refresher_secret_12345
```

### Langkah 3: Menjalankan Worker di Lucifer

1. Buka aplikasi/executor **Lucifer v2.86**.
2. Salin seluruh isi file [`worker/lucifer_worker.lua`](worker/lucifer_worker.lua) ke tab script Lucifer.
3. Jalankan script (**Start Script**).
4. Di console Lucifer akan tampil:
   ```text
   ==================================================
     LUCIFER TOKEN REFRESHER WORKER v2.86 ACTIVE     
     Listening on Port : 8081
   ==================================================
   [WORKER] Server HTTP siap menerima request di port 8081
   ```

### Langkah 4: Menjalankan Bot Discord

Jalankan bot Discord di terminal:
```bash
python main.py
```

---

## 📖 Cara Penggunaan

### 1. Menambahkan Akun ke Sistem (Admin)
Gunakan slash command `/add_account`:
* `/add_account label:Bot_Google_01 email_or_growid:user@gmail.com password:Rahasia123 account_type:GOOGLE initial_token:token_aktif_pertama`

### 2. Memeriksa Koneksi ke Worker (Admin)
* Jalankan `/worker_status` untuk memastikan bot Discord terhubung dengan lancar ke Worker Lucifer.

### 3. Memasang Panel Refresh untuk Buyer
* Di channel publik/toko, jalankan `/refresh_panel`.
* Panel interaktif dengan tombol **[ ⚡ Input LToken Lama ]** akan terpasang di channel.

### 4. Buyer Melakukan Refresh
* Buyer klik tombol **[ ⚡ Input LToken Lama ]**.
* Buyer menempelkan LToken lamanya.
* Dalam hitungan detik, bot Discord membalas secara privat (ephemeral) dengan **LToken baru** yang siap di-copy!
