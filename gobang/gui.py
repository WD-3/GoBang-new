"""
PySide6 GUI for GoBang.

Features:
- Interactive game board
- Player configuration with dynamic LLM model selection
- AI and LLM player support
- Game recording and replay
- Stable, non-jumping layout
- Decoupled UI with background threads for AI/LLM moves
"""

import sys
from typing import Optional, Dict, Any, List
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QComboBox,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QMenuBar,
    QStatusBar,
    QMessageBox,
    QFileDialog,
    QHeaderView,
    QLineEdit,
    QStackedWidget,
    QFrame,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QThread, QMutex
from PySide6.QtGui import QAction

from gobang import __version__
from gobang.core import Game, Board, Player, PlayerType, Stone, GameState, RuleMode, Position
from gobang.ai import create_ai
from gobang.llm_player import (
    create_llm_player,
    LLMPlayer,
    OllamaClient,
    OpenAICompatibleClient,
)
from gobang.game_record import save_game_to_file, load_game_from_file


class AIWorker(QObject):
    finished = Signal(object, int)
    error = Signal(str)

    def __init__(self, game: Game, llm_players: Dict[Stone, LLMPlayer]):
        super().__init__()
        self.game = game
        self.llm_players = llm_players
        self._cancelled = False

    def run(self):
        try:
            import copy

            # Critical: Check if game is still playing before starting AI calculation
            if self.game.state != GameState.PLAYING:
                print(
                    f"[AI Worker] Game already ended (state={self.game.state}), skipping AI calculation"
                )
                self.finished.emit(None, 0)
                return

            game_copy = self.game.copy()
            current_player = game_copy.current_player
            pos = None
            thinking_time_ms = 0

            if current_player.player_type == PlayerType.AI:
                config = current_player.config
                ai = create_ai(config.get("algorithm", "minimax"), depth=config.get("depth", 3))
                pos = ai.get_best_move(game_copy)
            elif current_player.player_type == PlayerType.LLM:
                llm_player = self.llm_players.get(game_copy.current_stone)
                if llm_player:
                    pos = llm_player.get_move(game_copy)
                    thinking_time_ms = llm_player.last_thinking_time_ms

            if not self._cancelled:
                self.finished.emit(pos, thinking_time_ms)
        except Exception as e:
            self.error.emit(str(e))

    def cancel(self):
        self._cancelled = True


class GameSignals(QObject):
    move_made = Signal(str)
    game_over = Signal(str)
    status_update = Signal(str)
    ai_finished = Signal(object, int)


