import json
import os
import base64

try:
    import win32crypt
except ImportError:
    win32crypt = None


class ConfigManager:
    def __init__(self, config_path):
        self.config_path = config_path

        default = {
            "obs_host": "localhost",
            "obs_port": 4455,
            "obs_password_enc": "",
            "replay_output_dir": "",
            "ffmpeg_path": "ffmpeg",
        }

        if not os.path.isfile(self.config_path):
            self.save_config(default)

        self.config = self.load_config()

    # 暗号化/複合
    def encrypt_password(self, plain: str) -> str:
        if not win32crypt:
            return plain
        data = win32crypt.CryptProtectData(plain.encode("utf-8"), None, None, None, None, 0)
        return base64.b64encode(data).decode("ascii")

    def decrypt_password(self, enc: str) -> str:
        if not win32crypt:
            return enc
        try:
            raw = base64.b64decode(enc)
            plain = win32crypt.CryptUnprotectData(raw, None, None, None, 0)[1]
            return plain.decode("utf-8")
        except Exception:
            return ""

    # 設定の読み書き
    def load_config(self) -> dict:
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_config(self, cfg: dict):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
