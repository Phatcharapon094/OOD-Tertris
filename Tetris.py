import random
import os
import time

try:
    import msvcrt
    WINDOWS = True
except ImportError:
    WINDOWS = False
    import sys, tty, termios, select

# 🎨 ANSI สี
COLORS = {
    'I': "\033[96m██\033[0m",   # ฟ้า
    'J': "\033[94m██\033[0m",   # น้ำเงิน
    'L': "\033[93m██\033[0m",   # เหลือง
    'O': "\033[97m██\033[0m",   # ขาว
    'S': "\033[92m██\033[0m",   # เขียว
    'T': "\033[95m██\033[0m",   # ม่วง
    'Z': "\033[91m██\033[0m",   # แดง
    ' ': "  "
}

# ---------------- GridNode ----------------
class GridNode:
    def __init__(self, x, y, value=' '):
        self.x, self.y = x, y
        self.value = value
        self.up = self.down = self.left = self.right = None

    def set_value(self, v):
        self.value = v

    def is_empty(self):
        return self.value == ' '

# ---------------- 2D Linked List ----------------
class Grid2DLink:
    def __init__(self, width, height):
        self.width, self.height = width, height
        self.head = None
        self._build_grid()

    def _build_grid(self):
        prev_row = None
        for y in range(self.height):
            row_start = None
            prev_node = None
            for x in range(self.width):
                node = GridNode(x, y)
                if not self.head:
                    self.head = node
                if not row_start:
                    row_start = node
                if prev_node:
                    prev_node.right = node
                    node.left = prev_node
                if prev_row:
                    upper = prev_row
                    for _ in range(x):
                        upper = upper.right
                    upper.down = node
                    node.up = upper
                prev_node = node
            prev_row = row_start

    def get_node(self, x, y):
        node = self.head
        for _ in range(y):
            node = node.down
        for _ in range(x):
            node = node.right
        return node

    def clear_full_rows(self):
        lines = 0
        y = self.height - 1
        while y >= 0:
            full = True
            row = self.get_node(0, y)
            cur = row
            for _ in range(self.width):
                if cur.is_empty():
                    full = False
                    break
                cur = cur.right

            if full:
                lines += 1
                # ✅ เลื่อนบรรทัดบนลงมา
                for yy in range(y, 0, -1):  # จากแถว y ขึ้นไปเรื่อย ๆ
                    for x in range(self.width):
                        self.get_node(x, yy).set_value(self.get_node(x, yy - 1).value)
                # ✅ แถวบนสุดให้เป็นว่าง
                for x in range(self.width):
                    self.get_node(x, 0).set_value(' ')
            else:
                y -= 1
        return lines


    def place_block(self, block, pos):
        x0, y0 = pos
        game_over = False
        for i, row in enumerate(block.shape):
            for j, val in enumerate(row):
                if val != ' ':
                    x, y = x0 + j, y0 + i
                    if 0 <= x < self.width and 0 <= y < self.height:
                        node = self.get_node(x, y)
                        node.set_value(block.color_key)
                        if y0 <= 0:
                            game_over = True
        return game_over

    def is_valid_position(self, block, pos):
        x0, y0 = pos
        for i, row in enumerate(block.shape):
            for j, val in enumerate(row):
                if val != ' ':
                    x, y = x0 + j, y0 + i
                    if x < 0 or x >= self.width: return False
                    if y >= self.height: return False
                    if y >= 0 and not self.get_node(x, y).is_empty():
                        return False
        return True

# ---------------- Block ----------------
class Block:
    def __init__(self, shape, color_key='O'):
        self.shape = shape
        self.color_key = color_key
        self.position = (0, 0)

    def move(self, direction):
        x, y = self.position
        if direction == 'left': self.position = (x - 1, y)
        elif direction == 'right': self.position = (x + 1, y)
        elif direction == 'down': self.position = (x, y + 1)
        return self.position

    def rotate(self):
        self.shape = [list(r) for r in zip(*self.shape[::-1])]

# ---------------- Queue ----------------
class PieceQueue:
    def __init__(self):
        self.tetrominoes = {
            'I': [['#','#','#','#']],
            'J': [['#',' ',' '], ['#','#','#']],
            'L': [[' ',' ','#'], ['#','#','#']],
            'O': [['#','#'], ['#','#']],
            'S': [[' ','#','#'], ['#','#',' ']],
            'T': [[' ','#',' '], ['#','#','#']],
            'Z': [['#','#',' '], [' ','#','#']]
        }
        self.keys = list(self.tetrominoes.keys())
        self.queue = []
        self.refill()

    def refill(self):
        for k in random.sample(self.keys, len(self.keys)):
            self.queue.append(Block([list(r) for r in self.tetrominoes[k]], k))

    def next_piece(self):
        if not self.queue:
            self.refill()
        return self.queue.pop(0)

# ---------------- Stack ----------------
class MoveStack:
    def __init__(self):
        self.stack = []

    def push(self, snapshot):
        self.stack.append(snapshot)

    def pop(self):
        return self.stack.pop() if self.stack else None

