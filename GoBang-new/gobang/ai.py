"""
AI players for Gomoku using traditional algorithms.

This module provides:
- MinimaxAI: Minimax with Alpha-Beta pruning
- MCTSAI: Monte Carlo Tree Search
"""

from typing import Optional, List, Tuple
from abc import ABC, abstractmethod
import time
import random
import math

from gobang.core import Board, Game, Stone, Position, GameState


class AIPlayer(ABC):
    """Base class for AI players."""

    @abstractmethod
    def get_best_move(self, game: Game) -> Position:
        """Get the best move for the current position."""
        pass


class MinimaxAI(AIPlayer):
    """
    Minimax AI with Alpha-Beta pruning.

    Uses evaluation function based on:
    - Threats (open fours, open threes)
    - Pattern recognition
    - Positional scores
    """

    def __init__(self, depth: int = 3, time_limit: float = 5.0):
        self.depth = depth
        self.time_limit = time_limit
        self.nodes_evaluated = 0

    def get_best_move(self, game: Game) -> Position:
        """Get the best move using minimax with alpha-beta pruning."""
        self.nodes_evaluated = 0
        start_time = time.time()

        candidates = game.board.get_candidate_moves(distance=2)
        if not candidates:
            return Position(game.board_size // 2, game.board_size // 2)

        best_move = candidates[0]
        best_score = float("-inf")
        alpha = float("-inf")
        beta = float("inf")

        # Sort candidates by simple heuristic for better pruning
        candidates = self._sort_moves(game, candidates)

        for move in candidates:
            if time.time() - start_time > self.time_limit:
                break

            # Make move
            new_game = game.copy()
            new_game.make_move(move)

            # Evaluate
            score = -self._minimax(new_game, self.depth - 1, -beta, -alpha, start_time)

            if score > best_score:
                best_score = score
                best_move = move

            alpha = max(alpha, score)

        return best_move

    def _minimax(
        self,
        game: Game,
        depth: int,
        alpha: float,
        beta: float,
        start_time: float,
    ) -> float:
        """Minimax with alpha-beta pruning."""
        self.nodes_evaluated += 1

        # Terminal conditions
        if game.state == GameState.BLACK_WIN:
            return 100000 if game.winner == game.current_stone else -100000
        if game.state == GameState.WHITE_WIN:
            return 100000 if game.winner == game.current_stone else -100000
        if game.state == GameState.DRAW:
            return 0
        if depth == 0:
            return self._evaluate(game)
        if time.time() - start_time > self.time_limit:
            return self._evaluate(game)

        candidates = game.board.get_candidate_moves(distance=2)
        if not candidates:
            return self._evaluate(game)

        # Sort moves for better pruning
        candidates = self._sort_moves(game, candidates)

        max_score = float("-inf")

        for move in candidates:
            new_game = game.copy()
            new_game.make_move(move)

            score = -self._minimax(new_game, depth - 1, -beta, -alpha, start_time)

            max_score = max(max_score, score)
            alpha = max(alpha, score)

            if alpha >= beta:
                break  # Beta cutoff

        return max_score

    def _evaluate(self, game: Game) -> float:
        """Evaluate the board position."""
        if game.state == GameState.BLACK_WIN:
            return 100000
        if game.state == GameState.WHITE_WIN:
            return -100000
        if game.state == GameState.DRAW:
            return 0

        score = 0
        stone = game.current_stone
        opponent = stone.opponent()

        # Evaluate patterns for both players
        score += (
            self._evaluate_patterns(game.board, stone) * 1.1
        )  # Slight advantage to current player
        score -= self._evaluate_patterns(game.board, opponent)

        # Positional score
        score += self._evaluate_positions(game.board, stone)
        score -= self._evaluate_positions(game.board, opponent)

        return score

    def _evaluate_patterns(self, board: Board, stone: Stone) -> float:
        """Evaluate patterns on the board."""
        score = 0

        patterns = self._count_patterns(board, stone)

        # Pattern scores
        score += patterns["five"] * 100000
        score += patterns["open_four"] * 10000
        score += patterns["four"] * 1000
        score += patterns["open_three"] * 1000
        score += patterns["three"] * 100
        score += patterns["open_two"] * 100
        score += patterns["two"] * 10

        return score

    def _count_patterns(self, board: Board, stone: Stone) -> dict:
        """Count various patterns on the board."""
        patterns = {
            "five": 0,
            "open_four": 0,
            "four": 0,
            "open_three": 0,
            "three": 0,
            "open_two": 0,
            "two": 0,
        }

        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]

        for row in range(board.size):
            for col in range(board.size):
                if board._grid[row][col] != stone:
                    continue

                pos = Position(row, col)

                for dr, dc in directions:
                    # Only count from the start of a pattern
                    prev_r, prev_c = row - dr, col - dc
                    if (
                        0 <= prev_r < board.size
                        and 0 <= prev_c < board.size
                        and board._grid[prev_r][prev_c] == stone
                    ):
                        continue

                    count, open_ends = self._count_line(board, pos, stone, (dr, dc))

                    if count >= 5:
                        patterns["five"] += 1
                    elif count == 4:
                        if open_ends == 2:
                            patterns["open_four"] += 1
                        elif open_ends == 1:
                            patterns["four"] += 1
                    elif count == 3:
                        if open_ends == 2:
                            patterns["open_three"] += 1
                        elif open_ends == 1:
                            patterns["three"] += 1
                    elif count == 2:
                        if open_ends == 2:
                            patterns["open_two"] += 1
                        elif open_ends == 1:
                            patterns["two"] += 1

        return patterns

    def _count_line(
        self,
        board: Board,
        start: Position,
        stone: Stone,
        direction: Tuple[int, int],
    ) -> Tuple[int, int]:
        """
        Count consecutive stones and open ends in a direction.

        Returns (count, open_ends).
        """
        dr, dc = direction
        count = 0
        r, c = start.row, start.col

        # Count stones
        while 0 <= r < board.size and 0 <= c < board.size:
            if board._grid[r][c] == stone:
                count += 1
                r += dr
                c += dc
            else:
                break

        # Check open ends
        open_ends = 0

        # Start end
        prev_r, prev_c = start.row - dr, start.col - dc
        if (
            0 <= prev_r < board.size
            and 0 <= prev_c < board.size
            and board._grid[prev_r][prev_c] == Stone.EMPTY
        ):
            open_ends += 1

        # End end
        if 0 <= r < board.size and 0 <= c < board.size and board._grid[r][c] == Stone.EMPTY:
            open_ends += 1

        return count, open_ends

    def _evaluate_positions(self, board: Board, stone: Stone) -> float:
        """Evaluate positional advantage."""
        score = 0
        center = board.size // 2

        for row in range(board.size):
            for col in range(board.size):
                if board._grid[row][col] == stone:
                    # Prefer center positions
                    dist = abs(row - center) + abs(col - center)
                    score += max(0, board.size - dist)

        return score * 0.1

    def _sort_moves(self, game: Game, moves: List[Position]) -> List[Position]:
        """Sort moves by simple heuristic for better pruning."""

        def score_move(pos: Position) -> float:
            score = 0

            # Prefer center
            center = game.board_size // 2
            dist = abs(pos.row - center) + abs(pos.col - center)
            score -= dist * 0.1

            # Check for immediate win/loss
            test_game = game.copy()
            test_game.board.place_stone(pos, game.current_stone)
            if test_game.board.check_five_in_row(pos, game.current_stone):
                score += 10000

            # Check for blocking opponent
            test_game2 = game.copy()
            opponent = game.current_stone.opponent()
            test_game2.board.place_stone(pos, opponent)
            if test_game2.board.check_five_in_row(pos, opponent):
                score += 5000

            return score

        return sorted(moves, key=score_move, reverse=True)


