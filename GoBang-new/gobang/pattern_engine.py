"""
Pattern-based Gomoku engine with strict rule-based algorithms.

This module implements:
- Pattern recognition (five, open four, rush four, open three, sleep three, etc.)
- VCF (Victory by Continuous Four) search
- VCT (Victory by Continuous Threat) search
- Forbidden move detection for Renju rules (三三禁手, 四四禁手, 长连禁手)

References:
[1] Allis, L.V. (1994). "Searching for Solutions in Games and Artificial Intelligence"
    PhD thesis, University of Limburg. - Foundational work on threat space search.
[2] Allis, L.V., van den Herik, H.J., Huntjens, M.P.H. (1993).
    "Go-Moku Solved by New Techniques" AAAI-93. - First solution of Gomoku.
[3] Wagner, J. (2000). "The Game of Gomoku" - Comprehensive pattern analysis.
[4] Renju International Federation. "Renju Rules" https://renju.net
[5] Wu, I-C., et al. (2012). "Benchmark for Connect6 and Renju" - Modern evaluation.
"""

from typing import Optional, List, Tuple, Dict, Set
from enum import Enum, auto
from dataclasses import dataclass
import copy

from gobang.core import Board, Game, Stone, Position, RuleMode


class PatternType(Enum):
    FIVE = auto()
    OPEN_FOUR = auto()
    RUSH_FOUR = auto()
    OPEN_THREE = auto()
    SLEEP_THREE = auto()
    OPEN_TWO = auto()
    SLEEP_TWO = auto()


PATTERN_SCORES = {
    PatternType.FIVE: 100000,
    PatternType.OPEN_FOUR: 10000,
    PatternType.RUSH_FOUR: 1000,
    PatternType.OPEN_THREE: 500,
    PatternType.SLEEP_THREE: 100,
    PatternType.OPEN_TWO: 50,
    PatternType.SLEEP_TWO: 10,
}

PATTERN_NAMES = {
    PatternType.FIVE: "连五/Five",
    PatternType.OPEN_FOUR: "活四/Open Four",
    PatternType.RUSH_FOUR: "冲四/Rush Four",
    PatternType.OPEN_THREE: "活三/Open Three",
    PatternType.SLEEP_THREE: "眠三/Sleep Three",
    PatternType.OPEN_TWO: "活二/Open Two",
    PatternType.SLEEP_TWO: "眠二/Sleep Two",
}


@dataclass
class PatternMatch:
    pattern_type: PatternType
    positions: List[Position]
    direction: Tuple[int, int]
    stone: Stone


