# GoBang AI 启动指南

## 目录
- [环境要求](#环境要求)
- [安装步骤](#安装步骤)
- [Ollama 安装与配置](#ollama-安装与配置)
- [下载 LLM 模型](#下载-llm-模型)
- [启动方式](#启动方式)
- [常见问题](#常见问题)

---

## 环境要求

### 系统要求
| 项目 | 最低要求 | 推荐配置 |
|------|----------|----------|
| 操作系统 | Windows 10/macOS 10.14/Ubuntu 18.04 | Windows 11/macOS 12/Ubuntu 22.04 |
| Python | 3.9+ | 3.10/3.11/3.12 |
| 内存 | 4GB RAM | 16GB+ RAM |
| 磁盘空间 | 500MB | 20GB+ (包含LLM模型) |

### GPU 支持（可选）
- **NVIDIA GPU**: CUDA 11.8+ (用于加速 Ollama)
- **Apple Silicon**: Metal 加速（自动启用）
- **AMD GPU**: ROCm 支持

---

## 安装步骤

### 1. 克隆或下载项目

```bash
# 如果使用 Git
git clone https://github.com/CodeOfMe/GoBang.git
cd GoBang

# 或者直接解压ZIP文件到目标目录
```

### 2. 创建虚拟环境（推荐）

```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate

# macOS/Linux:
source .venv/bin/activate
```

### 3. 安装 Python 依赖

```bash
# 安装所有依赖
pip install -r requirements.txt

# 或使用 pip 安装项目（包含所有依赖）
pip install -e .
```

### 4. 安装 Ollama

请参考 [Ollama 安装与配置](#ollama-安装与配置) 部分。

### 5. 下载 LLM 模型

请参考 [下载 LLM 模型](#下载-llm-模型) 部分。

---

## Ollama 安装与配置

### Windows 安装

1. 访问 [https://ollama.ai/download](https://ollama.ai/download)
2. 下载 Windows 版本安装包
3. 运行安装程序，按照提示完成安装
4. 安装完成后，Ollama 会在后台自动运行

### macOS 安装

```bash
# 使用 Homebrew 安装
brew install ollama

# 或下载安装包
# 访问 https://ollama.ai/download
```

### Linux 安装

```bash
# 终端安装
curl -fsSL https://ollama.ai/install.sh | sh
```

### 验证 Ollama 安装

```bash
# 检查 Ollama 版本
ollama --version

# 检查正在运行的模型
ollama list
```

### 启动/停止 Ollama 服务

```bash
# Ollama 默认在后台运行
# Windows: 通过系统托盘图标管理
# macOS/Linux: 通过 launchctl/ systemctl 管理

# 手动启动（如果需要）
ollama serve
```

---

## 下载 LLM 模型

本项目支持以下 5 个 GGUF 量化模型，请选择您需要的模型下载：

### 模型列表

| 模型名称 | 大小 | 量化 | 内存需求 | 描述 |
|----------|------|------|----------|------|
| Qwen3-4B-Instruct | ~2.5GB | Q4_K_M | 4GB+ | 阿里通义千问4B指令模型 |
| gemma-3-4b-it | ~2.5GB | Q4_K_M | 4GB+ | Google Gemma 3 指令模型 |
| Phi-4-mini-instruct | ~2.2GB | Q4_K_M | 4GB+ | 微软 Phi-4 迷你指令模型 |
| Ministral-3.3B-Instruct | ~2.0GB | Q4_K_M | 4GB+ | Mistral Ministral 3.3B 指令模型 |
| Llama-3.2-3B-Instruct | ~2.0GB | Q4_K_M | 4GB+ | Meta Llama 3.2 3B 指令模型 |

### 下载命令

```bash
# 下载 Qwen3-4B-Instruct (GGUF Q4_K_M 量化)
ollama pull qwen3-4b

# 下载 gemma-3-4b-it (GGUF Q4_K_M 量化)
ollama pull gemma3:4b

# 下载 Phi-4-mini-instruct (GGUF Q4_K_M 量化)
ollama pull phi4-mini

# 下载 Ministral-3.3B-Instruct (GGUF Q4_K_M 量化)
ollama pull ministral-3.3b

# 下载 Llama-3.2-3B-Instruct (GGUF Q4_K_M 量化)
ollama pull llama3.2:3b
```

### 批量下载

如果您想一次性下载所有模型，可以逐个运行上述命令，或使用以下脚本：

```bash
#!/bin/bash
# download_models.sh

echo "开始下载所有 LLM 模型..."
echo "这可能需要 10-30 分钟，取决于您的网络速度"

ollama pull qwen3-4b
ollama pull gemma3:4b
ollama pull phi4-mini
ollama pull ministral-3.3b
ollama pull llama3.2:3b

echo "所有模型下载完成！"
echo "使用 'ollama list' 查看已安装的模型"
```

### 查看已安装的模型

```bash
ollama list
```

预期输出示例：
```
NAME                    ID          SIZE      MODIFIED
qwen3-4b                abc123...   2.5GB     2 hours ago
gemma3:4b               def456...   2.5GB     3 hours ago
phi4-mini               ghi789...   2.2GB     1 hour ago
ministral-3.3b          jkl012...   2.0GB     4 hours ago
llama3.2:3b             mno345...   2.0GB     5 hours ago
```

---

## 启动方式

### 方式一：图形界面（GUI）

启动带 Web 功能的 GUI 界面：

```bash
gobang gui
# 或直接运行
gobang
```

启动独立 GUI（无 Web 功能）：

```bash
gobang gui --no-web
```

### 方式二：Web 服务器

启动 Web 服务器，支持浏览器访问：

```bash
gobang web --port 5000
# 默认地址: http://127.0.0.1:5000
```

### 方式三：命令行界面（CLI）

#### 创建新游戏

```bash
# 人人对战
gobang cli new

# AI vs 人类
gobang cli new -b ai -w human

# AI vs LLM
gobang cli new -b ai -w llm:qwen3-4b

# LLM vs LLM (不同模型对战)
gobang cli new -b llm:gemma3:4b -w llm:llama3.2:3b
```

#### 落子

```bash
# 落子到 H8 位置
gobang cli move H8
```

#### AI/LLM 自动落子

```bash
gobang cli auto
```

#### 查看棋盘

```bash
gobang cli show
```

#### AI 对战（自动完成多局）

```bash
# AI vs LLM 对战 10 局
gobang cli battle -b ai -w llm:qwen3-4b -g 10

# LLM vs LLM 对战
gobang cli battle -b llm:gemma3:4b -w llm:llama3.2:3b
```

#### 保存/加载游戏

```bash
# 保存游戏
gobang cli save game.json

# 加载游戏
gobang cli load game.json
```

### 方式四：Python API

```python
from gobang import Game, Stone, Position
from gobang.ai import MinimaxAI
from gobang.llm_player import create_llm_player, OllamaClient

# 创建游戏
game = Game(board_size=15)

# 落子
game.make_move(Position(7, 7))  # H8

# 使用 AI
ai = MinimaxAI(depth=3)
best_move = ai.get_best_move(game)

# 使用 LLM
client = OllamaClient(model="qwen3-4b")
llm_player = create_llm_player(client, Stone.WHITE)
llm_move = llm_player.get_move(game)
```

### 启动选项说明

| 选项 | 说明 |
|------|------|
| `-s, --size` | 棋盘大小（默认15） |
| `-r, --rules` | 规则模式：free_style/standard/renju |
| `-b, --black` | 黑方玩家：human/ai/llm:模型名 |
| `-w, --white` | 白方玩家：human/ai/llm:模型名 |
| `--depth` | AI 搜索深度（默认3） |

---

## 常见问题

### Q1: 启动时报错 "No module named 'gobang'"

**解决方法**：
```bash
# 重新安装项目
pip install -e .
```

### Q2: LLM 模型不响应或响应超时

**解决方法**：
1. 确保 Ollama 服务正在运行：
   ```bash
   ollama list  # 查看是否有模型
   ```
2. 检查模型是否正确安装
3. 如果内存不足，关闭其他应用程序
4. 使用更小的模型（如 1b 版本）

### Q3: GUI 界面无法启动

**解决方法**：
1. 确保 PySide6 已安装：
   ```bash
   pip install PySide6
   ```
2. 在 Windows 上可能需要安装 Visual C++ Redistributable

### Q4: Web 服务器无法访问

**解决方法**：
1. 检查端口是否被占用：
   ```bash
   # 使用其他端口
   gobang web --port 8080
   ```
2. 检查防火墙设置

### Q5: 如何查看可用模型？

```bash
# 查看本地 Ollama 模型
gobang models

# 或直接在 Ollama 中查看
ollama list
```

### Q6: 如何切换不同的 LLM 模型？

在游戏中指定模型名称：
```bash
# 使用 qwen3-4b
gobang cli new -b llm:qwen3-4b -w human

# 使用 llama3.2:3b
gobang cli new -b llm:llama3.2:3b -w human
```

---

## 获取帮助

- **项目主页**: https://github.com/CodeOfMe/GoBang
- **问题反馈**: https://github.com/CodeOfMe/GoBang/issues
- **Ollama 文档**: https://github.com/ollama/ollama

---

祝您玩得开心！
