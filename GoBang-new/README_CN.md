# GoBang AI

五子棋游戏，支持AI和LLM玩家，提供CLI、GUI和Web三种界面。

## 项目背景

GoBang AI 是一个完整的五子棋游戏实现，旨在探索传统游戏AI算法与现代大语言模型（LLM）的结合。项目的创建是为了提供一个比较不同AI游戏方法的平台，从确定性的Minimax算法配合Alpha-Beta剪枝，到概率性的蒙特卡洛树搜索（MCTS），再到使用LLM作为游戏代理的新兴范式。

五子棋是一个两人策略棋盘游戏，玩家轮流在网格上放置棋子，目标是率先在水平、垂直或对角线方向上形成连续的五子连线。游戏规则简单但策略深度高，是AI研究和开发的理想测试平台。本实现支持多种规则变体，包括自由规则（无限制）、标准规则和连珠规则（黑棋有禁手）。

项目解决了几个关键挑战：实现高效的游戏状态管理、开发可调节难度的AI对手、与本地和云端LLM服务集成，以及在不同界面模式下提供一致的用户体验。无论您是想研究游戏AI算法、测试LLM推理能力，还是单纯享受五子棋游戏，这个项目都提供了完整的解决方案。

## 应用场景

GoBang AI 服务于多种用途和用户群体：

**AI研究者和开发者**：模块化架构便于实验不同的AI算法。MinimaxAI类实现了可配置搜索深度的Alpha-Beta剪枝，MCTSAI提供了基于模拟的方法。两者都可以轻松扩展或替换为自定义实现。全面的测试套例确保修改算法时的可靠性。

**LLM爱好者**：项目提供与Ollama本地LLM推理和OpenAI兼容API云服务的无缝集成。您可以让不同的LLM模型相互对弈，比较它们的下棋风格，或将其作为陪练对手。系统自动处理提示工程、落子解析和错误恢复。

**休闲玩家**：GUI为人类玩家提供了直观的界面，可以与不同难度的AI对手对弈。游戏记录所有落子，支持悔棋操作，允许保存/加载游戏以便后续分析。可视化棋盘清晰显示当前游戏状态和最后落子位置。

**教育目的**：清晰、文档完善的代码库是学习游戏AI实现、Python GUI开发（PySide6）、Web应用开发（Flask）和API设计模式的优秀资源。每个模块都是独立的，可以单独学习。

## 兼容硬件

GoBang AI 设计为在各种硬件配置上高效运行：

**CPU要求**：核心游戏逻辑和传统AI算法（Minimax、Alpha-Beta）基于CPU，可在任何现代处理器上流畅运行。对于AI深度3-4的舒适游戏体验，近10年的双核处理器即可满足要求。更高的搜索深度（5-6）受益于四核或更好的处理器。MCTS模拟可以有效利用多核。

**内存要求**：基础应用程序需要约50-100MB内存。游戏状态存储极小（15×15棋盘需要不到1KB）。LLM集成需要额外内存，取决于模型大小——本地Ollama模型通常需要4-16GB内存，取决于模型参数。

**GPU考虑**：应用程序本身不需要GPU。但是，如果您通过Ollama使用本地LLM模型，GPU加速可显著提高响应时间。Ollama支持NVIDIA（CUDA）和Apple Silicon（Metal）加速的兼容模型。

**存储要求**：应用程序本身需要不到10MB磁盘空间。游戏记录存储为JSON文件，通常每个1-5KB。通过Ollama下载的LLM模型单独存储，根据模型大小可从1GB到50GB不等。

## 操作系统

GoBang AI 以跨平台兼容性为设计目标：

**Windows**：完全支持Windows 10和Windows 11。GUI使用PySide6，提供原生Windows风格。通过pip安装或使用Python 3.9+从源码运行。某些用户可能需要安装Visual C++ Redistributable以支持PySide6。

**macOS**：完全支持macOS 11（Big Sur）及更高版本。Intel和Apple Silicon（M1/M2/M3）Mac均原生支持。GUI适应macOS系统外观设置。Apple Silicon用户通过Metal优化可受益于LLM推理加速。

**Linux**：完全支持主要发行版，包括Ubuntu 20.04+、Debian 11+、Fedora 35+和Arch Linux。GUI模式需要X11或Wayland显示服务器。无头操作（CLI和Web模式）可在无显示器的服务器上运行。某些发行版可能需要安装额外的Qt依赖。

**虚拟环境**：强烈建议使用虚拟环境（venv、conda）以避免依赖冲突。项目在requirements.txt中指定了确切的依赖版本以确保可重现性。

