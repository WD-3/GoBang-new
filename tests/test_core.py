"""
Tests for gobang.core module.
"""

import pytest
from gobang.core import Board, Game, Player, PlayerType, Stone, GameState, RuleMode, Position, Move


class TestPosition:
    def test_position_creation(self):
        pos = Position(7, 7)
        assert pos.row == 7
        assert pos.col == 7

    def test_position_invalid(self):
        with pytest.raises(ValueError):
            Position(-1, 0)
        with pytest.raises(ValueError):
            Position(0, -1)

    def test_position_notation(self):
        pos = Position(7, 7)
        assert pos.to_notation() == "H8"

        pos2 = Position.from_notation("H8")
        assert pos2.row == 7
        assert pos2.col == 7

    def test_position_notation_edge(self):
        pos = Position(0, 0)
        assert pos.to_notation() == "A1"

        pos2 = Position(14, 14)
        assert pos2.to_notation() == "O15"

    def test_position_hash_eq(self):
        pos1 = Position(5, 5)
        pos2 = Position(5, 5)
        pos3 = Position(5, 6)

        assert pos1 == pos2
        assert pos1 != pos3
        assert hash(pos1) == hash(pos2)


class TestBoard:
    def test_board_creation(self):
        board = Board(15)
        assert board.size == 15

        for row in range(15):
            for col in range(15):
                assert board.get(Position(row, col)) == Stone.EMPTY

    def test_board_invalid_size(self):
        with pytest.raises(ValueError):
            Board(4)

    def test_board_place_stone(self):
        board = Board(15)
        pos = Position(7, 7)

        assert board.place_stone(pos, Stone.BLACK)
        assert board.get(pos) == Stone.BLACK
        assert not board.is_empty(pos)

    def test_board_place_occupied(self):
        board = Board(15)
        pos = Position(7, 7)

        board.place_stone(pos, Stone.BLACK)
        assert not board.place_stone(pos, Stone.WHITE)
        assert board.get(pos) == Stone.BLACK

    def test_board_remove_stone(self):
        board = Board(15)
        pos = Position(7, 7)

        board.place_stone(pos, Stone.BLACK)
        board.remove_stone(pos)
        assert board.is_empty(pos)

    def test_board_copy(self):
        board1 = Board(15)
        board1.place_stone(Position(7, 7), Stone.BLACK)

        board2 = board1.copy()
        board2.place_stone(Position(8, 8), Stone.WHITE)

        assert board1.get(Position(8, 8)) == Stone.EMPTY
        assert board2.get(Position(8, 8)) == Stone.WHITE

    def test_board_candidate_moves(self):
        board = Board(15)

        candidates = board.get_candidate_moves()
        assert len(candidates) == 1
        assert candidates[0] == Position(7, 7)

        board.place_stone(Position(7, 7), Stone.BLACK)
        candidates = board.get_candidate_moves()
        assert len(candidates) > 1

    def test_board_five_in_row_horizontal(self):
        board = Board(15)
        for i in range(5):
            board.place_stone(Position(7, 7 + i), Stone.BLACK)

        assert board.check_five_in_row(Position(7, 7), Stone.BLACK)
        assert board.check_five_in_row(Position(7, 9), Stone.BLACK)

    def test_board_five_in_row_vertical(self):
        board = Board(15)
        for i in range(5):
            board.place_stone(Position(7 + i, 7), Stone.BLACK)

        assert board.check_five_in_row(Position(7, 7), Stone.BLACK)
        assert board.check_five_in_row(Position(9, 7), Stone.BLACK)

    def test_board_five_in_row_diagonal(self):
        board = Board(15)
        for i in range(5):
            board.place_stone(Position(7 + i, 7 + i), Stone.BLACK)

        assert board.check_five_in_row(Position(7, 7), Stone.BLACK)

    def test_board_no_five(self):
        board = Board(15)
        for i in range(4):
            board.place_stone(Position(7, 7 + i), Stone.BLACK)

        assert not board.check_five_in_row(Position(7, 7), Stone.BLACK)

    def test_board_full(self):
        board = Board(5)
        for row in range(5):
            for col in range(5):
                board.place_stone(Position(row, col), Stone.BLACK)

        assert board.is_full()

    def test_board_to_dict(self):
        board = Board(15)
        board.place_stone(Position(7, 7), Stone.BLACK)

        data = board.to_dict()
        assert data[7][7] == Stone.BLACK.value
        assert data[0][0] == Stone.EMPTY.value

    def test_board_from_dict(self):
        data = [[0] * 15 for _ in range(15)]
        data[7][7] = 1

        board = Board.from_dict(data)
        assert board.get(Position(7, 7)) == Stone.BLACK


