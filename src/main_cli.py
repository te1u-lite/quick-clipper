from obs_client import OBSClient
from clip_service import ClipService
from hotkeys import start_listening
from overlay import show_overlay


def main():
    obs = OBSClient()
    try:
        obs.connect()
    except Exception:
        print("[main_cli] OBSへの接続に失敗したため終了します。")
        return

    # CLI版: overlay.show_overlay を渡す
    clip_service = ClipService(obs, overlay_fn=show_overlay, logger=print)

    try:
        # ホットキーの監視開始
        start_listening(clip_service.handle_hotkey)
    except KeyboardInterrupt:
        print("[main_cli] KeyboardInterrupt を受け取りました。終了します。")
    finally:
        obs.disconnect()


if __name__ == "__main__":
    main()