## 依赖环境

GoBang AI 需要Python 3.9或更高版本以及以下核心依赖：

**PySide6 (>=6.5.0)**：GUI界面所需。提供Python的Qt绑定，实现原生风格的跨平台GUI。最低版本确保与现代Qt功能和Python 3.11+的兼容性。

**Flask (>=3.0.0)**：为Web服务器和REST API提供支持。Flask 3.0+包含改进的异步支持和安全功能。Flask-SocketIO实现实时游戏更新的通信。

**Requests (>=2.31.0)**：用于与Ollama API和其他外部服务的HTTP通信。最低版本解决了早期版本中的已知安全漏洞。

**OpenAI (>=1.0.0)**：提供官方OpenAI Python客户端，用于连接OpenAI兼容的API。这包括本地Ollama实例（通过其OpenAI兼容端点）和各种云服务。

**NumPy (>=1.24.0)**：用于游戏状态表示和AI计算中的高效数组操作。可选但推荐用于优化AI计算性能。

**开发依赖**：pytest用于测试，black和ruff用于代码格式化和检查。这些对最终用户是可选的，但对贡献者推荐使用。

## 安装过程

### 快速安装（推荐）

安装GoBang AI最简单的方法是通过pip：

```bash
pip install gobang
```

这会从PyPI安装最新稳定版本及所有依赖。安装后，从命令行运行`gobang`启动GUI，或使用`gobang --help`查看可用命令。

### 从源码安装

用于开发或获取最新功能：

```bash
git clone https://github.com/CodeOfMe/GoBang.git
cd GoBang
pip install -e .
```

`-e`标志以可编辑模式安装，允许您修改代码并立即看到更改。

### 安装Ollama支持

要使用LLM玩家，请单独安装Ollama：

1. 访问 https://ollama.ai 并下载适合您平台的安装程序
2. 安装一个或多个模型：`ollama pull gemma3:1b`、`ollama pull mistral`
3. 验证Ollama正在运行：`ollama list`

### 开发环境设置

用于为项目做贡献：

```bash
git clone https://github.com/CodeOfMe/GoBang.git
cd GoBang
python -m venv venv
source venv/bin/activate  # Windows上：venv\Scripts\activate
pip install -e ".[dev]"
pytest  # 运行测试验证设置
```

## 使用方法

### GUI模式（默认）

直接运行命令启动图形界面：

```bash
gobang
```

GUI提供：
- 可点击落子的交互式棋盘
- 玩家配置面板（人类/AI/LLM）
- 带悔棋功能的落子历史
- 保存/加载游戏功能
- AI对战或LLM对战的自动播放模式

### CLI模式

命令行操作：

```bash
# 创建新游戏
gobang cli new

# 创建AI对战LLM的游戏
gobang cli new -b ai:minimax -w llm:gemma3:1b

# 落子
gobang cli move H8

# 让AI/LLM自动下棋
gobang cli auto

# 运行AI对战（10局）
gobang cli battle -b ai:minimax -w llm:gemma3:1b -g 10

# 保存和加载游戏
gobang cli save game.json
gobang cli load game.json
```

### Web模式

启动Web服务器进行浏览器游戏：

```bash
gobang web --port 5000
```

然后在浏览器中打开 http://localhost:5000。Web界面支持：
- 通过WebSocket实时游戏更新
- 用于集成的RESTful API
- 与GUI相同的玩家选项（人类/AI/LLM）

### Python API

作为Python库使用：

```python
from gobang import Game, Stone, Position, Player, PlayerType
from gobang.ai import MinimaxAI

# 创建游戏
game = Game(board_size=15)

# 落子
game.make_move(Position(7, 7))  # H8

# 使用AI
ai = MinimaxAI(depth=3)
best_move = ai.get_best_move(game)

# 检查游戏状态
if game.winner:
    print(f"获胜者: {game.winner.name}")
```

## 运行截图

| GUI界面 | Web界面 |
|:-------------:|:-------------:|
| ![GUI](images/gui.png) | ![Web](images/web.png) |

## 授权协议

GNU通用公共许可证v3.0（GPLv3）。完整许可证文本请参见[LICENSE](LICENSE)。

本项目是自由软件：您可以根据自由软件基金会发布的GNU通用公共许可证条款重新分发和/或修改它，许可证版本为第3版或（根据您的选择）任何后续版本。

分发本程序是希望它有用，但不提供任何保证；甚至没有适销性或特定用途适用性的暗示保证。有关更多详细信息，请参阅GNU通用公共许可证。