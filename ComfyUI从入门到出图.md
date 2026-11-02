# ComfyUI 从入门到出图

> 2026-07-09 · 江楠的学习日志
>
> 从零装 ComfyUI portable、下底模、写工作流、Danbooru 提示词、HTTP API 批量出图、MCP 集成的完整笔记。基于 RTX 5070 (12GB) + Windows 11 实测。

---

## 一、ComfyUI 是什么

ComfyUI 是一个**节点式**的 Stable Diffusion / FLUX 前端。相对 SD WebUI（A1111）：

- 每一步（加载模型 → 编码提示词 → 采样 → 解码 → 保存）都是一个可视化节点，用连线组装
- 支持所有新模型 day-1（SD1.5、SDXL、Illustrious、FLUX、Video 模型）
- 生成的 PNG **自带工作流元数据**，把图拖回 UI 就能还原当时的所有参数
- 有完整 HTTP API 和 Python 库，方便脚本化 / 批量出图 / 集成到其他系统

## 二、环境搭建（Windows）

### 1. 下载 portable 版

官方地址：<https://github.com/comfyanonymous/ComfyUI/releases>

如果 GitHub 拉不动，用代理或者 Cloudflare WARP（`warp-cli.exe connect` 后能直连 GitHub 1.5-2 MB/s）。

下载 `ComfyUI_windows_portable_nvidia.7z`，解压到 `D:\ComfyUI\`（约 6GB，Python + PyTorch + CUDA 全打包）。

### 2. 启动

进入 `D:\ComfyUI\ComfyUI_windows_portable\`，根据显卡选启动脚本：

| 显卡 | 启动脚本 | 说明 |
|---|---|---|
| NVIDIA 通用 | `run_nvidia_gpu.bat` | 常规启动 |
| RTX 40/50 系 | `run_nvidia_gpu_fast_fp16_accumulation.bat` | 开 fp16 累加加速，~30% 提速 |
| 无独显 | `run_cpu.bat` | 极慢，仅测试用 |

启动后浏览器打开 `http://127.0.0.1:8188` 即是 UI。

### 3. VRAM 需求

| 模型档位 | 最低 VRAM | 推荐 VRAM |
|---|---|---|
| SD 1.5 | 4 GB | 6 GB |
| SDXL / Illustrious | 6 GB | 8-12 GB |
| FLUX.1 Schnell | 8 GB | 12 GB |
| FLUX.1 Dev | 12 GB | 24 GB |

## 三、核心工作流：文生图 7 节点

一个最小可用的文生图工作流由 7 个节点组成：

```
CheckpointLoaderSimple  ←── 加载底模，输出 MODEL/CLIP/VAE
        ├──► CLIPTextEncode (正面提示词)  ─┐
        ├──► CLIPTextEncode (负面提示词)  ─┤
        │                                  ├──► KSampler ──► VAEDecode ──► SaveImage
        └──► VAE ─────────────────────────►┤        ↑
                                            │        │
                                  EmptyLatentImage (宽×高)
```

### 节点作用

| # | 节点 | 输入 → 输出 | 关键参数 |
|---|---|---|---|
| 1 | `CheckpointLoaderSimple` | ckpt 文件 → MODEL / CLIP / VAE | 选底模 |
| 2 | `CLIPTextEncode` (正) | CLIP + 文本 → CONDITIONING | 正面提示词 |
| 3 | `CLIPTextEncode` (负) | CLIP + 文本 → CONDITIONING | 负面提示词 |
| 4 | `EmptyLatentImage` | 空 → LATENT | 分辨率、batch |
| 5 | `KSampler` | MODEL + 正/负 + LATENT → LATENT | seed / steps / cfg / sampler / scheduler |
| 6 | `VAEDecode` | LATENT + VAE → IMAGE | 潜空间 → RGB |
| 7 | `SaveImage` | IMAGE → PNG | 文件名前缀 |

## 四、底模选择

