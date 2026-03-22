"""
Tests for gobang.llm_player module.

Note: These tests mock the API calls since we don't want to require
an actual LLM service for testing.
"""

import pytest
from unittest.mock import Mock, patch
from gobang.core import Game, Stone, Position
from gobang.llm_player import (
    LLMPlayer,
    OllamaClient,
    OpenAICompatibleClient,
    create_llm_player,
    create_llm_player_from_spec,
    parse_llm_spec,
    list_local_ollama_models,
    check_ollama_available,
)


class TestParseLLMSpec:
    def test_simple_model(self):
        config = parse_llm_spec("llama3")
        assert config["model"] == "llama3"
        assert config["provider"] == "ollama"
        assert config["base_url"] == "http://localhost:11434"

    def test_model_with_local_url(self):
        config = parse_llm_spec("mistral@http://localhost:11434")
        assert config["model"] == "mistral"
        assert config["provider"] == "ollama"
        assert config["base_url"] == "http://localhost:11434"

    def test_model_with_remote_ollama(self):
        config = parse_llm_spec("llama3@http://192.168.1.100:11434")
        assert config["model"] == "llama3"
        assert config["provider"] == "ollama"
        assert config["base_url"] == "http://192.168.1.100:11434"

    def test_model_with_api_key(self):
        config = parse_llm_spec("gpt-4@https://api.openai.com/v1:sk-test123")
        assert config["model"] == "gpt-4"
        assert config["provider"] == "openai_compatible"
        assert "api.openai.com" in config["base_url"]
        assert config["api_key"] == "sk-test123"


class TestOllamaClient:
    def test_client_creation(self):
        client = OllamaClient(model="llama3")

        assert client.model == "llama3"
        assert client.base_url == "http://localhost:11434"

    def test_is_available_mock(self):
        client = OllamaClient()

        with patch.object(client, "_get_client") as mock_get_client:
            mock_session = Mock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_session.get.return_value = mock_response
            mock_get_client.return_value = mock_session

            assert client.is_available()

    def test_generate_mock(self):
        client = OllamaClient()

        with patch.object(client, "_get_client") as mock_get_client:
            mock_session = Mock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"response": "H8"}
            mock_session.post.return_value = mock_response
            mock_get_client.return_value = mock_session

            result = client.generate("test prompt")
            assert result == "H8"

    def test_get_model_info(self):
        client = OllamaClient(model="llama3")
        info = client.get_model_info()

        assert info["provider"] == "ollama"
        assert info["model"] == "llama3"


class TestOpenAICompatibleClient:
    def test_client_creation(self):
        client = OpenAICompatibleClient(
            model="gpt-4", base_url="https://api.openai.com/v1", api_key="sk-test"
        )

        assert client.model == "gpt-4"
        assert client.base_url == "https://api.openai.com/v1"
        assert client.api_key == "sk-test"


class TestLLMPlayer:
    def test_player_creation(self):
        mock_client = Mock()
        mock_client.get_model_info.return_value = {
            "provider": "ollama",
            "model": "llama3",
            "base_url": "http://localhost:11434",
        }
        player = LLMPlayer(mock_client, Stone.BLACK)

        assert player.stone == Stone.BLACK
        assert player.max_retries == 3

    def test_parse_move_valid(self):
        mock_client = Mock()
        mock_client.get_model_info.return_value = {}
        player = LLMPlayer(mock_client, Stone.BLACK)

        pos = player._parse_move("H8", 15)
        assert pos == Position(7, 7)

        pos = player._parse_move("The best move is H8", 15)
        assert pos == Position(7, 7)

        pos = player._parse_move("h8", 15)
        assert pos == Position(7, 7)

    def test_parse_move_invalid(self):
        mock_client = Mock()
        mock_client.get_model_info.return_value = {}
        player = LLMPlayer(mock_client, Stone.BLACK)

        pos = player._parse_move("invalid", 15)
        assert pos is None

        pos = player._parse_move("Z99", 15)
        assert pos is None

    def test_build_prompt(self):
        mock_client = Mock()
        mock_client.get_model_info.return_value = {}
        player = LLMPlayer(mock_client, Stone.BLACK)
        game = Game()

        prompt = player._build_prompt(game)

        assert "15" in prompt
        assert "黑" in prompt or "BLACK" in prompt

    def test_get_info_string(self):
        mock_client = Mock()
        mock_client.get_model_info.return_value = {
            "provider": "ollama",
            "model": "llama3",
            "base_url": "http://localhost:11434",
        }
        player = LLMPlayer(mock_client, Stone.BLACK)

        info = player.get_info_string()
        assert "ollama" in info
        assert "llama3" in info


class TestCreateLLMPlayer:
    def test_create_ollama_player(self):
        player = create_llm_player(Stone.BLACK, provider="ollama", model="llama3")

        assert player.stone == Stone.BLACK
        assert isinstance(player.client, OllamaClient)

    def test_create_openai_player(self):
        player = create_llm_player(Stone.WHITE, provider="openai_compatible", model="gpt-4")

        assert player.stone == Stone.WHITE
        assert isinstance(player.client, OpenAICompatibleClient)

    def test_create_unknown_provider(self):
        with pytest.raises(ValueError):
            create_llm_player(Stone.BLACK, provider="unknown")


class TestCreateLLMPlayerFromSpec:
    def test_create_from_simple_spec(self):
        player = create_llm_player_from_spec("llama3", Stone.BLACK)

        assert player.stone == Stone.BLACK
        assert isinstance(player.client, OllamaClient)

    def test_create_from_remote_spec(self):
        player = create_llm_player_from_spec("llama3@http://192.168.1.100:11434", Stone.WHITE)

        assert player.stone == Stone.WHITE
        assert player.model_info["base_url"] == "http://192.168.1.100:11434"
