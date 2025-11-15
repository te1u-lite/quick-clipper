import json
import os
import time

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

        self.replay_dir = cfg.get("replay_output_dir")
        self.ffmpeg_path = cfg.get("ffmpeg_path", "ffmpeg")

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

    def _wait_file_stable(self, path: str, timeout=5.0):
        """
        ファイルサイズが一定になるまで待つ。
        OBS が書き込み中の状態を避けるための簡易ヘルパ。
        """
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
                    # 3回連続同じサイズなら安定とみなす
                    print(f"[OBS] File size stabilized: {size} bytes")
                    return

            else:
                stable_count = 0
                last_size = size

            time.sleep(0.1)

        print("[OBS] File size may still be changing, but timeout reached.")

    def save_replay_and_wait_for_file(self, timeout=10):
        """
        リプレイバッファ保存をトリガーして、
        replay_output_dir に新しく作られたファイルパスを返す。
        """
        if not self.replay_dir:
            raise RuntimeError(
                "replay_output_dir が config.json に設定されていません。"
            )
        if not os.path.isdir(self.replay_dir):
            raise RuntimeError(
                f"replay_output_dir が存在しません: {self.replay_dir}"
            )

        before = set(os.listdir(self.replay_dir))

        # 通常の保存リクエスト
        self.save_replay()

        start = time.time()
        while time.time() - start < timeout:
            time.sleep(0.3)
            after = set(os.listdir(self.replay_dir))
            new_files = after - before
            if new_files:
                # 新しく出来たファイルの中で、更新時間が一番新しいものを返す
                candidates = [
                    os.path.join(self.replay_dir, name)
                    for name in new_files
                    if os.path.isfile(os.path.join(self.replay_dir, name))
                ]
                if candidates:
                    latest = max(candidates, key=os.path.getmtime)
                    print(f"[OBS] New replay file detected: {latest}")

                    # ここでサイズが安定するまで少し待つ
                    self._wait_file_stable(latest)

                    return latest

        raise RuntimeError("タイムアウト内に新しいリプレイファイルが見つかりませんでした。")