| 底模 | 大小 | 出图速度 (RTX 5070) | 二次元质量 | 用途 |
|---|---|---|---|---|
| SD 1.5 | 2 GB | 2 秒 | ★★ | 已过时，仅存档 |
| SDXL Base | 6.5 GB | 8-15 秒 | ★★★ | 通用 |
| **Illustrious XL v2.0** | 6.5 GB | 7-10 秒 | ★★★★★ | **二次元首选**，识别 Danbooru 角色 |
| NoobAI-XL | 6.5 GB | 7-10 秒 | ★★★★★ | Illustrious 分支，NSFW 友好 |
| Pony Diffusion V6 | 6.5 GB | 8-15 秒 | ★★★★ | `score_9` 系标签体系 |
| FLUX.1 Dev fp8 | 12 GB | 25-40 秒 | ★★★★ | 写实向、复杂场景 |
| FLUX.1 Schnell fp8 | 12 GB | 4-8 秒 | ★★★★ | 4 步出图，极速 |

### 底模下载（走 hf-mirror 国内镜像）

```powershell
cd D:\ComfyUI\ComfyUI_windows_portable\ComfyUI\models\checkpoints

# Illustrious XL v2.0（二次元首选，6.5GB）
curl -L -C - -o Illustrious-XL-v2.0.safetensors `
  "https://hf-mirror.com/OnomaAIResearch/Illustrious-XL-v2.0/resolve/main/Illustrious-XL-v2.0.safetensors"

# FLUX.1 Dev fp8（一体化 checkpoint，12GB）
curl -L -C - -o flux1-dev-fp8.safetensors `
  "https://hf-mirror.com/Comfy-Org/flux1-dev/resolve/main/flux1-dev-fp8.safetensors"
```

**加速三件套**：
- `hf-mirror.com` 替代 `huggingface.co`
- `curl -L -C -`：`-L` 跟随重定向，`-C -` 断点续传（大文件必备）
- Cloudflare WARP 连着，直连 GitHub 也能跑到 1.5 MB/s

## 五、提示词（Prompt）写法

Illustrious、Pony、NoobAI 系全部认 **Danbooru 标签**，语法：`snake_case`、逗号分隔、按重要度排序。

### 正面提示词模板

```
masterpiece, best quality, amazing quality, very aesthetic, absurdres,
1girl, solo,
chihaya_anon, bang_dream, mygo,
pink_hair, short_hair, side_ponytail, blue_eyes,
casual_clothes, hoodie,
holding_electric_guitar, guitar,
stage, spotlight, neon_lights, purple_theme,
dynamic_pose, looking_at_viewer, cowboy_shot, cinematic_lighting
```

### 顺序规则

1. **质量前缀** → `masterpiece, best quality, amazing quality, absurdres,`
2. **人数** → `1girl, solo` 或 `2girls, multiple_girls`
3. **角色 / IP** → `chihaya_anon, bang_dream, mygo`
4. **外貌** → 发色、发型、瞳色
5. **服装** → 上衣、下装、鞋
6. **动作 / 道具** → `holding_electric_guitar, sitting, waving`
7. **场景 / 背景** → `stage, sunset, indoors`
8. **构图 / 视角** → `cowboy_shot, close-up, wide_shot`
9. **光线** → `cinematic_lighting, backlight, spotlight`

### 负面提示词模板（通用）

```
worst quality, low quality, bad quality, normal quality, lowres,
bad anatomy, bad hands, bad fingers, extra fingers, missing fingers,
bad proportions, deformed, disfigured, mutated,
watermark, signature, text, error, jpeg artifacts,
blurry, out of focus, multiple views, cropped
```

### 权重语法

- `(tag:1.2)` — 权重放大 1.2 倍（1.0~1.3 之间为佳，超 1.5 容易崩）
- `[tag]` — 权重减到 ~0.9
- 组合：`(masterpiece:1.1), (pink_hair:1.2), 1girl`

## 六、采样参数（不同模型不一样）

| 底模 | Sampler | Scheduler | Steps | CFG | 推荐分辨率 |
|---|---|---|---|---|---|
| **Illustrious XL** | `euler_ancestral` 或 `dpmpp_2m` | `karras` | 28-30 | 5-7 | 832×1216（竖）/ 1216×832（横） |
| SDXL 常规 | `dpmpp_2m_sde` | `karras` | 25-30 | 6-8 | 1024×1024 |
| FLUX Dev | `euler` | `simple` | 20-24 | **1.0** ⚠️ | 1024×1024 |
| FLUX Schnell | `euler` | `simple` | **4** | **1.0** ⚠️ | 1024×1024 |

**关键坑**：FLUX 系列 CFG 一定要 1.0，写 7 会烧图。

## 七、HTTP API 批量出图

