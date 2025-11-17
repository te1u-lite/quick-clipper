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
    シンプルなオーバーレイ通知を表示する。
    duration_ms ミリ秒後に自動で消える (その間はホットキー処理は少しだけブロックされる)

    position: "top-right", "bottom-right" を想定。
    """

    thumb_path = _generate_thumbnail(
        video_path,
        ffmpeg_path=ffmpeg_path,
        seek_time=max(0.1, seconds / 2) if seconds > 1 else 0.1,
    )

    root = tk.Tk()

    # 枠なし & 最前面 & 透明度
    root.overrideredirect(True)  # タイトルバーなし
    root.attributes("-topmost", True)
    try:
        root.attributes("-toolwindow", True)  # 可能ならタスクバーに出さない
    except tk.TclError:
        pass
    root.attributes("-alpha", 0.9)  # 少し透過

    # 画面サイズ取得
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    margin = 24

    if position == "top-right":
        x = screen_w - width - margin
        y = margin
    else:  # bottom-right
        x = screen_w - width - margin
        y = screen_h - height - margin

    root.geometry(f"{width}x{height}+{int(x)}+{int(y)}")

    border_color = "#444444"
    card_bg = "#222222"
    text_main = "#ffffff"
    text_sub = "#aaaaaa"

    # 外枠
    root.configure(bg=border_color)
    outer = tk.Frame(root, bg=border_color, bd=0)
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

    # 一定時間後に閉じる
    root.after(duration_ms, root.destroy)
    root.mainloop()
