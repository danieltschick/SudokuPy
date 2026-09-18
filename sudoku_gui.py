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
SAME_NUM_COLOR = "#FDE68A"
PEER_COLOR = "#EFF4FF"
MODE_ON_COLOR = "#059669"
BTN_COLOR = "#2563EB"
BTN_TEXT = "#FFFFFF"
BTN_HOVER = "#1D4ED8"
CELL_SIZE = 58

# Modos de interação (mutuamente exclusivos)
MODE_WRITE = "write"      # clique escreve o número armado na célula
MODE_NOTES = "notes"      # clique alterna o número armado como anotação
MODE_HINT = "hint"        # clique revela a resposta correta da célula


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
        self.notes = {}  # (r,c) -> set de números candidatos
        self.mode = MODE_WRITE
        self.pending_number = None  # número "armado" (usado nos modos Escrever/Anotação)
        self.hover_cell = None  # (r, c) sob o cursor, para o destaque de linha/coluna/quadrante
        self.start_time = None
        self.timer_running = False
        self.hints_used = 0
        self.mistakes = 0

        self.title_font = tkfont.Font(family="Segoe UI", size=18, weight="bold")
        self.label_font = tkfont.Font(family="Segoe UI", size=11)
        self.cell_font = tkfont.Font(family="Segoe UI", size=20)
        self.note_font = tkfont.Font(family="Segoe UI", size=8)
        self.btn_font = tkfont.Font(family="Segoe UI", size=11, weight="bold")

        self._build_layout()
        self.new_game(self.difficulty)
        self._tick_timer()

    # ---------------- Layout ----------------
    def _build_layout(self):
        main = tk.Frame(self.root, bg=BG_COLOR)
        main.pack(padx=16, pady=16)

        # ---------- Coluna esquerda: título + tabuleiro ----------
        left = tk.Frame(main, bg=BG_COLOR)
        left.grid(row=0, column=0, sticky="n")

        tk.Label(left, text="Sudoku Clássico", font=self.title_font,
                 bg=BG_COLOR, fg="#1F2937").pack(anchor="w", pady=(0, 8))

        size = CELL_SIZE * 9 + 4
        self.canvas = tk.Canvas(left, width=size, height=size,
                                 bg=GRID_BG, highlightthickness=0)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Motion>", self._on_hover)
        self.canvas.bind("<Leave>", self._on_hover_leave)
        self.root.bind("<Key>", self._on_key)

        # ---------- Coluna direita: barra lateral ----------
        sidebar = tk.Frame(main, bg=BG_COLOR, width=210)
        sidebar.grid(row=0, column=1, sticky="n", padx=(20, 0))
        sidebar.grid_propagate(False)

        # Dificuldade
        tk.Label(sidebar, text="Dificuldade", font=self.label_font,
                 bg=BG_COLOR, fg="#374151").pack(anchor="w")
        self.diff_var = tk.StringVar(value=self.difficulty)
        diff_menu = tk.OptionMenu(sidebar, self.diff_var,
                                   "Fácil", "Médio", "Difícil", "Especialista",
                                   command=lambda d: self.new_game(d))
        diff_menu.config(font=self.label_font, bg="white", relief="flat",
                          highlightthickness=1, anchor="w")
        diff_menu.pack(fill="x", pady=(2, 12))

        # Info: timer, erros, dicas
        info_frame = tk.Frame(sidebar, bg=BG_COLOR)
        info_frame.pack(fill="x", pady=(0, 12))

        self.timer_label = tk.Label(info_frame, text="⏱ 00:00", font=self.label_font,
                                     bg=BG_COLOR, fg="#374151", anchor="w")
        self.timer_label.pack(fill="x", pady=1)

        self.mistakes_label = tk.Label(info_frame, text="Erros: 0", font=self.label_font,
                                        bg=BG_COLOR, fg="#374151", anchor="w")
        self.mistakes_label.pack(fill="x", pady=1)

        self.hints_label = tk.Label(info_frame, text="Dicas: 0", font=self.label_font,
                                     bg=BG_COLOR, fg="#374151", anchor="w")
        self.hints_label.pack(fill="x", pady=1)

        # Teclado numérico (grid 3x3 + apagar)
        tk.Label(sidebar, text="Números", font=self.label_font,
                 bg=BG_COLOR, fg="#374151").pack(anchor="w")
        pad_frame = tk.Frame(sidebar, bg=BG_COLOR)
        pad_frame.pack(pady=(2, 12))

        for n in range(1, 10):
            row, col = divmod(n - 1, 3)
            b = tk.Button(pad_frame, text=str(n), width=3, height=1, font=self.btn_font,
                          bg="white", fg="#1F2937", relief="flat", bd=1,
                          highlightbackground=THIN_LINE,
                          command=lambda n=n: self._select_number(n))
            b.grid(row=row, column=col, padx=2, pady=2)

        erase_btn = tk.Button(pad_frame, text="⌫ Apagar", width=11, height=1, font=self.btn_font,
                               bg="white", fg="#1F2937", relief="flat", bd=1,
                               command=lambda: self._select_number(0))
        erase_btn.grid(row=3, column=0, columnspan=3, padx=2, pady=(6, 2), sticky="ew")

        # Botões de controle (empilhados)
        controls = tk.Frame(sidebar, bg=BG_COLOR)
        controls.pack(fill="x")

        def make_btn(parent, text, cmd):
            btn = tk.Button(parent, text=text, font=self.btn_font, bg=BTN_COLOR, fg=BTN_TEXT,
                             activebackground=BTN_HOVER, activeforeground=BTN_TEXT,
                             relief="flat", padx=10, pady=8, command=cmd, cursor="hand2")
            return btn

        make_btn(controls, "Novo Jogo (N)", lambda: self.new_game(self.diff_var.get())).pack(fill="x", pady=3)
        self.notes_btn = make_btn(controls, "Anotações: OFF (A)", self._toggle_notes_mode)
        self.notes_btn.pack(fill="x", pady=3)
        self.hint_btn = make_btn(controls, "Dica: OFF (D)", self._toggle_hint_mode)
        self.hint_btn.pack(fill="x", pady=3)
        make_btn(controls, "Reiniciar (R)", self._restart).pack(fill="x", pady=3)
        make_btn(controls, "Solução (S)", self._solve_now).pack(fill="x", pady=3)

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
        self.pending_number = None
        self.mode = MODE_WRITE
        self._refresh_mode_buttons()
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

        # Número em evidência: o armado, só faz sentido destacar nos modos
        # Escrever/Anotação (no modo Dica não há número armado relevante).
        highlight_val = None
        if self.mode != MODE_HINT and self.pending_number:
            highlight_val = self.pending_number

        # cell backgrounds
        hover_r, hover_c = self.hover_cell if self.hover_cell else (None, None)
        for r in range(9):
            for c in range(9):
                x0, y0, x1, y1 = self._cell_coords(r, c)
                color = GRID_BG
                val = self.user_board[r][c]
                if self.hover_cell and (r == hover_r or c == hover_c or
                                         (r // 3 == hover_r // 3 and c // 3 == hover_c // 3)):
                    color = PEER_COLOR
                if highlight_val:
                    if val == highlight_val:
                        color = SAME_NUM_COLOR
                    elif val == 0 and highlight_val in self.notes.get((r, c), ()):
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
        if not (0 <= r < 9 and 0 <= c < 9):
            return
        if self.given_mask[r][c]:
            return  # célula de pista: não pode ser alterada em nenhum modo

        if self.mode == MODE_HINT:
            self._apply_hint_at(r, c)
        elif self.mode == MODE_NOTES:
            if self.pending_number:  # 0 (apagar) não faz sentido como anotação
                self._toggle_note_at(r, c, self.pending_number)
        else:  # MODE_WRITE
            # Só escreve se a célula estiver vazia, ou se "Apagar" (0) estiver
            # armado — nesse caso pode sempre limpar uma célula preenchida.
            n = self.pending_number
            if n is not None and (n == 0 or self.user_board[r][c] == 0):
                self._write_value_at(r, c, n)

        self._draw_board()

    def _on_hover(self, event):
        c = event.x // CELL_SIZE
        r = event.y // CELL_SIZE
        cell = (r, c) if (0 <= r < 9 and 0 <= c < 9) else None
        if cell != self.hover_cell:
            self.hover_cell = cell
            self._draw_board()

    def _on_hover_leave(self, event):
        if self.hover_cell is not None:
            self.hover_cell = None
            self._draw_board()

    # Teclas de atalho para os botões de ação
    SHORTCUTS = {"n": "_shortcut_new_game", "a": "_toggle_notes_mode", "d": "_toggle_hint_mode",
                 "r": "_restart", "s": "_solve_now"}

    def _on_key(self, event):
        key = event.keysym.lower()
        if key in self.SHORTCUTS:
            getattr(self, self.SHORTCUTS[key])()
            return

        if event.char in "123456789":
            self._select_number(int(event.char))
            return
        if event.keysym in ("BackSpace", "Delete"):
            self._select_number(0)

    def _shortcut_new_game(self):
        self.new_game(self.diff_var.get())

    def _select_number(self, n):
        """Marca 'n' como o número pendente e o destaca no tabuleiro
        (nos modos Escrever/Anotação). Fica armado até o usuário escolher
        outro número ou Apagar."""
        self.pending_number = n
        self._draw_board()

    # ---------------- Ações por célula (uma por modo) ----------------
    def _write_value_at(self, r, c, n):
        prev = self.user_board[r][c]
        self.user_board[r][c] = n
        if n != 0:
            self.notes.pop((r, c), None)
            self._clear_peer_notes(r, c, n)
            if n != self.solution[r][c] and prev != n:
                self.mistakes += 1
                self.mistakes_label.config(text=f"Erros: {self.mistakes}")
        self._check_win_silent()

    def _toggle_note_at(self, r, c, n):
        cand = self.notes.setdefault((r, c), set())
        if n in cand:
            cand.discard(n)
        else:
            cand.add(n)
        if not cand:
            self.notes.pop((r, c), None)

    def _apply_hint_at(self, r, c):
        if self.user_board[r][c] == self.solution[r][c]:
            return  # já está correta, nada a fazer
        self.user_board[r][c] = self.solution[r][c]
        self.notes.pop((r, c), None)
        self._clear_peer_notes(r, c, self.solution[r][c])
        self.hints_used += 1
        self.hints_label.config(text=f"Dicas: {self.hints_used}")
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

    # ---------------- Modos (Anotação / Dica) ----------------
    def _toggle_notes_mode(self):
        self.mode = MODE_WRITE if self.mode == MODE_NOTES else MODE_NOTES
        self._refresh_mode_buttons()
        self._draw_board()

    def _toggle_hint_mode(self):
        self.mode = MODE_WRITE if self.mode == MODE_HINT else MODE_HINT
        self._refresh_mode_buttons()
        self._draw_board()

    def _refresh_mode_buttons(self):
        notes_on = self.mode == MODE_NOTES
        hint_on = self.mode == MODE_HINT
        self.notes_btn.config(text=f"Anotações: {'ON' if notes_on else 'OFF'} (A)",
                               bg=(MODE_ON_COLOR if notes_on else BTN_COLOR))
        self.hint_btn.config(text=f"Dica: {'ON' if hint_on else 'OFF'} (D)",
                              bg=(MODE_ON_COLOR if hint_on else BTN_COLOR))

    def _restart(self):
        if messagebox.askyesno("Reiniciar", "Isso vai apagar tudo e recomeçar o mesmo jogo. Deseja continuar?"):
            self.user_board = [row[:] for row in self.puzzle]
            self.notes = {}
            self.pending_number = None
            self._draw_board()

    def _solve_now(self):
        if messagebox.askyesno("Resolver", "Isso vai preencher a solução completa. Deseja continuar?"):
            self.user_board = [row[:] for row in self.solution]
            self.notes = {}
            self.pending_number = None
            self.mode = MODE_WRITE
            self._refresh_mode_buttons()
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
