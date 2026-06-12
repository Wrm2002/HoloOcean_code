# Gaea 16384 / 4x4 到 UE5 导入规格

## 核心参数

- 世界尺寸：10.0 km x 10.0 km
- 总分辨率：16384 x 16384
- tile 数量：4 x 4
- 单 tile 分辨率：4096 x 4096
- UE Scale X/Y：61.035156
- UE Scale Z：58.593750
- Landscape Z：-30000.000 cm

## 输出文件

- CSV：`gaea_16384_4x4_ue_import_specs.csv`
- JSON contract：`gaea_16384_4x4_contract.json`

## Gaea 导出要求

1. 高度图导出为 `Erosion2_Out_x0_y0.r16` 到 `Erosion2_Out_x3_y3.r16`。
2. 每块高度图必须是 16-bit raw / `.r16`，且单块分辨率与上面的参数一致。
3. mask 至少保留 `Deposits`、`Flow`、`Wear`，用于 UE 材质。
4. 颜色或综合贴图优先用 UDIM；如果只能导出 `x/y` 命名，再用重命名脚本处理。
5. 导入 UE 后如果上下颠倒，优先回 Gaea 修正 Flip Y；不要在多个环节反复翻转。

## UE 导入顺序

1. 先建 `Env_Shared`、`Terrain_0_0` 到 `Terrain_3_3`、`Main_World_10km`。
2. 每次只打开一个 `Terrain_x_y` 子关卡导入对应 `.r16`。
3. 第一轮只加载 `Terrain_0_0`、`Terrain_1_0`、`Terrain_0_1`、`Terrain_1_1` 做 2x2 检查。
4. 2x2 稳定后再加载完整 4x4。
5. 放入水下光照、雾、水体效果、岩石/水草/沉船/管线等资产。
6. 新增目标必须加 `sonar_target` 和一个 `class_x`；需要回波差异时再加 `material_x`。

## HoloOcean 采集验收

1. 打包进 WRMAbyss 后先跑短 tick smoke test。
2. 采一小批 RGB / sonar / YOLO / meta / point cloud。
3. 审计点云里 `actor_name` 是否正确，`class_id` 是否还有 `-1`。
4. 确认 AUV 路径带来距离和角度变化，再扩大采集。