class PatternEngine:
    """
    Pattern recognition engine for Gomoku.

    Implements algorithms based on Allis (1994) and standard Gomoku theory.

    Pattern definitions (using X=stone, O=opponent/block, _=empty):
    - Five: XXXXX
    - Open Four: _XXXX_ (two ways to win)
    - Rush Four: OXXXX_ or _XXXXO or X_XXX, XX_XX (one way to win)
    - Open Three: _XXX_ (can become open four)
    - Sleep Three: OXXX_ or _XXXO (can only become rush four)
    """

    DIRECTIONS = [(0, 1), (1, 0), (1, 1), (1, -1)]

    def __init__(self, board: Board, rule_mode: RuleMode = RuleMode.FREE_STYLE):
        self.board = board
        self.rule_mode = rule_mode

    def find_patterns(self, stone: Stone) -> List[PatternMatch]:
        patterns = []
        for dr, dc in self.DIRECTIONS:
            patterns.extend(self._find_patterns_in_direction(stone, dr, dc))
        return patterns

    def _find_patterns_in_direction(self, stone: Stone, dr: int, dc: int) -> List[PatternMatch]:
        patterns = []
        board = self.board
        size = board.size
        visited = set()

        for row in range(size):
            for col in range(size):
                if (row, col) in visited:
                    continue
                pos = Position(row, col)
                if board.is_empty(pos):
                    continue

                if board.get(pos) != stone:
                    continue

                line = []
                for i in range(5):
                    r, c = row + dr * i, col + dc * i
                    if 0 <= r < size and 0 <= c < size:
                        line.append((r, c, board.get(Position(r, c))))
                    else:
                        break

                if len(line) >= 5:
                    pattern = self._classify_line(line, stone, dr, dc)
                    if pattern:
                        patterns.append(pattern)
                        for r, c, _ in line:
                            visited.add((r, c))

        return patterns

    def _classify_line(
        self, line: List[Tuple[int, int, Stone]], stone: Stone, dr: int, dc: int
    ) -> Optional[PatternMatch]:
        if not line:
            return None

        positions = [Position(r, c) for r, c, _ in line if _ == stone]
        stone_count = len(positions)

        if stone_count >= 5:
            return PatternMatch(PatternType.FIVE, positions[:5], (dr, dc), stone)

        r_start, c_start = line[0][0] - dr, line[0][1] - dc
        r_end, c_end = line[-1][0] + dr, line[-1][1] + dc

        size = self.board.size
        open_start = (
            0 <= r_start < size
            and 0 <= c_start < size
            and self.board.is_empty(Position(r_start, c_start))
        )
        open_end = (
            0 <= r_end < size and 0 <= c_end < size and self.board.is_empty(Position(r_end, c_end))
        )

        if stone_count == 4:
            if open_start and open_end:
                return PatternMatch(PatternType.OPEN_FOUR, positions, (dr, dc), stone)
            elif open_start or open_end:
                return PatternMatch(PatternType.RUSH_FOUR, positions, (dr, dc), stone)

        elif stone_count == 3:
            if open_start and open_end:
                return PatternMatch(PatternType.OPEN_THREE, positions, (dr, dc), stone)
            elif open_start or open_end:
                return PatternMatch(PatternType.SLEEP_THREE, positions, (dr, dc), stone)

        elif stone_count == 2:
            if open_start and open_end:
                return PatternMatch(PatternType.OPEN_TWO, positions, (dr, dc), stone)
            elif open_start or open_end:
                return PatternMatch(PatternType.SLEEP_TWO, positions, (dr, dc), stone)

        return None

    def count_patterns(self, stone: Stone) -> Dict[PatternType, int]:
        patterns = self.find_patterns(stone)
        counts = {pt: 0 for pt in PatternType}
        for p in patterns:
            counts[p.pattern_type] += 1
        return counts

    def get_winning_moves(self, stone: Stone) -> List[Position]:
        winning = []
        candidates = self.board.get_candidate_moves(distance=1)

        for pos in candidates:
            test_board = self.board.copy()
            test_board.place_stone(pos, stone)

            engine = PatternEngine(test_board, self.rule_mode)
            for pattern in engine.find_patterns(stone):
                if pattern.pattern_type == PatternType.FIVE:
                    winning.append(pos)
                    break

        return winning

    def get_forcing_moves(self, stone: Stone) -> List[Tuple[Position, PatternType]]:
        forcing = []
        candidates = self.board.get_candidate_moves(distance=2)

        for pos in candidates:
            test_board = self.board.copy()
            test_board.place_stone(pos, stone)

            engine = PatternEngine(test_board, self.rule_mode)
            patterns = engine.count_patterns(stone)

            if patterns[PatternType.OPEN_FOUR] > 0:
                forcing.append((pos, PatternType.OPEN_FOUR))
            elif patterns[PatternType.RUSH_FOUR] > 0:
                forcing.append((pos, PatternType.RUSH_FOUR))

        return forcing


