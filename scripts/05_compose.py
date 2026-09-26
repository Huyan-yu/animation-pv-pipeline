"""阶段 5：成片合成。有 ffmpeg 合 .mp4；无则输出成片帧序列 + 说明。"""
import os, json, subprocess
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_cfg():
    import yaml
    with open(os.path.join(ROOT, "config", "pipeline.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)

def has_ffmpeg():
    try:
        return subprocess.run(["ffmpeg", "-version"], capture_output=True).returncode == 0
    except (FileNotFoundError, OSError):
        return False

def main():
    cfg = load_cfg()
    manifest = json.load(open(os.path.join(ROOT, "clips", "manifest.json"), encoding="utf-8"))
    out_root = os.path.join(ROOT, "outputs")
    os.makedirs(out_root, exist_ok=True)
    sm = os.path.join(ROOT, "frames", "smoothed")

    if not has_ffmpeg():
        for clip in manifest:
            cid = clip["id"]
            dst = os.path.join(out_root, f"clip_{cid}_final_frames")
            os.makedirs(dst, exist_ok=True)
            for i in range(len(clip["keyframes"])):
                src = os.path.join(sm, f"{cid}_f{str(i).zfill(2)}.png")
                Image.open(src).save(os.path.join(dst, os.path.basename(src)))
        note = os.path.join(out_root, "NO_FFMPEG.txt")
        with open(note, "w", encoding="utf-8") as f:
            f.write("ffmpeg 不可用，成片输出为帧序列（outputs/clip_*_final_frames）。\n"
                    "安装 ffmpeg 后重跑本阶段即可合成带音轨的 .mp4。\n")
        print(f"[阶段5] ffmpeg 不可用，已输出成片帧序列 → {note}")
        return

    for clip in manifest:
        cid = clip["id"]
        interval = cfg["keyframe_interval_sec"]
        out_vid = os.path.join(out_root, f"clip_{cid}_replaced.mp4")
        subprocess.run(["ffmpeg", "-y", "-framerate", str(int(1 / interval)),
                        "-i", os.path.join(sm, f"{cid}_f%02d.png"),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-r", str(cfg["frame_rate"]), out_vid], check=True, capture_output=True)
        audio = os.path.join(out_root, f"{cid}_audio.wav")
        subprocess.run(["ffmpeg", "-y", "-i", clip.get("clip_path", "PV.mp4"), "-vn", audio],
                       capture_output=True, check=True)
        final = os.path.join(out_root, f"clip_{cid}_final.mp4")
        subprocess.run(["ffmpeg", "-y", "-i", out_vid, "-i", audio,
                        "-c:v", "libx264", "-c:a", "aac", "-shortest", final],
                       check=True, capture_output=True)
    print(f"[阶段5] 成片合成完成 → {out_root}")

if __name__ == "__main__":
    main()