class BoardWidget(QWidget):
    def __init__(self, game: Optional[Game] = None):
        super().__init__()
        self.game = game
        self.cell_size = 35
        self.margin = 30
        self.setFixedSize(570, 570)
        self.setMouseTracking(True)
        self.hover_pos: Optional[Position] = None
        self.on_click = None

    def set_game(self, game: Game) -> None:
        self.game = game
        self.update()

    def get_position(self, x: int, y: int) -> Optional[Position]:
        if self.game is None:
            return None
        size = self.game.board_size
        col = round((x - self.margin) / self.cell_size)
        row = round((y - self.margin) / self.cell_size)
        if 0 <= row < size and 0 <= col < size:
            return Position(row, col)
        return None

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QPen, QBrush, QColor

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self.game is None:
            return

        size = self.game.board_size
        cell = self.cell_size
        margin = self.margin

        painter.fillRect(self.rect(), QColor(222, 184, 135))

        painter.setPen(QPen(QColor(50, 50, 50), 1))
        for i in range(size):
            x = margin + i * cell
            y = margin + i * cell
            painter.drawLine(margin, y, margin + (size - 1) * cell, y)
            painter.drawLine(x, margin, x, margin + (size - 1) * cell)

        if size == 15:
            star_points = [(3, 3), (3, 11), (11, 3), (11, 11), (7, 7)]
            painter.setBrush(QBrush(Qt.black))
            for r, c in star_points:
                x = margin + c * cell
                y = margin + r * cell
                painter.drawEllipse(x - 4, y - 4, 8, 8)

        for row in range(size):
            for col in range(size):
                pos = Position(row, col)
                stone = self.game.board.get(pos)

                if stone != Stone.EMPTY:
                    x = margin + col * cell
                    y = margin + row * cell

                    if stone == Stone.BLACK:
                        painter.setBrush(QBrush(QColor(30, 30, 30)))
                        painter.setPen(QPen(Qt.black, 1))
                    else:
                        painter.setBrush(QBrush(QColor(250, 250, 250)))
                        painter.setPen(QPen(QColor(180, 180, 180), 1))

                    painter.drawEllipse(x - 13, y - 13, 26, 26)

        if self.game.moves:
            last_move = self.game.moves[-1]
            x = margin + last_move.position.col * cell
            y = margin + last_move.position.row * cell
            painter.setPen(QPen(QColor(220, 50, 50), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(x - 15, y - 15, 30, 30)

        if self.hover_pos and self.game.state == GameState.PLAYING:
            if self.game.board.is_empty(self.hover_pos):
                x = margin + self.hover_pos.col * cell
                y = margin + self.hover_pos.row * cell
                painter.setOpacity(0.4)
                if self.game.current_stone == Stone.BLACK:
                    painter.setBrush(QBrush(QColor(30, 30, 30)))
                else:
                    painter.setBrush(QBrush(QColor(250, 250, 250)))
                painter.setPen(QPen(Qt.gray, 1))
                painter.drawEllipse(x - 13, y - 13, 26, 26)
                painter.setOpacity(1.0)

    def mouseMoveEvent(self, event):
        pos = self.get_position(event.x(), event.y())
        if pos != self.hover_pos:
            self.hover_pos = pos
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.on_click:
            pos = self.get_position(event.x(), event.y())
            if pos:
                self.on_click(pos)


class PlayerConfigWidget(QWidget):
    def __init__(self, title: str, stone: Stone):
        super().__init__()
        self.stone = stone
        self._connected = False
        self._models: List[str] = []
        self._min_height = 180
        self.setup_ui(title)

    def setup_ui(self, title: str):
        self.setMinimumHeight(self._min_height)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        main_layout.addWidget(title_label)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #ccc;")
        main_layout.addWidget(line)

        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Human", "AI (Minimax)", "AI (MCTS)", "LLM"])
        self.type_combo.currentIndexChanged.connect(self.on_type_changed)
        type_layout.addWidget(self.type_combo)
        type_layout.addStretch()
        main_layout.addLayout(type_layout)

        self.stack = QStackedWidget()
        self.stack.setFixedHeight(100)

        empty_widget = QWidget()
        self.stack.addWidget(empty_widget)

        self.ai_widget = QWidget()
        ai_layout = QHBoxLayout(self.ai_widget)
        ai_layout.setContentsMargins(0, 0, 0, 0)
        ai_layout.addWidget(QLabel("Search Depth:"))
        self.depth_spin = QSpinBox()
        self.depth_spin.setRange(1, 6)
        self.depth_spin.setValue(3)
        self.depth_spin.setFixedWidth(60)
        ai_layout.addWidget(self.depth_spin)
        ai_layout.addStretch()
        self.stack.addWidget(self.ai_widget)

        self.llm_widget = QWidget()
        llm_layout = QVBoxLayout(self.llm_widget)
        llm_layout.setContentsMargins(0, 0, 0, 0)
        llm_layout.setSpacing(6)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("API URL:"))
        self.api_url_edit = QLineEdit()
        self.api_url_edit.setPlaceholderText("http://localhost:11434/v1")
        self.api_url_edit.setText("http://localhost:11434/v1")
        self.api_url_edit.textChanged.connect(self._on_api_url_changed)
        row1.addWidget(self.api_url_edit)
        llm_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("API Key:"))
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setPlaceholderText("Optional")
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        row2.addWidget(self.api_key_edit)
        llm_layout.addLayout(row2)

        row3 = QHBoxLayout()
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setFixedWidth(80)
        self.connect_btn.clicked.connect(self._connect_to_api)
        row3.addWidget(self.connect_btn)
        self.connection_status = QLabel("Not connected")
        self.connection_status.setFixedWidth(120)
        self.connection_status.setStyleSheet("color: #888;")
        row3.addWidget(self.connection_status)
        row3.addStretch()
        llm_layout.addLayout(row3)

        row4 = QHBoxLayout()
        row4.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.setEnabled(False)
        row4.addWidget(self.model_combo)
        llm_layout.addLayout(row4)

        self.stack.addWidget(self.llm_widget)
        main_layout.addWidget(self.stack)

    def _on_api_url_changed(self):
        self._connected = False
        self.connection_status.setText("Not connected")
        self.connection_status.setStyleSheet("color: #888;")
        self.model_combo.setEnabled(False)
        self.model_combo.clear()
        self._models = []

    def _connect_to_api(self):
        api_url = self.api_url_edit.text().strip()
        api_key = self.api_key_edit.text().strip()

        if not api_url:
            QMessageBox.warning(self, "Error", "Please enter API URL")
            return

        self.connect_btn.setEnabled(False)
        self.connection_status.setText("Connecting...")
        QApplication.processEvents()

        try:
            ollama_url = api_url.replace("/v1", "").rstrip("/")
            if ollama_url.endswith("/api"):
                ollama_url = ollama_url[:-4]

            is_ollama = ":11434" in api_url or "localhost" in api_url

            if is_ollama and not api_key:
                client = OllamaClient(base_url=ollama_url)
                if client.is_available():
                    models = client.list_models()
                    if models:
                        self._models = models
                        self._populate_models()
                        self._connected = True
                        self.connection_status.setText(f"✓ {len(models)} models")
                        self.connection_status.setStyleSheet("color: #2a2;")
                        self.model_combo.setEnabled(True)
                    else:
                        self.connection_status.setText("No models")
                        self.connection_status.setStyleSheet("color: #a80;")
                else:
                    self.connection_status.setText("Failed")
                    self.connection_status.setStyleSheet("color: #a22;")
                    QMessageBox.critical(self, "Error", "Cannot connect to Ollama")
            else:
                client = OpenAICompatibleClient(base_url=api_url, api_key=api_key)
                models = client.list_models()
                if models:
                    self._models = models
                    self._populate_models()
                    self._connected = True
                    self.connection_status.setText(f"✓ {len(models)} models")
                    self.connection_status.setStyleSheet("color: #2a2;")
                    self.model_combo.setEnabled(True)
                else:
                    self.connection_status.setText("Auth failed")
                    self.connection_status.setStyleSheet("color: #a22;")

        except Exception as e:
            self.connection_status.setText("Failed")
            self.connection_status.setStyleSheet("color: #a22;")

        self.connect_btn.setEnabled(True)

    def _populate_models(self):
        self.model_combo.clear()
        for model in self._models:
            self.model_combo.addItem(model)

    def on_type_changed(self, index):
        if index == 0:
            self.stack.setCurrentIndex(0)
        elif index in (1, 2):
            self.stack.setCurrentIndex(1)
        else:
            self.stack.setCurrentIndex(2)

    def get_player_config(self) -> Dict[str, Any]:
        idx = self.type_combo.currentIndex()

        if idx == 0:
            return {"type": "human"}
        elif idx == 1:
            return {"type": "ai", "algorithm": "minimax", "depth": self.depth_spin.value()}
        elif idx == 2:
            return {"type": "ai", "algorithm": "mcts", "depth": self.depth_spin.value()}
        else:
            api_url = self.api_url_edit.text().strip()
            api_key = self.api_key_edit.text().strip() or None
            model = self.model_combo.currentText() if self._connected else ""

            is_ollama = ":11434" in api_url or "localhost" in api_url
            provider = "ollama" if is_ollama else "openai_compatible"

            base_url = api_url.replace("/v1", "").rstrip("/")
            if base_url.endswith("/api"):
                base_url = base_url[:-4]

            return {
                "type": "llm",
                "model": model,
                "provider": provider,
                "base_url": base_url,
                "api_key": api_key,
            }

    def set_player_config(self, config: Dict[str, Any]):
        player_type = config.get("type", "human")

        if player_type == "human":
            self.type_combo.setCurrentIndex(0)
        elif player_type == "ai":
            algo = config.get("algorithm", "minimax")
            if algo == "mcts":
                self.type_combo.setCurrentIndex(2)
            else:
                self.type_combo.setCurrentIndex(1)
            self.depth_spin.setValue(config.get("depth", 3))
        elif player_type == "llm":
            self.type_combo.setCurrentIndex(3)
            base_url = config.get("base_url", "http://localhost:11434")
            if not base_url.endswith("/v1"):
                base_url = base_url + "/v1"
            self.api_url_edit.setText(base_url)
            api_key = config.get("api_key", "")
            if api_key:
                self.api_key_edit.setText(api_key)
            model = config.get("model", "")
            if model:
                self._models = [model]
                self._populate_models()
                self.model_combo.setCurrentText(model)
                self.model_combo.setEnabled(True)
                self._connected = True
                self.connection_status.setText("✓ Ready")
                self.connection_status.setStyleSheet("color: #2a2;")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.game: Optional[Game] = None
        self.llm_players: Dict[Stone, LLMPlayer] = {}
        self.signals = GameSignals()
        self.auto_play_enabled = False

        self._ai_thread: Optional[QThread] = None
        self._ai_worker: Optional[AIWorker] = None
        self._mutex = QMutex()

        self.setup_ui()
        self.create_new_game()

        self.signals.ai_finished.connect(self._on_ai_finished)

    def setup_ui(self):
        self.setWindowTitle(f"GoBang AI v{__version__}")
        self.setMinimumSize(1000, 700)
        self.setStyleSheet("""
            QMainWindow { background-color: #f5f5f5; }
            QGroupBox { 
                border: 1px solid #ccc; 
                border-radius: 5px; 
                margin-top: 10px; 
                padding-top: 10px;
                background-color: white;
            }
            QGroupBox::title { 
                subcontrol-origin: margin; 
                left: 10px; 
                padding: 0 5px;
            }
            QPushButton {
                padding: 6px 16px;
                border-radius: 4px;
                background-color: #4a90d9;
                color: white;
                border: none;
            }
            QPushButton:hover { background-color: #3a7bc8; }
            QPushButton:pressed { background-color: #2a6ab8; }
            QPushButton:disabled { background-color: #ccc; }
            QComboBox, QSpinBox, QLineEdit {
                padding: 4px 8px;
                border: 1px solid #ccc;
                border-radius: 3px;
                background-color: white;
            }
            QComboBox:focus, QSpinBox:focus, QLineEdit:focus {
                border: 1px solid #4a90d9;
            }
        """)

        self.create_menu_bar()

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)

        left_panel = QWidget()
        left_panel.setFixedWidth(300)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(12)

        game_group = QGroupBox("Game Settings")
        game_layout = QGridLayout(game_group)
        game_layout.addWidget(QLabel("Board Size:"), 0, 0)
        self.board_size_spin = QSpinBox()
        self.board_size_spin.setRange(9, 19)
        self.board_size_spin.setValue(15)
        self.board_size_spin.setFixedWidth(70)
        game_layout.addWidget(self.board_size_spin, 0, 1)
        game_layout.addWidget(QLabel("Rules:"), 0, 2)
        self.rules_combo = QComboBox()
        self.rules_combo.addItems(["Free Style", "Standard", "Renju"])
        game_layout.addWidget(self.rules_combo, 0, 3)
        left_layout.addWidget(game_group)

        self.black_config = PlayerConfigWidget("Black Player ●", Stone.BLACK)
        left_layout.addWidget(self.black_config)

        self.white_config = PlayerConfigWidget("White Player ○", Stone.WHITE)
        left_layout.addWidget(self.white_config)

        btn_layout = QHBoxLayout()
        self.new_game_btn = QPushButton("New Game")
        self.new_game_btn.clicked.connect(self.create_new_game)
        btn_layout.addWidget(self.new_game_btn)
        self.auto_play_btn = QPushButton("Auto Play")
        self.auto_play_btn.clicked.connect(self.toggle_auto_play)
        btn_layout.addWidget(self.auto_play_btn)
        left_layout.addLayout(btn_layout)

        self.status_frame = QFrame()
        self.status_frame.setStyleSheet(
            "background-color: white; border-radius: 5px; padding: 5px;"
        )
        self.status_frame.setMinimumHeight(60)
        status_layout = QVBoxLayout(self.status_frame)
        self.turn_label = QLabel("Black's turn")
        self.turn_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.turn_label.setAlignment(Qt.AlignCenter)
        status_layout.addWidget(self.turn_label)
        self.player_label = QLabel("Human")
        self.player_label.setStyleSheet("color: #666;")
        self.player_label.setAlignment(Qt.AlignCenter)
        status_layout.addWidget(self.player_label)
        left_layout.addWidget(self.status_frame)

        left_layout.addStretch()

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(10)

        board_container = QWidget()
        board_container.setFixedSize(580, 580)
        board_container.setStyleSheet("background-color: #222; border-radius: 5px;")
        board_layout = QVBoxLayout(board_container)
        board_layout.setContentsMargins(5, 5, 5, 5)
        self.board_widget = BoardWidget()
        self.board_widget.on_click = self.on_board_click
        board_layout.addWidget(self.board_widget, alignment=Qt.AlignCenter)
        right_layout.addWidget(board_container, alignment=Qt.AlignCenter)

        history_group = QGroupBox("Move History")
        history_layout = QVBoxLayout(history_group)
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(3)
        self.history_table.setHorizontalHeaderLabels(["#", "Black", "White"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.setFixedHeight(120)
        self.history_table.setAlternatingRowColors(True)
        history_layout.addWidget(self.history_table)
        right_layout.addWidget(history_group)

        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, stretch=1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        self.signals.status_update.connect(self.status_bar.showMessage)
        self.signals.game_over.connect(self.on_game_over)

    def create_menu_bar(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        file_menu.addAction(QAction("&New Game", self, triggered=self.create_new_game))
        file_menu.addAction(QAction("&Open...", self, triggered=self.open_game))
        file_menu.addAction(QAction("&Save...", self, triggered=self.save_game))
        file_menu.addSeparator()
        file_menu.addAction(QAction("E&xit", self, triggered=self.close))

        game_menu = menubar.addMenu("&Game")
        game_menu.addAction(QAction("&Undo", self, triggered=self.undo_move))
        game_menu.addAction(QAction("&Auto Play", self, triggered=self.toggle_auto_play))

        help_menu = menubar.addMenu("&Help")
        help_menu.addAction(QAction("&About", self, triggered=self.show_about))

    def create_new_game(self):
        board_size = self.board_size_spin.value()
        rule_mode = RuleMode(["free_style", "standard", "renju"][self.rules_combo.currentIndex()])

        black_config = self.black_config.get_player_config()
        white_config = self.white_config.get_player_config()

        black_player = self._create_player(Stone.BLACK, black_config)
        white_player = self._create_player(Stone.WHITE, white_config)

        self.game = Game(
            board_size=board_size,
            rule_mode=rule_mode,
            black_player=black_player,
            white_player=white_player,
        )

        self._setup_llm_players()
        self.board_widget.set_game(self.game)
        self.update_history_table()
        self.update_status()

        self.auto_play_enabled = False
        self.auto_play_btn.setText("Auto Play")

    def _create_player(self, stone: Stone, config: Dict[str, Any]) -> Player:
        player_type = config.get("type", "human")
        if player_type == "human":
            return Player(stone, PlayerType.HUMAN)
        elif player_type == "ai":
            algorithm = config.get("algorithm", "minimax")
            return Player(stone, PlayerType.AI, name=f"AI ({algorithm})", config=config)
        elif player_type == "llm":
            model = config.get("model", "unknown")
            return Player(stone, PlayerType.LLM, name=f"LLM ({model})", config=config)
        return Player(stone, PlayerType.HUMAN)

    def _setup_llm_players(self):
        self.llm_players = {}
        if self.game is None:
            return

        for stone, player in [
            (Stone.BLACK, self.game.black_player),
            (Stone.WHITE, self.game.white_player),
        ]:
            if player.player_type == PlayerType.LLM:
                config = player.config
                self.llm_players[stone] = create_llm_player(
                    stone,
                    provider=config.get("provider", "ollama"),
                    model=config.get("model", "unknown"),
                    base_url=config.get("base_url"),
                    api_key=config.get("api_key"),
                )

    def on_board_click(self, pos: Position):
        if self.game is None or self.game.state != GameState.PLAYING:
            return

        current_player = self.game.current_player
        if current_player.player_type in (PlayerType.AI, PlayerType.LLM):
            return

        success, message = self.game.make_move(pos)
        if success:
            self.board_widget.update()
            self.update_history_table()
            self.update_status()
            if self.game.state != GameState.PLAYING:
                self.signals.game_over.emit(message)
        else:
            self.signals.status_update.emit(message)

    def start_ai_move(self):
        if self.game is None or self.game.state != GameState.PLAYING:
            print(
                f"[DEBUG] start_ai_move: Game not playing (state={self.game.state if self.game else 'None'})"
            )
            return

        # Use mutex to prevent race conditions
        if self._mutex.tryLock():
            try:
                if self._ai_thread is not None and self._ai_thread.isRunning():
                    print(f"[DEBUG] start_ai_move: AI thread already running, skipping")
                    return
            finally:
                self._mutex.unlock()
        else:
            print(f"[DEBUG] start_ai_move: Could not acquire mutex, skipping")
            return

        current_player = self.game.current_player
        self.turn_label.setText(f"{current_player.name} thinking...")
        QApplication.processEvents()

        self._ai_thread = QThread()
        self._ai_worker = AIWorker(self.game, self.llm_players)
        self._ai_worker.moveToThread(self._ai_thread)

        self._ai_thread.started.connect(self._ai_worker.run)
        self._ai_worker.finished.connect(self._on_ai_finished)
        self._ai_worker.finished.connect(self._ai_thread.quit)
        self._ai_worker.error.connect(self._on_ai_error)
        self._ai_thread.finished.connect(self._cleanup_ai_thread)

        self._ai_thread.start()

    def _on_ai_finished(self, pos: Optional[Position], thinking_time_ms: int):
        if pos is None or self.game is None:
            self.update_status()
            if self.auto_play_enabled:
                QTimer.singleShot(100, self.auto_move_step)
            return

        # Critical fix: Check if game is still playing before making AI move
        # This prevents AI from making moves after game has ended
        if self.game.state != GameState.PLAYING:
            print(f"[DEBUG] Game already ended (state={self.game.state}), ignoring AI move")
            self.stop_auto_play()
            return

        success, message = self.game.make_move(pos, thinking_time_ms)
        if success:
            self.board_widget.update()
            self.update_history_table()
            self.update_status()
            if self.game.state != GameState.PLAYING:
                self.signals.game_over.emit(
                    f"{'Black' if self.game.winner == Stone.BLACK else 'White'} wins!"
                )
                self.stop_auto_play()
            elif self.auto_play_enabled:
                QTimer.singleShot(300, self.auto_move_step)
        else:
            print(f"[DEBUG] AI move failed: {message}")
            if self.auto_play_enabled:
                QTimer.singleShot(300, self.auto_move_step)

    def _on_ai_error(self, error_msg: str):
        self.status_bar.showMessage(f"Error: {error_msg}")
        self.update_status()

    def _cleanup_ai_thread(self):
        if self._ai_worker:
            self._ai_worker.deleteLater()
            self._ai_worker = None
        if self._ai_thread:
            self._ai_thread.deleteLater()
            self._ai_thread = None

    def auto_move_step(self):
        if self.game is None or self.game.state != GameState.PLAYING:
            self.stop_auto_play()
            return

        if self.game.current_player.player_type == PlayerType.HUMAN:
            self.stop_auto_play()
            return

        self.start_ai_move()

    def stop_auto_play(self):
        self.auto_play_enabled = False
        self.auto_play_btn.setText("Auto Play")

        if self._ai_thread and self._ai_thread.isRunning():
            if self._ai_worker:
                self._ai_worker.cancel()
            self._ai_thread.quit()
            self._ai_thread.wait(1000)

    def toggle_auto_play(self):
        self.auto_play_enabled = not self.auto_play_enabled
        if self.auto_play_enabled:
            self.auto_play_btn.setText("Stop")
            self.auto_move_step()
        else:
            self.stop_auto_play()

    def update_history_table(self):
        if self.game is None:
            return

        moves = self.game.moves
        rows = (len(moves) + 1) // 2
        self.history_table.setRowCount(rows)

        for i in range(rows):
            black_move = moves[i * 2] if i * 2 < len(moves) else None
            white_move = moves[i * 2 + 1] if i * 2 + 1 < len(moves) else None
            self.history_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.history_table.setItem(
                i, 1, QTableWidgetItem(black_move.position.to_notation() if black_move else "")
            )
            self.history_table.setItem(
                i, 2, QTableWidgetItem(white_move.position.to_notation() if white_move else "")
            )

    def update_status(self):
        if self.game is None:
            return

        if self.game.state == GameState.PLAYING:
            stone_name = "Black" if self.game.current_stone == Stone.BLACK else "White"
            self.turn_label.setText(f"{stone_name}'s turn")
            self.player_label.setText(self.game.current_player.name)
        elif self.game.winner:
            winner_name = "Black" if self.game.winner == Stone.BLACK else "White"
            self.turn_label.setText(f"{winner_name} wins!")
            self.player_label.setText("Game Over")
        else:
            self.turn_label.setText("Draw")
            self.player_label.setText("Game Over")

    def undo_move(self):
        if self.game and self.game.undo_move():
            self.board_widget.update()
            self.update_history_table()
            self.update_status()
            self.status_bar.showMessage("Move undone")

    def on_game_over(self, message: str):
        self.stop_auto_play()
        self.update_status()
        QMessageBox.information(self, "Game Over", message)

    def open_game(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Open Game", "", "JSON Files (*.json)")
        if filepath:
            try:
                self.game = load_game_from_file(filepath)
                self._setup_llm_players()
                self.board_widget.set_game(self.game)
                self.update_history_table()
                self.update_status()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load: {e}")

    def save_game(self):
        if self.game is None:
            return
        filepath, _ = QFileDialog.getSaveFileName(self, "Save Game", "", "JSON Files (*.json)")
        if filepath:
            try:
                save_game_to_file(self.game, filepath)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save: {e}")

    def show_about(self):
        QMessageBox.about(
            self,
            "About GoBang AI",
            f"GoBang AI v{__version__}\n\n"
            "Gomoku (五子棋) with AI and LLM players.\n\n"
            "Features:\n"
            "• Pattern-based rule engine (VCF, VCT)\n"
            "• Traditional AI (Minimax, MCTS)\n"
            "• LLM players (Ollama, OpenAI)\n\n"
            "© 2024 CodeOfMe",
        )

    def closeEvent(self, event):
        self.stop_auto_play()
        if self._ai_thread and self._ai_thread.isRunning():
            if self._ai_worker:
                self._ai_worker.cancel()
            self._ai_thread.quit()
            self._ai_thread.wait(2000)
        event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
