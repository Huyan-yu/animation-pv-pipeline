"""阶段 1：选取片段 + 抽关键帧（纯 PIL 版，无 ffmpeg 也可跑）。

输出 frames/original/{cid}_fNN.png + clips/manifest.json。
若系统有 ffmpeg 且 PV.mp4 存在则走真实裁剪；否则合成占位帧。
"""
import os, json, subprocess
from PIL import Image, ImageDraw

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

def synth_pv_frame(t, W=1280, H=720):
    img = Image.new("RGB", (W, H), (40 + int(t * 3) % 160, 60, 90))
    d = ImageDraw.Draw(img)
    x = int((t % 10) / 10 * W)
    d.ellipse([x-60, H//3, x+60, 2*H//3], fill=(200, 60, 60))
    return img

def main():
    cfg = load_cfg()
    frames_dir = os.path.join(ROOT, "frames", "original")
    os.makedirs(frames_dir, exist_ok=True)

    pv = os.path.join(ROOT, cfg["pv_source"])
    use_ffmpeg = has_ffmpeg() and os.path.exists(pv)
    print(f"[阶段1] ffmpeg 可用={has_ffmpeg()}, PV 存在={os.path.exists(pv)} → 模式={'真实' if use_ffmpeg else 'mock'}")

    manifest = []
    for clip in cfg["clips"]:
        cid = clip["id"]
        n = int(round((clip["out_sec"] - clip["in_sec"]) / cfg["keyframe_interval_sec"]))
        kfs = []
        for i in range(n):
            t = clip["in_sec"] + i * cfg["keyframe_interval_sec"]
            out = os.path.join(frames_dir, f"{cid}_f{str(i).zfill(2)}.png")
            if use_ffmpeg:
                subprocess.run(["ffmpeg", "-y", "-ss", str(t), "-i", pv,
                                "-frames:v", "1", out], check=True, capture_output=True)
            else:
                synth_pv_frame(t).save(out)
            kfs.append({"idx": i, "t": round(t, 2), "path": out})
        manifest.append({**clip, "keyframes": kfs})

    with open(os.path.join(ROOT, "clips", "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"[阶段1] 完成，{len(manifest)} 个片段 + 关键帧")

if __name__ == "__main__":
    main()
