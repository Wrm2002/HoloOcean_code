# WRM HoloOcean/UE5 工作区入口

更新时间：2026-06-12

## 2026-06-12 代码重构状态

重构前代码已经备份：

```text
GitHub:
git@github.com:Wrm2002/HoloOcean_code.git

本地完整备份分支:
backup/pre-refactor-20260612
```

当前推荐先从短入口读项目，不要一上来读长 UE 场景脚本：

```bash
python3 -m wrm_pipeline status
python3 -m wrm_pipeline list-scripts
python3 -m wrm_pipeline check-final-exam
```

重构说明见：

```text
WRM_REFACTOR_STATUS_CN.md
wrm_projects/08_refactor/README_CN.md
```

## 2026-06-11 最新状态

### 慢速接力版总结：我们到底要做什么

终极目标不是只做一张好看的 UE 地图，也不是只做一个声呐 demo，而是做出一条可汇报、可复现、可继续扩展的水下多模态数据生成链路：

```text
Gaea/高度图大地形
-> UE5/Holodeck 水下大世界
-> HoloOcean package/scenario 自动运行
-> C++ LineTrace 扇形声呐 + RGB 同步采集
-> YOLO 标签 / meta JSON / 3D 点云 CSV+PLY
-> 用小模型或检测训练证明数据链路可用于识别研究
```

当前最重要的判断：

```text
声呐、标签、点云、HoloOcean 自动采集这条工程链路已经基本闭合，不要从头重做声呐。
当前短板已经转到“场景真实性、资产真实性、数据规模和训练验证”。
为了汇报，当前默认使用清澈水体/中性海底视觉，不再使用红褐或重浑浊水体。
```

### 2026-06-10 清澈汇报版最新产物

为避免红色/浑浊水体影响汇报，已经生成一版清澈深蓝远景的 4K 大世界小样本：

```text
dataset:
~/.local/share/holoocean/2.3.0/worlds/WRMAbyss/Linux/Holodeck/Saved/SonarDataset_BigWorld4KBatch08_ClearBlue

representative RGB:
~/.local/share/holoocean/2.3.0/worlds/WRMAbyss/Linux/Holodeck/Saved/SonarDataset_BigWorld4KBatch08_ClearBlue/images_rgb/bigworld4k_batch08_clearblue000000_rgb.png

audit:
wrm_projects/05_validation_outputs/bigworld4k_batch08_clearblue_audit_20260610/audit_report.md
wrm_projects/05_validation_outputs/bigworld4k_batch08_clearblue_audit_20260610/audit_preview.png
```

审计结果：

```text
frames = 8
rgb_frames = 8
point_csv_frames = 8
point_ply_frames = 8
total_boxes = 55
classes = {3: 16, 4: 24, 5: 8, 6: 7}
boxes_per_frame min/avg/max = 6 / 6.88 / 8
point_cloud_classes = {-1: 35616, 3: 161, 4: 174, 5: 82, 6: 7}
```

这版只用于“清澈视觉汇报基线”。更完整的数据规模仍参考 Batch05 的 24 帧目标簇闭环。

### 2026-06-10 材质/贴图管线 v0

第四步已完成一个可复用的材质管线基线：脚本会自动创建 WRM 材质库，并在每次生成场景时分配给海底、岩石、金属、沙和植物。

```text
material assets:
engine/Content/BigWorld4K20260609/Materials/M_WRM_Seabed_Neutral.uasset
engine/Content/BigWorld4K20260609/Materials/M_WRM_Rock_DarkWet.uasset
engine/Content/BigWorld4K20260609/Materials/M_WRM_Metal_DarkWet.uasset
engine/Content/BigWorld4K20260609/Materials/M_WRM_Sand_Muted.uasset
engine/Content/BigWorld4K20260609/Materials/M_WRM_Plant_Kelp.uasset

dataset:
~/.local/share/holoocean/2.3.0/worlds/WRMAbyss/Linux/Holodeck/Saved/SonarDataset_BigWorld4KBatch10_MaterialV0

representative RGB:
~/.local/share/holoocean/2.3.0/worlds/WRMAbyss/Linux/Holodeck/Saved/SonarDataset_BigWorld4KBatch10_MaterialV0/images_rgb/bigworld4k_batch10_materialv0000000_rgb.png

audit:
wrm_projects/05_validation_outputs/bigworld4k_batch10_materialv0_audit_20260610/audit_report.md
wrm_projects/05_validation_outputs/bigworld4k_batch10_materialv0_audit_20260610/audit_preview.png
```

