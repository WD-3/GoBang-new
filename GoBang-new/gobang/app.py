"""
Flask web application for GoBang.

Provides:
- REST API for game operations
- WebSocket for real-time updates
- Web interface for playing
"""

from typing import Optional, Dict, Any, List
from flask import Flask, render_template, jsonify, request, send_file
from flask_socketio import SocketIO, emit
import json
import uuid
from datetime import datetime
import subprocess
import platform

from gobang import __version__
from gobang.core import Game, Board, Player, PlayerType, Stone, GameState, RuleMode, Position
from gobang.api import (
    ToolResult,
    create_game,
    get_game,
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
)
from gobang.ai import create_ai
from gobang.llm_player import (
    create_llm_player,
    list_local_ollama_models,
    check_ollama_available,
    LLMPlayer,
)
from gobang.game_record import GameRecord


app = Flask(__name__)
app.config["SECRET_KEY"] = "gobang-secret-key"
socketio = SocketIO(app, cors_allowed_origins="*")

games: Dict[str, Game] = {}
llm_players: Dict[str, Dict[Stone, LLMPlayer]] = {}


@app.route("/")
def index():
    return render_template("index.html", version=__version__)


@app.route("/api/version")
def api_version():
    return jsonify({"version": __version__})


@app.route("/api/games", methods=["GET"])
def api_list_games():
    result = list_games()
    return jsonify(result.to_dict())


@app.route("/api/games", methods=["POST"])
def api_create_game():
    data = request.json or {}

    game_id = data.get("game_id", str(uuid.uuid4()))
    board_size = data.get("board_size", 15)
    rule_mode = data.get("rule_mode", "free_style")

    black_config = data.get("black_player", {})
    white_config = data.get("white_player", {})

    result = create_game(
        game_id=game_id,
        board_size=board_size,
        rule_mode=rule_mode,
        black_player=black_config,
        white_player=white_config,
    )

    if result.success:
        game = get_game(game_id)
        if game:
            games[game_id] = game
            _setup_llm_players(game_id, game)

    return jsonify(result.to_dict())


@app.route("/api/games/<game_id>", methods=["GET"])
def api_get_game(game_id: str):
    result = get_game_state(game_id)
    return jsonify(result.to_dict())


@app.route("/api/games/<game_id>", methods=["DELETE"])
def api_delete_game(game_id: str):
    result = delete_game(game_id)
    if game_id in games:
        del games[game_id]
    if game_id in llm_players:
        del llm_players[game_id]
    return jsonify(result.to_dict())


@app.route("/api/games/<game_id>/move", methods=["POST"])
def api_make_move(game_id: str):
    data = request.json or {}
    position = data.get("position", "")
    thinking_time_ms = data.get("thinking_time_ms", 0)

    result = make_move(game_id, position, thinking_time_ms)

    if result.success:
        socketio.emit("game_update", result.data, room=game_id)

    return jsonify(result.to_dict())


