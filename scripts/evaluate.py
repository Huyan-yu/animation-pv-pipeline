"""评估：片段 A/B 同口径打分（4 量化维度 + 加权总分，75/90 口径）。

维度与权重：
  角色一致性 0.35 | 时序稳定性 0.30 | 背景保真 0.20 | 替换一致性 0.15
稳定判定：A、B 都 ≥ 75 → 管线稳定；仅单片段高 → 特调偏科（不鼓励）。
"""
import os, json
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_img(p):
    return np.array(Image.open(p).convert("RGB"), dtype=np.float32)

def frame_diff(a, b):
    return float(np.mean(np.abs(a - b))) / 255.0

def color_hist(region, bins=16):
    hist = np.zeros(bins * 3, dtype=np.float32)
    for c in range(3):
        hist[c*bins:(c+1)*bins] = np.histogram(region[..., c], bins=bins, range=(0, 256))[0]
    return hist / (np.linalg.norm(hist) + 1e-6)

def hist_sim(h1, h2):
    return float(np.dot(h1, h2))

def main():
    manifest = json.load(open(os.path.join(ROOT, "clips", "manifest.json"), encoding="utf-8"))
    orig = os.path.join(ROOT, "frames", "original")
    rep = os.path.join(ROOT, "frames", "replaced")
    sm = os.path.join(ROOT, "frames", "smoothed")

    report = []
    for clip in manifest:
        cid = clip["id"]
        n = len(clip["keyframes"])
        sm_frames = [load_img(os.path.join(sm, f"{cid}_f{str(i).zfill(2)}.png")) for i in range(n)]
        h, w = sm_frames[0].shape[:2]

        # 角色一致性：相邻平滑帧中央区域直方图相似度
        char_scores = []
        for i in range(n - 1):
            c1 = sm_frames[i][h//3:2*h//3, w//3:2*w//3].reshape(-1, 3)
            c2 = sm_frames[i+1][h//3:2*h//3, w//3:2*w//3].reshape(-1, 3)
            char_scores.append(hist_sim(color_hist(c1), color_hist(c2)))

        # 时序稳定性：相邻平滑帧整体差异（小=稳）
        stability = [1.0 - frame_diff(sm_frames[i], sm_frames[i+1]) for i in range(n - 1)]

        # 背景保真 + 替换一致性：原帧 vs 替换帧
        bg_scores, ssims = [], []
        for i in range(n):
            o = load_img(os.path.join(orig, f"{cid}_f{str(i).zfill(2)}.png"))
            r = load_img(os.path.join(rep, f"{cid}_f{str(i).zfill(2)}.png"))
            m = np.zeros((h, w), bool)
            m[:h//10] = True; m[-h//10:] = True; m[:, :w//10] = True; m[:, -w//10:] = True
            bg_scores.append(1.0 - frame_diff(o[m], r[m]))
            ssims.append(1.0 - frame_diff(o, r))

        total = (0.35 * float(np.mean(char_scores)) +
                 0.30 * float(np.mean(stability)) +
                 0.20 * float(np.mean(bg_scores)) +
                 0.15 * float(np.mean(ssims))) * 100

        report.append({
            "clip": cid,
            "char_consistency": round(float(np.mean(char_scores)), 4),
            "temporal_stability": round(float(np.mean(stability)), 4),
            "background_fidelity": round(float(np.mean(bg_scores)), 4),
            "replace_ssim": round(float(np.mean(ssims)), 4),
            "total_score": round(float(total), 2),
            "pass_75": bool(total >= 75),
        })

    out = os.path.join(ROOT, "outputs", "eval_report.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    stable = all(r["pass_75"] for r in report)
    print("[评估] 片段得分：")
    for r in report:
        print(f"  {r['clip']}: 总分 {r['total_score']}  ({'PASS' if r['pass_75'] else 'FAIL'} 75)")
    print(f"[评估] 管线整体稳定性: {'稳定(全部≥75)' if stable else '不稳定(存在<75)'}")
    print(f"[评估] 报告 → {out}")

if __name__ == "__main__":
    main()