审计结果：

```text
frames = 8
rgb_frames = 8
point_csv_frames = 8
point_ply_frames = 8
total_boxes = 55
classes = {3: 16, 4: 24, 5: 8, 6: 7}
point_cloud_classes = {-1: 35616, 3: 161, 4: 174, 5: 82, 6: 7}
```

这版说明：材质分配不会破坏 RGB/sonar/YOLO/meta/point cloud 链路。它不是最终电影级贴图，后续如有真实 PBR/扫描/资产包材质，可以替换同名材质或扩展材质库。

### 2026-06-11 Step5A 数据生产管线

第五步已经开始，当前重点不是写识别算法，而是建立稳定产出高质量水下仿真数据集的工作线。已新增可参数化跑批脚本：

```text
scripts/run_bigworld4k_step5_dataset_batch.sh
scripts/audit_dataset_visual_quality.py
```

默认流程：

```text
UE setup -> WRMAbyss package -> 保守同步安装 -> HoloOcean 采集 -> sonar/label/point audit -> RGB visual quality audit -> batch summary
```

Step5A 32 帧基线已经跑通：

```text
dataset:
~/.local/share/holoocean/2.3.0/worlds/WRMAbyss/Linux/Holodeck/Saved/SonarDataset_BigWorld4KStep5A_MaterialV0_32f

audit:
wrm_projects/05_validation_outputs/step5_BigWorld4KStep5A_MaterialV0_32f_audit/audit_report.md
wrm_projects/05_validation_outputs/step5_BigWorld4KStep5A_MaterialV0_32f_audit/audit_preview.png

visual quality:
wrm_projects/05_validation_outputs/step5_BigWorld4KStep5A_MaterialV0_32f_audit/visual_quality_report.md

summary:
wrm_projects/05_validation_outputs/step5_BigWorld4KStep5A_MaterialV0_32f_summary.md
```

审计结果：

```text
frames = 32
rgb_frames = 32
point_csv_frames = 32
point_ply_frames = 32
total_boxes = 242
classes = {3: 64, 4: 96, 5: 32, 6: 50}
boxes_per_frame min/avg/max = 6 / 7.56 / 9
point_cloud_classes = {-1: 142418, 3: 725, 4: 840, 5: 340, 6: 57}
visual avg_luma min/avg/max = 17.168 / 25.130875 / 42.002
visual status = ok
```

Step5A 证明：当前 pipeline 可以稳定产出 32 帧级别的 RGB/sonar/YOLO/meta/point cloud 数据，并自动生成质量报告。下一步应继续扩展采集变化，而不是进入识别训练。

### 2026-06-11 Step5B AIGC/FBX 真实资产环境预览

用户提供了桌面 `Fbx` 文件夹中的 11 个 AIGC/2D-to-3D FBX 模型，已完成自动导入、摆放、打包和短批次采集预览。

```text
source:
/home/wrm/桌面/Fbx

imported assets:
engine/Content/WRMImported/FbxEnv_20260611/

scripts:
scripts/ue_import_fbx_environment_assets.py
scripts/ue_place_fbx_environment_scene.py

reports:
wrm_projects/05_validation_outputs/fbx_env_20260611_import_report.json
wrm_projects/05_validation_outputs/fbx_env_20260611_placement_report.json
```

导入结果：

```text
FBX count = 11
lighter meshes = 9 个，约 4.1 万到 5 万 triangles
heavy meshes = 2 个，约 128 万和 150 万 triangles
placement = 11 个候选环境资产已摆进 /Game/BigWorld4K20260609/Maps/Main_World_10km_4K_20260609
tags = wrm_environment_asset / candidate_sonar_target / fbx_env_20260611 / review_class_required
```

