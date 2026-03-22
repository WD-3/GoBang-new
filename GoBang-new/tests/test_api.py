"""
Tests for gobang.api module.
"""

import pytest
from gobang.api import (
    ToolResult,
    create_game,
    make_move,
    get_game_state,
    undo_move,
    get_valid_moves,
    delete_game,
    list_games,
    save_game,
    load_game,
    get_board_string,
    ai_suggest_move,
    _games,
)
from gobang.core import Stone, GameState


class TestToolResult:
    def test_success_result(self):
        result = ToolResult.ok(data={"test": "data"}, key="value")

        assert result.success
        assert result.data == {"test": "data"}
        assert result.metadata["key"] == "value"
        assert result.error is None

    def test_fail_result(self):
        result = ToolResult.fail("Error message")

        assert not result.success
        assert result.error == "Error message"
        assert result.data is None

    def test_to_dict(self):
        result = ToolResult.ok(data="test")
        d = result.to_dict()

        assert d["success"]
        assert d["data"] == "test"


class TestGameAPI:
    def setup_method(self):
        _games.clear()

    def test_create_game(self):
        result = create_game("test_game")

        assert result.success
        assert "test_game" in _games

    def test_create_game_custom(self):
        result = create_game(
            "custom_game",
            board_size=13,
            rule_mode="standard",
            black_player={"type": "ai"},
            white_player={"type": "human"},
        )

        assert result.success
        game = _games["custom_game"]
        assert game.board_size == 13

    def test_create_game_invalid_rule(self):
        result = create_game("bad_game", rule_mode="invalid")

        assert not result.success
        assert "Invalid rule mode" in result.error

    def test_make_move(self):
        create_game("move_test")
        result = make_move("move_test", "H8")

        assert result.success

    def test_make_move_invalid_position(self):
        create_game("invalid_test")
        result = make_move("invalid_test", "Z99")

        assert not result.success

    def test_make_move_game_not_found(self):
        result = make_move("nonexistent", "H8")

        assert not result.success
        assert "not found" in result.error.lower()

    def test_get_game_state(self):
        create_game("state_test")
        result = get_game_state("state_test")

        assert result.success
        assert result.data["state"] == "playing"

    def test_get_game_state_not_found(self):
        result = get_game_state("nonexistent")

        assert not result.success

    def test_undo_move(self):
        create_game("undo_test")
        make_move("undo_test", "H8")

        result = undo_move("undo_test")
        assert result.success

        state = get_game_state("undo_test")
        assert len(state.data["moves"]) == 0

    def test_get_valid_moves(self):
        create_game("valid_test")
        result = get_valid_moves("valid_test")

        assert result.success
        assert len(result.data) > 0

    def test_delete_game(self):
        create_game("delete_test")
        result = delete_game("delete_test")

        assert result.success
        assert "delete_test" not in _games

    def test_list_games(self):
        create_game("game1")
        create_game("game2")

        result = list_games()

        assert result.success
        assert "game1" in result.data
        assert "game2" in result.data

    def test_save_and_load_game(self):
        create_game("save_test")
        make_move("save_test", "H8")
        make_move("save_test", "H9")

        save_result = save_game("save_test")
        assert save_result.success

        game_data = save_result.data

        delete_game("save_test")
        assert "save_test" not in _games

        load_result = load_game("save_test", game_data)
        assert load_result.success
        assert len(load_result.data["moves"]) == 2

    def test_get_board_string(self):
        create_game("board_test")
        result = get_board_string("board_test")

        assert result.success
        assert "A" in result.data  # Column header

    def test_ai_suggest_move(self):
        create_game("suggest_test")
        result = ai_suggest_move("suggest_test", depth=2)

        assert result.success
        assert result.data is not None
