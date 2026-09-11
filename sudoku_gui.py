"""
Sudoku Clássico - Interface Gráfica
Jogo de Sudoku com interface amigável usando tkinter (multiplataforma).

Para gerar um executável Windows (.exe):
    pip install pyinstaller
    pyinstaller --onefile --windowed --name Sudoku sudoku_gui.py
"""
import tkinter as tk
from tkinter import messagebox, font as tkfont
import time
import threading
import queue

from sudoku_logic import generate_puzzle, is_valid, board_is_complete_and_valid

# ---------- Cores / Tema ----------
BG_COLOR = "#F4F1EA"
GRID_BG = "#FFFFFF"
THICK_LINE = "#2B2B2B"
THIN_LINE = "#C9C4B8"
GIVEN_COLOR = "#1F2937"
USER_COLOR = "#2563EB"
ERROR_COLOR = "#DC2626"
SELECT_COLOR = "#DCE8FF"
PEER_COLOR = "#EFF4FF"
SAME_NUM_COLOR = "#FDE68A"
BTN_COLOR = "#2563EB"
BTN_TEXT = "#FFFFFF"
BTN_HOVER = "#1D4ED8"
CELL_SIZE = 58


class SudokuGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Sudoku Clássico")
        self.root.configure(bg=BG_COLOR)
        self.root.resizable(False, False)

        self.difficulty = "Médio"
        self.puzzle = None
        self.solution = None
        self.given_mask = None
        self.user_board = None
        self.notes = {}  # (r,c) -> set of candidate numbers
        self.notes_mode = False
        self.selected = None
        self.start_time = None
        self.timer_running = False
        self.hints_used = 0
        self.mistakes = 0

        self.title_font = tkfont.Font(family="Segoe UI", size=20, weight="bold")
        self.label_font = tkfont.Font(family="Segoe UI", size=11)
        self.cell_font = tkfont.Font(family="Segoe UI", size=20)
        self.note_font = tkfont.Font(family="Segoe UI", size=8)
        self.btn_font = tkfont.Font(family="Segoe UI", size=11, weight="bold")

        self._build_layout()
        self.new_game(self.difficulty)
        self._tick_timer()

    # ---------------- Layout ----------------
    def _build_layout(self):
        header = tk.Frame(self.root, bg=BG_COLOR)
        header.pack(pady=(16, 4))

        tk.Label(header, text="Sudoku Clássico", font=self.title_font,
                 bg=BG_COLOR, fg="#1F2937").pack()

        info_frame = tk.Frame(self.root, bg=BG_COLOR)
        info_frame.pack(pady=(4, 8))

        self.timer_label = tk.Label(info_frame, text="⏱ 00:00", font=self.label_font,
                                     bg=BG_COLOR, fg="#374151")
        self.timer_label.grid(row=0, column=0, padx=10)

        self.mistakes_label = tk.Label(info_frame, text="Erros: 0", font=self.label_font,
                                        bg=BG_COLOR, fg="#374151")
        self.mistakes_label.grid(row=0, column=1, padx=10)

        self.hints_label = tk.Label(info_frame, text="Dicas: 0", font=self.label_font,
                                     bg=BG_COLOR, fg="#374151")
        self.hints_label.grid(row=0, column=2, padx=10)

        self.diff_var = tk.StringVar(value=self.difficulty)
        diff_menu = tk.OptionMenu(info_frame, self.diff_var,
                                   "Fácil", "Médio", "Difícil", "Especialista",
                                   command=lambda d: self.new_game(d))
        diff_menu.config(font=self.label_font, bg="white", relief="flat", highlightthickness=1)
        diff_menu.grid(row=0, column=3, padx=10)

        # Grid canvas
        size = CELL_SIZE * 9 + 4
        self.canvas = tk.Canvas(self.root, width=size, height=size,
                                 bg=GRID_BG, highlightthickness=0)
        self.canvas.pack(padx=16, pady=4)
        self.canvas.bind("<Button-1>", self._on_click)
        self.root.bind("<Key>", self._on_key)

        # Number pad + controls
        pad_frame = tk.Frame(self.root, bg=BG_COLOR)
        pad_frame.pack(pady=(8, 4))

        for n in range(1, 10):
            b = tk.Button(pad_frame, text=str(n), width=3, height=1, font=self.btn_font,
                          bg="white", fg="#1F2937", relief="flat", bd=1,
                          highlightbackground=THIN_LINE,
                          command=lambda n=n: self._input_number(n))
            b.grid(row=0, column=n - 1, padx=2, pady=2)

        erase_btn = tk.Button(pad_frame, text="⌫", width=3, height=1, font=self.btn_font,
                               bg="white", fg="#1F2937", relief="flat", bd=1,
                               command=lambda: self._input_number(0))
        erase_btn.grid(row=0, column=9, padx=(8, 2), pady=2)

        controls = tk.Frame(self.root, bg=BG_COLOR)
        controls.pack(pady=(8, 16))

        def make_btn(parent, text, cmd):
            btn = tk.Button(parent, text=text, font=self.btn_font, bg=BTN_COLOR, fg=BTN_TEXT,
                             activebackground=BTN_HOVER, activeforeground=BTN_TEXT,
                             relief="flat", padx=14, pady=8, command=cmd, cursor="hand2")
            return btn

        make_btn(controls, "Novo Jogo", lambda: self.new_game(self.diff_var.get())).grid(row=0, column=0, padx=6)
        self.notes_btn = make_btn(controls, "Anotações: OFF", self._toggle_notes)
        self.notes_btn.grid(row=0, column=1, padx=6)
        make_btn(controls, "Dica", self._give_hint).grid(row=0, column=2, padx=6)
        make_btn(controls, "Verificar", self._check_board).grid(row=0, column=3, padx=6)
        make_btn(controls, "Resolver", self._solve_now).grid(row=0, column=4, padx=6)

    # ---------------- Game setup ----------------
    def new_game(self, difficulty):
        self.difficulty = difficulty
        self.diff_var.set(difficulty)
        self.timer_running = False

        self.canvas.delete("all")
        w = int(self.canvas["width"])
        h = int(self.canvas["height"])
        self.canvas.create_text(w / 2, h / 2, text="Gerando novo jogo...",
                                 font=self.cell_font, fill="#6B7280")
        self.root.update_idletasks()

        result_q = queue.Queue()

        def worker():
            result_q.put(generate_puzzle(difficulty))

        threading.Thread(target=worker, daemon=True).start()
        self._poll_new_game(result_q)

    def _poll_new_game(self, result_q):
        try:
            self.puzzle, self.solution = result_q.get_nowait()
        except queue.Empty:
            self.root.after(50, lambda: self._poll_new_game(result_q))
            return

        self.given_mask = [[self.puzzle[r][c] != 0 for c in range(9)] for r in range(9)]
        self.user_board = [row[:] for row in self.puzzle]
        self.notes = {}
        self.selected = None
        self.hints_used = 0
        self.mistakes = 0
        self.start_time = time.time()
        self.timer_running = True
        self.hints_label.config(text="Dicas: 0")
        self.mistakes_label.config(text="Erros: 0")
        self._draw_board()

    def _tick_timer(self):
        if self.timer_running:
            elapsed = int(time.time() - self.start_time)
            m, s = divmod(elapsed, 60)
            self.timer_label.config(text=f"⏱ {m:02d}:{s:02d}")
        self.root.after(1000, self._tick_timer)

    # ---------------- Drawing ----------------
    def _cell_coords(self, r, c):
        x0 = c * CELL_SIZE + 2
        y0 = r * CELL_SIZE + 2
        return x0, y0, x0 + CELL_SIZE, y0 + CELL_SIZE

    def _draw_board(self):
        self.canvas.delete("all")

        sel_r = sel_c = None
        sel_val = 0
        if self.selected:
            sel_r, sel_c = self.selected
            sel_val = self.user_board[sel_r][sel_c]

        # cell backgrounds
        for r in range(9):
            for c in range(9):
                x0, y0, x1, y1 = self._cell_coords(r, c)
                color = GRID_BG
                val = self.user_board[r][c]
                if self.selected:
                    if r == sel_r and c == sel_c:
                        color = SELECT_COLOR
                    elif r == sel_r or c == sel_c or (r // 3 == sel_r // 3 and c // 3 == sel_c // 3):
                        color = PEER_COLOR
                    if sel_val != 0 and val == sel_val and not (r == sel_r and c == sel_c):
                        color = SAME_NUM_COLOR
                self.canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="")

        # numbers / notes
        for r in range(9):
            for c in range(9):
                x0, y0, x1, y1 = self._cell_coords(r, c)
                val = self.user_board[r][c]
                if val != 0:
                    is_given = self.given_mask[r][c]
                    color = GIVEN_COLOR if is_given else USER_COLOR
                    if not is_given and not is_valid_cell(self.user_board, r, c):
                        color = ERROR_COLOR
                    self.canvas.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=str(val),
                                             font=self.cell_font, fill=color)
                else:
                    cand = self.notes.get((r, c))
                    if cand:
                        self._draw_notes(x0, y0, cand)

        # grid lines
        for i in range(10):
            width = 3 if i % 3 == 0 else 1
            color = THICK_LINE if i % 3 == 0 else THIN_LINE
            self.canvas.create_line(2, i * CELL_SIZE + 2, 9 * CELL_SIZE + 2, i * CELL_SIZE + 2,
                                     fill=color, width=width)
            self.canvas.create_line(i * CELL_SIZE + 2, 2, i * CELL_SIZE + 2, 9 * CELL_SIZE + 2,
                                     fill=color, width=width)

    def _draw_notes(self, x0, y0, cand):
        for n in cand:
            row = (n - 1) // 3
            col = (n - 1) % 3
            nx = x0 + col * (CELL_SIZE / 3) + CELL_SIZE / 6
            ny = y0 + row * (CELL_SIZE / 3) + CELL_SIZE / 6
            self.canvas.create_text(nx, ny, text=str(n), font=self.note_font, fill="#6B7280")

    # ---------------- Interaction ----------------
    def _on_click(self, event):
        c = event.x // CELL_SIZE
        r = event.y // CELL_SIZE
        if 0 <= r < 9 and 0 <= c < 9:
            self.selected = (r, c)
            self._draw_board()

    def _on_key(self, event):
        if not self.selected:
            return
        r, c = self.selected
        if event.keysym in ("Up", "Down", "Left", "Right"):
            dr, dc = {"Up": (-1, 0), "Down": (1, 0), "Left": (0, -1), "Right": (0, 1)}[event.keysym]
            nr, nc = max(0, min(8, r + dr)), max(0, min(8, c + dc))
            self.selected = (nr, nc)
            self._draw_board()
            return
        if event.char in "123456789":
            self._input_number(int(event.char))
        elif event.keysym in ("BackSpace", "Delete"):
            self._input_number(0)

    def _input_number(self, n):
        if not self.selected:
            return
        r, c = self.selected
        if self.given_mask[r][c]:
            return

        if self.notes_mode and n != 0:
            cand = self.notes.setdefault((r, c), set())
            if n in cand:
                cand.remove(n)
            else:
                cand.add(n)
            self._draw_board()
            return

        prev = self.user_board[r][c]
        self.user_board[r][c] = n
        if n != 0:
            self.notes.pop((r, c), None)
            self._clear_peer_notes(r, c, n)
            if n != self.solution[r][c] and prev != n:
                self.mistakes += 1
                self.mistakes_label.config(text=f"Erros: {self.mistakes}")

        self._draw_board()
        self._check_win_silent()

    def _clear_peer_notes(self, r, c, n):
        """Remove a anotação 'n' das células da mesma linha, coluna e quadrante."""
        box_r, box_c = (r // 3) * 3, (c // 3) * 3
        peers = set()
        for i in range(9):
            peers.add((r, i))
            peers.add((i, c))
        for pr in range(box_r, box_r + 3):
            for pc in range(box_c, box_c + 3):
                peers.add((pr, pc))
        peers.discard((r, c))

        for pos in peers:
            cand = self.notes.get(pos)
            if cand and n in cand:
                cand.discard(n)
                if not cand:
                    self.notes.pop(pos, None)

    def _toggle_notes(self):
        self.notes_mode = not self.notes_mode
        self.notes_btn.config(text=f"Anotações: {'ON' if self.notes_mode else 'OFF'}",
                               bg=("#059669" if self.notes_mode else BTN_COLOR))

    def _give_hint(self):
        if not self.selected:
            messagebox.showinfo("Dica", "Selecione uma célula vazia primeiro.")
            return
        r, c = self.selected
        if self.given_mask[r][c] or self.user_board[r][c] == self.solution[r][c]:
            messagebox.showinfo("Dica", "Selecione uma célula vazia ou incorreta.")
            return
        self.user_board[r][c] = self.solution[r][c]
        self.notes.pop((r, c), None)
        self._clear_peer_notes(r, c, self.solution[r][c])
        self.hints_used += 1
        self.hints_label.config(text=f"Dicas: {self.hints_used}")
        self._draw_board()
        self._check_win_silent()

    def _check_board(self):
        errors = 0
        for r in range(9):
            for c in range(9):
                v = self.user_board[r][c]
                if v != 0 and not self.given_mask[r][c] and v != self.solution[r][c]:
                    errors += 1
        if errors == 0:
            filled = all(self.user_board[r][c] != 0 for r in range(9) for c in range(9))
            if filled:
                self._on_win()
            else:
                messagebox.showinfo("Verificação", "Até agora está tudo certo! Continue.")
        else:
            messagebox.showwarning("Verificação", f"Encontrado(s) {errors} número(s) incorreto(s).")

    def _solve_now(self):
        if messagebox.askyesno("Resolver", "Isso vai preencher a solução completa. Deseja continuar?"):
            self.user_board = [row[:] for row in self.solution]
            self.notes = {}
            self.timer_running = False
            self._draw_board()

    def _check_win_silent(self):
        filled = all(self.user_board[r][c] != 0 for r in range(9) for c in range(9))
        if filled and board_is_complete_and_valid([row[:] for row in self.user_board]):
            self._on_win()

    def _on_win(self):
        self.timer_running = False
        elapsed = int(time.time() - self.start_time)
        m, s = divmod(elapsed, 60)
        messagebox.showinfo("Parabéns!",
                             f"Você completou o Sudoku em {m:02d}:{s:02d}\n"
                             f"Erros: {self.mistakes} | Dicas usadas: {self.hints_used}")


def is_valid_cell(board, row, col):
    val = board[row][col]
    if val == 0:
        return True
    board[row][col] = 0
    ok = is_valid(board, val, (row, col))
    board[row][col] = val
    return ok


def main():
    root = tk.Tk()
    app = SudokuGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
