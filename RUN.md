# 运行管线（Mock 模式，无需 API key）

## 环境

```bash
pip install pyyaml pillow numpy
# ffmpeg 可选（有则合成 .mp4，无则输出成片帧序列）
ffmpeg -version
```

## 全流程

```bash
python scripts/01_select_clips.py      # 选取片段 + 抽关键帧
python scripts/02_parse_reference.py   # 人设图 → 角色描述
python scripts/03_replace_frames.py    # 帧级替换
python scripts/04_stabilize.py         # 时序稳定
python scripts/05_compose.py           # 成片合成
python scripts/evaluate.py            # 评估（A/B 同口径打分）
```

## 输出

- `outputs/eval_report.json` — 片段 A/B 的 4 项指标 + 总分 + 75 达标判定
- `outputs/clip_A_final.mp4`（有 ffmpeg）或 `outputs/clip_A_final_frames/`（无 ffmpeg）
- `outputs/NO_FFMPEG.txt` — 无 ffmpeg 时的说明

## 真实接入（加分项）

- 设 `USE_REAL_GEN=1` + 配 Agnes / SD key → 阶段 3 走真实图像生成
- 真实 PV：把 `PV.mp4` 放到项目根，`config/pipeline.yaml` 的 `pv_source` 指向它，阶段 1 走 ffmpeg 裁剪
- 人设图：放 `assets/character_sheet.png`，阶段 2 接多模态 LLM 解析
