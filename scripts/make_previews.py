import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def streams(path):
    output = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_streams", "-of", "json", str(path),
    ])
    return json.loads(output)["streams"]


def encode(filename):
    source = Path("public") / filename
    target = Path("previews") / (source.stem + "-stream.mp4")
    subprocess.run([
        "ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(source),
        "-map", "0:v:0", "-map", "0:a:0?", "-c:v", "libx264", "-threads", "2",
        "-preset", "veryfast", "-crf", "24", "-maxrate", "960k", "-bufsize", "960k",
        "-g", "50", "-keyint_min", "50", "-sc_threshold", "0", "-pix_fmt", "yuv420p",
        "-fps_mode", "passthrough", "-c:a", "copy", "-movflags", "+faststart", str(target),
    ], check=True)
    before, after = streams(source), streams(target)
    def signature(tracks):
        video = next(track for track in tracks if track["codec_type"] == "video")
        audio = [track for track in tracks if track["codec_type"] == "audio"]
        return ([video[k] for k in ("width", "height", "nb_frames", "avg_frame_rate", "duration")],
                [[t[k] for k in ("codec_name", "sample_rate", "channels", "duration")] for t in audio])
    if signature(before) != signature(after):
        raise ValueError(f"Stream timing or dimensions changed in {target}: {signature(before)} -> {signature(after)}")
    print(f"{target.name}: {target.stat().st_size} bytes; {signature(after)}", flush=True)


if __name__ == "__main__":
    Path("previews").mkdir(exist_ok=True)
    media = json.loads(Path("media.json").read_text())
    with ThreadPoolExecutor(max_workers=2) as workers:
        list(workers.map(encode, [item["file"] for item in media]))
