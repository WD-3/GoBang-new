"""
Command-line interface for GoBang.

Commands:
    gobang                    # Launch GUI (default)
    gobang gui                # Launch GUI explicitly
    gobang web                # Start web server
    gobang cli <args>         # CLI mode
    gobang cli new            # Create new game
    gobang cli move <pos>     # Make a move
    gobang cli battle         # AI vs AI battle
"""

import sys
import argparse
import json
import time
from typing import Optional, Dict, Any

from gobang import __version__
from gobang.core import Game, Board, Player, PlayerType, Stone, GameState, RuleMode, Position
from gobang.api import ToolResult, create_game, make_move, get_game_state
from gobang.ai import create_ai, MinimaxAI, MCTSAI
from gobang.llm_player import (
    create_llm_player,
    create_llm_player_from_spec,
    parse_llm_spec,
    list_local_ollama_models,
    check_ollama_available,
    LLMPlayer,
)
from gobang.game_record import GameRecord, save_game_to_file, load_game_from_file


class CLIGame:
    """CLI game controller."""

    def __init__(self):
        self.game: Optional[Game] = None
        self.verbose = False
        self.json_output = False
        self.game_id = "cli_game"
        self.llm_players: Dict[Stone, LLMPlayer] = {}

    def output(self, data: Any, message: str = "") -> None:
        """Output result."""
        if self.json_output:
            if isinstance(data, ToolResult):
                print(json.dumps(data.to_dict(), indent=2))
            elif isinstance(data, dict):
                print(json.dumps(data, indent=2))
            else:
                print(json.dumps({"data": str(data)}))
        else:
            if message:
                print(message)
            if self.verbose and isinstance(data, dict):
                print(json.dumps(data, indent=2))

    def create_new_game(
        self,
        board_size: int = 15,
        rule_mode: str = "free_style",
        black: str = "human",
        white: str = "human",
        black_config: Dict[str, Any] = None,
        white_config: Dict[str, Any] = None,
    ) -> None:
        """Create a new game."""
        black_player = self._create_player(Stone.BLACK, black, black_config or {})
        white_player = self._create_player(Stone.WHITE, white, white_config or {})

        self.game = Game(
            board_size=board_size,
            rule_mode=RuleMode(rule_mode),
            black_player=black_player,
            white_player=white_player,
        )

        self._setup_llm_players()

        result = ToolResult.ok(
            data=self.game.get_game_state(),
            message=f"New game created: {board_size}x{board_size}, {rule_mode}",
        )
        self.output(result.data, f"New game created ({board_size}x{board_size}, {rule_mode})")

        if not self.json_output:
            self.print_board()

    def _create_player(self, stone: Stone, player_spec: str, config: Dict[str, Any]) -> Player:
        """Create a player from specification string.

        Supported formats:
        - human
        - ai or ai:minimax or ai:mcts
        - llm or llm:gemma3:1b or llm:mistral
        - llm:gemma3:1b@http://localhost:11434
        - llm:gpt-4@https://api.openai.com/v1:sk-xxx
        """
        parts = player_spec.split(":", 1)
        player_type = parts[0].lower()

        if player_type == "human":
            return Player(stone, PlayerType.HUMAN, config=config)
        elif player_type == "ai":
            algorithm = "minimax"
            if len(parts) > 1:
                algo_part = parts[1]
                if "@" in algo_part:
                    algorithm = algo_part.split("@")[0]
                else:
                    algorithm = algo_part
            depth = config.get("depth", 3)
            return Player(
                stone,
                PlayerType.AI,
                name=f"AI ({algorithm})",
                config={"algorithm": algorithm, "depth": depth, **config},
            )
        elif player_type == "llm":
            llm_spec = parts[1] if len(parts) > 1 else "gemma3:1b"
            llm_config = parse_llm_spec(llm_spec)
            llm_config.update(config)

            model = llm_config.get("model", "gemma3:1b")
            provider = llm_config.get("provider", "ollama")
            base_url = llm_config.get("base_url", "http://localhost:11434")

            display_name = f"LLM ({model})"
            if provider == "openai_compatible" or not base_url.startswith("http://localhost"):
                display_name = f"LLM ({model}@external)"

            return Player(
                stone,
                PlayerType.LLM,
                name=display_name,
                config=llm_config,
            )
        else:
            raise ValueError(f"Unknown player type: {player_type}")

    def _setup_llm_players(self) -> None:
        """Setup LLM players for the game."""
        self.llm_players = {}

        if self.game is None:
            return

        if self.game.black_player.player_type == PlayerType.LLM:
            config = self.game.black_player.config
            self.llm_players[Stone.BLACK] = create_llm_player(
                Stone.BLACK,
                provider=config.get("provider", "ollama"),
                model=config.get("model", "gemma3:1b"),
                base_url=config.get("base_url"),
                api_key=config.get("api_key"),
            )

        if self.game.white_player.player_type == PlayerType.LLM:
            config = self.game.white_player.config
            self.llm_players[Stone.WHITE] = create_llm_player(
                Stone.WHITE,
                provider=config.get("provider", "ollama"),
                model=config.get("model", "gemma3:1b"),
                base_url=config.get("base_url"),
                api_key=config.get("api_key"),
            )

    def make_move(self, position: str) -> None:
        """Make a move."""
        if self.game is None:
            self.output(ToolResult.fail("No game in progress"))
            return

        if self.game.state != GameState.PLAYING:
            self.output(ToolResult.fail(f"Game is over: {self.game.state.value}"))
            return

        try:
            pos = Position.from_notation(position, self.game.board_size)
        except ValueError as e:
            self.output(ToolResult.fail(f"Invalid position: {position} - {e}"))
            return

        current_player = self.game.current_player

        # Check if it's an AI or LLM turn (shouldn't be making manual moves)
        if current_player.player_type in (PlayerType.AI, PlayerType.LLM):
            self.output(
                ToolResult.fail(
                    f"It's {current_player.player_type.value}'s turn. Use 'auto' to let them play."
                )
            )
            return

        success, message = self.game.make_move(pos)

        if success:
            self.output(self.game.get_game_state(), f"Move: {position}")
            if not self.json_output:
                self.print_board()

            if self.game.state != GameState.PLAYING:
                self.print_result()
        else:
            self.output(ToolResult.fail(message))

    def auto_move(self) -> None:
        """Let current player make a move automatically."""
        if self.game is None:
            self.output(ToolResult.fail("No game in progress"))
            return

        if self.game.state != GameState.PLAYING:
            self.output(ToolResult.fail(f"Game is over: {self.game.state.value}"))
            return

        current_player = self.game.current_player
        pos = None
        thinking_time_ms = 0

        if current_player.player_type == PlayerType.AI:
            config = current_player.config
            algorithm = config.get("algorithm", "minimax")
            depth = config.get("depth", 3)

            print(f"AI ({algorithm}) thinking...")
            start = time.time()

            ai = create_ai(algorithm, depth=depth)
            pos = ai.get_best_move(self.game)
            thinking_time_ms = int((time.time() - start) * 1000)

        elif current_player.player_type == PlayerType.LLM:
            llm_player = self.llm_players.get(self.game.current_stone)
            if llm_player is None:
                self.output(ToolResult.fail("LLM player not initialized"))
                return

            model_info = llm_player.get_info_string()
            print(f"LLM ({model_info}) thinking...")
            start = time.time()

            pos = llm_player.get_move(self.game)
            thinking_time_ms = llm_player.last_thinking_time_ms

            if self.verbose:
                print(f"LLM response: {llm_player.last_response[:200]}")
        else:
            self.output(ToolResult.fail("Current player is human - cannot auto move"))
            return

        if pos is None:
            self.output(ToolResult.fail("Failed to get move"))
            return

        success, message = self.game.make_move(pos, thinking_time_ms)

        if success:
            self.output(
                self.game.get_game_state(),
                f"{current_player.player_type.value.upper()} move: {pos.to_notation()} ({thinking_time_ms}ms)",
            )
            if not self.json_output:
                self.print_board()

            if self.game.state != GameState.PLAYING:
                self.print_result()
        else:
            self.output(ToolResult.fail(message))

    def run_battle(
        self,
        black: str = "ai:minimax",
        white: str = "llm:gemma3:1b",
        games: int = 1,
        delay: float = 0.5,
    ) -> None:
        """Run AI vs AI battle."""
        results = {"black_wins": 0, "white_wins": 0, "draws": 0, "games": []}

        for game_num in range(1, games + 1):
            print(f"\n{'=' * 50}")
            print(f"Game {game_num}/{games}: {black} vs {white}")
            print("=" * 50)

            self.create_new_game(black=black, white=white)

            move_count = 0
            max_moves = self.game.board_size * self.game.board_size

            while self.game.state == GameState.PLAYING and move_count < max_moves:
                time.sleep(delay)
                self.auto_move()
                move_count += 1

            # Record result
            game_result = {
                "game": game_num,
                "winner": self.game.winner.name if self.game.winner else "draw",
                "moves": len(self.game.moves),
            }
            results["games"].append(game_result)

            if self.game.winner == Stone.BLACK:
                results["black_wins"] += 1
            elif self.game.winner == Stone.WHITE:
                results["white_wins"] += 1
            else:
                results["draws"] += 1

            print(f"\nGame {game_num} result: {game_result['winner']}")

        # Print summary
        print("\n" + "=" * 50)
        print("BATTLE SUMMARY")
        print("=" * 50)
        print(f"Black wins: {results['black_wins']}")
        print(f"White wins: {results['white_wins']}")
        print(f"Draws: {results['draws']}")

        if self.json_output:
            print(json.dumps(results, indent=2))

    def print_board(self) -> None:
        """Print the current board state."""
        if self.game is None:
            print("No game in progress")
            return

        print("\n" + self.game.board.to_string())
        print(f"\nCurrent turn: {self.game.current_stone.name}")
        print(f"Move: {len(self.game.moves) + 1}")

        if self.game.moves:
            last_move = self.game.moves[-1]
            print(f"Last move: {last_move.position.to_notation()} ({last_move.stone.name})")

    def print_result(self) -> None:
        """Print game result."""
        if self.game is None:
            return

        print("\n" + "=" * 30)
        if self.game.winner:
            print(f"WINNER: {self.game.winner.name}")
            if self.game.winning_line:
                print(f"Winning line: {'-'.join(p.to_notation() for p in self.game.winning_line)}")
        elif self.game.state == GameState.DRAW:
            print("DRAW")
        print("=" * 30)

    def save_game(self, filepath: str) -> None:
        """Save the current game."""
        if self.game is None:
            self.output(ToolResult.fail("No game to save"))
            return

        save_game_to_file(self.game, filepath)
        self.output(ToolResult.ok(message=f"Game saved to {filepath}"))

    def load_game(self, filepath: str) -> None:
        """Load a game from file."""
        self.game = load_game_from_file(filepath)
        self._setup_llm_players()
        self.output(self.game.get_game_state(), f"Game loaded from {filepath}")
        if not self.json_output:
            self.print_board()

    def list_models(self) -> None:
        """List available LLM models."""
        print("Checking Ollama availability...")

        if check_ollama_available():
            print("Ollama is running\n")
            models = list_local_ollama_models()
            print("Available models:")
            for model in models:
                print(f"  - {model}")
        else:
            print("Ollama is not running or not installed")
            print("Install from: https://ollama.ai")


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog="gobang",
        description="Gomoku (Five-in-a-Row) game with AI and LLM players",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  gobang                           Launch GUI (default)
  gobang cli new                   Create new game (human vs human)
  gobang cli new -b ai -w llm:gemma3:1b   AI vs LLM game
  gobang cli move H8               Make a move at H8
  gobang cli auto                  Let AI/LLM play current turn
  gobang cli battle -b ai -w llm:gemma3:1b -g 10   Run 10 battles
  gobang web --port 5000           Start web server
  gobang models                    List available LLM models
        """,
    )

    # Global flags
    parser.add_argument("-V", "--version", action="version", version=f"gobang {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output as JSON")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress non-essential output")

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # GUI subcommand
    gui_parser = subparsers.add_parser("gui", help="Launch GUI")
    gui_parser.add_argument("--no-web", action="store_true", help="Disable embedded web server")

    # Web subcommand
    web_parser = subparsers.add_parser("web", help="Start web server")
    web_parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    web_parser.add_argument("--port", type=int, default=5000, help="Port to listen on")
    web_parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    # CLI subcommand
    cli_parser = subparsers.add_parser("cli", help="CLI mode")
    cli_subparsers = cli_parser.add_subparsers(dest="cli_command", help="CLI commands")

    # New game
    new_parser = cli_subparsers.add_parser("new", help="Create new game")
    new_parser.add_argument("-s", "--size", type=int, default=15, help="Board size")
    new_parser.add_argument(
        "-r",
        "--rules",
        default="free_style",
        choices=["free_style", "standard", "renju"],
        help="Rule mode",
    )
    new_parser.add_argument(
        "-b",
        "--black",
        default="human",
        help="Black player: human, ai[:minimax|mcts], llm[:model|model@url:key]",
    )
    new_parser.add_argument(
        "-w",
        "--white",
        default="human",
        help="White player: human, ai[:minimax|mcts], llm[:model|model@url:key]",
    )
    new_parser.add_argument("--depth", type=int, default=3, help="AI search depth")

    # Move
    move_parser = cli_subparsers.add_parser("move", help="Make a move")
    move_parser.add_argument("position", help="Position (e.g., H8)")

    # Auto
    cli_subparsers.add_parser("auto", help="Let current player move automatically")

    # Undo
    cli_subparsers.add_parser("undo", help="Undo last move")

    # Show
    cli_subparsers.add_parser("show", help="Show current board")

    # Save
    save_parser = cli_subparsers.add_parser("save", help="Save game")
    save_parser.add_argument("filepath", help="File path")

    # Load
    load_parser = cli_subparsers.add_parser("load", help="Load game")
    load_parser.add_argument("filepath", help="File path")

    # Battle
    battle_parser = cli_subparsers.add_parser("battle", help="AI/LLM battle")
    battle_parser.add_argument(
        "-b",
        "--black",
        default="ai:minimax",
        help="Black player: ai[:minimax|mcts] or llm[:model|model@url:key]",
    )
    battle_parser.add_argument(
        "-w",
        "--white",
        default="llm:gemma3:1b",
        help="White player: ai[:minimax|mcts] or llm[:model|model@url:key]",
    )
    battle_parser.add_argument("-g", "--games", type=int, default=1, help="Number of games")
    battle_parser.add_argument(
        "-d", "--delay", type=float, default=0.5, help="Delay between moves (seconds)"
    )

    # Models
    subparsers.add_parser("models", help="List available LLM models")

    return parser


def main(args: list = None) -> int:
    """Main entry point."""
    parser = create_parser()
    parsed_args = parser.parse_args(args)

    cli_game = CLIGame()
    cli_game.verbose = parsed_args.verbose
    cli_game.json_output = parsed_args.json_output

    # Default: launch GUI
    if parsed_args.command is None:
        return launch_gui()

    if parsed_args.command == "gui":
        return launch_gui()

    if parsed_args.command == "web":
        return launch_web(parsed_args.host, parsed_args.port, parsed_args.debug)

    if parsed_args.command == "models":
        cli_game.list_models()
        return 0

    if parsed_args.command == "cli":
        if parsed_args.cli_command is None:
            parser.print_help()
            return 0

        if parsed_args.cli_command == "new":
            black_config = {"depth": parsed_args.depth} if "ai" in parsed_args.black else {}
            white_config = {"depth": parsed_args.depth} if "ai" in parsed_args.white else {}

            cli_game.create_new_game(
                board_size=parsed_args.size,
                rule_mode=parsed_args.rules,
                black=parsed_args.black,
                white=parsed_args.white,
                black_config=black_config,
                white_config=white_config,
            )

        elif parsed_args.cli_command == "move":
            cli_game.make_move(parsed_args.position)

        elif parsed_args.cli_command == "auto":
            cli_game.auto_move()

        elif parsed_args.cli_command == "undo":
            if cli_game.game and cli_game.game.undo_move():
                print("Move undone")
                cli_game.print_board()
            else:
                print("Cannot undo")

        elif parsed_args.cli_command == "show":
            cli_game.print_board()

        elif parsed_args.cli_command == "save":
            cli_game.save_game(parsed_args.filepath)

        elif parsed_args.cli_command == "load":
            cli_game.load_game(parsed_args.filepath)

        elif parsed_args.cli_command == "battle":
            cli_game.run_battle(
                black=parsed_args.black,
                white=parsed_args.white,
                games=parsed_args.games,
                delay=parsed_args.delay,
            )

        return 0

    return 0


def launch_gui() -> int:
    """Launch GUI application."""
    try:
        from gobang.gui import main as gui_main

        return gui_main()
    except ImportError as e:
        print(f"Failed to launch GUI: {e}")
        print("Make sure PySide6 is installed: pip install PySide6")
        return 1


def launch_web(host: str, port: int, debug: bool = False) -> int:
    """Launch web server."""
    try:
        from gobang.app import run_server

        run_server(host=host, port=port, debug=debug)
        return 0
    except ImportError as e:
        print(f"Failed to start web server: {e}")
        print("Make sure Flask is installed: pip install Flask")
        return 1


if __name__ == "__main__":
    sys.exit(main())
