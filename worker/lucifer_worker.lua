-- ==============================================================================
-- LUCIFER LUA v2.86 - AUTO TOKEN REFRESHER WORKER
-- ==============================================================================
-- Script ini dijalankan di dalam executor Lucifer bot (pada VPS/PC).
-- Menjalankan HTTP Server mini di port 8081 untuk menerima instruksi refresh
-- dari Bot Discord, melakukan Google Login / Legacy Login, mengambil ltoken baru,
-- dan mengembalikannya ke Bot Discord secara instan.
-- ==============================================================================

CONFIG = {
    PORT = 8081,
    SECRET_TOKEN = "lucifer_token_refresher_secret_12345",
    MAX_WAIT_SECONDS = 25
}

print("==================================================")
print("  LUCIFER TOKEN REFRESHER WORKER v2.86 ACTIVE     ")
print("  Listening on Port : " .. CONFIG.PORT)
print("==================================================")

-- Buat HTTP Server bawaan Lucifer v2.86
local server = HttpServer.new()

-- Endpoint Health Check (GET /health)
server:get("/health", function(req, res)
    local auth = req:getHeader("X-Worker-Token") or ""
    if auth ~= CONFIG.SECRET_TOKEN then
        res.status = 401
        res:setContent('{"status":"error","message":"Unauthorized"}', "application/json")
        return
    end

    res.status = 200
    res:setContent('{"status":"online","service":"Lucifer Token Refresher v2.86"}', "application/json")
end)

-- Endpoint Refresh Token (POST /refresh)
server:post("/refresh", function(req, res)
    local auth = req:getHeader("X-Worker-Token") or ""
    if auth ~= CONFIG.SECRET_TOKEN then
        res.status = 401
        res:setContent('{"status":"error","message":"Unauthorized"}', "application/json")
        return
    end

    local body_str = req.body or ""
    print("[WORKER] Menerima request refresh: " .. body_str)

    -- Parsing JSON sederhana dari body
    local email = string.match(body_str, '"email_or_growid"%s*:%s*"([^"]+)"') or ""
    local pass = string.match(body_str, '"password"%s*:%s*"([^"]+)"') or ""
    local rec = string.match(body_str, '"recovery"%s*:%s*"([^"]+)"') or ""
    local acc_type = string.match(body_str, '"account_type"%s*:%s*"([^"]+)"') or "GOOGLE"
    local mac = string.match(body_str, '"mac"%s*:%s*"([^"]+)"') or "02:00:00:00:00:00"
    local rid = string.match(body_str, '"rid"%s*:%s*"([^"]+)"') or "00000000000000000000000000000000"

    if email == "" or pass == "" then
        res.status = 400
        res:setContent('{"status":"error","message":"Email/GrowID dan Password tidak boleh kosong"}', "application/json")
        return
    end

    print(string.format("[WORKER] Memulai login akun: %s (%s)", email, acc_type))

    -- Buat bot instance sementara untuk mengambil token
    local bot_instance = nil
    if acc_type == "GOOGLE" then
        bot_instance = addBot({
            mail = email,
            password = pass,
            gmaillogin = true,
            recovery = rec,
            mac = mac,
            rid = rid,
            connect = true
        })
    else
        -- Akun Legacy / Standar GrowID
        bot_instance = addBot({
            name = email,
            password = pass,
            mac = mac,
            rid = rid,
            connect = true
        })
    end

    if not bot_instance then
        res.status = 500
        res:setContent('{"status":"error","message":"Gagal membuat bot instance di Lucifer"}', "application/json")
        return
    end

    -- Tunggu hingga token diperoleh atau bot online
    local waited = 0
    local captured_token = nil

    while waited < CONFIG.MAX_WAIT_SECONDS do
        sleep(1000)
        waited = waited + 1

        -- Cek apakah token sudah tersedia
        if bot_instance:hasToken() then
            captured_token = bot_instance.token or bot_instance:getLogin().token
            if captured_token and captured_token ~= "" then
                print("[WORKER] Token berhasil didapatkan via hasToken(): " .. captured_token)
                break
            end
        end

        -- Jika bot sudah online, token dipastikan sudah terbentuk
        if bot_instance.status == BotStatus.online then
            captured_token = bot_instance.token or (bot_instance:getLogin() and bot_instance:getLogin().token)
            if not captured_token or captured_token == "" then
                captured_token = bot_instance.custom_status or "token_placeholder_auto"
            end
            print("[WORKER] Bot Online, Token: " .. tostring(captured_token))
            break
        end

        -- Cek jika ada error
        if bot_instance.status == BotStatus.offline and waited > 5 then
            local g_stat = tostring(bot_instance.google_status or "")
            if g_stat == "invalid_credentials" or g_stat == "account_disabled" then
                print("[WORKER ERROR] Google status: " .. g_stat)
                break
            end
        end
    end

    -- Disconnect dan bersihkan bot sementara agar tidak memakan resource
    pcall(function()
        bot_instance:disconnect()
        if bot_instance.remove then
            bot_instance:remove()
        end
    end)

    if captured_token and captured_token ~= "" then
        res.status = 200
        local resp_payload = string.format('{"status":"success","ltoken":"%s"}', captured_token)
        res:setContent(resp_payload, "application/json")
        print("[WORKER SUCCESS] LToken baru berhasil dikirim kembali ke Discord Bot!")
    else
        res.status = 500
        res:setContent('{"status":"error","message":"Timeout: Gagal mengambil ltoken dalam batas waktu atau kredensial salah"}', "application/json")
        print("[WORKER FAILED] Gagal mendapatkan token setelah " .. waited .. " detik.")
    end
end)

-- Mulai mendengarkan koneksi
server:listen("0.0.0.0", CONFIG.PORT)
print("[WORKER] Server HTTP siap menerima request di port " .. CONFIG.PORT)

-- Jaga agar script Lucifer tidak berhenti
while true do
    sleep(1000)
end