class TestGame:
    def test_game_creation(self):
        game = Game()

        assert game.board_size == 15
        assert game.state == GameState.PLAYING
        assert game.current_stone == Stone.BLACK

    def test_game_make_move(self):
        game = Game()

        success, message = game.make_move(Position(7, 7))
        assert success
        assert len(game.moves) == 1
        assert game.current_stone == Stone.WHITE

    def test_game_invalid_move(self):
        game = Game()

        game.make_move(Position(7, 7))
        success, message = game.make_move(Position(7, 7))

        assert not success

    def test_game_undo(self):
        game = Game()

        game.make_move(Position(7, 7))
        game.make_move(Position(8, 8))

        assert game.undo_move()
        assert len(game.moves) == 1
        assert game.current_stone == Stone.WHITE

        assert game.undo_move()
        assert len(game.moves) == 0
        assert game.current_stone == Stone.BLACK

    def test_game_win_horizontal(self):
        game = Game()

        for i in range(5):
            game.make_move(Position(7, 5 + i))
            if i < 4:
                game.make_move(Position(0, i))

        assert game.state == GameState.BLACK_WIN
        assert game.winner == Stone.BLACK

    def test_game_win_vertical(self):
        game = Game()

        for i in range(5):
            game.make_move(Position(5 + i, 7))
            if i < 4:
                game.make_move(Position(0, i))

        assert game.state == GameState.BLACK_WIN

    def test_game_win_diagonal(self):
        game = Game()

        for i in range(5):
            game.make_move(Position(5 + i, 5 + i))
            if i < 4:
                game.make_move(Position(0, i))

        assert game.state == GameState.BLACK_WIN

    def test_game_draw(self):
        game = Game(board_size=5)

        for row in range(5):
            for col in range(5):
                stone = Stone.BLACK if (row + col) % 2 == 0 else Stone.WHITE
                result = game.make_move(Position(row, col))
                if not result[0]:
                    break

        if game.board.is_full() and game.state == GameState.PLAYING:
            assert game.state == GameState.DRAW

    def test_game_copy(self):
        game1 = Game()
        game1.make_move(Position(7, 7))

        game2 = game1.copy()
        game2.make_move(Position(8, 8))

        assert len(game1.moves) == 1
        assert len(game2.moves) == 2

    def test_game_to_dict(self):
        game = Game()
        game.make_move(Position(7, 7))

        data = game.to_dict()
        assert data["board_size"] == 15
        assert len(data["moves"]) == 1
        assert data["moves"][0]["position"] == "H8"

    def test_game_from_dict(self):
        game1 = Game()
        game1.make_move(Position(7, 7))
        game1.make_move(Position(8, 8))

        data = game1.to_dict()
        game2 = Game.from_dict(data)

        assert len(game2.moves) == 2
        assert game2.current_stone == Stone.BLACK


class TestPlayer:
    def test_player_creation(self):
        player = Player(Stone.BLACK, PlayerType.HUMAN)
        assert player.stone == Stone.BLACK
        assert player.player_type == PlayerType.HUMAN

    def test_player_with_name(self):
        player = Player(Stone.WHITE, PlayerType.AI, name="TestAI")
        assert player.name == "TestAI"

    def test_player_to_dict(self):
        player = Player(Stone.BLACK, PlayerType.AI, name="AI", config={"depth": 3})
        data = player.to_dict()

        assert data["stone"] == "BLACK"
        assert data["type"] == "ai"
        assert data["name"] == "AI"
        assert data["config"]["depth"] == 3


class TestStone:
    def test_stone_opponent(self):
        assert Stone.BLACK.opponent() == Stone.WHITE
        assert Stone.WHITE.opponent() == Stone.BLACK
        assert Stone.EMPTY.opponent() == Stone.EMPTY

    def test_stone_str(self):
        assert str(Stone.EMPTY) == "·"
        assert str(Stone.BLACK) == "●"
        assert str(Stone.WHITE) == "○"