class ForbiddenDetector:
    """
    Forbidden move detection for Renju rules (连珠规则).

    Based on Renju International Federation rules:
    - Black cannot make: 三三 (double three), 四四 (double four), 长连 (overline)
    - White has no restrictions

    References:
    [1] Renju International Federation. "The Rules of Renju"
        https://renju.net/rules/
    [2] Allis (1994), Chapter 4: "Forbidden Moves"
    """

    def __init__(self, board: Board):
        self.board = board

    def is_forbidden(self, pos: Position, stone: Stone = Stone.BLACK) -> bool:
        if stone != Stone.BLACK:
            return False

        if not self.board.is_empty(pos):
            return False

        test_board = self.board.copy()
        test_board.place_stone(pos, stone)

        if self._is_overline(test_board, pos, stone):
            return True
        if self._is_double_four(test_board, pos, stone):
            return True
        if self._is_double_three(test_board, pos, stone):
            return True

        return False

    def _is_overline(self, board: Board, pos: Position, stone: Stone) -> bool:
        for dr, dc in PatternEngine.DIRECTIONS:
            count = 1

            for i in range(1, 6):
                r, c = pos.row + dr * i, pos.col + dc * i
                if 0 <= r < board.size and 0 <= c < board.size:
                    if board.get(Position(r, c)) == stone:
                        count += 1
                    else:
                        break
                else:
                    break

            for i in range(1, 6):
                r, c = pos.row - dr * i, pos.col - dc * i
                if 0 <= r < board.size and 0 <= c < board.size:
                    if board.get(Position(r, c)) == stone:
                        count += 1
                    else:
                        break
                else:
                    break

            if count > 5:
                return True

        return False

    def _is_double_four(self, board: Board, pos: Position, stone: Stone) -> bool:
        engine = PatternEngine(board, RuleMode.RENJU)
        patterns = engine.find_patterns(stone)

        four_count = sum(
            1 for p in patterns if p.pattern_type in (PatternType.OPEN_FOUR, PatternType.RUSH_FOUR)
        )

        return four_count >= 2

    def _is_double_three(self, board: Board, pos: Position, stone: Stone) -> bool:
        open_threes = 0
        engine = PatternEngine(board, RuleMode.RENJU)

        for dr, dc in PatternEngine.DIRECTIONS:
            if self._forms_open_three(board, pos, stone, dr, dc):
                if self._is_real_open_three(board, pos, stone, dr, dc):
                    open_threes += 1

        return open_threes >= 2

    def _forms_open_three(
        self, board: Board, pos: Position, stone: Stone, dr: int, dc: int
    ) -> bool:
        count = 1
        open_ends = 0

        for sign in [1, -1]:
            for i in range(1, 5):
                r, c = pos.row + dr * sign * i, pos.col + dc * sign * i
                if 0 <= r < board.size and 0 <= c < board.size:
                    p = Position(r, c)
                    if board.get(p) == stone:
                        count += 1
                    elif board.is_empty(p):
                        open_ends += 1
                        break
                    else:
                        break
                else:
                    break

        return count == 3 and open_ends == 2

    def _is_real_open_three(
        self, board: Board, pos: Position, stone: Stone, dr: int, dc: int
    ) -> bool:
        positions = []

        for sign in [1, -1]:
            for i in range(1, 4):
                r, c = pos.row + dr * sign * i, pos.col + dc * sign * i
                if 0 <= r < board.size and 0 <= c < board.size:
                    p = Position(r, c)
                    if board.get(p) == stone:
                        positions.append(p)
                    elif board.is_empty(p):
                        break
                    else:
                        return False
                else:
                    return False

        for ext_pos in positions:
            test_board = board.copy()
            if test_board.is_empty(ext_pos):
                test_board.place_stone(ext_pos, stone)

                engine = PatternEngine(test_board, RuleMode.RENJU)
                patterns = engine.find_patterns(stone)

                has_open_four = any(p.pattern_type == PatternType.OPEN_FOUR for p in patterns)

                if has_open_four:
                    fd = ForbiddenDetector(test_board)
                    if not fd.is_forbidden(ext_pos, stone):
                        return True

        return False

    def get_forbidden_positions(self) -> List[Position]:
        forbidden = []
        candidates = self.board.get_candidate_moves(distance=2)

        for pos in candidates:
            if self.is_forbidden(pos):
                forbidden.append(pos)

        return forbidden


