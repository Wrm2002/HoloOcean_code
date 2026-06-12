# PDF Gaea -> UE5 导入检查清单

来源：`/home/wrm/下载/大世界地形.pdf`

## 当前采用的版本

先走 PDF 最后“正确流程（成功）”对应的 8192 版：

```text
世界尺寸：10km x 10km
tile 数量：4 x 4 = 16
单块尺寸：2.5km x 2.5km
总分辨率：8192 x 8192
单块分辨率：2048 x 2048
UE Scale X：122.070312
UE Scale Y：122.070312
UE Scale Z：58.593750
```

PDF 前面还写过最终 16K 高精度版：

```text
总分辨率：16384 x 16384
单块分辨率：4096 x 4096
UE Scale X/Y：61.035156
UE Scale Z：58.593750
```

这台机器先不硬上 16K，等 8192/Gaea/HoloOcean 全流程稳定后再升级。

## 关键文件

Python 生成的种子高度图：

```text
/home/wrm/holoocean/wrm_projects/02_bigworld_terrain_generation/outputs/generated_terrain/r16
```

导入参数表：

```text
/home/wrm/holoocean/wrm_projects/02_bigworld_terrain_generation/outputs/generated_terrain/terrain_tiles_manifest.csv
```

收件箱里的副本：

```text
/home/wrm/holoocean/wrm_projects/03_gaea_heightfield_workflow/01_python_height_seed/terrain_tiles_manifest_8192_4x4.csv
```

## Gaea 导出要求

地形高度图：

```text
优先导出 Erosion2_Out
格式优先用 .r16 / 16-bit heightmap
保持 4x4 tile
保持 tile 顺序 x0_y0 到 x3_y3
```

贴图和 mask：

```text
开启或导出 UDIM 命名
例如 Combine_1001.png, Combine_1002.png
如果只能导出 _x0_y0，后续用 rename_gaea_tiles_to_udim.py 改名
```

Y 轴：

```text
如果导入 UE5 后上下颠倒，优先在 Gaea 导出时勾选 Flip Y / Invert Y
如果已经导出，则改名时反转 y 轴
```

## UDIM 改名命令

先预览：

```bash
cd /home/wrm/holoocean
.venv/bin/python wrm_projects/02_bigworld_terrain_generation/scripts/rename_gaea_tiles_to_udim.py \
  wrm_projects/03_gaea_heightfield_workflow/02_gaea_export_dropbox
```

确认无误后执行：

```bash
cd /home/wrm/holoocean
.venv/bin/python wrm_projects/02_bigworld_terrain_generation/scripts/rename_gaea_tiles_to_udim.py \
  wrm_projects/03_gaea_heightfield_workflow/02_gaea_export_dropbox \
  --no-dry-run
```

## UE5 项目设置

导入大量贴图前必须做：

```text
Edit -> Project Settings -> 搜索 Virtual Texture
勾选 Enable Virtual Texture Support
重启 UE5
```

## UE5 地形导入

每次只打开一个子关卡：

```text
Terrain_0_0
Terrain_0_1
...
Terrain_3_3
```

导入时填：

```text
Heightmap File：对应 Gaea 导出的 Erosion2_Out tile
Location：看 terrain_tiles_manifest.csv
Scale：8192 版 X/Y=122.070312，Z=58.593750
```

## HoloOcean 原则

不要让原版 Octree 声呐一次吞 10km 全世界。路线 B 当前使用：

```text
SonarDatasetTools LineTrace 声呐
```

这和公司现在的 ray/line-trace 声呐方向一致，也能避开旧 HoloOcean 静态 Octree 的世界分区冲突。
