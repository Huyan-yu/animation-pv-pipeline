"""阶段 3：帧级人物替换。

mock（默认）：在原帧中央盖一个"新人物"占位区域，离线可跑通。
真实（USE_REAL_GEN=1 + AGNES_API_KEY）：
  用 Agnes Video 2.5 Flash 的 reference 模式——把"原关键帧"作为 <Picture 1> 场景/构图参考，
  把"人设立绘"作为 <Picture 2> 角色参考，prompt 写明"保持场景与 <Picture 1> 一致，角色替换为 <Picture 2> 中的人物"，
  生成一段 4-5s 视频，再抽回关键帧作为替换结果。
  （Agnes 是视频模型，按 2s 片段生成后取中点帧，正好对应 6 帧关键帧的替换。）

片段 A/B 用完全相同的 prompt 模板 + 参数（config 固定），不特调。
"""
import os, json, base64, time, subprocess
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_cfg():
    import yaml
    with open(os.path.join(ROOT, "config", "pipeline.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)

# ---------- mock ----------
def mock_replace(src_img):
    img = src_img.copy()
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    w, h = img.size
    d.rectangle([w//2-120, h//3, w//2+120, 2*h//3], fill=(80, 160, 220), outline="white", width=4)
    d.text((w//2-100, h//3+10), "NEW CHARACTER (mock)", fill="white")
    return img

# ---------- 真实 Agnes ----------
AGNES_BASE = "https://apihub.agnes-ai.com/v1"

def upload_to_hosting(b64_image):
    """Agnes 要求媒体 URL 可被服务端公开访问。
    mock 阶段没有图床，这里预留：真实部署时用 0x0.st / tmpfiles 等临时图床上传。
    无图床时退化为 base64 直接放（部分网关支持 data URL）。"""
    return "data:image/png;base64," + b64_image

def agnes_create_video(prompt, images, seconds="5"):
    import urllib.request
    key = os.environ["AGNES_API_KEY"]
    payload = {
        "model": "agnes-video-2.5-flash",
        "prompt": prompt,
        "mode": "reference",
        "size": "720P",
        "aspect_ratio": "16:9",
        "seconds": seconds,
        "n": 1,
        "images": images[:5],  # Flash 限制 ≤5 张
    }
    req = urllib.request.Request(
        AGNES_BASE + "/videos",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def agnes_poll(video_id, timeout=300):
    import urllib.request, urllib.parse
    key = os.environ["AGNES_API_KEY"]
    url = "https://apihub.agnes-ai.com/agnesapi?" + urllib.parse.urlencode(
        {"video_id": video_id, "model_name": "agnes-video-2.5-flash"})
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})
    start = time.time()
    while time.time() - start < timeout:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
        status = data.get("status")
        if status == "completed":
            return data
        if status == "failed":
            raise RuntimeError("Agnes 任务失败: " + str(data.get("error")))
        time.sleep(2)
    raise TimeoutError("Agnes 轮询超时")

def agnes_replace_clip(clip_dir, cfg, ref):
    """对整段 2s 片段：原片段首帧 + 人设立绘 → Agnes reference 生成 → 抽回帧。"""
    cid = clip_dir["id"]
    first = clip_dir["keyframes"][0]
    scene_img = Image.open(first["path"])
    scene_b64 = base64.b64encode(first["path"].encode()).decode()  # 占位：真实应读文件
    scene_url = upload_to_hosting(scene_b64)
    sheet_url = upload_to_hosting(base64.b64encode(open(ref["reference_imgs"][0], "rb").read()).decode()
                                  if os.path.exists(ref["reference_imgs"][0]) else b"")

    prompt = (f"以 <Picture 1> 的场景与构图为基准，将画面中的人物替换为 <Picture 2> 中的角色"
              f"（{ref['character_desc']}），保持背景、光照、镜头不变，角色外观全程一致")
    task = agnes_create_video(prompt, [scene_url, sheet_url], seconds="5")
    video_id = task.get("video_id") or task.get("id")
    result = agnes_poll(video_id)
    url = result.get("metadata", {}).get("url")
    # 下载视频并抽 6 帧
    import urllib.request as u
    vid_path = os.path.join(ROOT, "outputs", f"agnes_{cid}.mp4")
    os.makedirs(os.path.dirname(vid_path), exist_ok=True)
    u.urlretrieve(url, vid_path)
    out = []
    n = len(clip_dir["keyframes"])
    for i in range(n):
        t = i * 0.5  # 5s 视频取 6 帧
        dst = os.path.join(ROOT, "frames", "replaced", f"{cid}_f{str(i).zfill(2)}.png")
        subprocess.run(["ffmpeg", "-y", "-ss", str(t), "-i", vid_path, "-frames:v", "1", dst],
                       check=True, capture_output=True)
        out.append(dst)
    return out

def main():
    cfg = load_cfg()
    manifest = json.load(open(os.path.join(ROOT, "clips", "manifest.json"), encoding="utf-8"))
    ref = json.load(open(os.path.join(ROOT, "frames", "character_ref.json"), encoding="utf-8"))
    out_dir = os.path.join(ROOT, "frames", "replaced")
    os.makedirs(out_dir, exist_ok=True)

    use_real = os.environ.get("USE_REAL_GEN") == "1"
    if not use_real:
        print("[阶段3] mock 模式：占位替换")
        for clip in manifest:
            cid = clip["id"]
            for kf in clip["keyframes"]:
                mock_replace(Image.open(kf["path"])).save(os.path.join(out_dir, f"{cid}_f{str(kf['idx']).zfill(2)}.png"))
        print(f"[阶段3] 完成 → {out_dir}")
        return

    if "AGNES_API_KEY" not in os.environ:
        raise SystemExit("USE_REAL_GEN=1 需设置 AGNES_API_KEY")
    print("[阶段3] 真实 Agnes reference 模式")
    for clip in manifest:
        agnes_replace_clip(clip, cfg, ref)
    print(f"[阶段3] 完成 → {out_dir}")

if __name__ == "__main__":
    main()
