import keyboard
import threading


def start_listening(callback):
    """
    グローバルホットキーを登録し、Ctrl+Alt+Qが押されるまで待機する。

    callback(preset: str) を呼び出す:
        "15s", "30s", "60s", "5min", "15min"
    """

    print("=== Hotkey Listener 起動 ===")
    print("  Ctrl+Alt+1 : 直近15秒のクリップ")
    print("  Ctrl+Alt+2 : 直近30秒のクリップ")
    print("  Ctrl+Alt+3 : 直近1分のクリップ")
    print("  Ctrl+Alt+4 : 直近5分のクリップ")
    print("  Ctrl+Alt+5 : 直近15分のクリップ")
    print("  Ctrl+Alt+Q : 終了")
    print("============================")

    def run_async(preset: str):
        t = threading.Thread(target=callback, args=(preset,), daemon=True)
        t.start()

    # 各ホットキーとプレセットの対応を登録
    keyboard.add_hotkey("ctrl+alt+1", lambda: run_async("15s"))
    keyboard.add_hotkey("ctrl+alt+2", lambda: run_async("30s"))
    keyboard.add_hotkey("ctrl+alt+3", lambda: run_async("60s"))
    keyboard.add_hotkey("ctrl+alt+4", lambda: run_async("5min"))
    keyboard.add_hotkey("ctrl+alt+5", lambda: run_async("15min"))

    # 終了ホットキー
    print("Hotkey待機中... (Ctrl+Alt+Q で終了) ")
    keyboard.wait("ctrl+alt+q")

    print("Ctrl+Alt+Q が押されたので終了します。")
