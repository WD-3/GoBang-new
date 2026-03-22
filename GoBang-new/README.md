# GoBang AI

Gomoku (Five-in-a-Row/五子棋) game with AI and LLM players - featuring CLI, GUI, and Web interfaces.

## Project Background

GoBang AI is a comprehensive implementation of the classic Gomoku (五子棋) board game, designed to explore the intersection of traditional game AI algorithms and modern Large Language Models (LLMs). The project was created to provide a platform for comparing different AI approaches to game playing, from deterministic algorithms like Minimax with Alpha-Beta pruning to probabilistic methods like Monte Carlo Tree Search (MCTS), and finally to the emerging paradigm of using LLMs as game-playing agents.

Gomoku is a two-player strategy board game where players take turns placing stones on a grid, with the objective of being the first to form an unbroken line of five stones horizontally, vertically, or diagonally. The game's simple rules but deep strategic complexity make it an ideal testbed for AI research and development. This implementation supports multiple rule variations including free style (no restrictions), standard rules, and Renju (with forbidden moves for black).

The project addresses several key challenges: implementing efficient game state management, developing competitive AI opponents with adjustable difficulty, integrating with both local and cloud-based LLM services, and providing a consistent user experience across different interface modes. Whether you're interested in studying game AI algorithms, testing LLM reasoning capabilities, or simply enjoying a game of Gomoku, this project provides a complete solution.

## Application Scenarios

GoBang AI serves multiple purposes and user groups:

**For AI Researchers and Developers**: The modular architecture allows easy experimentation with different AI algorithms. The MinimaxAI class implements alpha-beta pruning with configurable search depth, while MCTSAI provides a simulation-based approach. Both can be easily extended or replaced with custom implementations. The comprehensive test suite ensures reliability when modifying algorithms.

**For LLM Enthusiasts**: The project provides seamless integration with Ollama for local LLM inference and OpenAI-compatible APIs for cloud services. You can pit different LLM models against each other, compare their playing styles, or use them as sparring partners. The system handles prompt engineering, move parsing, and error recovery automatically.

**For Casual Players**: The GUI provides an intuitive interface for human players to enjoy Gomoku against AI opponents of varying difficulty. The game records all moves, supports undo operations, and allows saving/loading games for later analysis. The visual board clearly shows the current game state and last move.

**For Educational Purposes**: The clean, well-documented codebase serves as an excellent resource for learning about game AI implementation, Python GUI development with PySide6, web application development with Flask, and API design patterns. Each module is self-contained and can be studied independently.

## Hardware Compatibility

GoBang AI is designed to run efficiently on a wide range of hardware configurations:

**CPU Requirements**: The core game logic and traditional AI algorithms (Minimax, Alpha-Beta) are CPU-based and run well on any modern processor. For comfortable gameplay with AI depth 3-4, a dual-core processor from the last 10 years is sufficient. Higher search depths (5-6) benefit from quad-core or better processors. MCTS simulations can utilize multiple cores effectively.

**Memory Requirements**: The base application requires approximately 50-100MB of RAM. Game state storage is minimal (a 15×15 board needs less than 1KB). LLM integration requires additional memory depending on the model size - local Ollama models typically need 4-16GB RAM depending on model parameters.

**GPU Considerations**: The application itself does not require a GPU. However, if you're using local LLM models through Ollama, GPU acceleration significantly improves response times. Ollama supports both NVIDIA (CUDA) and Apple Silicon (Metal) acceleration for compatible models.

**Storage Requirements**: The application itself requires less than 10MB of disk space. Game records are stored as JSON files, typically 1-5KB each. LLM models downloaded through Ollama are stored separately and can range from 1GB to 50GB depending on model size.

## Operating Systems

GoBang AI is developed with cross-platform compatibility in mind:

**Windows**: Fully supported on Windows 10 and Windows 11. The GUI uses PySide6 which provides native Windows styling. Install via pip or run from source with Python 3.9+. Some users may need to install Visual C++ Redistributable for PySide6.

**macOS**: Fully supported on macOS 11 (Big Sur) and later. Both Intel and Apple Silicon (M1/M2/M3) Macs are supported natively. The GUI adapts to macOS system appearance settings. Apple Silicon users benefit from optimized LLM inference through Metal.

