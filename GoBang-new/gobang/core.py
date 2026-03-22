"""
Core game logic for Gomoku (GoBang).

This module provides:
- Board: Game board with position management
- Game: Game state machine
- Player: Player abstraction
- Win detection algorithms
- Rule modes (free style, standard)
"""

from enum import Enum
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import copy


class Stone(Enum):
    """Represents a stone on the board."""

    EMPTY = 0
    BLACK = 1
    WHITE = 2

    def __str__(self) -> str:
        symbols = {Stone.EMPTY: "·", Stone.BLACK: "●", Stone.WHITE: "○"}
        return symbols[self]

    def opponent(self) -> "Stone":
        """Get opponent's stone color."""
        if self == Stone.BLACK:
            return Stone.WHITE
        elif self == Stone.WHITE:
            return Stone.BLACK
        return Stone.EMPTY


class PlayerType(Enum):
    """Type of player."""

    HUMAN = "human"
    AI = "ai"
    LLM = "llm"


class RuleMode(Enum):
    """Game rule modes."""

    FREE_STYLE = "free_style"  # No restrictions
    STANDARD = "standard"  # Standard Gomoku rules
    RENJU = "renju"  # Renju rules (black has forbidden moves)


class GameState(Enum):
    """Game state."""

    PLAYING = "playing"
    BLACK_WIN = "black_win"
    WHITE_WIN = "white_win"
    DRAW = "draw"


@dataclass
class Position:
    """Board position."""

    row: int
    col: int

    def __post_init__(self):
        if self.row < 0 or self.col < 0:
            raise ValueError(f"Invalid position: ({self.row}, {self.col})")

    def to_notation(self) -> str:
        """Convert to algebraic notation (e.g., 'A1', 'H8')."""
        col_letter = chr(ord("A") + self.col)
        row_number = self.row + 1
        return f"{col_letter}{row_number}"

    @classmethod
    def from_notation(cls, notation: str, board_size: int = 15) -> "Position":
        """Create position from algebraic notation."""
        notation = notation.strip().upper()
        if len(notation) < 2:
            raise ValueError(f"Invalid notation: {notation}")

        col_letter = notation[0]
        row_number = notation[1:]

        col = ord(col_letter) - ord("A")
        row = int(row_number) - 1

        if not (0 <= row < board_size and 0 <= col < board_size):
            raise ValueError(f"Position out of bounds: {notation}")

        return cls(row, col)

    def __hash__(self):
        return hash((self.row, self.col))

    def __eq__(self, other):
        if not isinstance(other, Position):
            return False
        return self.row == other.row and self.col == other.col


@dataclass
class Move:
    """A move in the game."""

    position: Position
    stone: Stone
    timestamp: datetime = field(default_factory=datetime.now)
    thinking_time_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "position": self.position.to_notation(),
            "stone": self.stone.name,
            "timestamp": self.timestamp.isoformat(),
            "thinking_time_ms": self.thinking_time_ms,
        }


@dataclass
class Player:
    """Player information."""

    stone: Stone
    player_type: PlayerType
    name: str = ""
    config: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.name:
            self.name = f"{self.player_type.value.capitalize()} ({self.stone.name})"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "stone": self.stone.name,
            "type": self.player_type.value,
            "name": self.name,
            "config": self.config,
        }


