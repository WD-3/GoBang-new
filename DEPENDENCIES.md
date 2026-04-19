# GoBang AI 依赖项文档

## 目录
- [Python 依赖](#python-依赖)
- [系统依赖](#系统依赖)
- [LLM 模型依赖](#llm-模型依赖)
- [GPU 支持](#gpu-支持)
- [完整安装命令](#完整安装命令)

---

## Python 依赖

### 核心依赖

| 包名 | 版本要求 | 用途 |
|------|----------|------|
| PySide6 | >=6.5.0 | 图形用户界面 (GUI) |
| Flask | >=3.0.0 | Web 服务器和 REST API |
| Flask-SocketIO | >=5.3.0 | WebSocket 实时通信 |
| requests | >=2.31.0 | HTTP 请求（用于 Ollama API） |
| openai | >=1.0.0 | OpenAI 兼容 API 客户端 |
| numpy | >=1.24.0 | 高效数组运算 |

### 开发依赖（可选）

| 包名 | 版本要求 | 用途 |
|------|----------|------|
| pytest | >=7.0.0 | 单元测试框架 |
| pytest-cov | >=4.0.0 | 测试覆盖率 |
| black | >=23.0.0 | 代码格式化 |
| ruff | >=0.1.0 | 代码 linting |

### requirements.txt 内容

```
PySide6>=6.5.0
Flask>=3.0.0
Flask-SocketIO>=5.3.0
requests>=2.31.0
openai>=1.0.0
numpy>=1.24.0

# Development dependencies
pytest>=7.0.0
pytest-cov>=4.0.0
black>=23.0.0
ruff>=0.1.0
```

### 安装 Python 依赖

```bash
# 安装所有核心依赖
pip install -r requirements.txt

# 安装包含开发依赖
pip install -e ".[dev]"
```

---

## 系统依赖

### Windows

1. **Python 3.9+**
   - 下载地址: https://www.python.org/downloads/
   - 安装时勾选 "Add Python to PATH"

2. **Visual C++ Redistributable**（用于 PySide6）
   - 通常随 Python 一起安装
   - 如需单独安装: https://aka.ms/vs/17/release/vc_redist.x64.exe

### macOS

1. **Python 3.9+**
   ```bash
   # 使用 Homebrew 安装
   brew install python@3.11
   ```

2. **Xcode Command Line Tools**
   ```bash
   xcode-select --install
   ```

### Linux (Ubuntu/Debian)

```bash
# 安装 Python 和相关工具
sudo apt update
sudo apt install python3.11 python3-pip python3-venv

# 安装 Qt 依赖（用于 PySide6）
sudo apt install libxcb-xinerama0 libxcb-cursor0 libxkbcommon-x11-0 libegl1 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0
```

---

## LLM 模型依赖

本项目使用 Ollama 作为本地 LLM 推理引擎。

### Ollama 安装

| 操作系统 | 安装方式 |
|----------|----------|
| Windows | 下载安装包: https://ollama.ai/download/windows |
| macOS | `brew install ollama` 或下载安装包 |
| Linux | `curl -fsSL https://ollama.ai/install.sh \| sh` |

### 支持的 GGUF 量化模型

本项目测试并推荐以下 5 个 Q4_K_M 量化模型：

#### 1. Qwen3-4B-Instruct

| 属性 | 值 |
|------|-----|
| 模型名称 | `qwen3-4b` |
| 完整名称 | Qwen3-4B-Instruct-2507-GGUF:Q4_K_M |
| 量化方式 | Q4_K_M |
| 文件大小 | ~2.5 GB |
| 最小内存 | 4 GB RAM |
| 下载命令 | `ollama pull qwen3-4b` |
| 来源 | Hugging Face (TheBloke/Qwen3-4B-Instruct-GGUF) |
| 特点 | 阿里通义千问最新4B指令模型，支持中文 |

#### 2. gemma-3-4b-it

| 属性 | 值 |
|------|-----|
| 模型名称 | `gemma3:4b` |
| 完整名称 | gemma-3-4b-it-GGUF:Q4_K_M |
| 量化方式 | Q4_K_M |
| 文件大小 | ~2.5 GB |
| 最小内存 | 4 GB RAM |
| 下载命令 | `ollama pull gemma3:4b` |
| 来源 | Hugging Face (bartowski/gemma-3-4b-it-GGUF) |
| 特点 | Google Gemma 3 指令模型 |

#### 3. Phi-4-mini-instruct

| 属性 | 值 |
|------|-----|
| 模型名称 | `phi4-mini` |
| 完整名称 | Phi-4-mini-instruct-GGUF:Q4_K_M |
| 量化方式 | Q4_K_M |
| 文件大小 | ~2.2 GB |
| 最小内存 | 4 GB RAM |
| 下载命令 | `ollama pull phi4-mini` |
| 来源 | Hugging Face (TheBloke/Phi-4-mini-instruct-GGUF) |
| 特点 | 微软 Phi-4 迷你指令模型 |

#### 4. Ministral-3.3B-Instruct

| 属性 | 值 |
|------|-----|
| 模型名称 | `ministral-3.3b` |
| 完整名称 | Ministral-3.3B-Instruct-2512-GGUF:Q4_K_M |
| 量化方式 | Q4_K_M |
| 文件大小 | ~2.0 GB |
| 最小内存 | 4 GB RAM |
| 下载命令 | `ollama pull ministral-3.3b` |
| 来源 | Hugging Face (mistralai/Ministral-3.3B-Instruct-GGUF) |
| 特点 | Mistral Ministral 3.3B 指令模型 |

#### 5. Llama-3.2-3B-Instruct

| 属性 | 值 |
|------|-----|
| 模型名称 | `llama3.2:3b` |
| 完整名称 | Llama-3.2-3B-Instruct-GGUF:Q4_K_M |
| 量化方式 | Q4_K_M |
| 文件大小 | ~2.0 GB |
| 最小内存 | 4 GB RAM |
| 下载命令 | `ollama pull llama3.2:3b` |
| 来源 | Hugging Face (TheBloke/Llama-3.2-3B-Instruct-GGUF) |
| 特点 | Meta Llama 3.2 3B 指令模型 |

### 模型下载汇总

```bash
# 逐个下载
ollama pull qwen3-4b
ollama pull gemma3:4b
ollama pull phi4-mini
ollama pull ministral-3.3b
ollama pull llama3.2:3b
```

### 模型规格对比

| 模型 | 参数量 | Q4_K_M 大小 | 推荐内存 |
|------|--------|-------------|----------|
| Qwen3-4B | 4B | ~2.5 GB | 6 GB |
| gemma-3-4b | 4B | ~2.5 GB | 6 GB |
| Phi-4-mini | 3.8B | ~2.2 GB | 5 GB |
| Ministral-3.3B | 3.3B | ~2.0 GB | 4 GB |
| Llama-3.2-3B | 3B | ~2.0 GB | 4 GB |

---

## GPU 支持

### NVIDIA GPU (CUDA)

Ollama 自动支持 NVIDIA GPU 加速。

**要求**：
- NVIDIA GPU（至少 4GB VRAM）
- CUDA 11.8+
- NVIDIA 驱动程序

**验证 GPU 加速**：
```bash
# 查看 GPU 状态
nvidia-smi

# 测试 Ollama GPU 使用
ollama run llama3.2:3b "Hello"
```

### Apple Silicon (Metal)

macOS 上的 Apple Silicon (M1/M2/M3/M4) 自动启用 Metal 加速。

### AMD GPU (ROCm)

Linux 上的 AMD GPU 支持：
```bash
# 设置 ROCm
export HSA_OVERRIDE_GFX_VERSION=10.3.0
ollama serve
```

### 内存不足时的建议

1. **使用更小的模型**：
   - `qwen3-1b` / `gemma3:1b` / `llama3.2:1b` (约 1GB)

2. **降低并发**：
   - 避免同时运行多个 LLM 模型

3. **增加交换空间**（Linux/macOS）：
   ```bash
   # macOS
   sudo launchctl load -w /System/Library/LaunchDaemons/com.apple.dynamic_pager.plist
   
   # Linux
   sudo fallocate -l 8G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

---

## 完整安装命令

### Windows 完整安装流程

```powershell
# 1. 克隆项目
git clone https://github.com/CodeOfMe/GoBang.git
cd GoBang

# 2. 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 3. 安装 Python 依赖
pip install -r requirements.txt

# 4. 安装 Ollama（从 https://ollama.ai/download/windows 下载安装包）

# 5. 下载 LLM 模型
ollama pull qwen3-4b
ollama pull gemma3:4b
ollama pull phi4-mini
ollama pull ministral-3.3b
ollama pull llama3.2:3b

# 6. 启动程序
gobang
```

### macOS 完整安装流程

```bash
# 1. 克隆项目
git clone https://github.com/CodeOfMe/GoBang.git
cd GoBang

# 2. 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 3. 安装 Python 依赖
pip install -r requirements.txt

# 4. 安装 Ollama
brew install ollama

# 5. 启动 Ollama 服务
ollama serve

# 6. 下载 LLM 模型（在另一个终端）
ollama pull qwen3-4b
ollama pull gemma3:4b
ollama pull phi4-mini
ollama pull ministral-3.3b
ollama pull llama3.2:3b

# 7. 启动程序
gobang
```

### Linux 完整安装流程

```bash
# 1. 安装系统依赖
sudo apt update
sudo apt install python3.11 python3-pip python3-venv libxcb-xinerama0

# 2. 克隆项目
git clone https://github.com/CodeOfMe/GoBang.git
cd GoBang

# 3. 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 4. 安装 Python 依赖
pip install -r requirements.txt

# 5. 安装 Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# 6. 启动 Ollama 服务
ollama serve

# 7. 下载 LLM 模型（在另一个终端）
ollama pull qwen3-4b
ollama pull gemma3:4b
ollama pull phi4-mini
ollama pull ministral-3.3b
ollama pull llama3.2:3b

# 8. 启动程序
gobang
```

---

## 依赖版本检查

验证所有依赖是否正确安装：

```bash
# Python 版本
python --version  # 应该 >= 3.9

# 核心包
python -c "import PySide6; print('PySide6:', PySide6.__version__)"
python -c "import flask; print('Flask:', flask.__version__)"
python -c "import numpy; print('NumPy:', numpy.__version__)"
python -c "import requests; print('Requests:', requests.__version__)"

# Ollama
ollama --version
ollama list  # 查看已安装模型
```

---

## 故障排除

### 依赖冲突

如果遇到依赖冲突：
```bash
# 使用 pip-tools 生成锁定文件
pip-compile requirements.in
pip-sync requirements.txt
```

### 重新安装所有依赖

```bash
# 删除虚拟环境
rm -rf .venv

# 重新创建
python -m venv .venv
source .venv/bin/activate

# 重新安装
pip install -e .
```

---

## 下一步

安装完成后，请参考 [README_启动指南.md](README_启动指南.md) 了解如何启动和使用程序。

祝您使用愉快！
