import json
import os
import sys
import time

from obswebsocket import obsws, requests
from config_manager import ConfigManager


class OBSClient:
    def __init__(self, config_path=None):
        self.ws = None

        # === 実行環境に応じたベースディレクトリ ===
        if getattr(sys, "frozen", False):
            # PyInstaller EXE
            base_dir = os.path.dirname(sys.executable)
        else:
            # dev 環境 / Python 実行 → src の絶対パス
            base_dir = os.path.dirname(os.path.abspath(__file__))

        # === config.json の絶対パス ===
        if config_path is None:
            # src/ の 1つ上がプロジェクト root
            root_dir = os.path.dirname(base_dir)
            config_path = os.path.join(root_dir, "config", "config.json")

        if not os.path.isfile(config_path):
            raise FileNotFoundError(f"config.json が見つかりません:\n{config_path}")

        # === ConfigManager を使って読み込む ===
        self.config_mgr = ConfigManager(config_path)
        cfg = self.config_mgr.config

        # ---- 重要：必要な属性を必ず定義する ----
        self.host = cfg.get("obs_host", "localhost")
        self.port = cfg.get("obs_port", 4455)
        self.password = self.config_mgr.decrypt_password(cfg.get("obs_password_enc", ""))

        self.replay_dir = cfg.get("replay_output_dir")
        self.ffmpeg_path = cfg.get("ffmpeg_path", "ffmpeg")

    # -------------------------------
    # 接続 / 切断
    # -------------------------------
    def connect(self):
        if self.ws:
            return

        print(f"[OBS] Connecting to ws://{self.host}:{self.port} ...")
        self.ws = obsws(self.host, self.port, self.password)

        try:
            self.ws.connect()
            print("[OBS] Connected successfully.")
        except Exception as e:
            print("[OBS] Connection failed:", e)
            raise

    def disconnect(self):
        if self.ws:
            self.ws.disconnect()
            print("[OBS] Disconnected.")
            self.ws = None

    # -------------------------------
    # リプレイ保存
    # -------------------------------
    def save_replay(self):
        if not self.ws:
            raise RuntimeError("OBS is not connected.")

        print("[OBS] Saving replay buffer...")
        try:
            self.ws.call(requests.SaveReplayBuffer())
            print("[OBS] Replay saved request sent.")
        except Exception as e:
            print("[OBS] Failed to save replay:", e)
            raise

    def _wait_file_stable(self, path: str, timeout=5.0):
        start = time.time()
        last_size = -1
        stable_count = 0

        while time.time() - start < timeout:
            try:
                size = os.path.getsize(path)
            except FileNotFoundError:
                time.sleep(0.1)
                continue

            if size > 0 and size == last_size:
                stable_count += 1
                if stable_count >= 3:
                    print(f"[OBS] File size stabilized: {size} bytes")
                    return
            else:
                stable_count = 0
                last_size = size

            time.sleep(0.1)

        print("[OBS] File size may still be changing, but timeout reached.")

    def save_replay_and_wait_for_file(self, timeout=10):
        if not self.replay_dir:
            raise RuntimeError("replay_output_dir が config.json に設定されていません。")
        if not os.path.isdir(self.replay_dir):
            raise RuntimeError(f"replay_output_dir が存在しません: {self.replay_dir}")

        before = set(os.listdir(self.replay_dir))

        self.save_replay()

        start = time.time()
        while time.time() - start < timeout:
            time.sleep(0.3)
            after = set(os.listdir(self.replay_dir))
            new_files = after - before
            if new_files:
                candidates = [
                    os.path.join(self.replay_dir, name)
                    for name in new_files
                    if os.path.isfile(os.path.join(self.replay_dir, name))
                ]
                if candidates:
                    latest = max(candidates, key=os.path.getmtime)
                    print(f"[OBS] New replay file detected: {latest}")

                    self._wait_file_stable(latest)
                    return latest

        raise RuntimeError("タイムアウト内に新しいリプレイファイルが見つかりませんでした。")
