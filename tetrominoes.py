# %%
import sys
import os
import math
import random
from enum import Enum, IntEnum
import copy
import threading
import time

import tkinter as tk


class GameState:
    STANDBY = 1
    PLAYING = 2
    GAMEOVER = 3


def generate_shape():
    shapes = [
        [
            ' #',
            ' #',
            '##',
        ],
        [
            ' #',
            '##',
            '# ',
        ],
        [
            ' #',
            '##',
            ' #',
        ],
        [
            '##',
            '##',
        ],
        [
            '#',
            '#',
            '#',
            '#',
        ],
    ]
    shape = random.choice(shapes)
    reverse = random.choice([False, True, ])
    if reverse:
        for i in range(len(shape)):
            shape[i] = shape[i][::-1]
    return shape

class MinoState(IntEnum):
    STANDBY = 1
    FALLING = 2
    LANDING = 3
    LANDED = 4

    def check_next(self, next_state):
        return self < next_state or (self == MinoState.LANDED) and (next_state == MinoState.STANDBY)

    def is_shown(self):
        return self in (MinoState.STANDBY, MinoState.FALLING, MinoState.LANDING)


class Mino:
    progress = 0
    # 着陸態勢フラグ
    state = MinoState.STANDBY
    lock = None

    def __init__(self, shape):
        self.shape = shape
        self.lock = threading.Lock()
        self.x = math.floor((width - len(shape[0])) // 2)
        self.y = math.floor(0)

    def change_state(self, next_state: MinoState):
        msg = f'不正な状態遷移({self.state} -> {next_state})'
        assert self.state.check_next(next_state), msg
        self.state = next_state

    def fall(self):
        def falling(lock):
            unit = 1.0 / size
            elapsed = time.perf_counter() - p1
            step = 0
            while elapsed < 1 and step < size:
                elapsed = time.perf_counter() - p1
                time.sleep((1 - elapsed) / (size - step))
                with lock:
                    if self.state in (MinoState.FALLING, MinoState.LANDING):
                        self.progress += unit
                        if self.progress > 1:
                            self.progress = 1
                            break
                    else:
                        break
                remain = time.perf_counter() - p1
                step += 1
            with lock:
                if self.state is MinoState.FALLING:
                    if is_conflicted(field, mino, 0, 1):
                        self.change_state(MinoState.LANDING)
                        self.change_state(MinoState.LANDED)
                    else:
                        self.y += 1
                        self.change_state(MinoState.LANDED)
                        self.change_state(MinoState.STANDBY)
                elif self.state is MinoState.LANDING:
                    # 着地
                    self.change_state(MinoState.LANDED)
                self.progress = 0
        if self.state is not MinoState.STANDBY:
            return
        p1 = time.perf_counter()
        th = threading.Thread(target=falling, args=(self.lock,))
        if is_conflicted(field, mino, 0, 1):
            # 下にブロックがあるので着陸態勢に入る
            self.change_state(MinoState.LANDING)
        else:
            self.change_state(MinoState.FALLING)
        self.progress = 0
        th.start()
    
    def left(self, reverse=False):
        if not self.state.is_shown():
            return
        dx = -1 if not reverse else 1
        with self.lock:
            if is_conflicted(field, self, dx):
                return
            px = self.x + dx
            if 0 <= px < width:
                self.x = px
    
    def right(self):
        self.left(reverse=True)

    def up(self):
        if not self.state.is_shown():
            return
        self.y -= 1

    def down(self):
        with self.lock:
            if self.state is MinoState.LANDED:
                pass
            elif self.state is MinoState.LANDING:
                self.change_state(MinoState.LANDED)
                self.progress = 0
            elif self.state in (MinoState.STANDBY, MinoState.FALLING):
                if not is_conflicted(field, self, dy=1):
                    self.y += 1
                    self.change_state(MinoState.LANDED)
                    self.change_state(MinoState.STANDBY)
                    self.progress = 0
                    return True
        return False

    def _rotate(self, reverse=False):
        w = len(self.shape[0])
        h = len(self.shape)
        new_shape = [[' '] * h for _ in range(w)]
        for y in range(h):
            for x in range(w):
                if self.shape[y][x] == '#':
                    if reverse:
                        ny = x
                        nx = h - y - 1
                    else:
                        ny = w - x -1
                        nx = y
                    new_shape[ny][nx] = '#'
        self.shape = new_shape
        # theta = math.pi/2
        # math.floor(math.cos(theta) * x - math.sin(theta) * y)
        # math.floor(math.sin(theta) * x + math.cos(theta) * y)
    def rotate_left(self):
        with self.lock:
            self._rotate()
            if is_conflicted(field, mino):
                self._rotate(reverse=True)

    def rotate_right(self):
        with self.lock:
            self._rotate(reverse=True)
            if is_conflicted(field, mino):
                self._rotate()
    
    def drop(self):
        while self.down():
            self.erase()
            self.draw()
            cv.update()
            time.sleep(0.0017)
        with self.lock:
            self.change_state(MinoState.LANDED)
            self.progress = 0

    def draw(self):
        if not self.state.is_shown():
            return
        with self.lock:
            progress = 0 if self.state is MinoState.LANDING else self.progress
            cx, cy = self.x, self.y
        for y, line in enumerate(mino.shape):
            for x, cell in enumerate(line):
                if cell == "#":
                    px, py = cx + x, cy + y + progress
                    cv.create_rectangle(
                        px * size, py * size,
                        (px+1) * size -1, (py+1) * size -1,
                        outline='midnightblue', fill='royalblue', tag='mino')
    
    def erase(self):
        cv.delete('mino')


class Field:
    def __init__(self):
        self.shape = []
        for y in range(height-1):
            self.shape.append(self.new_line())
        self.shape.append(['#'] * width)

    def new_line(self):
        return [
            "#" if x in (0, width-1) else " "
            for x in range(width)
        ]

    def fix(self, mino):
        mx, my = mino.x, mino.y
        for y, line in enumerate(mino.shape):
            for x, cell in enumerate(line):
                if cell != '#': continue
                px, py = mx + x, my + y
                self.shape[py][px] = '#'
        # self.text_display()
        self.draw()
        cv.update()

    def text_display(self):
        screen = copy.deepcopy(field.shape)
        for line in screen:
            print(" ".join(line))

    def erase(self):
        cv.delete('field')

    def draw(self):
        for y, line in enumerate(self.shape):
            for x, cell in enumerate(line):
                if cell != '#': continue
                cv.create_rectangle(
                    x * size, y * size,
                    (x+1) * size -1, (y+1) * size -1,
                    outline='dimgray', fill='gray', tag='field')

    def clear_line(self):
        targets = []
        for y in range(len(self.shape) - 2, -1, -1):
            line = self.shape[y]
            if all(map(lambda x: x == '#', line[1:-1])):
                self.shape.pop(y)
                targets.append(y)
        if not targets:
            return
        for i in range(-255, 256, 2):
            cv.delete('effect')
            color = '#' + f'{math.floor(255-(i/16)**2):02x}'*3
            for y in targets:
                cv.create_rectangle(
                    size, y * size,
                    (width-1) * size-1, (y+1) * size -1,
                    outline=color, fill=color, tag='effect')
            cv.pack()
            cv.update()
            time.sleep(0.0001)
        for _ in targets:
            self.shape.insert(0, self.new_line())
        cv.delete('effect')

def is_conflicted(field, mino, dx = 0, dy = 0):
    mx, my = mino.x + dx, mino.y + dy
    for y, line in enumerate(mino.shape):
        for x, cell in enumerate(line):
            if cell == ' ': continue
            px, py = mx + x, my + y
            if field.shape[py][px] != ' ':
                return True


# Presentation
def display():
    cv.delete('newgame')
    cv.delete('gameover')
    if game_state == GameState.STANDBY:
        cv.create_text(win_width/2, win_height/2, fill='blue', text='TETROMINOES', font="Tetris 50 ", tag="newgame")
    elif game_state == GameState.PLAYING:
        mino.erase()
        field.erase()
        field.draw()
        mino.draw()
    elif game_state == GameState.GAMEOVER:
        mino.erase()
        field.erase()
        field.draw()
        mino.draw()
        cv.create_text(win_width/2, win_height/2, fill='red', text='GAMEOVER!', font="Tetris 50 ", tag="gameover")
        time.sleep(0.1)
    cv.update()


# Key Input
def processKey(ev):
    """
    See: https://www.tcl.tk/man/tcl8.4/TkCmd/keysyms.htm
    """
    global mino
    # keycodeのほうが速いかも
    if ev.keysym == 'Escape':
        quit()
    elif ev.keysym in ('space', 'Return'):
        if game_state == GameState.PLAYING:
            mino.drop()
        else:
            newgame()
    elif ev.keysym in ('h', 'H', 'Left'):
        mino.left()
    elif ev.keysym in ('l', 'L', 'Right'):
        mino.right()
    elif ev.keysym in ('j', 'J', 'Down'):
        mino.down()
    elif ev.keysym in ('k', 'Up', 'r', 'E'):
        mino.rotate_right()
    elif ev.keysym in ('K', 'R', 'e'):
        mino.rotate_left()
    else:
        pass
        # print(ev)

def newgame():
    global field
    global mino
    global game_state
    field = Field()
    mino = Mino(generate_shape())
    game_state = GameState.PLAYING
    gameloop()
    
def gameover():
    global game_state
    game_state = GameState.GAMEOVER
    display()


def quit():
    cv.destroy()
    root.destroy()

def gameloop():
    global mino
    global game_state
    if game_state is GameState.PLAYING:
        with mino.lock:
            if mino.state is MinoState.LANDED:
                display()
                field.fix(mino)
                # clear
                field.clear_line()
                # new mino
                mino = Mino(generate_shape())
                if is_conflicted(field, mino):
                    gameover()
            if game_state is GameState.PLAYING and mino.state is MinoState.STANDBY:
                mino.fall()
    display()
    root.after(tick, gameloop)

def start():
    root.bind('<Key>', processKey)
    display()
    root.mainloop()


# initialize
root = tk.Tk()
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
width = 12
height = 21
# size = 40
# fps = 60
# win_width = width * size
# win_height = height * size
fps = 60
win_height = math.floor(screen_height * 0.8)
size = math.floor(win_height / height)
win_width = size * width
win_center_x = win_width/2
tick = math.ceil(1000/fps)

root.title('Tetrominoes')
win_px = math.floor((screen_width+win_height)/2)
win_py = math.floor((screen_height - win_height) / 2)
root.geometry(f'{width*size}x{height*size}+{win_px}+{win_py}')
cv = tk.Canvas(root, width=win_width, height=win_height)
cv.pack()

mino = None
field = None
game_state = GameState.STANDBY


if __name__ == '__main__':
    start()