class MCTSAI(AIPlayer):
    """
    Monte Carlo Tree Search AI.

    Uses UCT (Upper Confidence Bound for Trees) for selection.
    """

    def __init__(self, iterations: int = 1000, time_limit: float = 5.0):
        self.iterations = iterations
        self.time_limit = time_limit

    def get_best_move(self, game: Game) -> Position:
        """Get the best move using MCTS."""
        root = MCTSNode(game.copy())

        start_time = time.time()

        for _ in range(self.iterations):
            if time.time() - start_time > self.time_limit:
                break

            # Selection
            node = self._select(root)

            # Expansion
            if not node.is_terminal() and not node.is_fully_expanded():
                node = node.expand()

            # Simulation
            result = self._simulate(node.game.copy())

            # Backpropagation
            node.backpropagate(result)

        # Select best move by visit count
        if not root.children:
            candidates = game.board.get_candidate_moves()
            if candidates:
                return candidates[0]
            return Position(game.board_size // 2, game.board_size // 2)

        best_child = max(root.children, key=lambda c: c.visits)
        return best_child.move

    def _select(self, node: "MCTSNode") -> "MCTSNode":
        """Select node for expansion using UCT."""
        while not node.is_terminal() and node.is_fully_expanded():
            node = node.best_child_uct()
        return node

    def _simulate(self, game: Game) -> float:
        """Simulate random game to completion."""
        max_moves = game.board_size * game.board_size
        moves = 0

        while game.state == GameState.PLAYING and moves < max_moves:
            candidates = game.board.get_candidate_moves(distance=1)
            if not candidates:
                candidates = game.board.get_empty_positions()

            if not candidates:
                break

            move = random.choice(candidates)
            game.make_move(move)
            moves += 1

        if game.state == GameState.BLACK_WIN:
            return 1.0 if game.winner == Stone.BLACK else -1.0
        elif game.state == GameState.WHITE_WIN:
            return 1.0 if game.winner == Stone.WHITE else -1.0
        return 0.0


class MCTSNode:
    """Node in MCTS tree."""

    def __init__(
        self, game: Game, parent: Optional["MCTSNode"] = None, move: Optional[Position] = None
    ):
        self.game = game
        self.parent = parent
        self.move = move
        self.children: List["MCTSNode"] = []
        self.untried_moves: List[Position] = game.board.get_candidate_moves()
        self.wins = 0.0
        self.visits = 0

    def is_terminal(self) -> bool:
        """Check if node is terminal."""
        return self.game.state != GameState.PLAYING

    def is_fully_expanded(self) -> bool:
        """Check if all moves have been tried."""
        return len(self.untried_moves) == 0

    def expand(self) -> "MCTSNode":
        """Expand node by adding a child."""
        if not self.untried_moves:
            return self

        move = self.untried_moves.pop()
        new_game = self.game.copy()
        new_game.make_move(move)

        child = MCTSNode(new_game, self, move)
        self.children.append(child)
        return child

    def best_child_uct(self, c: float = 1.414) -> "MCTSNode":
        """Select best child using UCT."""

        def uct_value(child: "MCTSNode") -> float:
            if child.visits == 0:
                return float("inf")
            exploitation = child.wins / child.visits
            exploration = c * math.sqrt(math.log(self.visits) / child.visits)
            return exploitation + exploration

        return max(self.children, key=uct_value)

    def backpropagate(self, result: float) -> None:
        """Backpropagate result up the tree."""
        node: Optional["MCTSNode"] = self
        while node is not None:
            node.visits += 1
            # Result is from perspective of the player at this node
            if node.game.current_stone == Stone.BLACK:
                node.wins += result
            else:
                node.wins -= result
            node = node.parent


def create_ai(algorithm: str = "minimax", **kwargs) -> AIPlayer:
    """
    Create an AI player.

    Args:
        algorithm: AI algorithm ('minimax' or 'mcts')
        **kwargs: Algorithm-specific parameters

    Returns:
        AIPlayer instance
    """
    if algorithm == "minimax":
        depth = kwargs.get("depth", 3)
        time_limit = kwargs.get("time_limit", 5.0)
        return MinimaxAI(depth=depth, time_limit=time_limit)
    elif algorithm == "mcts":
        iterations = kwargs.get("iterations", 1000)
        time_limit = kwargs.get("time_limit", 5.0)
        return MCTSAI(iterations=iterations, time_limit=time_limit)
    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")


__all__ = [
    "AIPlayer",
    "MinimaxAI",
    "MCTSAI",
    "create_ai",
]