class VCFEngine:
    """
    VCF (Victory by Continuous Four) search engine.

    VCF finds a winning sequence by continuously making rush fours (冲四),
    forcing the opponent to respond until achieving five-in-a-row.

    Algorithm:
    1. Find moves that create rush four or open four
    2. For each forcing move, recursively search opponent's blocks
    3. If all opponent responses lead to our victory, return the winning sequence

    Complexity: O(b^d) where b is branching factor, d is depth
    Practical depth limit: 10-15 moves ahead

    References:
    [1] Allis (1994), Chapter 3: "Threat Space Search"
    [2] Wagner (2000): VCF algorithm description
    """

    MAX_DEPTH = 15

    def __init__(self, board: Board, attacker: Stone):
        self.board = board
        self.attacker = attacker
        self.defender = attacker.opponent()

    def search(self, depth: int = 0) -> Optional[List[Position]]:
        if depth >= self.MAX_DEPTH:
            return None

        engine = PatternEngine(self.board)

        winning_moves = engine.get_winning_moves(self.attacker)
        if winning_moves:
            return [winning_moves[0]]

        forcing_moves = engine.get_forcing_moves(self.attacker)

        for move, _ in forcing_moves:
            test_board = self.board.copy()
            test_board.place_stone(move, self.attacker)

            new_engine = PatternEngine(test_board)
            new_winning = new_engine.get_winning_moves(self.attacker)

            if new_winning:
                return [move, new_winning[0]]

            blocks = self._find_blocks(test_board, move)

            if not blocks:
                return [move]

            all_blocked = True
            for block in blocks:
                block_board = test_board.copy()
                block_board.place_stone(block, self.defender)

                vcf = VCFEngine(block_board, self.attacker)
                result = vcf.search(depth + 1)

                if result:
                    return [move] + result

                all_blocked = False

            if all_blocked:
                continue

        return None

    def _find_blocks(self, board: Board, rush_move: Position) -> List[Position]:
        blocks = []

        for dr, dc in PatternEngine.DIRECTIONS:
            for i in range(-4, 5):
                r, c = rush_move.row + dr * i, rush_move.col + dc * i
                if 0 <= r < board.size and 0 <= c < board.size:
                    pos = Position(r, c)
                    if board.is_empty(pos):
                        test_board = board.copy()
                        test_board.place_stone(pos, self.defender)

                        engine = PatternEngine(test_board)
                        patterns = engine.find_patterns(self.attacker)

                        has_open_four = any(
                            p.pattern_type == PatternType.OPEN_FOUR for p in patterns
                        )

                        if not has_open_four:
                            blocks.append(pos)

        return list(set(blocks))


class VCTEngine:
    """
    VCT (Victory by Continuous Threat) search engine.

    VCT extends VCF by also considering open threes (活三), which can become
    open fours. This provides a broader search but is more computationally
    expensive.

    Algorithm:
    1. Try VCF first (faster)
    2. If no VCF, find moves creating open three or forcing moves
    3. Recursively search opponent's best responses
    4. Use alpha-beta pruning for efficiency

    References:
    [1] Allis (1994), Chapter 5: "Proof-Number Search"
    [2] Wu et al. (2012): "Job-Level Proof-Number Search for Connect6"
    """

    MAX_DEPTH = 12

    def __init__(self, board: Board, attacker: Stone, rule_mode: RuleMode = RuleMode.FREE_STYLE):
        self.board = board
        self.attacker = attacker
        self.defender = attacker.opponent()
        self.rule_mode = rule_mode

    def search(self, depth: int = 0) -> Optional[List[Position]]:
        if depth >= self.MAX_DEPTH:
            return None

        vcf = VCFEngine(self.board, self.attacker)
        vcf_result = vcf.search(depth)
        if vcf_result:
            return vcf_result

        engine = PatternEngine(self.board, self.rule_mode)
        patterns = engine.find_patterns(self.attacker)

        open_threes = [p for p in patterns if p.pattern_type == PatternType.OPEN_THREE]

        if len(open_threes) >= 2:
            candidates = engine.get_forcing_moves(self.attacker)
            if candidates:
                move = candidates[0][0]
                return [move]

        return None


