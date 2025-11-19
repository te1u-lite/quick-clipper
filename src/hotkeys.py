# hotkeys.py
import threading
import time
from queue import Queue

try:
    import win32api
    import win32con
except ImportError as e:
    raise RuntimeError(
        "pywin32 がインストールされていません。\n"
        "CLI 版のグローバルホットキーを使うには:\n"
        "  pip install pywin32\n"
        "を実行してください。"
    ) from e


def _is_pressed(vk_code: int) -> bool:
    """
    指定した仮想キーコードが現在押されているかどうかを返す。
    """
    if vk_code == 0:
        return False
    # 上位ビットが 1 なら押されている
    return (win32api.GetAsyncKeyState(vk_code) & 0x8000) != 0


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

    # Ctrl+Alt+数字 → プリセット
    preset_vk_map: dict[str, int] = {
        "15s": ord("1"),
        "30s": ord("2"),
        "60s": ord("3"),
        "5min": ord("4"),
        "15min": ord("5"),
    }

    prev_pressed: dict[str, bool] = {k: False for k in preset_vk_map.keys()}
    prev_quit = False

    # 簡易デバウンス（同じプリセットが短時間に連続発火しないように）
    last_fire_time: dict[str, float] = {k: 0.0 for k in preset_vk_map.keys()}
    debounce_sec = 0.3

    # コールバックを実行するワーカースレッド用キュー
    task_queue: Queue[str | None] = Queue()

    def worker():
        """
        キューから preset を取り出して callback(preset) を実行するワーカー。
        """
        while True:
            preset = task_queue.get()
            if preset is None:
                break
            try:
                callback(preset)
            except Exception as e:
                print(f"[Hotkeys] コールバック内でエラーが発生しました: {e}")

    worker_thread = threading.Thread(target=worker, daemon=True)
    worker_thread.start()

    try:
        print("Hotkey待機中... (Ctrl+Alt+Q で終了) ")

        while True:
            # 修飾キー状態
            ctrl = (
                _is_pressed(win32con.VK_CONTROL)
                or _is_pressed(getattr(win32con, "VK_LCONTROL", 0xA2))
                or _is_pressed(getattr(win32con, "VK_RCONTROL", 0xA3))
            )
            alt = (
                _is_pressed(win32con.VK_MENU)
                or _is_pressed(getattr(win32con, "VK_LMENU", 0xA4))
                or _is_pressed(getattr(win32con, "VK_RMENU", 0xA5))
            )

            # 各プリセットの立ち上がり検出
            now_t = time.time()
            for preset, vk in preset_vk_map.items():
                now = ctrl and alt and _is_pressed(vk)
                before = prev_pressed.get(preset, False)

                if now and not before:
                    # デバウンス
                    if now_t - last_fire_time[preset] >= debounce_sec:
                        print(f"[Hotkeys] ホットキー検知: {preset}")
                        task_queue.put(preset)
                        last_fire_time[preset] = now_t

                prev_pressed[preset] = now

            # 終了ホットキー Ctrl+Alt+Q
            quit_now = ctrl and alt and _is_pressed(ord("Q"))
            if quit_now and not prev_quit:
                print("Ctrl+Alt+Q が押されたので終了します。")
                break
            prev_quit = quit_now

            time.sleep(0.03)

    except KeyboardInterrupt:
        print("[Hotkeys] KeyboardInterrupt を受け取りました。終了します。")
    finally:
        # ワーカー終了
        task_queue.put(None)
        try:
            worker_thread.join(timeout=1.0)
        except Exception:
            pass