@app.route("/api/games/<game_id>/auto", methods=["POST"])
def api_auto_move(game_id: str):
    import time
    import threading
    
    TIMEOUT_SECONDS = 20  # 超时时间20秒
    
    print(f"[AUTO] 收到自动对弈请求 game_id={game_id}")
    if game_id not in games:
        return jsonify(ToolResult.fail("Game not found").to_dict())

    game = games[game_id]

    if game.state != GameState.PLAYING:
        return jsonify(ToolResult.fail("Game is not in progress").to_dict())

    current_player = game.current_player
    current_stone = game.current_stone
    print(f"[AUTO] 当前玩家: {current_player.player_type}, 棋子: {current_stone}")
    pos = None
    thinking_time_ms = 0
    timeout_occurred = False

    if current_player.player_type == PlayerType.AI:
        config = current_player.config
        ai = create_ai(config.get("algorithm", "minimax"), depth=config.get("depth", 3))
        pos = ai.get_best_move(game)

    elif current_player.player_type == PlayerType.LLM:
        print(f"[AUTO] LLM玩家, 调用中...")
        if game_id in llm_players:
            llm_player = llm_players[game_id].get(current_stone)
            if llm_player:
                print(f"[AUTO] 调用LLM get_move, 超时设置{TIMEOUT_SECONDS}秒...")
                
                # 使用线程实现超时
                result_container = {'pos': None, 'time': 0, 'done': False}
                
                def call_llm():
                    try:
                        result_container['pos'] = llm_player.get_move(game)
                        result_container['time'] = llm_player.last_thinking_time_ms
                    except Exception as e:
                        print(f"[AUTO] LLM错误: {e}")
                    result_container['done'] = True
                
                thread = threading.Thread(target=call_llm)
                thread.start()
                thread.join(timeout=TIMEOUT_SECONDS)
                
                if result_container['done']:
                    pos = result_container['pos']
                    thinking_time_ms = result_container['time']
                    print(f"[AUTO] LLM返回: {pos}, 耗时: {thinking_time_ms}ms")
                else:
                    # 超时了
                    timeout_occurred = True
                    print(f"[AUTO] LLM超时! 超过{TIMEOUT_SECONDS}秒")
            else:
                print(f"[AUTO] 找不到{current_stone}的LLM玩家")
        else:
            print(f"[AUTO] 游戏{game_id}不在llm_players中")

    # 超时判负
    if timeout_occurred:
        loser = "BLACK" if current_stone == Stone.BLACK else "WHITE"
        winner = "WHITE" if current_stone == Stone.BLACK else "BLACK"
        winner_cn = "白方" if winner == "WHITE" else "黑方"
        loser_cn = "黑方" if loser == "BLACK" else "白方"
        print(f"[AUTO] {loser_cn}超时，{winner_cn}获胜！")
        
        # 设置游戏状态为获胜
        if winner == "BLACK":
            game.state = GameState.BLACK_WIN
        else:
            game.state = GameState.WHITE_WIN
        
        return jsonify(ToolResult.ok(
            data={
                **game.get_game_state(),
                "timeout": True,
                "timeout_player": loser,
                "winner": winner,
                "message": f"{loser_cn}响应超时({TIMEOUT_SECONDS}秒)，{winner_cn}获胜！"
            },
            game_id=game_id
        ).to_dict())

    if pos is None:
        print(f"[AUTO] 获取移动失败, pos为None")
        return jsonify(ToolResult.fail("Failed to get move").to_dict())

    result = make_move(game_id, pos.to_notation(), thinking_time_ms)
    print(f"[AUTO] 移动结果: {result.success}")

    if result.success:
        socketio.emit("game_update", result.data, room=game_id)

    return jsonify(result.to_dict())


@app.route("/api/games/<game_id>/undo", methods=["POST"])
def api_undo_move(game_id: str):
    result = undo_move(game_id)

    if result.success:
        socketio.emit("game_update", result.data, room=game_id)

    return jsonify(result.to_dict())


@app.route("/api/games/<game_id>/valid-moves", methods=["GET"])
def api_valid_moves(game_id: str):
    result = get_valid_moves(game_id)
    return jsonify(result.to_dict())


@app.route("/api/games/<game_id>/save", methods=["GET"])
def api_save_game(game_id: str):
    result = save_game(game_id)
    return jsonify(result.to_dict())


@app.route("/api/games/<game_id>/load", methods=["POST"])
def api_load_game(game_id: str):
    data = request.json or {}
    result = load_game(game_id, data)

    if result.success:
        game = get_game(game_id)
        if game:
            games[game_id] = game
            _setup_llm_players(game_id, game)

    return jsonify(result.to_dict())


@app.route("/api/games/<game_id>/suggest", methods=["GET"])
def api_suggest_move(game_id: str):
    depth = request.args.get("depth", 3, type=int)
    result = ai_suggest_move(game_id, depth)
    return jsonify(result.to_dict())


@app.route("/api/games/<game_id>/board", methods=["GET"])
def api_get_board(game_id: str):
    result = get_board_string(game_id)
    return jsonify(result.to_dict())


@app.route("/api/models", methods=["GET"])
def api_list_models():
    models = {
        "ollama_available": check_ollama_available(),
        "local_models": list_local_ollama_models(),
    }
    return jsonify(models)


