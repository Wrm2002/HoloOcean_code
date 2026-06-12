# WRM Python/Shell 工具脚本

这个目录保存仓库级工具，不属于某一个 UE 子项目。

## 脚本说明

```text
validate_wrm_pipeline.sh
  检查当前主线关键文件是否存在，并验证轻量地形。

validate_route_b_package_skeleton.py
  检查 WRMAbyss package/scenario 骨架。

validate_bigworld_readiness.py
  离线检查 Gaea 4x4 tile 导入 CSV、.r16 文件、UE 坐标/缩放、WRMAbyss worlds/scenario 对齐，并输出大场景下一步验收报告。

build_gaea_highres_import_specs.py
  生成 Gaea 8192/16384 高分辨率 4x4 tile 的 UE 导入 CSV、JSON contract 和中文导入清单；只生成规格，不生成大体积高度图。

generate_ocean_terrain_tiles_stdlib.py
  不依赖 numpy/matplotlib，只用 Python 标准库生成 10km / 4x4 `.r16` 海底大地图、PGM 预览和 UE manifest。Windows 上缺科学计算包时优先用它。

validate_big_world_tiles_stdlib.py
  不依赖 numpy，验证标准库生成的大地图 tile 数量、尺寸、高度范围、边界连续性和 UE scale。

validate_holoocean_scenarios.py
  实际启动 WRMAbyss 的所有 HoloOcean scenario 并 tick 几帧。

package_route_b_wrmabyss.sh
  调用 Unreal AutomationTool 重新打包 WRMAbyss。

audit_sonar_dataset.py
  审计 SonarDatasetTools 输出的数据集，包括 RGB、sonar、YOLO、meta、point cloud CSV/PLY。

prepare_sonar_yolo_dataset.py
  把采集结果整理成 YOLO 图像数据集。

train_line_trace_sonar_baseline.py
  早期小识别基线，当前不是主线重点。
```

## 当前推荐先跑

```powershell
python scripts\validate_bigworld_readiness.py
python scripts\build_gaea_highres_import_specs.py
python scripts\generate_ocean_terrain_tiles_stdlib.py --total-resolution 4096 --out wrm_projects\02_bigworld_terrain_generation\outputs\generated_terrain_4k_windows_YYYYMMDD
python scripts\validate_big_world_tiles_stdlib.py --tiles-dir wrm_projects\02_bigworld_terrain_generation\outputs\generated_terrain_4k_windows_YYYYMMDD
python scripts\validate_route_b_package_skeleton.py
```

`build_gaea_highres_import_specs.py` 默认输出位置：

```text
wrm_projects/03_gaea_heightfield_workflow/03_ue_import_specs/
```

`validate_bigworld_readiness.py` 默认报告位置：

```text
wrm_projects/05_validation_outputs/bigworld_readiness_YYYYMMDD/readiness_report.md
```

如果只看到 `no ViewportCapture sensor` 之类 warning，说明 package/scenario 骨架和 4x4 tile 文件本身可继续推进；回到 UE 后仍要目视确认地形拼接、水下效果、目标资产尺度和点云 `class_id`。

## Windows Python 注意

这台机器的裸 Python 在长循环读写 `.r16` 时偶发 `access violation`。如果标准库地形生成/验证脚本无输出退出，先这样跑：

```powershell
$env:PYTHONMALLOC='debug'
python scripts\generate_ocean_terrain_tiles_stdlib.py --total-resolution 4096 --out wrm_projects\02_bigworld_terrain_generation\outputs\generated_terrain_4k_windows_YYYYMMDD
python scripts\validate_big_world_tiles_stdlib.py --tiles-dir wrm_projects\02_bigworld_terrain_generation\outputs\generated_terrain_4k_windows_YYYYMMDD
```

## Gaea CLI 注意

Gaea 2 的无头构建入口是：

```powershell
& 'C:\Program Files\QuadSpinner\Gaea 2\Gaea.Swarm.exe' --help
```

不要继续把 `Gaea.BuildManager.exe` 当主入口；当前安装里它会报缺 `Gaea.BuildManager.dll`。

截至 2026-06-09，`Gaea.Swarm.exe` 已确认能启动、验证 license、扫描设备并打开 `.terrain`，但 WRM 旧的单 File 节点工程会触发 `System.IO.IOException: 句柄无效。`。详见：

```text
wrm_projects/05_validation_outputs/gaea_cli_probe_20260609/gaea_cli_probe_report.md
```

下一步应从 Gaea GUI 的 Build 窗口使用 Copy Command Line 取官方生成命令，再回填到脚本自动化里。
