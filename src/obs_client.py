import json
import os
from obswebsocket import obsws, requests


class OBSClient:
    def __init__(self, config_path="../config/config.json"):
        self.ws = None
        config_file = os.path.join(os.path.dirname(__file__), config_path)
        with open(config_file, "r", encoding="utf-8")as f:
            cfg = json.load(f)

        self.host = cfg["obs_host"]
        self.port = cfg["obs_port"]
        self.password = cfg["obs_password"]

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

    def save_replay(self):
        """
        リプレイバッファを保存 (OBS の SaveReplayBuffer コマンド)
        """
        if not self.ws:
            raise RuntimeError("OBS is not connected.")

        print("[OBS] Saving replay buffer...")
        try:
            self.ws.call(requests.SaveReplayBuffer())
            print("[OBS] Replay saved request sent.")
        except Exception as e:
            print("[OBS] Failed to save replay:", e)
            raise
