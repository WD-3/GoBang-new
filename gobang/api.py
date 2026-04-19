"""
Unified API for GoBang game operations.

This module provides a clean API with ToolResult pattern for all game operations.
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from gobang.core import Board, Game, Player, PlayerType, Stone, GameState, RuleMode, Position, Move


@dataclass
class ToolResult:
    """
    Standard result type for all API operations.

    Attributes:
        success: Whether the operation succeeded
        data: Result data if successful
        error: Error message if failed
        metadata: Additional metadata
    """

    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
        }

    @classmethod
    def ok(cls, data: Any = None, **metadata) -> "ToolResult":
        """Create successful result."""
        return cls(success=True, data=data, metadata=metadata)

    @classmethod
    def fail(cls, error: str, **metadata) -> "ToolResult":
        """Create failed result."""
        return cls(success=False, error=error, metadata=metadata)


# Global game storage (for simple use cases)
_games: Dict[str, Game] = {}


def create_game(
    game_id: str,
    board_size: int = 15,
    rule_mode: str = "free_style",
    black_player: Optional[Dict[str, Any]] = None,
    white_player: Optional[Dict[str, Any]] = None,
) -> ToolResult:
    """
    Create a new game.

    Args:
        game_id: Unique game identifier
        board_size: Size of the board (default 15)
        rule_mode: Game rule mode (free_style, standard, renju)
        black_player: Black player configuration
        white_player: White player configuration

    Returns:
        ToolResult with game data
    """
    try:
        # Parse rule mode
        mode = RuleMode(rule_mode)
    except ValueError:
        return ToolResult.fail(f"Invalid rule mode: {rule_mode}")

    # Create players
    black = _create_player(Stone.BLACK, black_player)
    white = _create_player(Stone.WHITE, white_player)

    # Create game
    game = Game(
        board_size=board_size,
        rule_mode=mode,
        black_player=black,
        white_player=white,
    )

    _games[game_id] = game

    return ToolResult.ok(
        data=game.get_game_state(),
        game_id=game_id,
    )


def _create_player(stone: Stone, config: Optional[Dict[str, Any]] = None) -> Player:
    """Create a player from configuration."""
    if config is None:
        return Player(stone, PlayerType.HUMAN)

    player_type = PlayerType(config.get("type", "human"))
    name = config.get("name", "")
    extra_config = {k: v for k, v in config.items() if k not in ("type", "name")}

    return Player(stone, player_type, name, extra_config)


def get_game(game_id: str) -> Optional[Game]:
    """Get game by ID."""
    return _games.get(game_id)


def make_move(
    game_id: str,
    position: str,
    thinking_time_ms: int = 0,
) -> ToolResult:
    """
    Make a move in the game.

    Args:
        game_id: Game identifier
        position: Position in algebraic notation (e.g., "H8")
        thinking_time_ms: Thinking time in milliseconds

    Returns:
        ToolResult with updated game state
    """
    game = _games.get(game_id)
    if game is None:
        return ToolResult.fail(f"Game not found: {game_id}")

    try:
        pos = Position.from_notation(position, game.board_size)
    except ValueError as e:
        return ToolResult.fail(f"Invalid position: {position} - {e}")

    success, message = game.make_move(pos, thinking_time_ms)

    if not success:
        return ToolResult.fail(message)

    return ToolResult.ok(
        data=game.get_game_state(),
        message=message,
    )


def get_game_state(game_id: str) -> ToolResult:
    """
    Get current game state.

    Args:
        game_id: Game identifier

    Returns:
        ToolResult with game state
    """
    game = _games.get(game_id)
    if game is None:
        return ToolResult.fail(f"Game not found: {game_id}")

    return ToolResult.ok(data=game.get_game_state())


def undo_move(game_id: str) -> ToolResult:
    """
    Undo the last move.

    Args:
        game_id: Game identifier

    Returns:
        ToolResult with updated game state
    """
    game = _games.get(game_id)
    if game is None:
        return ToolResult.fail(f"Game not found: {game_id}")

    if not game.undo_move():
        return ToolResult.fail("No moves to undo")

    return ToolResult.ok(data=game.get_game_state())


def get_valid_moves(game_id: str) -> ToolResult:
    """
    Get all valid moves for the current position.

    Args:
        game_id: Game identifier

    Returns:
        ToolResult with list of valid positions
    """
    game = _games.get(game_id)
    if game is None:
        return ToolResult.fail(f"Game not found: {game_id}")

    if game.state != GameState.PLAYING:
        return ToolResult.ok(data=[])

    # Get candidate moves
    candidates = game.board.get_candidate_moves()

    # Filter valid moves
    valid_moves = [pos.to_notation() for pos in candidates if game.is_valid_move(pos)]

    return ToolResult.ok(data=valid_moves)


def delete_game(game_id: str) -> ToolResult:
    """
    Delete a game.

    Args:
        game_id: Game identifier

    Returns:
        ToolResult indicating success
    """
    if game_id not in _games:
        return ToolResult.fail(f"Game not found: {game_id}")

    del _games[game_id]
    return ToolResult.ok(message=f"Game {game_id} deleted")


def list_games() -> ToolResult:
    """
    List all games.

    Returns:
        ToolResult with list of game IDs and states
    """
    games = {game_id: game.state.value for game_id, game in _games.items()}
    return ToolResult.ok(data=games)


def save_game(game_id: str) -> ToolResult:
    """
    Save game to dictionary for serialization.

    Args:
        game_id: Game identifier

    Returns:
        ToolResult with game data
    """
    game = _games.get(game_id)
    if game is None:
        return ToolResult.fail(f"Game not found: {game_id}")

    return ToolResult.ok(data=game.to_dict())


def load_game(game_id: str, data: Dict[str, Any]) -> ToolResult:
    """
    Load game from dictionary.

    Args:
        game_id: Game identifier
        data: Game data dictionary

    Returns:
        ToolResult with game state
    """
    try:
        game = Game.from_dict(data)
        _games[game_id] = game
        return ToolResult.ok(data=game.get_game_state())
    except Exception as e:
        return ToolResult.fail(f"Failed to load game: {e}")


def get_board_string(game_id: str) -> ToolResult:
    """
    Get board as string representation.

    Args:
        game_id: Game identifier

    Returns:
        ToolResult with board string
    """
    game = _games.get(game_id)
    if game is None:
        return ToolResult.fail(f"Game not found: {game_id}")

    return ToolResult.ok(data=game.board.to_string())


def ai_suggest_move(game_id: str, depth: int = 3) -> ToolResult:
    """
    Get AI suggested move (using minimax).

    Args:
        game_id: Game identifier
        depth: Search depth

    Returns:
        ToolResult with suggested position
    """
    game = _games.get(game_id)
    if game is None:
        return ToolResult.fail(f"Game not found: {game_id}")

    if game.state != GameState.PLAYING:
        return ToolResult.fail("Game is not in progress")

    # Import AI module
    try:
        from gobang.ai import MinimaxAI

        ai = MinimaxAI(depth=depth)
        pos = ai.get_best_move(game)
        return ToolResult.ok(data=pos.to_notation())
    except Exception as e:
        return ToolResult.fail(f"AI error: {e}")


# Export all public functions
__all__ = [
    "ToolResult",
    "create_game",
    "get_game",
    "make_move",
    "get_game_state",
    "undo_move",
    "get_valid_moves",
    "delete_game",
    "list_games",
    "save_game",
    "load_game",
    "get_board_string",
    "ai_suggest_move",
]
