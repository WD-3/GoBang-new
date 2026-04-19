"""
LLM-based players for Gomoku.

Supports:
- Local Ollama models (different models can play against each other)
- OpenAI-compatible API services (cloud or self-hosted)
- Mixed mode: local vs external, different providers
- Pattern-based threat analysis for better move understanding

Player specification format:
- llm:gemma3:1b                                # Local Ollama with model gemma3:1b
- llm:mistral                                   # Local Ollama with model mistral
- llm:qwen2@http://192.168.1.100:11434          # Remote Ollama server
- llm:gpt-4@https://api.openai.com/v1:sk-xxx    # OpenAI API with key
- llm:claude@https://api.anthropic.com/v1:sk-xxx # Anthropic API

References:
[1] Allis, L.V. (1994). "Searching for Solutions in Games and AI"
[2] Pattern-based evaluation from gobang.pattern_engine
"""

from typing import Optional, Dict, Any, List, Tuple
from abc import ABC, abstractmethod
import time
import re
import json

from gobang.core import Game, Stone, Position, GameState
from gobang.pattern_engine import (
    PatternEngine,
    PatternType,
    VCFEngine,
    ForbiddenDetector,
    PATTERN_NAMES,
    get_best_move_rule_based,
)


class LLMClient(ABC):
    """Base class for LLM clients."""

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate response from LLM."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the LLM service is available."""
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, str]:
        """Get model and provider info."""
        pass


class OllamaClient(LLMClient):
    """Client for local or remote Ollama service."""

    def __init__(
        self,
        model: str = "gemma3:1b",
        base_url: str = "http://localhost:11434",
        timeout: float = 60.0,
        temperature: float = 0.1,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.temperature = temperature
        self._client = None

    def _get_client(self):
        if self._client is None:
            import requests

            self._client = requests.Session()
        return self._client

    def is_available(self) -> bool:
        try:
            client = self._get_client()
            response = client.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def list_models(self) -> List[str]:
        try:
            client = self._get_client()
            response = client.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            pass
        return []

    def generate(self, prompt: str, **kwargs) -> str:
        client = self._get_client()

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", self.temperature),
                "seed": -1,
                "num_predict": kwargs.get("max_tokens", 100),
            },
        }

        response = client.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=kwargs.get("timeout", self.timeout),
        )

        if response.status_code != 200:
            raise RuntimeError(f"Ollama API error: {response.status_code} - {response.text}")

        data = response.json()
        return data.get("response", "").strip()

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        client = self._get_client()

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", self.temperature),
                "num_predict": kwargs.get("max_tokens", 100),
            },
        }

        response = client.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=kwargs.get("timeout", self.timeout),
        )

        if response.status_code != 200:
            raise RuntimeError(f"Ollama API error: {response.status_code} - {response.text}")

        data = response.json()
        return data.get("message", {}).get("content", "").strip()

    def get_model_info(self) -> Dict[str, str]:
        return {
            "provider": "ollama",
            "model": self.model,
            "base_url": self.base_url,
        }


class OpenAICompatibleClient(LLMClient):
    """Client for OpenAI-compatible APIs (OpenAI, Azure, self-hosted, etc.)."""

    def __init__(
        self,
        model: str = "gpt-4",
        base_url: str = "https://api.openai.com/v1",
        api_key: str = "",
        timeout: float = 60.0,
        temperature: float = 0.1,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.temperature = temperature
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI

                self._client = OpenAI(
                    base_url=self.base_url,
                    api_key=self.api_key or "no-key",
                    timeout=self.timeout,
                )
            except ImportError:
                raise ImportError("openai package required: pip install openai")
        return self._client

    def is_available(self) -> bool:
        try:
            client = self._get_client()
            client.models.list()
            return True
        except Exception:
            return False

    def list_models(self) -> List[str]:
        try:
            client = self._get_client()
            models = client.models.list()
            return [m.id for m in models.data]
        except Exception:
            return []

    def generate(self, prompt: str, **kwargs) -> str:
        client = self._get_client()

        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", 100),
        )

        return response.choices[0].message.content.strip()

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        client = self._get_client()

        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", 100),
        )

        return response.choices[0].message.content.strip()

    def get_model_info(self) -> Dict[str, str]:
        return {
            "provider": "openai_compatible",
            "model": self.model,
            "base_url": self.base_url,
        }


