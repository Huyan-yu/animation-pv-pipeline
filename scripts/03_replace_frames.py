"""阶段 3：帧级人物替换（保留背景，替换人物）。

mock：在原帧中央盖一个"新人物"占位区域。
真实（USE_REAL_GEN=1）：调 Agnes / SD 图生图，prompt 由 02 的 character_desc 驱动。
片段 A/B 用完全相同的 prompt_base + strength + seed（config 固定），不特调。
"""
import os, json
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_cfg():
    import yaml
    with open(os.path.join(ROOT, "config", "pipeline.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)

def replace_frame(src_img, char_desc, cfg):
    if os.environ.get("USE_REAL_GEN") == "1":
        # TODO: 接 Agnes / SD img2img，传 char_desc + src_img，返回替换图
        return src_img
    img = src_img.copy()
    d = ImageDraw.Draw(img)
    w, h = img.size
    d.rectangle([w//2-120, h//3, w//2+120, 2*h//3], fill=(80, 160, 220), outline="white", width=4)
    d.text((w//2-100, h//3+10), "NEW CHARACTER", fill="white")
    return img

def main():
    cfg = load_cfg()
    manifest = json.load(open(os.path.join(ROOT, "clips", "manifest.json"), encoding="utf-8"))
    ref = json.load(open(os.path.join(ROOT, "frames", "character_ref.json"), encoding="utf-8"))
    out_dir = os.path.join(ROOT, "frames", "replaced")
    os.makedirs(out_dir, exist_ok=True)

    for clip in manifest:
        cid = clip["id"]
        for kf in clip["keyframes"]:
            src = Image.open(kf["path"])
            replaced = replace_frame(src, ref["character_desc"], cfg)
            replaced.save(os.path.join(out_dir, f"{cid}_f{str(kf['idx']).zfill(2)}.png"))
    print(f"[阶段3] 关键帧替换完成 → {out_dir}")

if __name__ == "__main__":
    main()