ComfyUI 内置 HTTP API，`POST /prompt` 提交工作流 JSON 就能触发一次出图。

### API 端点

| 端点 | 方法 | 作用 |
|---|---|---|
| `/prompt` | POST | 提交工作流，返回 `prompt_id` |
| `/history/{prompt_id}` | GET | 查询状态、拿输出文件名 |
| `/view?filename=...&subfolder=...&type=...` | GET | 下载已生成的图 |
| `/system_stats` | GET | 查询服务器状态、VRAM |

### 出图流程

```
POST /prompt (workflow JSON)
    │
    ▼
拿到 prompt_id
    │
    ▼
GET /history/{prompt_id} 轮询直到 status.completed == True
    │
    ▼
从 outputs 里拿 filename，GET /view 下载图
```

### Python 模板脚本

```python
import json, time, uuid, urllib.request, urllib.parse
from pathlib import Path

SERVER = "127.0.0.1:8188"
CLIENT_ID = str(uuid.uuid4())
OUT = Path(r"D:\ComfyUI_setup\outputs")
OUT.mkdir(parents=True, exist_ok=True)

WORKFLOW = {
    "3": {"inputs": {"seed": 0, "steps": 30, "cfg": 6.0,
                     "sampler_name": "euler_ancestral", "scheduler": "karras", "denoise": 1.0,
                     "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0],
                     "latent_image": ["5", 0]},
          "class_type": "KSampler"},
    "4": {"inputs": {"ckpt_name": "Illustrious-XL-v2.0.safetensors"},
          "class_type": "CheckpointLoaderSimple"},
    "5": {"inputs": {"width": 832, "height": 1216, "batch_size": 1},
          "class_type": "EmptyLatentImage"},
    "6": {"inputs": {"text": "", "clip": ["4", 1]}, "class_type": "CLIPTextEncode"},
    "7": {"inputs": {"text": "worst quality, ...", "clip": ["4", 1]},
          "class_type": "CLIPTextEncode"},
    "8": {"inputs": {"samples": ["3", 0], "vae": ["4", 2]}, "class_type": "VAEDecode"},
    "9": {"inputs": {"filename_prefix": "gen", "images": ["8", 0]},
          "class_type": "SaveImage"},
}

def queue(wf):
    body = json.dumps({"prompt": wf, "client_id": CLIENT_ID}).encode()
    req = urllib.request.Request(f"http://{SERVER}/prompt",
                                  data=body,
                                  headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())["prompt_id"]

def wait(pid):
    while True:
        h = json.loads(urllib.request.urlopen(f"http://{SERVER}/history/{pid}").read())
        e = h.get(pid)
        if e and e.get("status", {}).get("completed"):
            return e["outputs"]
        time.sleep(1)

wf = json.loads(json.dumps(WORKFLOW))
wf["6"]["inputs"]["text"] = "masterpiece, best quality, 1girl, chihaya_anon, ..."
pid = queue(wf)
outputs = wait(pid)
for _, out in outputs.items():
    for img in out.get("images", []):
        q = urllib.parse.urlencode({"filename": img["filename"],
                                     "subfolder": img["subfolder"],
                                     "type": img["type"]})
        data = urllib.request.urlopen(f"http://{SERVER}/view?{q}").read()
        (OUT / img["filename"]).write_bytes(data)
```

## 八、MCP 集成（让 AI 直接驱动 ComfyUI）

`comfyui-mcp` (`artokun/comfyui-mcp`) 是一个把 ComfyUI 封装成 MCP server 的 npm 包，装完后 Claude / ChatGPT / 本地 Ollama 都能用自然语言指挥 ComfyUI 出图。

### 配置

在 Claude Code 的项目根目录（比如 `C:\Users\jiangnan`）建 `.mcp.json`：

```json
{
  "mcpServers": {
    "comfyui": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "comfyui-mcp"],
      "env": {
        "CIVITAI_API_TOKEN": "",
        "COMFYUI_PATH": "D:\\ComfyUI\\ComfyUI_windows_portable\\ComfyUI"
      }
    }
  }
}
```

**生效方式**：重启 Claude Code + 弹窗信任 → 工具 `generate_image` / `create_workflow` / `enqueue_workflow` / `view_image` 就会出现。

### 自测

