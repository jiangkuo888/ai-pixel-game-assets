# 可执行合同

路径相对合同文件，输出由 CLI 指定且必须不存在。示例仅演示已配准 640px 源到 32px 道具，不是通用默认尺寸：

```json
{
  "version": 1,
  "project": {"tile_pixels": 32, "world_pixels_per_unit": 32, "display_scale": 3},
  "families": {
    "pickup": {
      "canvas": [32, 32], "alpha": "binary", "colors": "preserve",
      "bbox_size": {"min": [8, 8], "max": [26, 28]},
      "anchors": {"ground": [16, 29]}, "anchor_tolerance": 0.5
    }
  },
  "assets": [
    {"id": "potion", "family": "pickup", "source": "art/aligned/potion.png", "expected_source_size": [640, 640], "source_anchors": {"ground": [320, 580]}}
  ]
}
```

## 字段与坐标

- `canvas`：必需，最终逻辑宽高正整数；可矩形。`bbox_size` 可选，按 alpha>0 包围盒检查主体宽高的 `min`/`max`。不同用途单独配置。
- `alpha`：`binary` 默认，遇到半透明失败；`preserve` 为特效保留 alpha。family 可显式设置 `alpha_threshold: 128` 等 1..255 阈值，二值化被采样 alpha；preserve 不允许阈值。
- `colors`：`preserve` 默认；或 `palette` 并给 `palette: ["#112233", "#aabbcc"]`，按 RGB 欧氏最近色、不抖动映射。此简单算法不代替美术选色。`max_colors` 可选，来自项目合同，不从当前输出倒推。
- `source`：实际 PNG。`expected_source_size` 可选，建议记录实测值以防误替换。
- `source_rect`：asset 可选 `[left, top, right, bottom]` 整数、右下开区间，切出已测量图格；不自动紧裁。默认完整源。矩形比例必须与 canvas 一致，否则失败；不同宽高比先在制作阶段等比摆放到合适留白画布。
- `anchors`：family 的目标挂点。`source_anchors`：asset 在完整源画布的对应挂点。均为画布边缘连续坐标，首像素中心 `(0.5,0.5)`。映射为 `(sourcePoint - rectOrigin) * targetSize / rectSize`。`anchor_tolerance` 默认 0.5 目标像素。这里只核对提供的测量值，不自动识别脚底/人脸。
- `group`：asset 可选，分层/动画共同 ID。同组同 family、源矩形宽高和目标画布；矩形原点可不同以支持图集帧。已经配准的层应传完整画布，不能单独裁紧。
- `allow_empty`：family 默认 false，合法空帧或空遮罩可设 true。
- `preview_scale`：顶层 1..32 整数，默认 8，仅用于审阅。

id 只用字母数字、下划线、连字符且唯一。所有素材验证后才开始写输出。合同失败不输出；文件系统写入故障可能留下不完整目录，不能拿来发布。

输出 `<id>.png`、`previews/<id>@<n>x.png`、`manifest.json`，包含源/产物哈希、裁格、变换、颜色、alpha、bbox、锚点与待人工检查状态。其他元数据可扩展，但脚本不验证 project 的世界尺度语义、分层合成、拼缝、动画或引擎配置，需另外检查。

## 生图 brief

> 设计 [游戏/用途] 的 [素材]，参考 [批准样本]。最终 [W×H] 逻辑像素，主体 [尺寸/占格]，基线 [y]，接触点 [x,y]，安全留白 [范围]。相机/透视 [约定]、光照 [方向]、描边约 [n] 逻辑像素；与样本保持色块密度，最终尺寸保留 [关键符号]。干净阶梯边界、大色块，避免柔焦和平滑描边及依赖微纹理。按 [布局模板] 保留完整画布，不紧裁、不改变批准人物比例。背景 [透明或可分离纯色]，无文字、网格线或烘焙棋盘格。

模型输出不是精确网格保证。多尺寸采样比较需保持主体世界尺度；提高逻辑分辨率与在屏幕放大人物不是同一操作。
