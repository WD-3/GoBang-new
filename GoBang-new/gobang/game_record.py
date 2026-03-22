"""
Game recording and replay functionality.
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import json
import os

from gobang.core import Game, Position, Stone, GameState, RuleMode


@dataclass
class GameRecord:
    """
    Complete record of a Gomoku game.

    Supports saving, loading, and replaying games.
    """

    game_id: str
    board_size: int = 15
    rule_mode: RuleMode = RuleMode.FREE_STYLE
    black_player: Dict[str, Any] = field(default_factory=dict)
    white_player: Dict[str, Any] = field(default_factory=dict)
    moves: List[Dict[str, Any]] = field(default_factory=list)
    result: Optional[str] = None
    winner: Optional[str] = None
    winning_line: List[str] = field(default_factory=list)
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_move(
        self,
        position: str,
        stone: str,
        thinking_time_ms: int = 0,
        llm_response: str = "",
    ) -> None:
        """Add a move to the record."""
        move = {
            "num": len(self.moves) + 1,
            "position": position,
            "stone": stone,
            "thinking_time_ms": thinking_time_ms,
            "timestamp": datetime.now().isoformat(),
        }
        if llm_response:
            move["llm_response"] = llm_response
        self.moves.append(move)

    def set_result(
        self,
        winner: Optional[str],
        reason: str,
        winning_line: List[str] = None,
    ) -> None:
        """Set game result."""
        self.winner = winner
        self.result = reason
        self.winning_line = winning_line or []
        self.end_time = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "version": "1.0",
            "game_id": self.game_id,
            "board_size": self.board_size,
            "rule_mode": self.rule_mode.value,
            "black_player": self.black_player,
            "white_player": self.white_player,
            "moves": self.moves,
            "result": self.result,
            "winner": self.winner,
            "winning_line": self.winning_line,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GameRecord":
        """Create from dictionary."""
        return cls(
            game_id=data.get("game_id", ""),
            board_size=data.get("board_size", 15),
            rule_mode=RuleMode(data.get("rule_mode", "free_style")),
            black_player=data.get("black_player", {}),
            white_player=data.get("white_player", {}),
            moves=data.get("moves", []),
            result=data.get("result"),
            winner=data.get("winner"),
            winning_line=data.get("winning_line", []),
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
            metadata=data.get("metadata", {}),
        )

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "GameRecord":
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def save(self, filepath: str) -> None:
        """Save record to file."""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, filepath: str) -> "GameRecord":
        """Load record from file."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    @classmethod
    def from_game(cls, game: Game, game_id: Optional[str] = None) -> "GameRecord":
        """Create record from Game object."""
        record = cls(
            game_id=game_id or f"game_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            board_size=game.board_size,
            rule_mode=game.rule_mode,
            black_player=game.black_player.to_dict(),
            white_player=game.white_player.to_dict(),
            start_time=game.start_time.isoformat(),
        )

        for move in game.moves:
            record.add_move(
                position=move.position.to_notation(),
                stone=move.stone.name,
                thinking_time_ms=move.thinking_time_ms,
            )

        if game.winner:
            record.set_result(
                winner=game.winner.name,
                reason=game.state.value,
                winning_line=[p.to_notation() for p in game.winning_line],
            )
        elif game.state == GameState.DRAW:
            record.set_result(winner=None, reason="draw")

        record.end_time = game.end_time.isoformat() if game.end_time else None

        return record

    def to_game(self) -> Game:
        """Convert record back to Game object."""
        game = Game(
            board_size=self.board_size,
            rule_mode=self.rule_mode,
        )

        for move_data in self.moves:
            pos = Position.from_notation(move_data["position"], self.board_size)
            stone = Stone[move_data["stone"]]
            game.make_move(pos)

        return game


class GameReplayer:
    """
    Replay controller for game records.

    Allows stepping through moves forward and backward.
    """

    def __init__(self, record: GameRecord):
        self.record = record
        self.current_move_index = -1
        self._game = Game(board_size=record.board_size, rule_mode=record.rule_mode)

    @property
    def game(self) -> Game:
        """Get current game state."""
        return self._game

    @property
    def total_moves(self) -> int:
        """Get total number of moves."""
        return len(self.record.moves)

    @property
    def current_move_number(self) -> int:
        """Get current move number (1-indexed, 0 if at start)."""
        return self.current_move_index + 1

    @property
    def is_at_start(self) -> bool:
        """Check if at the start of the game."""
        return self.current_move_index < 0

    @property
    def is_at_end(self) -> bool:
        """Check if at the end of the game."""
        return self.current_move_index >= self.total_moves - 1

    def reset(self) -> None:
        """Reset to the start of the game."""
        self.current_move_index = -1
        self._game = Game(board_size=self.record.board_size, rule_mode=self.record.rule_mode)

    def go_to_start(self) -> None:
        """Go to the start of the game."""
        self.reset()

    def go_to_end(self) -> None:
        """Go to the end of the game."""
        while self.next_move():
            pass

    def next_move(self) -> bool:
        """
        Go to the next move.

        Returns True if successful, False if at end.
        """
        if self.is_at_end:
            return False

        self.current_move_index += 1
        move_data = self.record.moves[self.current_move_index]

        pos = Position.from_notation(move_data["position"], self.record.board_size)
        self._game.make_move(pos)

        return True

    def previous_move(self) -> bool:
        """
        Go to the previous move.

        Returns True if successful, False if at start.
        """
        if self.is_at_start:
            return False

        self._game.undo_move()
        self.current_move_index -= 1

        return True

    def go_to_move(self, move_number: int) -> bool:
        """
        Go to a specific move number (1-indexed).

        Returns True if successful, False if invalid move number.
        """
        if move_number < 0 or move_number > self.total_moves:
            return False

        # Go back to start then forward
        self.reset()
        for _ in range(move_number):
            if not self.next_move():
                return False

        return True

    def get_move_info(self, move_number: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Get information about a move."""
        if move_number is None:
            move_number = self.current_move_number

        if move_number < 1 or move_number > self.total_moves:
            return None

        return self.record.moves[move_number - 1]


def save_game_to_file(game: Game, filepath: str, game_id: Optional[str] = None) -> None:
    """Save a game to a file."""
    record = GameRecord.from_game(game, game_id)
    record.save(filepath)


def load_game_from_file(filepath: str) -> Game:
    """Load a game from a file."""
    record = GameRecord.load(filepath)
    return record.to_game()


def list_saved_games(directory: str = ".") -> List[str]:
    """List saved game files in a directory."""
    games = []
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            try:
                filepath = os.path.join(directory, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "moves" in data and "board_size" in data:
                        games.append(filepath)
            except (json.JSONDecodeError, IOError):
                continue
    return games


__all__ = [
    "GameRecord",
    "GameReplayer",
    "save_game_to_file",
    "load_game_from_file",
    "list_saved_games",
]