注意：这些 FBX 当前先作为“候选真实环境资产”进入场景，暂时没有加正式 `sonar_target + class_x`，避免未确认形态就污染正式类别。

Step5B 16 帧预览已跑通：

```text
dataset:
~/.local/share/holoocean/2.3.0/worlds/WRMAbyss/Linux/Holodeck/Saved/SonarDataset_BigWorld4KStep5B_FbxEnvPreview_16f

audit:
wrm_projects/05_validation_outputs/step5_BigWorld4KStep5B_FbxEnvPreview_16f_audit/audit_report.md
wrm_projects/05_validation_outputs/step5_BigWorld4KStep5B_FbxEnvPreview_16f_audit/audit_preview.png

RGB preview:
wrm_projects/05_validation_outputs/step5_BigWorld4KStep5B_FbxEnvPreview_16f_audit/rgb_preview_contact_sheet.png

visual quality:
wrm_projects/05_validation_outputs/step5_BigWorld4KStep5B_FbxEnvPreview_16f_audit/visual_quality_report.md
```

审计结果：

```text
frames = 16
rgb_frames = 16
point_csv_frames = 16
point_ply_frames = 16
total_boxes = 104
classes = {3: 32, 4: 38, 5: 16, 6: 18}
boxes_per_frame min/avg/max = 6 / 6.50 / 8
point_cloud_classes = {-1: 71628, 3: 334, 4: 321, 5: 168, 6: 19}
visual avg_luma min/avg/max = 21.689 / 31.07775 / 41.335
visual status = ok
```

审计中出现的额外 `class_id=-1` StaticMeshActor 是新 FBX 候选环境资产被声呐命中了，但还没正式标成目标类别。这是预期结果；下一步如果要把它们变成训练目标，需要先人工确认每个 FBX 是岩石、金属残骸、植物、管线等，再批量加 `sonar_target + class_x + material_x`。

### 还没有完成的事

```text
1. 真实水下资产：当前 class4/5/6 仍有较多 basic shape / StarterContent 组合，需要换成真实 FBX/OBJ/UE/AIGC/扫描资产。
2. 高质量真实贴图：材质管线 v0 已完成，但还不是高分辨率 PBR/扫描级材质。
3. 更大数据规模：Step5A 已有 32 帧稳定跑批，需要继续扩展路径、角度、距离、遮挡后采更多批次。
4. 多目标检测训练：当前 tiny baseline 只是 smoke proof，不是正式多目标检测结论。
5. 高级声学真实感：多路径、频率吸收、旁瓣、散斑标定、真实材料声阻抗还没做。
6. Gaea 8K/16K 和更高质量地形/贴图：属于远期增强，不是当前第一步。
```

### 用户和 Codex 分工

用户优先做：

```text
1. 看代表性 RGB/sonar 图，判断“汇报观感”是否接受。
2. 提供或下载真实水下资产：岩石、水草、管线、沉船残骸、海底碎片、FBX/OBJ/UE asset pack。
3. 提供 Gaea 8K/16K、高质量材质、AIGC 3D、ComfyUI/混元 3D/Gaussian Splatting 生成结果。
4. 对 UE 编辑器里的视觉效果做主观确认：颜色、比例、真实感、是否适合汇报。
5. 处理账号、许可证、付费资源、验证码、外部软件下载等 Codex 不能代做的事。
```

Codex 优先做：

```text
1. UE Python 自动化：摆放资产、加 sonar_target/class_x/material_x 标签、保存关卡。
2. WRMAbyss 打包、同步安装、HoloOcean scenario 运行。
3. RGB/sonar/YOLO/meta/point cloud 数据采集和审计。
4. 把已有模型接进 class3/4/5/6 目标体系，保证标签和点云闭合。
5. 写/更新 README、Prompt、审计报告和下一步计划。
6. 后续准备多目标检测数据整理和训练脚本。
```