class Board:
    """
    Gomoku game board.

    Supports variable board sizes and rule modes.
    """

    def __init__(self, size: int = 15):
        if size < 5:
            raise ValueError("Board size must be at least 5")
        self.size = size
        self._grid: List[List[Stone]] = [[Stone.EMPTY] * size for _ in range(size)]
        self._move_history: List[Move] = []

    def copy(self) -> "Board":
        """Create a deep copy of the board."""
        new_board = Board(self.size)
        new_board._grid = [row[:] for row in self._grid]
        new_board._move_history = self._move_history[:]
        return new_board

    def get(self, pos: Position) -> Stone:
        """Get stone at position."""
        if not self.is_valid_position(pos):
            raise ValueError(f"Invalid position: {pos}")
        return self._grid[pos.row][pos.col]

    def set(self, pos: Position, stone: Stone) -> None:
        """Set stone at position."""
        if not self.is_valid_position(pos):
            raise ValueError(f"Invalid position: {pos}")
        self._grid[pos.row][pos.col] = stone

    def is_valid_position(self, pos: Position) -> bool:
        """Check if position is valid."""
        return 0 <= pos.row < self.size and 0 <= pos.col < self.size

    def is_empty(self, pos: Position) -> bool:
        """Check if position is empty."""
        return self.get(pos) == Stone.EMPTY

    def place_stone(self, pos: Position, stone: Stone) -> bool:
        """
        Place a stone on the board.

        Returns True if successful, False if position is occupied.
        """
        if not self.is_empty(pos):
            return False
        self.set(pos, stone)
        return True

    def remove_stone(self, pos: Position) -> None:
        """Remove a stone from the board."""
        self.set(pos, Stone.EMPTY)

    def get_empty_positions(self) -> List[Position]:
        """Get all empty positions."""
        positions = []
        for row in range(self.size):
            for col in range(self.size):
                pos = Position(row, col)
                if self.is_empty(pos):
                    positions.append(pos)
        return positions

    def get_neighbors(self, pos: Position, distance: int = 2) -> List[Position]:
        """Get neighboring positions within distance."""
        neighbors = []
        for dr in range(-distance, distance + 1):
            for dc in range(-distance, distance + 1):
                if dr == 0 and dc == 0:
                    continue
                new_row = pos.row + dr
                new_col = pos.col + dc
                if 0 <= new_row < self.size and 0 <= new_col < self.size:
                    neighbors.append(Position(new_row, new_col))
        return neighbors

    def get_candidate_moves(self, distance: int = 2) -> List[Position]:
        """Get candidate moves near existing stones."""
        candidates = set()
        has_stones = False

        for row in range(self.size):
            for col in range(self.size):
                pos = Position(row, col)
                if self.get(pos) != Stone.EMPTY:
                    has_stones = True
                    for neighbor in self.get_neighbors(pos, distance):
                        if self.is_empty(neighbor):
                            candidates.add(neighbor)

        if not has_stones:
            center = Position(self.size // 2, self.size // 2)
            return [center]

        return list(candidates)

    def count_consecutive(self, pos: Position, stone: Stone, direction: Tuple[int, int]) -> int:
        """Count consecutive stones in a direction."""
        count = 0
        dr, dc = direction
        r, c = pos.row, pos.col

        while 0 <= r < self.size and 0 <= c < self.size:
            if self._grid[r][c] == stone:
                count += 1
                r += dr
                c += dc
            else:
                break

        return count

    def check_five_in_row(self, pos: Position, stone: Stone) -> bool:
        """Check if there are five consecutive stones through position."""
        directions = [
            (0, 1),  # Horizontal
            (1, 0),  # Vertical
            (1, 1),  # Diagonal \
            (1, -1),  # Diagonal /
        ]

        for dr, dc in directions:
            count = 1  # Include the stone at pos
            count += self.count_consecutive(pos, stone, (dr, dc)) - 1
            count += self.count_consecutive(pos, stone, (-dr, -dc)) - 1

            if count >= 5:
                return True

        return False

    def get_winning_line(self, pos: Position, stone: Stone) -> List[Position]:
        """Get the winning line of five stones."""
        directions = [
            (0, 1),  # Horizontal
            (1, 0),  # Vertical
            (1, 1),  # Diagonal \
            (1, -1),  # Diagonal /
        ]

        for dr, dc in directions:
            line = [pos]

            # Forward direction
            r, c = pos.row + dr, pos.col + dc
            while 0 <= r < self.size and 0 <= c < self.size:
                if self._grid[r][c] == stone:
                    line.append(Position(r, c))
                    r += dr
                    c += dc
                else:
                    break

            # Backward direction
            r, c = pos.row - dr, pos.col - dc
            while 0 <= r < self.size and 0 <= c < self.size:
                if self._grid[r][c] == stone:
                    line.insert(0, Position(r, c))
                    r -= dr
                    c -= dc
                else:
                    break

            if len(line) >= 5:
                return line[:5]

        return []

    def is_full(self) -> bool:
        """Check if board is full."""
        for row in range(self.size):
            for col in range(self.size):
                if self._grid[row][col] == Stone.EMPTY:
                    return False
        return True

    def to_string(self) -> str:
        """Convert board to string representation."""
        lines = []

        # Column headers
        header = "   " + " ".join(chr(ord("A") + i) for i in range(self.size))
        lines.append(header)

        # Board rows
        for row in range(self.size):
            row_str = f"{row + 1:2d} " + " ".join(
                str(self._grid[row][col]) for col in range(self.size)
            )
            lines.append(row_str)

        return "\n".join(lines)

    def to_dict(self) -> List[List[int]]:
        """Convert board to 2D list."""
        return [
            [self._grid[row][col].value for col in range(self.size)] for row in range(self.size)
        ]

    @classmethod
    def from_dict(cls, data: List[List[int]]) -> "Board":
        """Create board from 2D list."""
        size = len(data)
        board = cls(size)
        for row in range(size):
            for col in range(size):
                board._grid[row][col] = Stone(data[row][col])
        return board


class Game:
    """
    Gomoku game state machine.

    Manages game flow, players, and rules.
    """

    def __init__(
        self,
        board_size: int = 15,
        rule_mode: RuleMode = RuleMode.FREE_STYLE,
        black_player: Optional[Player] = None,
        white_player: Optional[Player] = None,
    ):
        self.board = Board(board_size)
        self.rule_mode = rule_mode
        self.board_size = board_size

        # Default players
        self.black_player = black_player or Player(Stone.BLACK, PlayerType.HUMAN)
        self.white_player = white_player or Player(Stone.WHITE, PlayerType.HUMAN)

        self.moves: List[Move] = []
        self.state = GameState.PLAYING
        self.current_stone = Stone.BLACK
        self.winner: Optional[Stone] = None
        self.winning_line: List[Position] = []
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None

    @property
    def current_player(self) -> Player:
        """Get current player."""
        return self.black_player if self.current_stone == Stone.BLACK else self.white_player

    def is_valid_move(self, pos: Position) -> bool:
        """Check if move is valid."""
        if self.state != GameState.PLAYING:
            return False
        if not self.board.is_valid_position(pos):
            return False
        if not self.board.is_empty(pos):
            return False

        # Check forbidden moves for Renju rules
        if self.rule_mode == RuleMode.RENJU and self.current_stone == Stone.BLACK:
            if self._is_forbidden_move(pos):
                return False

        return True

    def _is_forbidden_move(self, pos: Position) -> bool:
        """Check if move is forbidden in Renju rules (for black only)."""
        # Renju rules:
        # 1. Double-three: two open threes at once
        # 2. Double-four: two fours at once
        # 3. Overline: six or more in a row

        # Temporarily place the stone
        self.board.set(pos, Stone.BLACK)

        # Check overline
        if self._count_max_line(pos, Stone.BLACK) >= 6:
            self.board.set(pos, Stone.EMPTY)
            return True

        # Count open threes and fours
        open_threes = self._count_pattern(pos, Stone.BLACK, "open_three")
        fours = self._count_pattern(pos, Stone.BLACK, "four")

        self.board.set(pos, Stone.EMPTY)

        if open_threes >= 2 or fours >= 2:
            return True

        return False

    def _count_max_line(self, pos: Position, stone: Stone) -> int:
        """Count maximum consecutive stones through position."""
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        max_count = 0

        for dr, dc in directions:
            count = 1
            count += self.board.count_consecutive(pos, stone, (dr, dc)) - 1
            count += self.board.count_consecutive(pos, stone, (-dr, -dc)) - 1
            max_count = max(max_count, count)

        return max_count

    def _count_pattern(self, pos: Position, stone: Stone, pattern: str) -> int:
        """Count pattern occurrences through position."""
        # Simplified pattern counting
        # TODO: Implement proper pattern detection
        return 0

    def make_move(self, pos: Position, thinking_time_ms: int = 0) -> Tuple[bool, str]:
        """
        Make a move on the board.

        Returns (success, message).
        """
        if self.state != GameState.PLAYING:
            return False, "Game is not in progress"

        if not self.is_valid_move(pos):
            return False, "Invalid move"

        # Place stone
        self.board.place_stone(pos, self.current_stone)

        # Record move
        move = Move(pos, self.current_stone, datetime.now(), thinking_time_ms)
        self.moves.append(move)

        # Check win
        if self.board.check_five_in_row(pos, self.current_stone):
            self.state = (
                GameState.BLACK_WIN if self.current_stone == Stone.BLACK else GameState.WHITE_WIN
            )
            self.winner = self.current_stone
            self.winning_line = self.board.get_winning_line(pos, self.current_stone)
            self.end_time = datetime.now()
            return True, f"{self.current_stone.name} wins!"

        # Check draw
        if self.board.is_full():
            self.state = GameState.DRAW
            self.end_time = datetime.now()
            return True, "Draw!"

        # Switch turn
        self.current_stone = self.current_stone.opponent()
        return True, "Move successful"

    def undo_move(self) -> bool:
        """Undo the last move."""
        if not self.moves:
            return False

        last_move = self.moves.pop()
        self.board.remove_stone(last_move.position)
        self.current_stone = last_move.stone
        self.state = GameState.PLAYING
        self.winner = None
        self.winning_line = []
        self.end_time = None

        return True

    def get_game_state(self) -> Dict[str, Any]:
        """Get current game state as dictionary."""
        return {
            "board_size": self.board_size,
            "rule_mode": self.rule_mode.value,
            "state": self.state.value,
            "current_stone": self.current_stone.name,
            "current_player": self.current_player.to_dict(),
            "moves": [m.to_dict() for m in self.moves],
            "winner": self.winner.name if self.winner else None,
            "winning_line": [p.to_notation() for p in self.winning_line],
            "board": self.board.to_dict(),
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "black_player": self.black_player.to_dict(),
            "white_player": self.white_player.to_dict(),
        }

    def copy(self) -> "Game":
        """Create a deep copy of the game."""
        new_game = Game(
            board_size=self.board_size,
            rule_mode=self.rule_mode,
            black_player=copy.deepcopy(self.black_player),
            white_player=copy.deepcopy(self.white_player),
        )
        new_game.board = self.board.copy()
        new_game.moves = self.moves[:]
        new_game.state = self.state
        new_game.current_stone = self.current_stone
        new_game.winner = self.winner
        new_game.winning_line = self.winning_line[:]
        new_game.start_time = self.start_time
        new_game.end_time = self.end_time
        return new_game

    def to_dict(self) -> Dict[str, Any]:
        """Convert game to dictionary for serialization."""
        return {
            "version": "1.0",
            "board_size": self.board_size,
            "rule_mode": self.rule_mode.value,
            "state": self.state.value,
            "moves": [m.to_dict() for m in self.moves],
            "winner": self.winner.name if self.winner else None,
            "winning_line": [p.to_notation() for p in self.winning_line],
            "board": self.board.to_dict(),
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "black_player": self.black_player.to_dict(),
            "white_player": self.white_player.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Game":
        """Create game from dictionary."""
        game = cls(
            board_size=data["board_size"],
            rule_mode=RuleMode(data["rule_mode"]),
        )

        # Restore board
        game.board = Board.from_dict(data["board"])

        # Restore moves
        for move_data in data["moves"]:
            pos = Position.from_notation(move_data["position"], game.board_size)
            move = Move(
                position=pos,
                stone=Stone[move_data["stone"]],
                timestamp=datetime.fromisoformat(move_data["timestamp"]),
                thinking_time_ms=move_data.get("thinking_time_ms", 0),
            )
            game.moves.append(move)

        # Restore state
        game.state = GameState(data["state"])
        game.winner = Stone[data["winner"]] if data.get("winner") else None
        game.winning_line = [
            Position.from_notation(p, game.board_size) for p in data.get("winning_line", [])
        ]
        game.current_stone = Stone.BLACK if len(game.moves) % 2 == 0 else Stone.WHITE
        game.start_time = datetime.fromisoformat(data["start_time"])
        game.end_time = datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None

        return game


def check_win(board: Board, pos: Position, stone: Stone) -> bool:
    """Standalone function to check win condition."""
    return board.check_five_in_row(pos, stone)


def get_all_empty_positions(board: Board) -> List[Position]:
    """Get all empty positions on the board."""
    return board.get_empty_positions()


def get_candidate_moves(board: Board, distance: int = 2) -> List[Position]:
    """Get candidate moves near existing stones."""
    return board.get_candidate_moves(distance)
