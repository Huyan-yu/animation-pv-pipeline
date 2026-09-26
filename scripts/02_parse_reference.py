"""阶段 2：解析标准日式人设图 → 结构化角色描述。

mock：无真实人设图时用预制描述。
真实：接多模态 LLM 读人设图 → 输出 character_desc + reference_imgs。
"""
import os, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_cfg():
    import yaml
    with open(os.path.join(ROOT, "config", "pipeline.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)

def main():
    cfg = load_cfg()
    sheet = os.path.join(ROOT, cfg["reference_sheet"]) if not os.path.isabs(cfg["reference_sheet"]) else cfg["reference_sheet"]
    if not os.path.exists(sheet):
        print("[mock] 人设图不存在，使用预制角色描述")
    if os.environ.get("USE_REAL_GEN") == "1":
        # 真实：多模态 LLM 解析人设图
        ref = {"character_desc": "<TODO 接多模态 LLM 解析>", "reference_imgs": [sheet]}
    else:
        ref = {
            "character_desc": "a 17-year-old anime girl, long silver hair, green eyes, "
                              "black sailor uniform with red ribbon, thin build, "
                              "soft cel-shaded lighting, consistent character sheet style",
            "reference_imgs": [sheet],
            "source": "character_sheet (mock)" if not os.path.exists(sheet) else "character_sheet",
        }
    out = os.path.join(ROOT, "frames", "character_ref.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(ref, f, ensure_ascii=False, indent=2)
    print(f"[阶段2] 角色描述已生成: {out}")

if __name__ == "__main__":
    main()
