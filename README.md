# AI Pixel Game Assets

将 AI 生成的高清图整理成像素密度、主体比例、分辨率与锚点一致的游戏素材。包含可被 AI 编程助手使用的 skill、确定性导出脚本、合同示例和测试。

A reusable agent skill and deterministic exporter for turning aligned AI-generated artwork into consistent game pixel assets. Define logical pixel density, subject scale, canvas, anchors and runtime rendering separately. Nearest-neighbor sampling alone does not make arbitrary illustrations good pixel art.

## 解决什么问题

| 问题 | 方法 |
| --- | --- |
| 图片宽高相同，但人物大小不同 | 按素材类别约定主体包围盒、基线、世界尺度与挂点，先配准再采样 |
| AI 图的像素颗粒粗细混杂 | 识别网格与色块密度，使用批准样本做视觉比较；必要时修复源设计 |
| 放进游戏后模糊 | nearest 采样，检查引擎过滤、Canvas backing store、DPR 和显示倍率 |
| 帧/换装层错位 | 共享画布、变换与锚点，保留透明留白 |
| 图集边缘串色 | 检查 padding、extrusion、UV、mipmap 与压缩 |

完整流程：**素材合同 → AI 生图 → 原尺寸抠图 → 配准 → 统一采样 → 自动检查 → 视觉与游戏内检查**。

不同类别可使用不同画布，支持矩形。大树无需缩成与小石头相同大小。“16-bit”是风格，不等于 16×16、16 色或 16 位 PNG。默认保留源 RGB；固定调色板与半透明特效由项目合同决定。

## 作为 Skill 使用

将本仓库复制或克隆为助手的技能目录中的 `ai-pixel-game-assets` 文件夹。Codex 默认用户目录示例：

```bash
git clone https://github.com/jiangkuo888/ai-pixel-game-assets.git ~/.codex/skills/ai-pixel-game-assets
```

Windows PowerShell：

```powershell
git clone https://github.com/jiangkuo888/ai-pixel-game-assets.git "$env:USERPROFILE/.codex/skills/ai-pixel-game-assets"
```

若目标文件夹已经存在，先检查现有内容，不直接覆盖。自定义技能目录应使用对应路径。

调用示例：

> 使用 $ai-pixel-game-assets，把这批 AI 高清图整理成比例、像素密度一致的游戏素材，检查锚点并验证游戏里的显示。

入口：[SKILL.md](SKILL.md)。生成新图需要助手环境提供图像生成工具；导出脚本本身不调用模型、不需要 API key。

## 独立运行导出脚本

依赖 Python 3.10+ 和 Pillow：

```bash
python -m pip install -r requirements.txt
python scripts/export_assets.py --help
python scripts/export_assets.py --spec /path/to/pixel-assets.json --out /path/to/new-output
```

先根据 [合同说明](references/contract.md) 编写 JSON。源路径相对 JSON 文件，输入为**已完成抠图和配准的 PNG**。脚本不会自动识别主体、抠图或纠正美术比例。输出目录必须不存在，避免覆盖批准资产。

输出包含：

- 逻辑分辨率 PNG 与整数放大预览。
- `manifest.json`：源/产物 SHA256、尺寸、裁格、变换、颜色、alpha、包围盒及锚点。
- 独立的自动检查、视觉检查和游戏内检查状态。脚本只将自动检查标为通过。

### 可运行示例

仓库不携带任何私人项目素材。以下脚本创建纯色几何测试夹具，用于演示管线，不代表 AI 生图质量：

```bash
python examples/make_fixture.py --out demo-input
python scripts/export_assets.py --spec demo-input/pixel-assets.json --out demo-output
python -m unittest discover -s scripts -p test_export_assets.py -v
```

`demo-output/potion.png` 为 32×32，放大预览位于 `demo-output/previews/`。示例为 640→32 的 20:1 采样，参数不是通用默认值。

## 范围与限制

脚本检查画布与等比采样、二值/保留 alpha、保留 RGB/共享 palette、包围盒、锚点、组内采样一致性及输出覆盖。分层合成、动画抖动、瓦片拼缝、实际物体尺度和游戏内显示仍需另外验证。

自动缩小不能保证轮廓可读、关键符号完整或视觉颗粒一致。参考 [运行时排查](references/runtime.md) 完成实际接入。没有可运行工程时，只能交付资源和导入建议，不能声称游戏内验收通过。

贡献时请提供最小合同、可公开的测试源及目标/实际结果。改动导出行为时补充可观察行为测试，勿提交私有原图、密钥或本地生成的 manifest。

## License

[MIT](LICENSE)。本许可覆盖仓库内的代码、文档与测试夹具，不授予用户输入的图片、模型输出或第三方游戏素材的权利。
