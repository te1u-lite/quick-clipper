import os
import sys
import time
import configparser

from obswebsocket import obsws, requests
from config_manager import ConfigManager


class OBSClient:
    def __init__(self, config_path: str | None = None):
        self.ws = None

        # ========== config.json の場所を決定 ==========
        if config_path is not None:
            config_file = os.path.abspath(config_path)
        elif getattr(sys, "frozen", False):
            # exe 実行時 → AppData/Roaming/quick-clipper/config.json
            appdata = os.getenv("APPDATA")
            config_dir = os.path.join(appdata, "quick-clipper")
            config_file = os.path.join(config_dir, "config.json")
        else:
            # 開発環境 → プロジェクトルート/config/config.json
            base_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(base_dir)
            config_file = os.path.join(root_dir, "config", "config.json")

        # 絶対パスとして保持
        self.config_path = config_file

        # ConfigManager 経由で読み込む
        self.config_mgr = ConfigManager()
        cfg = self.config_mgr.config

        # ========= 重要：属性を必ず定義 =========
        self.host = cfg.get("obs_host", "localhost")
        self.port = cfg.get("obs_port", 4455)
        self.password = self.config_mgr.decrypt_password(
            cfg.get("obs_password_enc", "")
        )

        self.replay_dir = cfg.get("replay_output_dir")

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
            raise RuntimeError(
                "OBS へ接続できませんでした。\n"
                "OBS が起動していない、または WebSocket サーバーが無効です。\n"
                f"詳細: {e}"
            )

    def disconnect(self):
        if self.ws:
            self.ws.disconnect()
            print("[OBS] Disconnected.")
            self.ws = None

    def ensure_replaybuffer_running(self, retries=10, delay=0.5):
        """
        リプレイバッファが起動するまで StartReplayBuffer をリトライする。
        StartReplayBuffer が成功した時点で ReplayBuffer は確実に起動している。
        """
        if not self.ws:
            raise RuntimeError("OBS is not connected.")

        # 録画中なら開始不可
        if self.is_recording():
            raise RuntimeError("OBS は現在録画中のため、リプレイバッファを開始できません。")

        # まず最初の1回
        try:
            self.ws.call(requests.StartReplayBuffer())
            print("[OBS] ReplayBuffer started.")
            return
        except Exception as e:
            print("[OBS] StartReplayBuffer failed:", e)

        # ---- リトライ ----
        for i in range(retries):
            time.sleep(delay)
            try:
                print(f"[OBS] Retrying ReplayBuffer start... {i+1}/{retries}")
                self.ws.call(requests.StartReplayBuffer())
                print("[OBS] ReplayBuffer started.")
                return
            except Exception as e:
                print("[OBS] Retry failed:", e)

        # 全部ダメなら失敗
        raise RuntimeError("リプレイバッファを開始できませんでした。OBS の起動直後は少し待つ必要があります。")

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

    def get_obs_record_directory(self):
        """
        OBS のプロファイル設定 / ReplayBuffer 設定 / 録画設定を総合して
        最終的なリプレイバッファ保存先を決定する。
        全 OBS バージョン・全プロファイルに対応。
        """
        # ------------ 1) OBS プロファイル basic.ini を読む ------------
        appdata = os.getenv("APPDATA")
        fallback = os.path.normpath(os.path.join(os.path.expanduser("~"), "Videos"))

        if not appdata:
            return fallback

        profiles_path = os.path.join(appdata, "obs-studio", "basic", "profiles")

        try:
            profiles = [
                p for p in os.listdir(profiles_path)
                if os.path.isdir(os.path.join(profiles_path, p))
            ]
        except FileNotFoundError:
            # OBS がまだ一度も起動されていないなど
            return fallback

        if not profiles:
            return fallback

        profile = "default" if "default" in profiles else profiles[0]
        ini_path = os.path.join(profiles_path, profile, "basic.ini")

        try:
            with open(ini_path, "r", encoding="utf-8-sig") as f:
                ini_text = f.read()
        except FileNotFoundError:
            return fallback

        config = configparser.ConfigParser()
        config.read_string(ini_text)

        # ------------ 2) RecFilePath があるなら使う ------------
        if config.has_option("Output", "RecFilePath"):
            path = config.get("Output", "RecFilePath")
            if path:
                return os.path.normpath(path)

        # ------------ 3) ReplayBuffer.Path があるなら使う（新仕様） ------------
        if config.has_option("Output", "ReplayBuffer.Path"):
            path = config.get("Output", "ReplayBuffer.Path")
            if path:
                return os.path.normpath(path)

        # ------------ 4) 録画中なら recordingFilename からフォルダ取得 ------------
        try:
            status = self.ws.call(requests.GetRecordingStatus())
            recfile = status.getRecordingFilename()
            if recfile:
                return os.path.dirname(os.path.normpath(recfile))
        except Exception:
            pass

        # ------------ 5) 最終手段：Windows の Videos フォルダ（OBSデフォルト） ------------
        videos = os.path.join(os.path.expanduser("~"), "Videos")
        return os.path.normpath(videos)

    def save_replay_and_wait_for_file(self, timeout=10):
        # 1) OBS の保存先フォルダを設定ファイルから取得
        record_dir = self.get_obs_record_directory()
        record_dir = os.path.normpath(record_dir)

        before = set(os.listdir(record_dir))

        # 2) リプレイ保存
        self.save_replay()

        # 3) 新規ファイルを検出
        start = time.time()
        while time.time() - start < timeout:
            time.sleep(0.3)
            after = set(os.listdir(record_dir))
            new_files = after - before
            if new_files:
                candidates = [
                    os.path.join(record_dir, name)
                    for name in new_files
                    if os.path.isfile(os.path.join(record_dir, name))
                ]
                if candidates:
                    latest = max(candidates, key=os.path.getmtime)
                    self._wait_file_stable(latest)
                    return latest

        raise RuntimeError("OBS の Replay Buffer ファイルが見つかりませんでした。")

    def is_recording(self):
        if not self.ws:
            return False
        try:
            status = self.ws.call(requests.GetRecordingStatus())
            return status.getRecording()
        except Exception:
            return False
