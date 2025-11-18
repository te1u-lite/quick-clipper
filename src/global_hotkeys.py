import threading
import time

try:
    import win32api
    import win32con
except ImportError:
    win32api = None
    win32con = None


class GlobalHotkeyListener:
    """
    Window 用のシンプルなグローバルホットキー監視。

    callback(preset: str) 別スレッドで呼び出します。
    """

    def __init__(self, callback, logger=None, poll_interval=0.03):
        self.callback = callback
        self.logger = logger or (lambda msg: print(msg))
        self.poll_interval = poll_interval

        self._thread: threading.ThreadError | None = None
        self._stop_event = threading.Event()

        # 立ち上がり検出用の前回状態
        self._pressed_prev: dict[str, bool] = {
            "15s": False,
            "30s": False,
            "60s": False,
            "5min": False,
            "15min": False,
        }

    def start(self):
        if self._thread and self._thread.is_alive():
            return

        if win32api is None or win32con is None:
            raise RuntimeError(
                "pywin32 がインストールされていません。"
                " 例: pip install pywin32"
            )

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self.logger("[Hotkeys] グローバルホットキーリスナーを開始しました。")

    def stop(self):
        if not self._thread:
            return
        self._stop_event.set()
        self.logger("[Hotkeys] グローバルホットキーリスナーに停止指示を送りました。")
        self._thread = None

    def _loop(self):
        vk_map: dict[str, int] = {
            "15s": ord("1"),
            "30s": ord("2"),
            "60s": ord("3"),
            "5min": ord("4"),
            "15min": ord("5"),
        }

        while not self._stop_event.is_set():
            ctrl = (
                self._is_pressed(win32con.VK_CONTROL)
                or self._is_pressed(getattr(win32con, "VK_LCONTROL", 0xA2))
                or self._is_pressed(getattr(win32con, "VK_RCONTROL", 0xA3))
            )
            alt = (
                self._is_pressed(win32con.VK_MENU)
                or self._is_pressed(getattr(win32con, "VK_LMENU", 0xA4))
                or self._is_pressed(getattr(win32con, "VK_RMENU", 0xA5))
            )

            for preset, vk in vk_map.items():
                now = ctrl and alt and self._is_pressed(vk)
                prev = self._pressed_prev.get(preset, False)

                if now and not prev:
                    self._fire(preset)

                self._pressed_prev[preset] = now

            time.sleep(self.poll_interval)

    def _is_pressed(self, vk_code: int) -> bool:
        if vk_code == 0:
            return False
        return (win32api.GetAsyncKeyState(vk_code) & 0x8000) != 0

    def _fire(self, preset: str):
        self.logger(f"[Hotkeys] ホットキー検知: {preset}")

        t = threading.Thread(target=self.callback, args=(preset,), daemon=True)
        t.start()
