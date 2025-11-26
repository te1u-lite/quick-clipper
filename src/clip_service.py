from datetime import datetime
import os

from obs_client import OBSClient
from clip_trimmer import trim_tail


class ClipService:
    """
    ホットキー → OBSリプレイ保存 の橋渡しをするサービスクラス

    overlay_fn:
        overlay_fn(message, seconds, video_path, ffmpeg_path, duration_ms, position)
        というシグネチャの関数を渡せる。
        GUI版では Tk メインスレッド経由のオーバーレイ関数、
        CLI版では overlay.show_overlay を渡す想定。

    logger:
        1引数の logger(str) を渡すとログ出力に使用。
        未指定なら print を使う。
    """

    def __init__(self, obs_client: OBSClient, overlay_fn=None, logger=None):
        self.obs = obs_client
        self.enabled = True
        self.overlay_fn = overlay_fn
        self.logger = logger

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

    # 内部用: ログヘルパ
    def _log(self, msg: str):
        if self.logger is not None:
            try:
                self.logger(msg)
                return
            except Exception:
                # logger 側で例外が出たら最後の手段として print
                pass
        print(msg)

    def handle_hotkey(self, preset: str):
        """
        ホットキーから呼ばれるエントリポイント
        preset: "15s" / "30s" / "60s" / "5min" / "15min"
        """
        if not self.enabled:
            self._log("[ClipService] 現在は無効状態のためホットキーを無視しました。")
            return

        label = self.preset_labels.get(preset, preset)
        seconds = self.preset_seconds.get(preset)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if seconds is None:
            self._log(f"[ClipService] 未知のプリセット: {preset}")
            return

        self._log(f"[{timestamp}] ホットキー検知: {label} のクリップを保存します。")

        try:
            # 1) OBSにリプレイ保存を指示 + 保存された元ファイルのパスを取得
            original_path = self.obs.save_replay_and_wait_for_file()

            # 2) ffmpegで末尾 seconds 秒だけを切り出す
            trimmed_path = trim_tail(
                original_path,
                seconds=seconds,
            )

            # GUIで指定した出力先に移動する
            output_dir = self.obs.config_mgr.config.get("replay_output_dir", "")
            if output_dir:
                try:
                    os.makedirs(output_dir, exist_ok=True)
                    new_path = os.path.join(output_dir, os.path.basename(trimmed_path))
                    os.replace(trimmed_path, new_path)
                    trimmed_path = new_path
                    self._log(f"[ClipService] トリミング結果を移動: {trimmed_path}")
                except Exception as e:
                    self._log(f"[ClipService] トリミング結果の移動に失敗しました: {e}")

            self._log(
                f"[{timestamp}] {label} のトリミング済みクリップを作成しました: {trimmed_path}"
            )

            # 3) 元15分 (フル) クリップを削除
            try:
                os.remove(original_path)
                self._log(f"[ClipService] 元クリップを削除しました: {original_path}")
            except Exception as e:
                self._log(f"[ClipService] 元クリップの削除に失敗しました: {e}")

            # 4) オーバーレイ表示（必要なら）
            if self.overlay_fn is not None:
                overlay_text = f"{label} のクリップを保存しました"
                try:
                    self.overlay_fn(
                        overlay_text,
                        seconds=seconds,
                        video_path=trimmed_path,
                        ffmpeg_path=self.obs.ffmpeg_path,
                        duration_ms=1700,
                        position="top-right",
                    )
                except Exception as e:
                    self._log(f"[ClipService] オーバーレイ表示に失敗しました: {e}")

        except Exception as e:
            self._log(f"[ClipService] クリップ保存またはトリミングに失敗しました: {e}")
