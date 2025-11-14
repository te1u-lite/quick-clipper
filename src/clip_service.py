from datetime import datetime
from obs_client import OBSClient


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

        self.preset_labels = {
            "15s": "直近15秒",
            "30s": "直近30秒",
            "60s": "直近1分",
            "5min": "直近5分",
            "15min": "直近15分",
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
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] ホットキー検知: {label} のクリップを保存します。")

        try:
            self.obs.save_replay()
            print(f"[{timestamp}] {label} のクリップ保存要求をOBSに送信しました。")
        except Exception as e:
            print(f"[ClipService] クリップ保存に失敗しました: {e}")