4K 大世界已经从 60 帧基础目标采集推进到 24 帧“半真实目标簇”采集闭环：

```text
UE/Holodeck map:
/Game/BigWorld4K20260609/Maps/Main_World_10km_4K_20260609

HoloOcean scenario:
Main_World_10km_4K_20260609-LineTraceDataset

latest dataset:
~/.local/share/holoocean/2.3.0/worlds/WRMAbyss/Linux/Holodeck/Saved/SonarDataset_BigWorld4KBatch05

latest audit:
wrm_projects/05_validation_outputs/bigworld4k_batch05_audit_20260610/audit_report.md
wrm_projects/05_validation_outputs/bigworld4k_batch05_audit_20260610/audit_preview.png

latest YOLO:
wrm_projects/05_validation_outputs/yolo_bigworld4k_batch05_20260610/data.yaml
```

审计结果：

```text
24 帧 RGB / sonar / YOLO label / meta / point cloud CSV / point cloud PLY 全部生成。
total_boxes = 177
classes = {3: 48, 4: 72, 5: 24, 6: 33}
boxes_per_frame min/avg/max = 6 / 7.38 / 9
point_cloud_classes = {-1: 106764, 3: 519, 4: 604, 5: 259, 6: 36}
class3 已扩成真实岩石小簇。
class4 已扩成金属管/箱/板残骸簇。
class5 已扩成可被声呐命中的沙丘/沙脊。
class6 已扩成多株植物簇。
Landscape_0 的 class_id=-1 是背景海底地形命中，不是目标漏标。
```

当前优先级已经从“能否导入 4K 地图”转为：

```text
把当前半真实 basic/StarterContent 组合目标继续替换成真实水下资产或 AIGC/扫描资产。
继续扩大采集路径、角度、距离和遮挡变化。
准备多目标检测训练脚本；当前 tiny baseline 只算脚本 smoke proof，不代表多目标检测效果。
```

一键复跑当前 60 帧 Batch01：

```bash
cd /home/wrm/holoocean
sh scripts/run_bigworld4k_batch01.sh
```

一键复验当前 4K 多类 smoke：

```bash
cd /home/wrm/holoocean
sh scripts/run_bigworld4k_multiclass_smoke.sh
```

## 2026-06-09 最新状态

今天从 Windows/Gaea 带回的压缩包已经解压进 Linux 项目：

```text
/home/wrm/桌面/WRM_Gaea_4K_ReturnToLinux_20260609.zip
```

回传包完成的是 Gaea 侧大世界地形生成，不是 UE 侧最终拼接：

```text
10km / 4x4 / 4096 总分辨率 height seed 已生成。
16 个基础 .r16 tile 已生成。
Gaea GUI 单块 Erosion2 验证已完成。
Gaea 4x4 / 16 tile CLI 批处理已完成。
每块 tile 有 Erosion2_Out / Flow / Wear / Deposits 四个 EXR。
Gaea CLI 结果：16 / 16 Success。
Linux 解压后验数：16 个 Erosion2_Out、64 个 Erosion2_*.exr、16 个基础 .r16。
```

关键新目录：

```text
wrm_projects/02_bigworld_terrain_generation/outputs/generated_terrain_4k_windows_20260609/
wrm_projects/03_gaea_heightfield_workflow/02_gaea_export_dropbox/gaea_4k_cli_batch_20260609/
wrm_projects/03_gaea_heightfield_workflow/03_ue_import_specs/
wrm_projects/05_validation_outputs/bigworld_readiness_20260609/readiness_report.md
RETURN_TO_LINUX_GAEA_4K_PACKAGE_CN.md
```

本批 4K 地图的 UE 手动导入步骤：

```text
wrm_projects/02_bigworld_terrain_generation/GAEA_4K_20260609_UE_IMPORT_STEPS_CN.md
```

当前大世界下一步：

```text
先 2x2，再 full 4x4。
只走 Level Streaming / 分块子关卡路线。
先确认 tile 边界对齐，再加水下环境和资产。
如果 UE Landscape 不能直接稳定导入 Gaea 的 Erosion2_Out.exr，就先把 Erosion2_Out.exr 转成 UE 可导入的 16-bit R16。
```

