from obs_client import OBSClient
from clip_service import ClipService
from hotkeys import start_listening


def main():
    obs = OBSClient()
    try:
        obs.connect()
    except Exception:
        print("[main_cli] OBSへの接続に失敗したため終了します。")
        return

    clip_service = ClipService(obs)

    try:
        # ホットキーの監視開始
        start_listening(clip_service.handle_hotkey)
    except KeyboardInterrupt:
        print("[main_cli] KeyboardInterrupt を受け取りました。終了します。")
    finally:
        obs.disconnect()


if __name__ == "__main__":
    main()
