"""
GoBang AI - Gomoku (Five-in-a-Row) game with AI and LLM players.

This package provides a complete implementation of Gomoku (五子棋) with:
- Pattern-based rule engine (VCF, VCT, forbidden moves)
- Traditional AI players (Minimax, Alpha-Beta, MCTS)
- LLM players (Ollama, OpenAI-compatible APIs)
- Multiple interfaces (CLI, GUI, Web)
- Game recording and replay

References:
[1] Allis, L.V. (1994). "Searching for Solutions in Games and AI"
[2] Renju International Federation. "Renju Rules" https://renju.net
"""

__version__ = "1.1.0"
__author__ = "CodeOfMe"
__license__ = "GPLv3"

from gobang.core import Board, Game, Player, PlayerType, Stone, GameState, RuleMode, Position, Move
from gobang.api import ToolResult, create_game, make_move, get_game_state
from gobang.pattern_engine import (
    PatternType,
    PatternMatch,
    PatternEngine,
    ForbiddenDetector,
    VCFEngine,
    VCTEngine,
    evaluate_position,
    get_best_move_rule_based,
)

__all__ = [
    "__version__",
    "__author__",
    "__license__",
    "Board",
    "Game",
    "Player",
    "PlayerType",
    "Stone",
    "GameState",
    "RuleMode",
    "ToolResult",
    "create_game",
    "make_move",
    "get_game_state",
    "PatternType",
    "PatternMatch",
    "PatternEngine",
    "ForbiddenDetector",
    "VCFEngine",
    "VCTEngine",
    "evaluate_position",
    "get_best_move_rule_based",
]