注意：以前的 `generated_terrain_4k` / `BigWorldLite` 是轻量验证版；现在 `generated_terrain_4k_windows_20260609` 和 `gaea_4k_cli_batch_20260609` 才是 Windows/Gaea 回传的新成果。

如果你是新开的对话，或者让另一个大模型接手，先复制这个文件给它：

```text
NEXT_CHAT_PROMPT_CN.md
wrm_projects/NEXT_CHAT_PROMPT_CN.md
```

其中 `wrm_projects/NEXT_CHAT_PROMPT_CN.md` 是当前路线最新的详细接力 Prompt。

项目结构说明在：

```text
PROJECT_STRUCTURE_CN.md
MANUAL_CN.md
wrm_projects/README_CN.md
wrm_projects/MANUAL_CN.md
```

先读这个入口，再决定下一步打开哪个文件。

## 当前目标

我们要跑通一条完整链路：

```text
Gaea/高度图地形 -> UE5/Holodeck 场景 -> LineTrace 扇形声呐 + RGB 同步采集 -> YOLO 标签/meta/3D 点云 -> HoloOcean package/scenario -> Python 自动运行
```

当前主线：

```text
工程师已确认：当前重点是 UE/HoloOcean 水下虚拟环境搭建、3D 模型导入、点云与多模态数据采集。
UE 侧大场景实现只选 Level Streaming / 分块子关卡，水下环境需要搭得更大；World Partition、Data Layer 暂时只作为概念了解。
Gaea 后续要尝试 8K/16K 高分辨率，并学习 Gaea + UE 大世界流程。
3D 模型生成要了解 AIGC、ComfyUI、Gaussian Splatting、混元 3D。
2D 声呐多帧分割 SAM2/Cutie/XMem、点云/3D 检测算法、agent 自动化是明确学习线，但不是当前工程闭环第一优先级。
```

今晚确认的现状：

```text
声呐完成度已经较高，采集链路已经基本闭合。
当前核心短板是：Gaea 分辨率不够、地图不够大、Level Streaming 分块大地图尚未做更大规模复验、水下 3D/AIGC 资产导入尚未验证。
后续算法暂时不急，等场景和数据质量上来再接。
```

不要从头重做声呐。当前主线是近几天基于 Word 文档工程化出来的 UE5 `SonarDatasetTools` / LineTrace 扇形声呐。旧的 HoloOcean 避开 Octree 声呐项目已归档，不再作为当前主线入口。

## 一键验证

```bash
cd /home/wrm/holoocean
scripts/validate_wrm_pipeline.sh
```

当前验证内容：

- UE5 声呐数据集是否完整。
- WRMAbyss HoloOcean package 是否能启动。
- UE5 LineTrace 插件源码导出是否存在。
- RGB、sonar、YOLO、meta、point cloud CSV/PLY 是否能同步生成。

验证输出会写到：

```text
wrm_projects/05_validation_outputs/pipeline_validation_latest
```

## 声呐入口

UE5 插件源码导出：

```text
wrm_projects/01_line_trace_sonar_plugin/SonarDatasetTools
```

UE5 项目内插件实际位置：

```text
/home/wrm/UEProjects/SonarCppTest/Plugins/SonarDatasetTools
```

## 大世界入口

推荐入口：

```text
wrm_projects/02_bigworld_terrain_generation/README_CN.md
wrm_projects/02_bigworld_terrain_generation/MANUAL_CN.md
wrm_projects/02_bigworld_terrain_generation/BIGWORLD_LITE_UE_IMPORT_STEPS_CN.md
```

轻量 tile 输出：

```text
wrm_projects/02_bigworld_terrain_generation/outputs/generated_terrain_4k
```

导入参数表：

```text
wrm_projects/02_bigworld_terrain_generation/outputs/ue_tile_import_steps_4k_lite.csv
```

注意：你的电脑加载多个 Landscape tile 时崩过。路线 B 当前已经通过 Gaea 1K/4x4 Static Mesh bridge 跑通 HoloOcean 采集；正式 Landscape/UDIM/VT 版本后续再补。

