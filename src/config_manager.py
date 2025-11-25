import json
import os
import base64
import sys

try:
    import win32crypt
except ImportError:
    win32crypt = None


class ConfigManager:
    def __init__(self, config_path=None):
        # -----------------------------
        # config_path の決定
        # -----------------------------
        if getattr(sys, "frozen", False):
            # exe バージョン → AppData/Roaming/quick-clipper/config.json
            appdata = os.getenv("APPDATA")
            config_dir = os.path.join(appdata, "quick-clipper")
            config_path = os.path.join(config_dir, "config.json")
        else:
            # 開発バージョン → プロジェクト/config/config.json
            base_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(base_dir)
            config_dir = os.path.join(project_root, "config")
            config_path = os.path.join(config_dir, "config.json")

        self.config_path = config_path
        os.makedirs(config_dir, exist_ok=True)

        # -----------------------------
        # 初期 config が無ければ作成
        # -----------------------------
        default = {
            "obs_host": "localhost",
            "obs_port": 4455,
            "obs_password_enc": "",
            "replay_output_dir": "",
            "ffmpeg_path": ""
        }

        if not os.path.isfile(self.config_path):
            self.save_config(default)

        # -----------------------------
        # config.json の読み込み
        # -----------------------------
        self.config = self.load_config()

        # -----------------------------
        # 古い形式 → 新形式へアップグレード
        # -----------------------------
        self._upgrade_old_config()

        # -----------------------------
        # ffmpeg_path の自動設定（※ここが重要※）
        # -----------------------------
        cfg = self.config

        if getattr(sys, "frozen", False):
            # exe → exe と同階層の ffmpeg/ffmpeg.exe
            exe_dir = os.path.dirname(sys.executable)
            auto_ffmpeg = os.path.join(exe_dir, "ffmpeg", "ffmpeg.exe")
        else:
            # 開発時 → プロジェクト直下の ffmpeg/ffmpeg.exe
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            auto_ffmpeg = os.path.join(project_root, "ffmpeg", "ffmpeg.exe")

        if not cfg.get("ffmpeg_path"):
            cfg["ffmpeg_path"] = auto_ffmpeg
            self.save_config(cfg)

    # ---------------- 暗号化/復号 ----------------

    def encrypt_password(self, plain: str) -> str:
        if not win32crypt:
            return plain
        data = win32crypt.CryptProtectData(
            plain.encode("utf-8"), None, None, None, None, 0
        )
        return base64.b64encode(data).decode("ascii")

    def decrypt_password(self, enc: str) -> str:
        if not win32crypt:
            return enc
        if not enc:
            return ""
        try:
            raw = base64.b64decode(enc)
            plain = win32crypt.CryptUnprotectData(raw, None, None, None, 0)[1]
            return plain.decode("utf-8")
        except Exception:
            return ""

    # ---------------- 読み書き ----------------
    def load_config(self):
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_config(self, cfg: dict):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)

    # ---------------- 古い形式からアップグレード ----------------
    def _upgrade_old_config(self):
        updated = False

        # obs_password → obs_password_enc
        if "obs_password" in self.config:
            plain = self.config["obs_password"]
            self.config["obs_password_enc"] = self.encrypt_password(plain)
            del self.config["obs_password"]
            updated = True

        # デフォルトのキーを補完
        defaults = {
            "obs_host": "localhost",
            "obs_port": 4455,
            "obs_password_enc": "",
            "replay_output_dir": "",
            "ffmpeg_path": ""
        }
        for k, v in defaults.items():
            if k not in self.config:
                self.config[k] = v
                updated = True

        if updated:
            self.save_config(self.config)