**Linux**: Fully supported on major distributions including Ubuntu 20.04+, Debian 11+, Fedora 35+, and Arch Linux. Requires X11 or Wayland display server for GUI mode. Headless operation (CLI and Web modes) works on servers without displays. Some distributions may require installing additional Qt dependencies.

**Virtual Environments**: Strongly recommended to use virtual environments (venv, conda) to avoid dependency conflicts. The project specifies exact dependency versions in requirements.txt for reproducibility.

## Dependencies

GoBang AI requires Python 3.9 or higher and the following core dependencies:

**PySide6 (>=6.5.0)**: Required for the GUI interface. Provides Qt bindings for Python, enabling native-looking cross-platform GUIs. The minimum version ensures compatibility with modern Qt features and Python 3.11+.

**Flask (>=3.0.0)**: Powers the web server and REST API. Flask 3.0+ includes improved async support and security features. Flask-SocketIO enables real-time communication for live game updates.

**Requests (>=2.31.0)**: Used for HTTP communication with Ollama API and other external services. The minimum version addresses known security vulnerabilities in earlier releases.

**OpenAI (>=1.0.0)**: Provides the official OpenAI Python client for connecting to OpenAI-compatible APIs. This includes local Ollama instances (via its OpenAI-compatible endpoint) and various cloud services.

**NumPy (>=1.24.0)**: Used for efficient array operations in game state representation and AI calculations. Optional but recommended for optimal performance in AI computations.

**Development Dependencies**: pytest for testing, black and ruff for code formatting and linting. These are optional for end users but recommended for contributors.

## Installation

### Quick Install (Recommended)

The easiest way to install GoBang AI is via pip:

```bash
pip install gobang
```

This installs the latest stable release from PyPI along with all dependencies. After installation, run `gobang` from the command line to launch the GUI, or use `gobang --help` to see available commands.

### Install from Source

For development or to get the latest features:

```bash
git clone https://github.com/CodeOfMe/GoBang.git
cd GoBang
pip install -e .
```

The `-e` flag installs in editable mode, allowing you to modify the code and see changes immediately.

### Install with Ollama Support

To use LLM players, install Ollama separately:

1. Visit https://ollama.ai and download the installer for your platform
2. Install one or more models: `ollama pull gemma3:1b`, `ollama pull mistral`
3. Verify Ollama is running: `ollama list`

### Development Setup

For contributing to the project:

```bash
git clone https://github.com/CodeOfMe/GoBang.git
cd GoBang
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
pytest  # Run tests to verify setup
```

## Usage

### GUI Mode (Default)

Simply run the command without arguments to launch the graphical interface:

```bash
gobang
```

The GUI provides:
- Interactive board with click-to-place stones
- Player configuration panel (Human/AI/LLM)
- Move history with undo capability
- Save/Load game functionality
- Auto-play mode for AI vs AI or LLM battles

### CLI Mode

For command-line operation:

```bash
# Create a new game
gobang cli new

# Create AI vs LLM game
gobang cli new -b ai:minimax -w llm:gemma3:1b

# Make a move
gobang cli move H8

# Let AI/LLM play automatically
gobang cli auto

# Run AI battle (10 games)
gobang cli battle -b ai:minimax -w llm:gemma3:1b -g 10

# Save and load games
gobang cli save game.json
gobang cli load game.json
```

### Web Mode

Start the web server for browser-based play:

```bash
gobang web --port 5000
```

Then open http://localhost:5000 in your browser. The web interface supports:
- Real-time game updates via WebSocket
- RESTful API for integration
- Same player options as GUI (Human/AI/LLM)

### Python API

Use as a Python library:

```python
from gobang import Game, Stone, Position, Player, PlayerType
from gobang.ai import MinimaxAI

# Create a game
game = Game(board_size=15)

# Make moves
game.make_move(Position(7, 7))  # H8

# Use AI
ai = MinimaxAI(depth=3)
best_move = ai.get_best_move(game)

# Check game state
if game.winner:
    print(f"Winner: {game.winner.name}")
```

## Screenshots

| GUI Interface | Web Interface |
|:-------------:|:-------------:|
| ![GUI](images/gui.png) | ![Web](images/web.png) |

## License

GNU General Public License v3.0 (GPLv3). See [LICENSE](LICENSE) for the full license text.

This project is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This project is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.