当前大世界状态：

```text
Content / BigWorldLite / Maps
16 个 Terrain_0_0 ... Terrain_3_3 子关卡已导入并保存
Main_World_10km_Lite 已加载 Env_Shared + Terrain_0_0/Terrain_1_0/Terrain_0_1/Terrain_1_1
BP_SonarEmitter + Class_0 Cube 已在大世界里采集通过
```

## 小识别入口

```bash
python3 -m wrm_pipeline train-tiny-sonar --data <dataset_dir> --out <run_out>
```

兼容旧入口仍可用：`scripts/train_line_trace_sonar_baseline.py`。它只是证明链路通了，不是最终网络。

当前 UE 数据集：

```text
/home/wrm/UEProjects/SonarCppTest/Saved/SonarDataset_Batch01
```

验证结果：

```text
frames = 21
boxes = 21
rgb frames = 21
status = OK
```

数据体检和 YOLO 整理输出现在放在：

```text
wrm_projects/05_validation_outputs/pipeline_validation_latest
```

## GitHub 整理入口

```text
GITHUB_PACKAGING_CHECKLIST_CN.md
```

新对话接班 Prompt：

```text
NEXT_CHAT_PROMPT_CN.md
```

项目结构说明：

```text
PROJECT_STRUCTURE_CN.md
```

发布时保留源码、脚本、README；不要直接上传 UE `Binaries/`、`Intermediate/`、大体积 `.r16` 和采集出来的大批量 `.png/.npy`。

## 路线 B 入口

```text
WRM_ROUTE_B_HOLOOCEAN_GAEA_PLAN_CN.md
```

路线 B 当前状态：

```text
SonarDatasetTools 已迁入 HoloOcean/Holodeck 工程
/home/wrm/holoocean/engine/Holodeck.uproject 已启用插件
HolodeckEditor 编译通过
岩石 StaticMeshActor_30 已补 sonar_target/class_3/material_rock，HoloOcean 复验点云 class_id=3
SonarDatasetTools 已支持 material_rock/material_metal/material_sand/material_plant 轻量声学反射倍率
Underwater 关卡已新增 class_4 metal、class_5 sand、class_6 plant 代表目标，HoloOcean 审计通过
```

## 下一步建议顺序

1. 继续导入/摆放更多水下 Static Mesh 资产。
2. 给新增资产加 `sonar_target`、`class_x` 和 `material_x`。
3. 用真实资产替代/补充当前 basic shape 代表目标，复验材料 tag 回波差异。
4. 重新打包并同步 WRMAbyss。
5. 运行 HoloOcean scenario 重新采集。
6. 审计 RGB、sonar、YOLO、meta、point cloud CSV/PLY，确认没有 `class_id=-1`。
7. 只推进 Level Streaming / 分块子关卡，把当前 4x4 tile 验证扩展到更大水下场景。
8. 准备高分辨率 Gaea 8K/16K，并按 Level Streaming 路线导入 UE/HoloOcean。
9. 学习 AIGC 3D 资产生成：ComfyUI、Gaussian Splatting、混元 3D，并验证导入 UE/HoloOcean。
10. 作为算法学习线，了解 SAM2/Cutie/XMem、点云/3D 检测，以及 agent 自动化。

## 我能做 / 你需要做

我能直接推进：

```text
改代码、脚本、JSON、README、prompt。
打包/同步/验证 WRMAbyss。
用 UE Python 操作已有地图和已有资产。
给已有资产加 sonar_target/class_x/material_x。
跑 HoloOcean 采集和审计报告。
设计 Level Streaming 分块验证流程。
```

需要你提供或手工确认：

```text
Gaea 8K/16K 导出环境和输出文件。
混元 3D / ComfyUI / Gaussian Splatting / 资产包得到的模型文件。
UE 编辑器里地形、材质、水体、资产外观和尺度的目视确认。
账号、授权、验证码、下载付费资源、破解软件等外部操作。
```
