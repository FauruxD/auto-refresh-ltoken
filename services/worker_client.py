import aiohttp
import os
import logging
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger("TokenRefresher.WorkerClient")

class LuciferWorkerClient:
    """
    Client HTTP asinkron untuk berkomunikasi dengan worker Lucifer Lua v2.86.
    Worker Lucifer bertanggung jawab untuk login ke Growtopia (Google Login / Legacy)
    dan menangkap ltoken baru.
    """

    def __init__(self, base_url: Optional[str] = None, secret_token: Optional[str] = None):
        self.base_url = (base_url or os.getenv("LUCIFER_WORKER_URL", "http://127.0.0.1:8081")).rstrip("/")
        self.secret_token = secret_token or os.getenv("WORKER_SECRET_TOKEN", "lucifer_token_refresher_secret_12345")

    async def check_health(self) -> Tuple[bool, str]:
        """Memeriksa apakah worker Lucifer sedang berjalan dan merespons."""
        url = f"{self.base_url}/health"
        headers = {"X-Worker-Token": self.secret_token}
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=4)) as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        return True, text
                    return False, f"HTTP Status {resp.status}"
        except Exception as e:
            return False, str(e)

    async def refresh_ltoken(self, account_data: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Mengirim instruksi ke worker Lucifer untuk login ke akun dan mengambil ltoken baru.
        Returns: (success: bool, new_ltoken: Optional[str], error_message: Optional[str])
        """
        url = f"{self.base_url}/refresh"
        headers = {
            "Content-Type": "application/json",
            "X-Worker-Token": self.secret_token
        }
        payload = {
            "account_type": account_data.get("account_type", "GOOGLE"),
            "email_or_growid": account_data.get("email_or_growid", ""),
            "password": account_data.get("password", ""),
            "recovery": account_data.get("recovery", ""),
            "mac": account_data.get("mac", "02:00:00:00:00:00"),
            "rid": account_data.get("rid", "00000000000000000000000000000000"),
            "current_ltoken": account_data.get("current_ltoken", "")
        }

        try:
            # Login Google / Growtopia biasanya butuh waktu 5-15 detik
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload, headers=headers) as resp:
                    data = await resp.json(content_type=None)
                    if resp.status == 200 and data.get("status") == "success":
                        new_token = data.get("ltoken")
                        if new_token:
                            return True, new_token, None
                        return False, None, "Worker tidak mengembalikan token valid."
                    else:
                        err = data.get("message") or data.get("error") or f"HTTP {resp.status}"
                        return False, None, err
        except aiohttp.ClientConnectorError:
            return False, None, "Tidak dapat terhubung ke Worker Lucifer (Worker Offline)."
        except Exception as e:
            logger.error(f"Error saat menghubungi worker: {e}", exc_info=True)
            return False, None, f"Terjadi kesalahan koneksi worker: {str(e)}"