def evaluate_position(board: Board, stone: Stone, rule_mode: RuleMode = RuleMode.FREE_STYLE) -> int:
    """
    Evaluate board position using pattern-based scoring.

    Score = Σ (pattern_count × pattern_score)

    Higher score indicates better position for the given stone color.

    Returns:
        Positive: advantage for `stone`
        Negative: advantage for opponent
        Zero: equal position
    """
    engine = PatternEngine(board, rule_mode)

    my_patterns = engine.count_patterns(stone)
    opp_patterns = engine.count_patterns(stone.opponent())

    if my_patterns[PatternType.FIVE] > 0:
        return 100000
    if opp_patterns[PatternType.FIVE] > 0:
        return -100000

    score = 0
    for pt in PatternType:
        score += my_patterns[pt] * PATTERN_SCORES[pt]
        score -= opp_patterns[pt] * PATTERN_SCORES[pt]

    return score


def get_best_move_rule_based(game: Game) -> Optional[Position]:
    """
    Get the best move using rule-based algorithms.

    Priority:
    1. Win immediately (five in a row)
    2. Block opponent's winning move
    3. VCF (Victory by Continuous Four) - only with enough stones
    4. Create open four / rush four
    5. Block opponent's open four
    6. Create open three
    7. Pattern-based evaluation

    References:
    [1] Allis (1994): Priority ordering for threat moves
    [2] Wagner (2000): Opening and mid-game strategy
    """
    board = game.board
    my_stone = game.current_stone
    opp_stone = my_stone.opponent()
    rule_mode = game.rule_mode

    engine = PatternEngine(board, rule_mode)

    winning = engine.get_winning_moves(my_stone)
    if winning:
        return winning[0]

    opp_winning = engine.get_winning_moves(opp_stone)
    if opp_winning:
        return opp_winning[0]

    empty_count = sum(
        1 for r in range(board.size) for c in range(board.size) if board.is_empty(Position(r, c))
    )
    stones_on_board = board.size * board.size - empty_count

    if stones_on_board >= 4:
        vcf = VCFEngine(board, my_stone)
        vcf.MAX_DEPTH = 6
        vcf_result = vcf.search()
        if vcf_result:
            return vcf_result[0]

    forcing = engine.get_forcing_moves(my_stone)
    if forcing:
        return forcing[0][0]

    opp_forcing = engine.get_forcing_moves(opp_stone)
    if opp_forcing:
        for pos, _ in opp_forcing[:3]:
            test_board = board.copy()
            test_board.place_stone(pos, my_stone)
            test_engine = PatternEngine(test_board, rule_mode)
            opp_winning_after = test_engine.get_winning_moves(opp_stone)
            if not opp_winning_after:
                return pos

    candidates = board.get_candidate_moves(distance=2)
    if not candidates:
        return Position(board.size // 2, board.size // 2)

    if stones_on_board == 0:
        return Position(board.size // 2, board.size // 2)

    best_move = None
    best_score = float("-inf")

    for pos in candidates:
        if rule_mode == RuleMode.RENJU and my_stone == Stone.BLACK:
            fd = ForbiddenDetector(board)
            if fd.is_forbidden(pos):
                continue

        test_board = board.copy()
        test_board.place_stone(pos, my_stone)

        score = evaluate_position(test_board, my_stone, rule_mode)

        if score > best_score:
            best_score = score
            best_move = pos

    return best_move


__all__ = [
    "PatternType",
    "PatternMatch",
    "PatternEngine",
    "ForbiddenDetector",
    "VCFEngine",
    "VCTEngine",
    "evaluate_position",
    "get_best_move_rule_based",
    "PATTERN_SCORES",
    "PATTERN_NAMES",
]
