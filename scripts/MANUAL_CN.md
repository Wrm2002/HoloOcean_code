# WRM 工具脚本阅读手册

## 常用顺序

先验证文件：

```bash
scripts/validate_wrm_pipeline.sh
```

再验证 package：

```bash
.venv/bin/python scripts/validate_route_b_package_skeleton.py
```

实际启动所有 WRMAbyss scenario：

```bash
.venv/bin/python scripts/validate_holoocean_scenarios.py
```

注意：带 `ViewportCapture` 的 scenario 会使用 JSON 里的原生窗口尺寸，不要手动用低分辨率覆盖，否则 HoloOcean 共享内存尺寸可能不匹配。

采集出数据后审计：

```bash
.venv/bin/python scripts/audit_sonar_dataset.py /path/to/SonarDataset
```

需要训练格式时整理为 YOLO：

```bash
.venv/bin/python scripts/prepare_sonar_yolo_dataset.py /path/to/SonarDataset /path/to/yolo_out
```

## 修改注意

脚本默认路径已经按 `wrm_projects` 新结构更新。移动项目目录后，需要同步更新这些默认路径。