class LLMPlayer:
    """
    LLM-based Gomoku player.

    Can use either Ollama native API or OpenAI-compatible API.
    Each player instance can have its own model and provider.
    """

    MOVE_PROMPT_TEMPLATE = """你是五子棋选手。你是{color}方。

棋盘 ({size}x{size}, ·=空, ●=黑, ○=白):
{board_visual}

{threat_info}

【重要提示】
五子棋获胜不分方向！横向、竖向、斜向连成五子均可获胜。
LLM 容易只关注横向，请务必检查竖向和斜向的棋型！

策略（按优先级）：
1. 必胜：己方有四连（活四/冲四）→ 下连五点获胜
2. 必防：对手有四连 → 必须堵连五点
3. 进攻：己方有活三 → 发展成活四
4. 防守：对手有活三 → 堵一端
5. 无威胁：向空旷区域发展，形成长连线（优先延伸竖向或斜向的棋子）

只输出坐标，格式：落子：H8
"""

    def __init__(
        self,
        client: LLMClient,
        stone: Stone,
        max_retries: int = 3,
    ):
        self.client = client
        self.stone = stone
        self.max_retries = max_retries
        self.last_response = ""
        self.last_thinking_time_ms = 0
        self.model_info = client.get_model_info()

    def _get_direction_name(self, direction: Tuple[int, int]) -> str:
        dr, dc = direction
        if dr == 0:
            return "横向"
        elif dc == 0:
            return "竖向"
        else:
            return "斜向"

    def _analyze_threats(self, game: Game) -> str:
        board = game.board
        my_stone = self.stone
        opp_stone = Stone.WHITE if my_stone == Stone.BLACK else Stone.BLACK
        engine = PatternEngine(board, game.rule_mode)

        lines = []

        # 必胜点（连五）
        my_winning = engine.get_winning_moves(my_stone)
        if my_winning:
            lines.append(f"【必胜】己方连五：{', '.join(p.to_notation() for p in my_winning[:3])}")

        opp_winning = engine.get_winning_moves(opp_stone)
        if opp_winning:
            lines.append(f"【必防】对手连五：{', '.join(p.to_notation() for p in opp_winning[:3])}")

        # 活四/冲四分析
        my_patterns = engine.find_patterns(my_stone)
        opp_patterns = engine.find_patterns(opp_stone)

        my_open_fours = [p for p in my_patterns if p.pattern_type == PatternType.OPEN_FOUR]
        my_rush_fours = [p for p in my_patterns if p.pattern_type == PatternType.RUSH_FOUR]
        opp_open_fours = [p for p in opp_patterns if p.pattern_type == PatternType.OPEN_FOUR]
        opp_rush_fours = [p for p in opp_patterns if p.pattern_type == PatternType.RUSH_FOUR]

        if my_open_fours:
            pos = my_open_fours[0].positions[0]
            d_name = self._get_direction_name(my_open_fours[0].direction)
            lines.append(f"【进攻】己方{d_name}活四：{pos.to_notation()} 附近可发展")
        if opp_open_fours:
            pos = opp_open_fours[0].positions[0]
            d_name = self._get_direction_name(opp_open_fours[0].direction)
            lines.append(f"【防守】对手{d_name}活四：{pos.to_notation()} 附近需堵")

        if my_rush_fours and not my_winning:
            pos = my_rush_fours[0].positions[0]
            d_name = self._get_direction_name(my_rush_fours[0].direction)
            lines.append(f"【进攻】己方{d_name}冲四：{pos.to_notation()} 附近可发展")
        if opp_rush_fours and not opp_winning:
            pos = opp_rush_fours[0].positions[0]
            d_name = self._get_direction_name(opp_rush_fours[0].direction)
            lines.append(f"【防守】对手{d_name}冲四：{pos.to_notation()} 附近需堵")

        # 活三分析
        my_open_threes = [p for p in my_patterns if p.pattern_type == PatternType.OPEN_THREE]
        opp_open_threes = [p for p in opp_patterns if p.pattern_type == PatternType.OPEN_THREE]

        if my_open_threes and not my_open_fours and not my_rush_fours:
            p = my_open_threes[0]
            pos = p.positions[0]
            d_name = self._get_direction_name(p.direction)
            lines.append(f"【进攻】己方{d_name}活三：{pos.to_notation()} 附近可发展")
        if opp_open_threes and not opp_open_fours and not opp_rush_fours:
            p = opp_open_threes[0]
            pos = p.positions[0]
            d_name = self._get_direction_name(p.direction)
            lines.append(f"【防守】对手{d_name}活三：{pos.to_notation()} 附近需堵")

        return "\n".join(lines) if lines else "【局面】无明显威胁，向空旷区域发展"

    def _get_candidates(self, game: Game) -> list:
        rule_move = get_best_move_rule_based(game)
        candidates = game.board.get_candidate_moves(distance=2)

        # 按战术价值排序，而不是距离中心
        # 优先选择能形成棋型或阻挡对手的位置
        def tactical_score(pos):
            test_board = game.board.copy()
            test_board.place_stone(pos, self.stone)
            engine = PatternEngine(test_board, game.rule_mode)
            my_patterns = engine.count_patterns(self.stone)
            opp_patterns = engine.count_patterns(self.stone.opponent())

            score = 0
            score += my_patterns.get(PatternType.OPEN_FOUR, 0) * 1000
            score += my_patterns.get(PatternType.RUSH_FOUR, 0) * 500
            score += my_patterns.get(PatternType.OPEN_THREE, 0) * 100
            score -= opp_patterns.get(PatternType.OPEN_FOUR, 0) * 1000
            score -= opp_patterns.get(PatternType.RUSH_FOUR, 0) * 500
            score -= opp_patterns.get(PatternType.OPEN_THREE, 0) * 100
            return score

        candidates.sort(key=tactical_score, reverse=True)

        if rule_move and rule_move in candidates:
            candidates.remove(rule_move)
            candidates.insert(0, rule_move)

        return candidates[:10]

    def get_move(self, game: Game) -> Optional[Position]:
        if game.state != GameState.PLAYING:
            return None

        prompt = self._build_prompt(game)
        start_time = time.time()

        for attempt in range(self.max_retries):
            try:
                response = self.client.generate(prompt, max_tokens=300)
                self.last_response = response

                position = self._parse_move(response, game.board_size)

                if position and game.is_valid_move(position):
                    self.last_thinking_time_ms = int((time.time() - start_time) * 1000)
                    return position

                prompt += f"\n\n'{response}'无效。只输出坐标如H8: "

            except Exception as e:
                print(f"LLM error (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    raise

        self.last_thinking_time_ms = int((time.time() - start_time) * 1000)
        return self._get_fallback_move(game)

    def _build_prompt(self, game: Game) -> str:
        board_visual = game.board.to_string()
        color = "黑(●)" if self.stone == Stone.BLACK else "白(○)"

        threat_info = self._analyze_threats(game)

        return self.MOVE_PROMPT_TEMPLATE.format(
            size=game.board_size,
            board_visual=board_visual,
            color=color,
            threat_info=threat_info,
        )

    def _parse_move(self, response: str, board_size: int) -> Optional[Position]:
        response = response.strip().upper()

        patterns = [
            r"\b([A-O])(\d{1,2})\b",
            r"\b([A-O])[\s\-_:]*(\d{1,2})\b",
            r"\b([A-O])(\d{1,2})\b.*",
        ]

        for pattern in patterns:
            match = re.search(pattern, response)
            if match:
                try:
                    col_letter = match.group(1)
                    row_number = int(match.group(2))

                    col = ord(col_letter) - ord("A")
                    row = row_number - 1

                    if 0 <= row < board_size and 0 <= col < board_size:
                        return Position(row, col)
                except (ValueError, IndexError):
                    continue

        return None

    def _get_fallback_move(self, game: Game) -> Optional[Position]:
        candidates = game.board.get_candidate_moves()
        if candidates:
            center = game.board_size // 2
            candidates.sort(key=lambda p: abs(p.row - center) + abs(p.col - center))
            return candidates[0]
        return None

    def get_info_string(self) -> str:
        info = self.model_info
        return f"{info['provider']}:{info['model']}@{info['base_url']}"


def parse_llm_spec(spec: str) -> Dict[str, Any]:
    """
    Parse LLM player specification string.

    Formats:
    - gemma3:1b                                 # Local Ollama with model gemma3:1b
    - mistral@http://192.168.1.100:11434        # Remote Ollama server
    - gpt-4@https://api.openai.com/v1:sk-xxx    # OpenAI API with key
    - claude@https://api.anthropic.com:sk-xxx   # Anthropic-style API

    Returns dict with: provider, model, base_url, api_key
    """
    config = {
        "provider": "ollama",
        "model": "gemma3:1b",
        "base_url": "http://localhost:11434",
        "api_key": None,
    }

    if "@" not in spec:
        config["model"] = spec
        return config

    parts = spec.split("@", 1)
    config["model"] = parts[0]
    url_part = parts[1]

    api_key_sep = None
    key_start = url_part.rfind(":sk-")
    if key_start > 0:
        api_key_sep = key_start
    else:
        last_colon = url_part.rfind(":")
        if last_colon > 7:
            after_colon = url_part[last_colon + 1 :]
            if not after_colon.isdigit() and "/" not in after_colon:
                api_key_sep = last_colon

    if api_key_sep is not None:
        config["base_url"] = url_part[:api_key_sep]
        config["api_key"] = url_part[api_key_sep + 1 :]
    else:
        config["base_url"] = url_part

    if config.get("api_key"):
        config["provider"] = "openai_compatible"
    elif ":11434" in config["base_url"]:
        config["provider"] = "ollama"
    elif not config["base_url"].startswith("http://localhost") and not config[
        "base_url"
    ].startswith("http://127.0.0.1"):
        config["provider"] = "openai_compatible"

    return config


def create_llm_player(
    stone: Stone,
    provider: str = "ollama",
    model: str = "gemma3:1b",
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    **kwargs,
) -> LLMPlayer:
    """
    Create an LLM player.

    Args:
        stone: Player's stone color
        provider: 'ollama' or 'openai_compatible'
        model: Model name
        base_url: API base URL
        api_key: API key (for external services)
        **kwargs: Additional client options

    Returns:
        LLMPlayer instance
    """
    if provider == "ollama":
        client = OllamaClient(model=model, base_url=base_url or "http://localhost:11434", **kwargs)
    elif provider == "openai_compatible":
        client = OpenAICompatibleClient(
            model=model,
            base_url=base_url or "https://api.openai.com/v1",
            api_key=api_key or "",
            **kwargs,
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")

    return LLMPlayer(client, stone)


def create_llm_player_from_spec(spec: str, stone: Stone, **kwargs) -> LLMPlayer:
    """
    Create an LLM player from specification string.

    Args:
        spec: Specification string (e.g., "gemma3:1b", "mistral@http://localhost:11434", "gpt-4@https://api.openai.com/v1:sk-xxx")
        stone: Player's stone color
        **kwargs: Additional options

    Returns:
        LLMPlayer instance
    """
    config = parse_llm_spec(spec)
    return create_llm_player(
        stone=stone,
        provider=config["provider"],
        model=config["model"],
        base_url=config["base_url"],
        api_key=config.get("api_key"),
        **kwargs,
    )


def list_local_ollama_models(base_url: str = "http://localhost:11434") -> List[str]:
    """List models available in local Ollama."""
    client = OllamaClient(base_url=base_url)
    return client.list_models()


def check_ollama_available(base_url: str = "http://localhost:11434") -> bool:
    """Check if Ollama is running locally."""
    client = OllamaClient(base_url=base_url)
    return client.is_available()


__all__ = [
    "LLMClient",
    "OllamaClient",
    "OpenAICompatibleClient",
    "LLMPlayer",
    "create_llm_player",
    "create_llm_player_from_spec",
    "parse_llm_spec",
    "list_local_ollama_models",
    "check_ollama_available",
]
