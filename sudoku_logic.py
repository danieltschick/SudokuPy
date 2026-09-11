"""
Lógica do Sudoku: geração de tabuleiros, resolução (backtracking) e validação.
"""
import random


def find_empty(board):
    for r in range(9):
        for c in range(9):
            if board[r][c] == 0:
                return r, c
    return None


def is_valid(board, num, pos):
    row, col = pos

    for c in range(9):
        if board[row][c] == num and c != col:
            return False

    for r in range(9):
        if board[r][col] == num and r != row:
            return False

    box_r, box_c = row // 3 * 3, col // 3 * 3
    for r in range(box_r, box_r + 3):
        for c in range(box_c, box_c + 3):
            if board[r][c] == num and (r, c) != pos:
                return False

    return True


def solve(board, randomize=False):
    """Resolve o tabuleiro via backtracking. Retorna True se resolvido."""
    empty = find_empty(board)
    if not empty:
        return True
    row, col = empty

    nums = list(range(1, 10))
    if randomize:
        random.shuffle(nums)

    for num in nums:
        if is_valid(board, num, (row, col)):
            board[row][col] = num
            if solve(board, randomize):
                return True
            board[row][col] = 0

    return False


def count_solutions(board, limit=2):
    """Conta soluções até o limite (usado para garantir unicidade)."""
    empty = find_empty(board)
    if not empty:
        return 1
    row, col = empty
    count = 0
    for num in range(1, 10):
        if is_valid(board, num, (row, col)):
            board[row][col] = num
            count += count_solutions(board, limit)
            board[row][col] = 0
            if count >= limit:
                break
    return count


def generate_full_board():
    board = [[0] * 9 for _ in range(9)]
    solve(board, randomize=True)
    return board


DIFFICULTY_CLUES = {
    "Fácil": 42,
    "Médio": 34,
    "Difícil": 29,
    "Especialista": 27,
}


def generate_puzzle(difficulty="Médio"):
    """Gera um tabuleiro (puzzle, solução) com solução única."""
    full = generate_full_board()
    solution = [row[:] for row in full]
    puzzle = [row[:] for row in full]

    clues_target = DIFFICULTY_CLUES.get(difficulty, 34)
    cells = [(r, c) for r in range(9) for c in range(9)]
    random.shuffle(cells)

    clues = 81
    for (r, c) in cells:
        if clues <= clues_target:
            break
        backup = puzzle[r][c]
        puzzle[r][c] = 0

        board_copy = [row[:] for row in puzzle]
        if count_solutions(board_copy, limit=2) != 1:
            puzzle[r][c] = backup
        else:
            clues -= 1

    return puzzle, solution


def board_is_complete_and_valid(board):
    for r in range(9):
        for c in range(9):
            val = board[r][c]
            if val == 0:
                return False
            board[r][c] = 0
            valid = is_valid(board, val, (r, c))
            board[r][c] = val
            if not valid:
                return False
    return True
