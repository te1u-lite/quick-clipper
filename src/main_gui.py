import threading
import queue
import tkinter as tk
from tkinter import ttk, messagebox


from obs_client import OBSClient
from clip_service import ClipService
from overlay import show_overlay_in_tk
from global_hotkeys import GlobalHotkeyListener


class QuickClipperApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Quick Clipper")
        self.root.geometry("420x260")
        self.root.minsize(420, 260)

        # OBS / ClipService
        self.obs_client: OBSClient | None = None
        self.clip_service: ClipService | None = None

        # ホットキー管理
        self.hotkey_listener: GlobalHotkeyListener | None = None
        self.running = False

        # クリップ処理用のキュー & ワーカースレッド
        self.task_queue = queue.Queue()
        self.worker_thread: threading.Thread | None = None

        self._build_ui()

        # ウィンドウ閉じるときの処理
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # UI構築
    def _build_ui(self):
        main_frame = ttk.Frame(self.root, padding=16)
        main_frame.pack(fill="both", expand=True)

        # タイトル
        title_label = ttk.Label(
            main_frame,
            text="Quick Clipper",
            font=("Yu Gothic UI", 16, "bold"),
        )
        title_label.pack(anchor="w")

        subtitle = ttk.Label(
            main_frame,
            text="OBS リプレイバッファをショートカットで保存",
            font=("Yu Gothic UI", 10),
            foreground="#666666",
        )
        subtitle.pack(anchor="w", pady=(0, 12))

        # ステータスエリア
        status_frame = ttk.LabelFrame(main_frame, text="ステータス")
        status_frame.pack(fill="x", pady=(0, 8))

        self.obs_status_var = tk.StringVar(value="OBS: 未接続")
        self.hotkey_status_var = tk.StringVar(value="ホットキー: 停止中")

        obs_label = ttk.Label(status_frame, textvariable=self.obs_status_var)
        obs_label.pack(anchor="w", padx=8, pady=2)

        hotkey_label = ttk.Label(status_frame, textvariable=self.hotkey_status_var)
        hotkey_label.pack(anchor="w", padx=8, pady=(0, 4))

        # ボタン行
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=(4, 8))

        self.start_button = ttk.Button(
            btn_frame, text="開始", command=self.on_start_clicked
        )
        self.start_button.pack(side="left")

        self.stop_button = ttk.Button(
            btn_frame, text="停止", command=self.on_stop_clicked, state="disabled"
        )
        self.stop_button.pack(side="left", padx=(8, 0))

        # 説明
        info_label = ttk.Label(
            main_frame,
            text=(
                "ショートカット:\n"
                "  Ctrl+Alt+1 : 直近15秒のクリップ\n"
                "  Ctrl+Alt+2 : 直近30秒のクリップ\n"
                "  Ctrl+Alt+3 : 直近1分のクリップ\n"
                "  Ctrl+Alt+4 : 直近5分のクリップ\n"
                "  Ctrl+Alt+5 : 直近15分のクリップ"
            ),
            font=("Yu Gothic UI", 9),
            justify="left",
        )
        info_label.pack(anchor="w", pady=(4, 8))

        # ログエリア（簡易）
        log_frame = ttk.LabelFrame(main_frame, text="ログ")
        log_frame.pack(fill="both", expand=True)

        self.log_text = tk.Text(
            log_frame,
            height=6,
            wrap="word",
            font=("Consolas", 9),
        )
        self.log_text.pack(fill="both", expand=True, padx=4, pady=4)

    # ---------- ログ出力 ----------
    def log(self, message: str):
        try:
            self.log_text.insert("end", message + "\n")
            self.log_text.see("end")
        except Exception:
            # ログ欄がすでに破棄されている等
            pass
        print(message)

    # ---------- ワーカースレッド ----------
    def _worker_loop(self):
        """
        キューに積まれたプリセットを順番に ClipService.handle_hotkey へ渡す。
        """
        while True:
            preset = self.task_queue.get()
            if preset is None:
                # 終了指示
                break

            if not self.running or not self.clip_service:
                continue

            try:
                self.clip_service.handle_hotkey(preset)
            except Exception as e:
                # Tk操作はメインスレッド経由で
                self.root.after(0, lambda: self.log(f"[GUI] クリップ保存処理でエラー: {e}"))

    # ---------- GUI用オーバーレイ呼び出し ----------
    def _show_overlay_gui(
        self,
        message: str,
        seconds: int,
        video_path: str,
        ffmpeg_path: str,
        duration_ms: int = 1700,
        position: str = "top-right",
    ):
        """
        ClipService から呼ばれるオーバーレイ表示関数（GUI版）。
        Tk の操作は root.after(0, ...) でメインスレッドに戻す。
        """

        def _run():
            try:
                show_overlay_in_tk(
                    self.root,
                    message=message,
                    seconds=seconds,
                    video_path=video_path,
                    ffmpeg_path=ffmpeg_path,
                    duration_ms=duration_ms,
                    position=position,
                )
            except Exception as e:
                self.log(f"[GUI] オーバーレイ表示に失敗しました: {e}")

        # メインスレッドで実行
        self.root.after(0, _run)

    # ---------- ボタンイベント ----------
    def on_start_clicked(self):
        if self.running:
            return

        # OBS 接続
        try:
            self.obs_client = OBSClient()
            self.obs_client.connect()
        except Exception as e:
            messagebox.showerror("エラー", f"OBSへの接続に失敗しました:\n{e}")
            self.obs_client = None
            self.clip_service = None
            self.obs_status_var.set("OBS: 接続失敗")
            return

        # ClipService 作成（GUI用オーバーレイ + GUIログを渡す）
        self.clip_service = ClipService(
            self.obs_client,
            overlay_fn=self._show_overlay_gui,
            logger=self.log,
        )

        self.obs_status_var.set("OBS: 接続中")

        # ワーカースレッド起動（未起動 or 止まっている場合のみ）
        if not self.worker_thread or not self.worker_thread.is_alive():
            self.worker_thread = threading.Thread(
                target=self._worker_loop,
                daemon=True,
            )
            self.worker_thread.start()
            self.log("[GUI] ワーカースレッドを起動しました。")

        self.register_hotkeys()
        self.running = True

        self.hotkey_status_var.set("ホットキー: 動作中 (Ctrl+Alt+1〜5)")
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")

        self.log("[GUI] 監視を開始しました。")

    def on_stop_clicked(self):
        if not self.running:
            return

        self.unregister_hotkeys()
        self.running = False

        self.hotkey_status_var.set("ホットキー: 停止中")
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")

        # キューを一旦クリア
        while not self.task_queue.empty():
            try:
                self.task_queue.get_nowait()
            except Exception:
                break

        # ワーカースレッドへ終了指示
        if self.worker_thread and self.worker_thread.is_alive():
            try:
                self.task_queue.put_nowait(None)
            except Exception:
                pass
            # daemon=True なので join は必須ではない
            self.worker_thread = None
            self.log("[GUI] ワーカースレッドに終了指示を送りました。")

        # OBS 切断
        if self.obs_client:
            try:
                self.obs_client.disconnect()
            except Exception:
                pass
            self.obs_client = None
            self.clip_service = None

        self.obs_status_var.set("OBS: 未接続")
        self.log("[GUI] 監視を停止しました。")

    # ---------- ホットキー登録 ----------
    def _on_hotkey(self, preset: str):
        """
        実際にホットキーが押されたときに呼ばれる関数。
        keyboard のフックスレッド上で動作するので、
        ここではキューに積むだけにして例外を外に漏らさない。
        """
        try:
            if not self.clip_service or not self.running:
                return

            self.task_queue.put_nowait(preset)
            self.root.after(0, lambda: self.log(f"[GUI] _on_hotkey: {preset} をキューに投入しました"))
        except Exception as e:
            # ここで例外を握りつぶさないと keyboard のフック自体が死ぬ
            self.root.after(0, lambda: self.log(f"[GUI] ホットキーキュー投入でエラー: {e}"))

    def register_hotkeys(self):
        if self.hotkey_listener and self.hotkey_listener._thread and self.hotkey_listener._thread.is_alive():
            return  # すでに登録済み

        self.hotkey_listener = GlobalHotkeyListener(
            callback=self._on_hotkey,
            logger=self.log,
        )
        try:
            self.hotkey_listener.start()
        except Exception as e:
            # ここで失敗したら OBS 接続を解除しておく
            self.log(f"[GUI] ホットキーリスナー開始に失敗しました: {e}")
            messagebox.showerror("エラー", f"グローバルホットキーの開始に失敗しました:\n{e}")

            if self.obs_client:
                try:
                    self.obs_client.disconnect()
                except Exception:
                    pass
                self.obs_client = None
                self.clip_service = None
            self.running = False
            self.hotkey_status_var.set("ホットキー: 停止中")
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")
            raise

        self.log("[GUI] ホットキーを登録しました。")

    def unregister_hotkeys(self):
        if self.hotkey_listener:
            try:
                self.hotkey_listener.stop()
            except Exception:
                pass
            self.hotkey_listener = None
            self.log("[GUI] ホットキーリスナーを解除しました。")

    # ---------- 終了処理 ----------
    def on_close(self):
        # アプリ終了時にクリーンアップ
        try:
            self.on_stop_clicked()
        except Exception:
            pass
        self.root.destroy()


def main():
    root = tk.Tk()
    try:
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
    except Exception:
        pass

    app = QuickClipperApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
