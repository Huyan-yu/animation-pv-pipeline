"""阶段 4：时序稳定（消除帧间闪烁）。

mock：对替换帧做前后帧加权平滑。
真实：光流插值 / 帧间一致性模型（RAFT + 时序平滑）。
"""
import os, json
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_cfg():
    import yaml
    with open(os.path.join(ROOT, "config", "pipeline.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)

def smooth_frame(prev, curr, next_):
    if prev is None and next_ is None:
        return curr
    if prev is None:
        return Image.blend(curr, next_, 0.3)
    if next_ is None:
        return Image.blend(prev, curr, 0.5)
    return Image.blend(Image.blend(prev, next_, 0.5), curr, 0.5)

def main():
    cfg = load_cfg()
    manifest = json.load(open(os.path.join(ROOT, "clips", "manifest.json"), encoding="utf-8"))
    rep = os.path.join(ROOT, "frames", "replaced")
    out = os.path.join(ROOT, "frames", "smoothed")
    os.makedirs(out, exist_ok=True)

    for clip in manifest:
        cid = clip["id"]
        n = len(clip["keyframes"])
        frames = [Image.open(os.path.join(rep, f"{cid}_f{str(i).zfill(2)}.png")) for i in range(n)]
        for i, cur in enumerate(frames):
            prev = frames[i-1] if i > 0 else None
            nxt = frames[i+1] if i < n-1 else None
            smooth_frame(prev, cur, nxt).save(os.path.join(out, f"{cid}_f{str(i).zfill(2)}.png"))
    print(f"[阶段4] 时序稳定完成 → {out}")

if __name__ == "__main__":
    main()