```powershell
timeout 8 npx -y comfyui-mcp
# → [comfyui-mcp] Found ComfyUI on port 8188
# → ComfyUI MCP server running on stdio
```

## 九、必装节点扩展

在 `ComfyUI/custom_nodes/` 目录下 git clone：

```powershell
cd D:\ComfyUI\ComfyUI_windows_portable\ComfyUI\custom_nodes

# 节点管理器（必装）
git clone https://github.com/ltdrdata/ComfyUI-Manager

# 标签自动补全（Danbooru 标签联想）
git clone https://github.com/Comfy-Org/ComfyUI-Autocomplete-Plus

# 节点整理、Reroute 美化
git clone https://github.com/rgthree/rgthree-comfy

# 中文汉化
git clone https://github.com/AIGODLIKE/AIGODLIKE-ComfyUI-Translation
```

装完重启 ComfyUI，Manager 装完后所有其他插件、模型都能在 UI 里点鼠标搞定。

## 十、效果对比：SD 1.5 vs Illustrious XL

同样的角色 prompt（千早爱音 / MyGO），实测差距：

| 项目 | SD 1.5 | Illustrious XL |
|---|---|---|
| 单张体积 | ~600 KB | 1.0~1.3 MB |
| 分辨率 | 512×768 | 832×1216 |
| 单张耗时 | 2 秒 | 7-9 秒 |
| 角色识别 | 不认（画个粉发女孩） | 认（画对爱音的马尾+瞳色） |
| 脸崩率 | 高 | 极低 |
| 手崩率 | 极高 | 低 |
| 光影质感 | 平淡 | 电影感 |

## 十一、常见坑与排错

| 症状 | 原因 | 解决 |
|---|---|---|
| 启动黑屏 / VRAM 溢出 | 底模太大 | 用 fp8 版本，或加 `--lowvram` |
| 图全糊 | prompt 写得像人类语言 | 换成逗号分隔的 Danbooru 标签 |
| 手指全崩 | 底模不认手 | 加负面 `bad hands, extra fingers`，或换 Illustrious/SDXL |
| FLUX 图烧成一片白 | CFG 不是 1 | 改回 `cfg=1.0` |
| 换模型后 UI 里不显示 | 节点缓存 | 页面刷新，或重启 ComfyUI |
| 中文 prompt 效果差 | 底模是英文训练 | 用英文 Danbooru 标签，或装翻译节点 |
| 下 HF 超时 | 直连被墙 | 换 hf-mirror.com |
| GitHub 拉不动 | 直连慢 | Cloudflare WARP `warp-cli.exe connect` |

## 十二、进阶方向

- **LoRA** — 小模型（几十~几百 MB）叠加在底模上，微调画风 / 角色 / 姿势。Civitai 上一堆二次元 LoRA
- **ControlNet** — 用姿势图 / 线稿 / 深度图控制构图
- **Regional Prompt** — 一张图分区域用不同 prompt（左边一个角色右边一个）
- **Hires Fix / Upscale** — 先出 832×1216 再放大到 1664×2432
- **ADetailer / FaceDetailer** — 自动检测脸部 → 局部重绘 → 提升脸的清晰度
- **Video / AnimateDiff** — 出动图 / 视频
- **FLUX Kontext** — FLUX 的图生图（局部改、换服装、换背景）

## 十三、参考资料

1. [ComfyUI 官方仓库](https://github.com/comfyanonymous/ComfyUI)
2. [官方 FLUX 示例工作流](https://comfyanonymous.github.io/ComfyUI_examples/flux/)
3. [ComfyUI Wiki（英文）](https://comfyui-wiki.com/)
4. [Illustrious XL Beginners Guide](https://techtactician.com/illustrious-xl-comfyui-sdxl-anime-guide-for-beginners/)
5. [Booru-Style Tagging Guide](https://techtactician.com/booru-style-tagging-sdxl-anime-prompts-guide/)
6. [ComfyUI 中文入门（小慧博客）](https://www.itxiaohui.top/archives/n37AGLmW)
7. [2026 最全面 ComfyUI 教程 (Bilibili)](https://www.bilibili.com/video/BV197jc6qEDA/)
8. [Civitai Illustrious 模型库](https://civitai.com/models?baseModel=Illustrious)

---

> 本笔记基于 2026-07-09 的实测：ComfyUI v0.27.0 + Illustrious XL v2.0 + RTX 5070 (12GB)。
