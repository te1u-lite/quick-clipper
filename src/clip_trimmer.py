import os
import subprocess


def _get_ffprobe_path(ffmpeg_path: str) -> str:
    """
    ffmpeg.exe のパスから、同じフォルダの ffprobe を推定。
    PATH に ffprobe が通っているならそのまま "ffprobe" でもOK。
    """
    if os.path.basename(ffmpeg_path).lower().startswith("ffmpeg"):
        ff_dir = os.path.dirname(ffmpeg_path)
        if ff_dir:
            return os.path.join(ff_dir, "ffprobe")
    return "ffprobe"


def get_duration_seconds(input_path: str, ffprobe_path: str = "ffprobe") -> float:
    """
    ffprobe を使って動画ファイルの長さ（秒）を取得する。
    1) format=duration
    2) stream=duration (v:0)
    3) frame=best_effort_timestamp_time の最後
    """
    # 1) format=duration
    cmd_format = [
        ffprobe_path,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        input_path,
    ]
    try:
        result = subprocess.run(
            cmd_format,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        duration_str = result.stdout.strip()
        print(f"[Trimmer] format.duration raw: '{duration_str}'")
        if duration_str and duration_str not in ("N/A", "nan", "inf"):
            return float(duration_str)
    except Exception as e:
        print("[Trimmer] format=duration 取得で例外:", e)

    # 2) stream=duration (映像ストリーム v:0)
    cmd_stream = [
        ffprobe_path,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        input_path,
    ]
    try:
        result2 = subprocess.run(
            cmd_stream,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        candidates = [line.strip() for line in result2.stdout.splitlines() if line.strip()]
        if candidates:
            duration_str2 = candidates
            print(f"[Trimmer] stream.duration raw: '{duration_str2}'")
            if duration_str2 and duration_str2 not in ("N/A", "nan", "inf"):
                return float(duration_str2)
    except Exception as e:
        print("[Trimmer] stream=duration 取得で例外:", e)

    # 3) frame=best_effort_timestamp_time の最後の値を duration とみなす
    cmd_frame = [
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "frame=best_effort_timestamp_time",
        "-of",
        "csv=p=0",
        input_path,
    ]
    try:
        result3 = subprocess.run(
            cmd_frame,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        lines = [line.strip() for line in result3.stdout.splitlines() if line.strip()]
        if not lines:
            raise RuntimeError("ffprobe から有効なフレームタイムスタンプが取得できませんでした。")

        last = lines[-1]
        print(f"[Trimmer] last frame ts raw: '{last}'")
        return float(last)
    except Exception as e:
        print("[Trimmer] frame=best_effort_timestamp_time 取得で例外:", e)
        raise RuntimeError("ffprobe で有効な duration が取得できませんでした。") from e


def trim_tail(input_path: str, seconds: int, ffmpeg_path: str = "ffmpeg") -> str:
    """
    input_path の「末尾 seconds 秒」を切り出して新しいファイルを作る。
    元ファイルは削除しない。
    """
    base, ext = os.path.splitext(input_path)
    output_path = f"{base}_{int(seconds)}s{ext}"

    ffprobe_path = _get_ffprobe_path(ffmpeg_path)

    # 1) 動画の総尺を取得
    duration = get_duration_seconds(input_path, ffprobe_path=ffprobe_path)
    print(f"[Trimmer] duration: {duration:.3f} sec")

    # 2) 開始位置 (末尾から seconds 秒前)
    start = max(0.0, duration - float(seconds))
    print(f"[Trimmer] start at: {start:.3f} sec (last {seconds} sec)")

    # 3)
    if seconds >= 300:
        # 長尺クリップは高速優先（シーク位置ぶれは多少許容）
        cmd = [
            ffmpeg_path,
            "-y",
            "-ss",
            str(start),
            "-i",
            input_path,
            "-t",
            str(int(seconds)),
            "-c",
            "copy",
            output_path,
        ]
        print(f"[Trimmer] Using FAST copy trim for {seconds} sec clip.")
    else:
        # 短めクリップは再エンコード（最後のN秒をなるべく正確に）
        cmd = [
            ffmpeg_path,
            "-y",
            "-ss",
            str(start),
            "-i",
            input_path,
            "-t",
            str(int(seconds)),
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",  # 速度優先
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            output_path,
        ]
        print(f"[Trimmer] Using re-encode trim for {seconds} sec clip.")

    print(f"[Trimmer] Running ffmpeg: {' '.join(cmd)}")

    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError as e:
        print("[Trimmer] ffmpeg によるトリミングに失敗しました:", e)
        raise

    print(f"[Trimmer] Created trimmed clip: {output_path}")
    return output_path
