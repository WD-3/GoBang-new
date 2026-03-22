"""
Tests for gobang.game_record module.
"""

import pytest
import tempfile
import os
from gobang.core import Game, Stone, Position, RuleMode
from gobang.game_record import GameRecord, GameReplayer, save_game_to_file, load_game_from_file


class TestGameRecord:
    def test_record_creation(self):
        record = GameRecord(game_id="test_game")

        assert record.game_id == "test_game"
        assert record.board_size == 15
        assert len(record.moves) == 0

    def test_add_move(self):
        record = GameRecord(game_id="test")
        record.add_move("H8", "BLACK", 100)

        assert len(record.moves) == 1
        assert record.moves[0]["position"] == "H8"
        assert record.moves[0]["thinking_time_ms"] == 100

    def test_set_result(self):
        record = GameRecord(game_id="test")
        record.set_result("BLACK", "five_in_a_row", ["E5", "F5", "G5", "H5", "I5"])

        assert record.winner == "BLACK"
        assert record.result == "five_in_a_row"
        assert len(record.winning_line) == 5

    def test_to_dict_and_from_dict(self):
        record = GameRecord(
            game_id="test",
            board_size=15,
            rule_mode=RuleMode.STANDARD,
        )
        record.add_move("H8", "BLACK")
        record.add_move("H9", "WHITE")
        record.set_result("BLACK", "five_in_a_row")

        data = record.to_dict()
        record2 = GameRecord.from_dict(data)

        assert record2.game_id == "test"
        assert len(record2.moves) == 2
        assert record2.winner == "BLACK"

    def test_to_json_and_from_json(self):
        record = GameRecord(game_id="json_test")
        record.add_move("H8", "BLACK")

        json_str = record.to_json()
        record2 = GameRecord.from_json(json_str)

        assert record2.game_id == "json_test"
        assert len(record2.moves) == 1

    def test_save_and_load_file(self):
        record = GameRecord(game_id="file_test")
        record.add_move("H8", "BLACK")
        record.set_result("BLACK", "win")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            filepath = f.name

        try:
            record.save(filepath)
            record2 = GameRecord.load(filepath)

            assert record2.game_id == "file_test"
            assert len(record2.moves) == 1
        finally:
            os.unlink(filepath)

    def test_from_game(self):
        game = Game()
        game.make_move(Position(7, 7))
        game.make_move(Position(8, 8))

        record = GameRecord.from_game(game, "from_game_test")

        assert record.board_size == 15
        assert len(record.moves) == 2

    def test_to_game(self):
        record = GameRecord(
            game_id="to_game",
            board_size=15,
            rule_mode=RuleMode.FREE_STYLE,
        )
        record.add_move("H8", "BLACK")
        record.add_move("H9", "WHITE")

        game = record.to_game()

        assert game.board_size == 15
        assert len(game.moves) == 2


class TestGameReplayer:
    def test_replayer_creation(self):
        record = GameRecord(game_id="replay_test")
        record.add_move("H8", "BLACK")
        record.add_move("H9", "WHITE")
        record.add_move("I8", "BLACK")

        replayer = GameReplayer(record)

        assert replayer.total_moves == 3
        assert replayer.is_at_start
        assert not replayer.is_at_end

    def test_next_move(self):
        record = GameRecord(game_id="test")
        record.add_move("H8", "BLACK")
        record.add_move("H9", "WHITE")

        replayer = GameReplayer(record)

        assert replayer.next_move()
        assert replayer.current_move_number == 1
        assert replayer.game.board.get(Position(7, 7)) == Stone.BLACK

        assert replayer.next_move()
        assert replayer.current_move_number == 2
        assert replayer.is_at_end

    def test_previous_move(self):
        record = GameRecord(game_id="test")
        record.add_move("H8", "BLACK")

        replayer = GameReplayer(record)
        replayer.go_to_end()

        assert replayer.previous_move()
        assert replayer.is_at_start

    def test_go_to_move(self):
        record = GameRecord(game_id="test")
        for i in range(5):
            record.add_move(f"{chr(65 + i)}8", "BLACK" if i % 2 == 0 else "WHITE")

        replayer = GameReplayer(record)

        assert replayer.go_to_move(3)
        assert replayer.current_move_number == 3

    def test_go_to_start_and_end(self):
        record = GameRecord(game_id="test")
        record.add_move("H8", "BLACK")
        record.add_move("H9", "WHITE")

        replayer = GameReplayer(record)
        replayer.go_to_end()

        assert replayer.is_at_end

        replayer.go_to_start()

        assert replayer.is_at_start


class TestSaveLoadFunctions:
    def test_save_game_to_file(self):
        game = Game()
        game.make_move(Position(7, 7))

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            filepath = f.name

        try:
            save_game_to_file(game, filepath)
            assert os.path.exists(filepath)
        finally:
            os.unlink(filepath)

    def test_load_game_from_file(self):
        game = Game()
        game.make_move(Position(7, 7))
        game.make_move(Position(8, 8))

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            filepath = f.name

        try:
            save_game_to_file(game, filepath)
            game2 = load_game_from_file(filepath)

            assert len(game2.moves) == 2
        finally:
            os.unlink(filepath)
