# Sudoku Clássico

Jogo de Sudoku com interface gráfica amigável, feito em Python puro com `tkinter`
(biblioteca que já vem instalada com o Python — não precisa instalar nada extra).

## Como jogar

1. Instale o Python 3 (se ainda não tiver): https://www.python.org/downloads/
   - No instalador do Windows, marque a opção **"Add python.exe to PATH"**.
2. Baixe os dois arquivos `sudoku_gui.py` e `sudoku_logic.py` para a mesma pasta.
3. Abra o terminal (Prompt de Comando) nessa pasta e rode:
   ```
   python sudoku_gui.py
   ```

## Funcionalidades

- 4 níveis de dificuldade (Fácil, Médio, Difícil, Especialista)
- Geração de tabuleiros com solução única garantida
- Destaque da linha, coluna e região da célula selecionada
- Números repetidos na mesma linha/coluna/bloco aparecem em **vermelho**
- Modo de anotações (candidatos) por célula
- Botão de Dica, botão Verificar e botão Resolver
- Cronômetro e contador de erros/dicas
- Suporte a teclado: setas para navegar, números para preencher, Backspace/Delete para apagar

## Arquivos

- `sudoku_gui.py` — interface gráfica (tkinter)
- `sudoku_logic.py` — geração de tabuleiro, solucionador (backtracking) e validação

Obs.: Criado com o auxílio do Claude