# ---------------- Copy Grid ----------------
def copy_grid(grid):
    new = Grid2DLink(grid.width, grid.height)
    for y in range(grid.height):
        for x in range(grid.width):
            new.get_node(x, y).set_value(grid.get_node(x, y).value)
    return new

# ---------------- GameBoard ----------------
class GameBoard:
    def __init__(self, w=10, h=20):
        self.width, self.height = w, h
        self.grid = Grid2DLink(w, h)
        self.queue = PieceQueue()
        self.stack = MoveStack()
        self.score, self.level, self.lines = 0, 1, 0
        self.drop_time = 0.8
        self.last_drop = time.time()
        self.is_game_over = False
        self.new_block()

    def save_state(self):
        snapshot = {
            "grid": copy_grid(self.grid),
            "block": Block([row[:] for row in self.current_block.shape], self.current_block.color_key),
            "pos": self.position,
            "score": self.score,
            "lines": self.lines
        }
        self.stack.push(snapshot)

    def new_block(self):
        self.current_block = self.queue.next_piece()
        x = self.width // 2 - len(self.current_block.shape[0]) // 2
        self.position = (x, 0)
        if not self.grid.is_valid_position(self.current_block, self.position):
            self.is_game_over = True

    def rotate_block(self):
        self.save_state()
        old = [row[:] for row in self.current_block.shape]
        self.current_block.rotate()
        if not self.grid.is_valid_position(self.current_block, self.position):
            self.current_block.shape = old

    def move_block(self, d):
        x,y = self.position
        if d=='down': new=(x,y+1)
        elif d=='left': new=(x-1,y)
        elif d=='right': new=(x+1,y)
        else: return
        if self.grid.is_valid_position(self.current_block, new):
            self.save_state()
            self.position=new
        elif d=='down':
            self._lock_block()

    def hard_drop(self):
        self.save_state()
        x,y = self.position
        while self.grid.is_valid_position(self.current_block, (x,y+1)):
            y+=1
        self.position=(x,y)
        self._lock_block()

    def _lock_block(self):
        self.save_state()
        if self.grid.place_block(self.current_block,self.position):
            self.is_game_over=True
            return
        lines=self.grid.clear_full_rows()
        if lines:
            self.score+={1:100,2:300,3:500,4:800}.get(lines,0)*self.level
            self.lines+=lines
        self.new_block()
        self.last_drop=time.time()

    def update(self):
        if time.time()-self.last_drop>=self.drop_time:
            self.move_block('down')
            self.last_drop=time.time()

    def undo(self):
        snapshot = self.stack.pop()
        if snapshot:
            self.grid = copy_grid(snapshot["grid"])
            self.current_block = snapshot["block"]
            self.position = snapshot["pos"]
            self.score = snapshot["score"]
            self.lines = snapshot["lines"]

    def draw(self):
        out="╔"+"══"*self.width+"╗\n"
        for y in range(self.height):
            out+="║"
            for x in range(self.width):
                node=self.grid.get_node(x,y)
                char=node.value
                drawn=False
                if node.is_empty():
                    x0,y0=self.position
                    for r,row in enumerate(self.current_block.shape):
                        for c,val in enumerate(row):
                            if val!=' ' and x0+c==x and y0+r==y:
                                out+=COLORS[self.current_block.color_key]
                                drawn=True
                                break
                        if drawn: break
                if not drawn:
                    out+=COLORS[char]
            out+="║\n"
        out+="╚"+"══"*self.width+"╝\n"
        out+=f"Score:{self.score} | Lines:{self.lines}\n"
        if self.is_game_over: 
            out+="*** GAME OVER ***\n"

        # คู่มือการเล่น
        out+="\n[Controls]\n"
        out+="  ← / A : Move Left\n"
        out+="  → / D : Move Right\n"
        out+="  ↓ / S : Soft Drop\n"
        out+="  ↑ / W : Rotate\n"
        out+="  Space : Hard Drop\n"
        out+="  U     : Undo last move\n"
        out+="  Q     : Quit game\n"

        os.system('cls' if WINDOWS else 'clear')
        print(out)

# ---------------- Input ----------------
def get_input():
    if WINDOWS:
        if msvcrt.kbhit():
            k=msvcrt.getch()
            if k==b'\xe0': k=msvcrt.getch(); return {b'H':'up',b'P':'down',b'K':'left',b'M':'right'}.get(k)
            return k.decode().lower()
    else:
        if sys.stdin in select.select([sys.stdin],[],[],0)[0]:
            return sys.stdin.read(1)
    return None

# ---------------- Main ----------------
def main():
    game=GameBoard()
    if not WINDOWS: tty.setcbreak(sys.stdin.fileno())
    try:
        while not game.is_game_over:
            key=get_input()
            if key:
                if key in('q','Q'): break
                if key in('a','left'): game.move_block('left')
                elif key in('d','right'): game.move_block('right')
                elif key in('s','down'): game.move_block('down')
                elif key in('w','up'): game.rotate_block()
                elif key==' ': game.hard_drop()
                elif key=='u': game.undo()
            game.update()
            game.draw()
            time.sleep(0.05)
    finally:
        if not WINDOWS: termios.tcsetattr(sys.stdin, termios.TCSADRAIN, termios.tcgetattr(sys.stdin))

if __name__=="__main__":
    main()
