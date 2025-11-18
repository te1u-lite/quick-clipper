import os
import subprocess
import tkinter as tk

from PIL import Image, ImageTk


def _generate_thumbnail(video_path: str, ffmpeg_path: str, seek_time: float = 0.5) -> str | None:
    """
    動画ファイルから1枚だけサムネイル画像を生成して、そのパスを返す。
    失敗した場合は None
    """
    base, _ = os.path.splitext(video_path)
    thumb_path = base + "_thumb.jpg"

    cmd = [
        ffmpeg_path,
        "-y",
        "-ss",
        f"{seek_time}",
        "-i",
        video_path,
        "-vframes",
        "1",
        "-q:v",
        "4",
        thumb_path,
    ]

    print(f"[Overlay] Generating thumbnail: {' '.join(cmd)}")
    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError as e:
        print("[Overlay] サムネイル生成に失敗しました:", e)
        return None

    if not os.path.isfile(thumb_path):
        print("[Overlay] サムネイルファイルが見つかりませんでした:", thumb_path)
        return None

    return thumb_path


def _build_overlay_window(
    root_win: tk.Misc,
    message: str,
    seconds: int,
    video_path: str,
    ffmpeg_path: str = "ffmpeg",
    duration_ms: int = 1500,
    position: str = "top-right",
    width: int = 260,
    height: int = 60,
):
    """
    既存の Tk / Toplevel 上にオーバーレイ用の Toplevel を構築する共通処理。
    root_win: tk.Tk または tk.Toplevel
    """
    thumb_path = _generate_thumbnail(
        video_path,
        ffmpeg_path=ffmpeg_path,
        seek_time=max(0.1, seconds / 2) if seconds > 1 else 0.1,
    )

    # 親(root_win)にぶら下げる Toplevel
    win = tk.Toplevel(root_win)
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    try:
        win.attributes("-toolwindow", True)
    except tk.TclError:
        pass
    win.attributes("-alpha", 0.9)

    border_color = "#444444"
    card_bg = "#222222"
    text_main = "#ffffff"
    text_sub = "#aaaaaa"

    # 外枠
    win.configure(bg=border_color)
    outer = tk.Frame(win, bg=border_color, bd=0)
    outer.pack(fill="both", expand=True, padx=1, pady=1)

    # カード本体
    frame = tk.Frame(outer, bg=card_bg)
    frame.pack(fill="both", expand=True)

    frame.columnconfigure(0, weight=0)
    frame.columnconfigure(1, weight=1)

    thumb_label = tk.Label(frame, bg=card_bg)
    thumb_label.grid(row=0, column=0, rowspan=2, padx=10, pady=10)

    # サムネイル読み込み
    if thumb_path is not None:
        try:
            img = Image.open(thumb_path)

            max_w, max_h = 96, 64
            img.thumbnail((max_w, max_h), Image.LANCZOS)

            photo = ImageTk.PhotoImage(img)
            thumb_label.configure(image=photo)
            thumb_label.image = photo

            try:
                os.remove(thumb_path)
                print(f"[Overlay] 一時サムネイルを削除しました: {thumb_path}")
            except OSError as e:
                print(f"[Overlay] サムネイル削除に失敗しました: {e}")
        except Exception as e:
            print("[Overlay] サムネイル画像のロードに失敗しました:", e)

    # テキスト部分
    title_label = tk.Label(
        frame,
        text=message,
        fg=text_main,
        bg=card_bg,
        font=("Yu Gothic UI", 11, "bold"),
        anchor="w",
        justify="left",
    )
    title_label.grid(row=0, column=1, sticky="nw", padx=(0, 12), pady=(10, 0))

    detail_text = f"長さ: {seconds} 秒"
    detail_label = tk.Label(
        frame,
        text=detail_text,
        fg=text_sub,
        bg=card_bg,
        font=("Yu Gothic UI", 10),
        anchor="w",
        justify="left",
    )
    detail_label.grid(row=1, column=1, sticky="sw", padx=(0, 12), pady=(4, 10))

    # レイアウト完了 → 必要サイズ取得
    win.update_idletasks()
    req_w = max(width, win.winfo_reqwidth())
    req_h = max(height, win.winfo_reqheight())

    # 画面サイズ
    screen_w = win.winfo_screenwidth()
    screen_h = win.winfo_screenheight()
    margin_x = 24
    margin_y = 60

    pos = position.lower()
    if pos == "top-right":
        x = screen_w - req_w - margin_x
        y = margin_y
    elif pos == "top-left":
        x = margin_x
        y = margin_y
    elif pos == "bottom-left":
        x = margin_x
        y = max(0, screen_h - req_h - margin_y)
    else:  # "bottom-right" ほか
        x = screen_w - req_w - margin_x
        y = max(0, screen_h - req_h - margin_y)

    win.geometry(f"{req_w}x{req_h}+{int(x)}+{int(y)}")

    # 一定時間後に閉じる
    win.after(duration_ms, win.destroy)
    return win


def show_overlay_in_tk(
    root: tk.Tk,
    message: str,
    seconds: int,
    video_path: str,
    ffmpeg_path: str = "ffmpeg",
    duration_ms: int = 1500,
    position: str = "top-right",
    width: int = 260,
    height: int = 60,
):
    """
    既存の Tk アプリ（GUI版）で使うためのオーバーレイ表示関数。
    - root: メインウィンドウ (tk.Tk)
    """
    _build_overlay_window(
        root,
        message=message,
        seconds=seconds,
        video_path=video_path,
        ffmpeg_path=ffmpeg_path,
        duration_ms=duration_ms,
        position=position,
        width=width,
        height=height,
    )


def show_overlay(
    message: str,
    seconds: int,
    video_path: str,
    ffmpeg_path: str = "ffmpeg",
    duration_ms: int = 1500,
    position: str = "top-right",
    width: int = 260,
    height: int = 60,
):
    """
    CLI 用のシンプルなオーバーレイ通知。
    独自に tk.Tk() を作って mainloop まで回す。
    """
    root = tk.Tk()
    _build_overlay_window(
        root,
        message=message,
        seconds=seconds,
        video_path=video_path,
        ffmpeg_path=ffmpeg_path,
        duration_ms=duration_ms,
        position=position,
        width=width,
        height=height,
    )
    root.mainloop()
