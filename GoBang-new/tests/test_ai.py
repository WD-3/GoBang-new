"""
Tests for gobang.ai module.
"""

import pytest
from gobang.core import Game, Stone, Position, GameState, Player, PlayerType
from gobang.ai import MinimaxAI, MCTSAI, create_ai


class TestMinimaxAI:
    def test_ai_creation(self):
        ai = MinimaxAI(depth=3)
        assert ai.depth == 3

    def test_ai_get_best_move(self):
        game = Game()
        ai = MinimaxAI(depth=2)

        move = ai.get_best_move(game)
        assert move is not None
        assert game.is_valid_move(move)

    def test_ai_winning_move(self):
        game = Game()

        for i in range(4):
            game.make_move(Position(7, 5 + i))
            if i < 3:
                game.make_move(Position(0, i))

        ai = MinimaxAI(depth=2)
        move = ai.get_best_move(game)

        assert move in [Position(7, 4), Position(7, 9)]

    def test_ai_blocks_opponent(self):
        game = Game()

        game.make_move(Position(7, 7))
        for i in range(4):
            game.make_move(Position(5 + i, 5 + i))
            if i < 3:
                game.make_move(Position(0, i))

        ai = MinimaxAI(depth=2)
        game.current_stone = Stone.WHITE
        move = ai.get_best_move(game)

        assert move is not None
        assert game.is_valid_move(move)


class TestMCTSAI:
    def test_mcts_creation(self):
        ai = MCTSAI(iterations=100)
        assert ai.iterations == 100

    def test_mcts_get_best_move(self):
        game = Game()
        ai = MCTSAI(iterations=50, time_limit=2.0)

        move = ai.get_best_move(game)
        assert move is not None
        assert game.is_valid_move(move)


class TestCreateAI:
    def test_create_minimax(self):
        ai = create_ai("minimax", depth=3)
        assert isinstance(ai, MinimaxAI)

    def test_create_mcts(self):
        ai = create_ai("mcts", iterations=100)
        assert isinstance(ai, MCTSAI)

    def test_create_unknown(self):
        with pytest.raises(ValueError):
            create_ai("unknown")