@app.route("/api/health", methods=["GET"])
def api_health():
    return jsonify(
        {
            "status": "healthy",
            "version": __version__,
            "games_active": len(games),
        }
    )


@app.route("/api/performance", methods=["GET"])
def api_performance():
    """Get system performance metrics."""
    perf = {
        "cpu_percent": 0,
        "memory_percent": 0,
        "gpu_memory_percent": 0,
        "gpu_utilization": 0,
        "gpu_available": False,
    }
    
    try:
        import psutil
        perf["cpu_percent"] = psutil.cpu_percent(interval=0.1)
        perf["memory_percent"] = psutil.virtual_memory().percent
    except ImportError:
        pass
    
    # Try to get NVIDIA GPU info
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used,memory.total,utilization.gpu", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                if lines and lines[0]:
                    parts = lines[0].split(", ")
                    if len(parts) >= 3:
                        mem_used = float(parts[0])
                        mem_total = float(parts[1])
                        gpu_util = float(parts[2])
                        perf["gpu_memory_percent"] = round((mem_used / mem_total) * 100, 1) if mem_total > 0 else 0
                        perf["gpu_utilization"] = gpu_util
                        perf["gpu_available"] = True
    except Exception:
        pass
    
    return jsonify(perf)


@app.route("/api/games/<game_id>/analyze", methods=["GET"])
def api_analyze_game(game_id: str):
    """
    分析游戏中的关键失误（错过必杀/未阻挡必杀）。
    
    关键失误定义：
    1. 错过必杀：自己有活三/活四但没有继续发展
    2. 未阻挡必杀：对手有活三/活四但没有去堵
    """
    from gobang.pattern_engine import PatternEngine, PatternType
    from gobang.core import Board, Stone, Position
    
    if game_id not in games:
        return jsonify(ToolResult.fail("Game not found").to_dict())
    
    game = games[game_id]
    moves = game.moves
    
    black_errors = 0
    white_errors = 0
    
    # 模拟重放游戏，分析每一步
    replay_board = Board(game.board_size)
    
    for i, move in enumerate(moves):
        current_stone = Stone.BLACK if i % 2 == 0 else Stone.WHITE
        opponent_stone = Stone.WHITE if current_stone == Stone.BLACK else Stone.BLACK
        
        # 在下棋之前分析局面
        if i > 0:  # 第一步不分析
            engine = PatternEngine(replay_board, game.rule_mode)
            
            # 检查当前玩家的棋型
            my_patterns = engine.count_patterns(current_stone)
            opp_patterns = engine.count_patterns(opponent_stone)
            
            has_my_open_four = my_patterns.get(PatternType.OPEN_FOUR, 0) > 0
            has_my_open_three = my_patterns.get(PatternType.OPEN_THREE, 0) > 0
            has_my_rush_four = my_patterns.get(PatternType.RUSH_FOUR, 0) > 0
            
            has_opp_open_four = opp_patterns.get(PatternType.OPEN_FOUR, 0) > 0
            has_opp_open_three = opp_patterns.get(PatternType.OPEN_THREE, 0) > 0
            has_opp_rush_four = opp_patterns.get(PatternType.RUSH_FOUR, 0) > 0
            
            move_pos = move.position
            is_error = False
            
            # 检查是否错过必杀：自己有活四或冲四但没有发展
            if has_my_open_four or has_my_rush_four:
                # 检查这一步是否形成了五连
                test_board = replay_board.copy()
                test_board.place_stone(move_pos, current_stone)
                test_engine = PatternEngine(test_board, game.rule_mode)
                new_patterns = test_engine.count_patterns(current_stone)
                if new_patterns.get(PatternType.FIVE, 0) == 0:
                    # 有活四/冲四但没有下完成五连
                    is_error = True
            
            # 检查是否未阻挡必杀：对手有活四或冲四但没有堵
            elif has_opp_open_four or has_opp_rush_four:
                # 检查这一步是否堵住了对手的威胁
                test_board = replay_board.copy()
                test_board.place_stone(move_pos, current_stone)
                test_engine = PatternEngine(test_board, game.rule_mode)
                new_opp_patterns = test_engine.count_patterns(opponent_stone)
                if new_opp_patterns.get(PatternType.OPEN_FOUR, 0) > 0 or new_opp_patterns.get(PatternType.RUSH_FOUR, 0) > 0:
                    # 对手仍然有活四/冲四，没有堵住
                    is_error = True
            
            # 检查是否错过发展活三：自己有活三但没有发展成活四/冲四
            elif has_my_open_three:
                test_board = replay_board.copy()
                test_board.place_stone(move_pos, current_stone)
                test_engine = PatternEngine(test_board, game.rule_mode)
                new_patterns = test_engine.count_patterns(current_stone)
                # 如果下完这步后没有形成活四或冲四，而且也没有堵对手活三
                if (new_patterns.get(PatternType.OPEN_FOUR, 0) == 0 and 
                    new_patterns.get(PatternType.RUSH_FOUR, 0) == 0 and
                    not has_opp_open_three):  # 如果对手也有活三，可能需要先防守
                    is_error = True
            
            # 检查是否未阻挡对手活三
            elif has_opp_open_three:
                test_board = replay_board.copy()
                test_board.place_stone(move_pos, current_stone)
                test_engine = PatternEngine(test_board, game.rule_mode)
                new_opp_patterns = test_engine.count_patterns(opponent_stone)
                if new_opp_patterns.get(PatternType.OPEN_THREE, 0) >= opp_patterns.get(PatternType.OPEN_THREE, 0):
                    # 对手的活三没有被堵住
                    # 但如果自己这步形成了更大威胁，不算失误
                    my_new_patterns = test_engine.count_patterns(current_stone)
                    if (my_new_patterns.get(PatternType.OPEN_FOUR, 0) == 0 and
                        my_new_patterns.get(PatternType.RUSH_FOUR, 0) == 0):
                        is_error = True
            
            if is_error:
                if current_stone == Stone.BLACK:
                    black_errors += 1
                else:
                    white_errors += 1
        
        # 执行这一步
        replay_board.place_stone(move.position, current_stone)
    
    return jsonify({
        "success": True,
        "data": {
            "black_errors": black_errors,
            "white_errors": white_errors,
            "total_moves": len(moves),
        }
    })


