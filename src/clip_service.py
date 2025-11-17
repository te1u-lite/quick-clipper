from datetime import datetime
from obs_client import OBSClient
from clip_trimmer import trim_tail
import os

from overlay import show_overlay


class ClipService:
    """
    ホットキー → OBSリプレイ保存 の橋渡しをするサービスクラス
    ToDo:
        - ON/OFFフラグ
        - オーバーレイ通知コールバック
        - ログ保存
    """

    def __init__(self, obs_client: OBSClient):
        self.obs = obs_client
        self.enabled = True

        # ラベル (ログ用)
        self.preset_labels = {
            "15s": "直近15秒",
            "30s": "直近30秒",
            "60s": "直近1分",
            "5min": "直近5分",
            "15min": "直近15分",
        }

        # 実際に切り出す秒数
        self.preset_seconds = {
            "15s": 15,
            "30s": 30,
            "60s": 60,
            "5min": 5 * 60,
            "15min": 15 * 60,
        }

    def handle_hotkey(self, preset: str):
        """
        ホットキーから呼ばれるエントリポイント
        preset: "15s" / "30s" / "60s" / "5min" / "15min"
        """
        if not self.enabled:
            # ON/OFF用
            print("[ClipService] 現在は無効状態のためホットキーを無視しました。")
            return

        label = self.preset_labels.get(preset, preset)
        seconds = self.preset_seconds.get(preset)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if seconds is None:
            print(f"[ClipService] 未知のプリセット: {preset}")
            return

        print(f"[{timestamp}] ホットキー検知: {label} のクリップを保存します。")

        try:
            # 1) OBSにリプレイ保存を指示 + 保存された元ファイルのパスを取得
            original_path = self.obs.save_replay_and_wait_for_file()

            # 2) ffmpegで末尾 seconds 秒だけを切り出す
            trimmed_path = trim_tail(
                original_path,
                seconds=seconds,
                ffmpeg_path=self.obs.ffmpeg_path,
            )

            print(
                f"[{timestamp}] {label} のトリミング済みクリップを作成しました: {trimmed_path}"
            )

            # 3) 元15分 (フル) クリップを削除
            try:
                os.remove(original_path)
                print(f"[ClipService] 元クリップを削除しました: {original_path}")
            except Exception as e:
                print(f"[ClipService] 元クリップの削除に失敗しました: {e}")

            # オーバーレイ表示
            overlay_text = f"{label} のクリップを保存しました"
            show_overlay(
                overlay_text,
                seconds=seconds,
                video_path=trimmed_path,
                ffmpeg_path=self.obs.ffmpeg_path,
                duration_ms=1700,
                position="top-right")

        except Exception as e:
            print(f"[ClipService] クリップ保存またはトリミングに失敗しました: {e}")