@socketio.on("connect")
def handle_connect():
    pass


@socketio.on("disconnect")
def handle_disconnect():
    pass


@socketio.on("join_game")
def handle_join_game(data):
    game_id = data.get("game_id")
    if game_id:
        from flask_socketio import join_room

        join_room(game_id)


@socketio.on("leave_game")
def handle_leave_game(data):
    game_id = data.get("game_id")
    if game_id:
        from flask_socketio import leave_room

        leave_room(game_id)


def _setup_llm_players(game_id: str, game: Game):
    llm_players[game_id] = {}
    print(f"Setting up LLM players for game {game_id}")
    print(f"Black player type: {game.black_player.player_type}, config: {game.black_player.config}")
    print(f"White player type: {game.white_player.player_type}, config: {game.white_player.config}")

    if game.black_player.player_type == PlayerType.LLM:
        config = game.black_player.config
        model = config.get("model", "gemma3:1b")
        print(f"Creating black LLM player with model: {model}")
        llm_players[game_id][Stone.BLACK] = create_llm_player(
            Stone.BLACK,
            provider=config.get("provider", "ollama"),
            model=model,
            base_url=config.get("base_url"),
        )

    if game.white_player.player_type == PlayerType.LLM:
        config = game.white_player.config
        model = config.get("model", "gemma3:1b")
        print(f"Creating white LLM player with model: {model}")
        llm_players[game_id][Stone.WHITE] = create_llm_player(
            Stone.WHITE,
            provider=config.get("provider", "ollama"),
            model=model,
            base_url=config.get("base_url"),
        )


def run_server(host: str = "127.0.0.1", port: int = 5000, debug: bool = False):
    print(f"Starting GoBang web server at http://{host}:{port}")
    print(f"Version: {__version__}")
    print("Press Ctrl+C to stop")
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    run_server(debug=True)
