#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
推箱子 Sokoban —— pygame 单文件实现，零外部素材。

操作
    方向键 / WASD   移动（推箱子）
    U               撤销
    Y               重做
    R               重开本关
    N               下一关
    P               上一关
    ESC             菜单 / 返回游戏
    Enter/Space     确认
    M               静音开关

作者：元宝（为陈怡华制作）
许可：MIT
"""

from __future__ import annotations

import math
import os
import random
import sys

import pygame

# ---------------------------------------------------------------- 常量

W_TITLE, W_PLAY, W_LEVELS, W_CLEAR = "title", "play", "levels", "clear"

WIN_W, WIN_H = 900, 700          # 窗口（逻辑画布同尺寸，见 README 说明）
FPS = 60

# 垂直分区（从下往上留够空间，避免棋盘压到按钮行）：
#   [0, HUD_TOP)            顶部信息条
#   [HUD_TOP, BOARD_BOTTOM) 棋盘可用区
#   [BTN_TOP, BTN_TOP+BTN_H) 按钮行
#   [BTN_TOP+BTN_H, WIN_H)   提示文字行
HUD_TOP = 20
HUD_H = 76
BAR_BOTTOM = HUD_TOP + HUD_H          # = 96
BTN_H = 42
HINT_H = 26
BTN_TOP = WIN_H - BTN_H - HINT_H - 6  # = 626
BOARD_TOP = BAR_BOTTOM + 14           # = 110
BOARD_BOTTOM = BTN_TOP - 10           # = 616

FLOOR, WALL, TARGET, PLAYER, BOX, BOX_ON, PLAYER_ON = range(7)

L, R, U, D = 0, 1, 2, 3
DIRS = {L: (-1, 0), R: (1, 0), U: (0, -1), D: (0, 1)}

# 每个状态最多累计多少帧才走一步（按住连续移动）
REPEAT_DELAY = 22                # 首次按住延迟
REPEAT_RATE = 7                  # 之后每帧速率
ANIM_MS = 110                    # 玩家滑动动画时长

# ---------------------------------------------------------------- 60 张经典地图
# 字符约定：
#   '#' 墙   ' ' 地板   '.' 目标点   '$' 箱子   '*' 已在目标上的箱子
#   '@' 玩家  '+' 站在目标上的玩家
# 每张图要求：箱子数 == 目标点数 == 玩家 1 个，且整张图被墙完全封闭。

LEVELS_RAW = [
    [  # 1  (6x7)
        "####  ",
        "# .#  ",
        "#  ###",
        "#*@  #",
        "#  $ #",
        "#  ###",
        "####  ",
    ],
    [  # 2  (6x7)
        "######",
        "#    #",
        "# #@ #",
        "# $* #",
        "# .* #",
        "#    #",
        "######",
    ],
    [  # 3  (9x6)
        "  ####   ",
        "###  ####",
        "#     $ #",
        "# #  #$ #",
        "# . .#@ #",
        "#########",
    ],
    [  # 4  (8x6)
        "########",
        "#      #",
        "# .**$@#",
        "#      #",
        "#####  #",
        "    ####",
    ],
    [  # 5  (8x7)
        " #######",
        " #     #",
        " # .$. #",
        "## $@$ #",
        "#  .$. #",
        "#      #",
        "########",
    ],
    [  # 6  (12x6)
        "###### #####",
        "#    ###   #",
        "# $$     #@#",
        "# $ #...   #",
        "#   ########",
        "#####       ",
    ],
    [  # 7  (7x8)
        "#######",
        "#     #",
        "# .$. #",
        "# $.$ #",
        "# .$. #",
        "# $.$ #",
        "#  @  #",
        "#######",
    ],
    [  # 8  (8x12)
        "  ######",
        "  # ..@#",
        "  # $$ #",
        "  ## ###",
        "   # #  ",
        "   # #  ",
        "#### #  ",
        "#    ## ",
        "# #   # ",
        "#   # # ",
        "###   # ",
        "  ##### ",
    ],
    [  # 9  (6x7)
        "##### ",
        "#.  ##",
        "#@$$ #",
        "##   #",
        " ##  #",
        "  ##.#",
        "   ###",
    ],
    [  # 10  (11x8)
        "      #####",
        "      #.  #",
        "      #.# #",
        "#######.# #",
        "# @ $ $ $ #",
        "# # # # ###",
        "#       #  ",
        "#########  ",
    ],
    [  # 11  (9x8)
        "  ###### ",
        "  #    # ",
        "  # ##@##",
        "### # $ #",
        "# ..# $ #",
        "#       #",
        "#  ######",
        "####     ",
    ],
    [  # 12  (9x8)
        "#####    ",
        "#   ##   ",
        "# $  #   ",
        "## $ ####",
        " ###@.  #",
        "  #  .# #",
        "  #     #",
        "  #######",
    ],
    [  # 13  (7x9)
        "####   ",
        "#. ##  ",
        "#.@ #  ",
        "#. $#  ",
        "##$ ###",
        " # $  #",
        " #    #",
        " #  ###",
        " ####  ",
    ],
    [  # 14  (7x6)
        "#######",
        "#     #",
        "# # # #",
        "#. $*@#",
        "#   ###",
        "#####  ",
    ],
    [  # 15  (9x7)
        "     ### ",
        "######@##",
        "#    .* #",
        "#   #   #",
        "#####$# #",
        "    #   #",
        "    #####",
    ],
    [  # 16  (10x8)
        " ####     ",
        " #  ####  ",
        " #     ## ",
        "## ##   # ",
        "#. .# @$##",
        "#   # $$ #",
        "#  .#    #",
        "##########",
    ],
    [  # 17  (6x7)
        "##### ",
        "# @ # ",
        "#...# ",
        "#$$$##",
        "#    #",
        "#    #",
        "######",
    ],
    [  # 18  (7x9)
        "#######",
        "#     #",
        "#. .  #",
        "# ## ##",
        "#  $ # ",
        "###$ # ",
        "  #@ # ",
        "  #  # ",
        "  #### ",
    ],
    [  # 19  (8x8)
        "########",
        "#   .. #",
        "#  @$$ #",
        "##### ##",
        "   #  # ",
        "   #  # ",
        "   #  # ",
        "   #### ",
    ],
    [  # 20  (9x8)
        "#######  ",
        "#     ###",
        "#  @$$..#",
        "#### ## #",
        "  #     #",
        "  #  ####",
        "  #  #   ",
        "  ####   ",
    ],
    [  # 21  (7x6)
        "####   ",
        "#  ####",
        "# . . #",
        "# $$#@#",
        "##    #",
        " ######",
    ],
    [  # 22  (7x9)
        "#####  ",
        "#   ###",
        "#. .  #",
        "#   # #",
        "## #  #",
        " #@$$ #",
        " #    #",
        " #  ###",
        " ####  ",
    ],
    [  # 23  (7x7)
        "#######",
        "#  *  #",
        "#     #",
        "## # ##",
        " #$@.# ",
        " #   # ",
        " ##### ",
    ],
    [  # 24  (7x7)
        "# #####",
        "  #   #",
        "###$$@#",
        "#   ###",
        "#     #",
        "# . . #",
        "#######",
    ],
    [  # 25  (7x7)
        " ####  ",
        " #  ###",
        " # $$ #",
        "##... #",
        "#  @$ #",
        "#   ###",
        "#####  ",
    ],
    [  # 26  (6x8)
        " #####",
        " # @ #",
        " #   #",
        "###$ #",
        "# ...#",
        "# $$ #",
        "###  #",
        "  ####",
    ],
    [  # 27  (7x7)
        "###### ",
        "#   .# ",
        "# ## ##",
        "#  $$@#",
        "# #   #",
        "#.  ###",
        "#####  ",
    ],
    [  # 28  (7x7)
        "#####  ",
        "#   #  ",
        "# @ #  ",
        "# $$###",
        "##. . #",
        " #    #",
        " ######",
    ],
    [  # 29  (11x9)
        "     ##### ",
        "     #   ##",
        "     #    #",
        " ######   #",
        "##     #. #",
        "# $ $ @  ##",
        "# ######.# ",
        "#        # ",
        "########## ",
    ],
    [  # 30  (6x7)
        "####  ",
        "#  ###",
        "# $$ #",
        "#... #",
        "# @$ #",
        "#   ##",
        "##### ",
    ],
    [  # 31  (7x7)
        "  #### ",
        " ##  # ",
        "##@$.##",
        "# $$  #",
        "# . . #",
        "###   #",
        "  #####",
    ],
    [  # 32  (7x7)
        " ####  ",
        "##  ###",
        "#     #",
        "#.**$@#",
        "#   ###",
        "##  #  ",
        " ####  ",
    ],
    [  # 33  (7x7)
        "#######",
        "#. #  #",
        "#  $  #",
        "#. $#@#",
        "#  $  #",
        "#. #  #",
        "#######",
    ],
    [  # 34  (9x6)
        "  ####   ",
        "###  ####",
        "#       #",
        "#@$***. #",
        "#       #",
        "#########",
    ],
    [  # 35  (7x10)
        "  #### ",
        " ##  # ",
        " #. $# ",
        " #.$ # ",
        " #.$ # ",
        " #.$ # ",
        " #. $##",
        " #   @#",
        " ##   #",
        "  #####",
    ],
    [  # 36  (15x5)
        "####           ",
        "#  ############",
        "# $ $ $ $ $ @ #",
        "# .....       #",
        "###############",
    ],
    [  # 37  (9x8)
        "      ###",
        "##### #.#",
        "#   ###.#",
        "#   $ #.#",
        "# $  $  #",
        "#####@# #",
        "    #   #",
        "    #####",
    ],
    [  # 38  (10x7)
        "##########",
        "#        #",
        "# ##.### #",
        "# # $$ . #",
        "# . @$## #",
        "#####    #",
        "    ######",
    ],
    [  # 39  (10x9)
        "#####     ",
        "#   ####  ",
        "# # # .#  ",
        "#    $ ###",
        "### #$.  #",
        "#   #@   #",
        "# # ######",
        "#   #     ",
        "#####     ",
    ],
    [  # 40  (7x6)
        " ##### ",
        " #   # ",
        "##   ##",
        "# $$$ #",
        "# .+. #",
        "#######",
    ],
    [  # 41  (8x6)
        "####### ",
        "#     # ",
        "#@$$$ ##",
        "#  #...#",
        "##    ##",
        " ###### ",
    ],
    [  # 42  (7x8)
        "   ####",
        "   #  #",
        "   #@ #",
        "####$.#",
        "#   $.#",
        "# # $.#",
        "#    ##",
        "###### ",
    ],
    [  # 43  (9x9)
        "     ####",
        "     # @#",
        "     #  #",
        "###### .#",
        "#   $  .#",
        "#  $$# .#",
        "#    ####",
        "###  #   ",
        "  ####   ",
    ],
    [  # 44  (5x3)
        "#####",
        "#@$.#",
        "#####",
    ],
    [  # 45  (6x7)
        "######",
        "#... #",
        "#  $ #",
        "# #$##",
        "#  $ #",
        "#  @ #",
        "######",
    ],
    [  # 46  (7x8)
        " ######",
        "##    #",
        "#  ## #",
        "# # $ #",
        "#  * .#",
        "## #@##",
        " #   # ",
        " ##### ",
    ],
    [  # 47  (11x7)
        "  #######  ",
        "###     #  ",
        "# $ $   #  ",
        "# ### #####",
        "# @ . .   #",
        "#   ###   #",
        "##### #####",
    ],
    [  # 48  (8x8)
        "######  ",
        "#  @ #  ",
        "#  # ## ",
        "# .#  ##",
        "# .$$$ #",
        "# .#   #",
        "####   #",
        "   #####",
    ],
    [  # 49  (8x10)
        "######  ",
        "# @  #  ",
        "# $# #  ",
        "# $  #  ",
        "# $ ##  ",
        "### ####",
        " #  #  #",
        " #...  #",
        " #     #",
        " #######",
    ],
    [  # 50  (10x7)
        "  ####    ",
        "###  #####",
        "#  $  @..#",
        "# $    # #",
        "### #### #",
        "  #      #",
        "  ########",
    ],
    [  # 51  (8x7)
        "####    ",
        "#  ###  ",
        "#    ###",
        "#  $*@ #",
        "### .# #",
        "  #    #",
        "  ######",
    ],
    [  # 52  (6x8)
        "  ####",
        "### @#",
        "#  $ #",
        "#  *.#",
        "#  *.#",
        "#  $ #",
        "###  #",
        "  ####",
    ],
    [  # 53  (7x7)
        " ##### ",
        "##. .##",
        "# * * #",
        "#  #  #",
        "# $ $ #",
        "## @ ##",
        " ##### ",
    ],
    [  # 54  (12x8)
        "      ######",
        "      #    #",
        "  ##### .  #",
        "###  ###.  #",
        "# $  $  . ##",
        "# @$$ # . # ",
        "##    ##### ",
        " ######     ",
    ],
    [  # 55  (10x8)
        "########  ",
        "# @ #  #  ",
        "#      #  ",
        "#####$ #  ",
        "    #  ###",
        " ## #$ ..#",
        " ## #  ###",
        "    ####  ",
    ],
    [  # 56  (7x6)
        "#####  ",
        "#   ###",
        "#  $  #",
        "##* . #",
        " #   @#",
        " ######",
    ],
    [  # 57  (8x9)
        "  ####  ",
        "  #  #  ",
        "  #@ #  ",
        "  #  #  ",
        "### ####",
        "#    * #",
        "#  $   #",
        "#####. #",
        "    ####",
    ],
    [  # 58  (7x7)
        "####   ",
        "#  ####",
        "#.*$  #",
        "# .$# #",
        "## @  #",
        " #   ##",
        " ##### ",
    ],
    [  # 59  (13x9)
        "############ ",
        "#          # ",
        "# ####### @##",
        "# #         #",
        "# #  $   #  #",
        "# $$ #####  #",
        "###  # # ...#",
        "  #### #    #",
        "       ######",
    ],
    [  # 60  (10x10)
        " #########",
        " #       #",
        "##@##### #",
        "#  #   # #",
        "#  #   $.#",
        "#  ##$##.#",
        "##$##  #.#",
        "#   $  #.#",
        "#   #  ###",
        "########  ",
    ],
]


def parse_level(text_lines):
    """把字符地图解析成 (静态格, 箱子集合, 玩家坐标)。静态格里不含箱子/玩家。

    注意 '*' 同时代表「箱子 + 目标点」，所以它既要进 boxes，也要把该格标成 TARGET。
    这是最容易搞错的一处：只当箱子处理会导致"箱数 > 目标数"、关卡看起来无解。
    """
    static = []
    boxes = set()
    player = None
    for y, line in enumerate(text_lines):
        row = []
        for x, ch in enumerate(line):
            if ch == "#":
                row.append(WALL)
            elif ch == ".":
                row.append(TARGET)
            elif ch == "*":              # 箱子已在目标点上
                row.append(TARGET)
                boxes.add((x, y))
            elif ch == "+":              # 玩家站在目标点上
                row.append(TARGET)
                player = (x, y)
            else:
                row.append(FLOOR)
                if ch == "$":
                    boxes.add((x, y))
                elif ch == "@":
                    player = (x, y)
        static.append(row)
    return static, boxes, player


class Level:
    """一关的全部数据。static 是矩形网格，外围补 FLOOR 以简化越界判断。"""

    def __init__(self, index, text_lines):
        self.index = index
        self.name = f"第 {index} 关"
        rows = [ln for ln in text_lines]
        width = max(len(ln) for ln in rows)
        rows = [ln.ljust(width) for ln in rows]
        static, boxes, player = parse_level(rows)
        self.static = static
        self.w = width
        self.h = len(rows)
        self.start_boxes = frozenset(boxes)
        self.start_player = player
        self.targets = frozenset(
            (x, y) for y in range(self.h) for x in range(self.w)
            if static[y][x] == TARGET
        )

    def cell(self, x, y):
        """越界一律返回 WALL，玩家与箱子都不会跑出地图。"""
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.static[y][x]
        return WALL

    @property
    def n_targets(self):
        return len(self.targets)


# ---------------------------------------------------------------- 求解器（自检用）
#
# 推箱子是 PSPACE-complete，通用求解很贵。这里用"死锁剪枝 + BFS/IDA*"只求
# 一个可行解。它的用途是自检时验证每一关确实可解，以及自动通关跑通整条链路。

def _freeze_deadlock(level):
    """预计算：哪些格子是"箱子推上去就永远回不来"的死格（简单角点判定）。"""
    dead = set()
    static = level.static
    for y in range(level.h):
        for x in range(level.w):
            if static[y][x] != FLOOR:
                continue
            up = level.cell(x, y - 1) == WALL
            dn = level.cell(x, y + 1) == WALL
            lf = level.cell(x - 1, y) == WALL
            rt = level.cell(x + 1, y) == WALL
            if (up or dn) and (lf or rt):
                # 只记"角落"，但排除那些本身是目标点、或紧贴目标点的格子
                if (x, y) not in level.targets:
                    dead.add((x, y))
    return dead


def solve_level(level, node_limit=400000):
    """返回一步序列（0..3 组成的 list），无解返回 None。

    用 A*（盒子到目标的曼哈顿距离和作启发）搜索，配合角点死锁剪枝。
    """
    import heapq

    dead = _freeze_deadlock(level)
    start = (level.start_player, level.start_boxes)
    targets = level.targets

    def heuristic(boxes):
        """贪心最近邻匹配：每个箱子挑最近的目标点，允许一个目标点被多个箱子
        认领（只是启发式，宁可高估也不能崩）。"""
        if not targets:
            return 0
        total = 0
        for b in boxes:
            total += min(abs(b[0] - t[0]) + abs(b[1] - t[1]) for t in targets)
        return total

    def push_deadlocks(boxes):
        return any(b in dead and b not in targets for b in boxes)

    if push_deadlocks(start[1]):
        return None

    counter = 0
    h0 = heuristic(start[1])
    # 堆元素：(f, g, tie, player, boxes_tuple, path)
    heap = [(h0, 0, counter, start[0], tuple(sorted(start[1])), [])]
    seen = {(start[0], tuple(sorted(start[1]))): 0}
    expanded = 0

    while heap:
        f, g, _, player, boxes_t, path = heapq.heappop(heap)
        boxes = set(boxes_t)
        if not boxes - targets:
            return path
        if expanded > node_limit:
            return None
        expanded += 1

        px, py = player
        for d, (dx, dy) in DIRS.items():
            nx, ny = px + dx, py + dy
            if level.cell(nx, ny) == WALL:
                continue
            nb = boxes
            if (nx, ny) in boxes:
                bx, by = nx + dx, ny + dy
                if level.cell(bx, by) == WALL or (bx, by) in boxes:
                    continue
                if (bx, by) in dead and (bx, by) not in targets:
                    continue
                nb = set(boxes)
                nb.remove((nx, ny))
                nb.add((bx, by))
            key = ((nx, ny), tuple(sorted(nb)))
            ng = g + 1
            if seen.get(key, 10 ** 9) <= ng:
                continue
            seen[key] = ng
            counter += 1
            heapq.heappush(heap, (ng + heuristic(nb), ng, counter,
                                  (nx, ny), tuple(sorted(nb)), path + [d]))
    return None


def is_solved(level, boxes):
    return not (set(boxes) - level.targets)


# ---------------------------------------------------------------- 音效

class Sfx:
    """numpy 合成音效；缺 numpy 或缺音频设备时整体降级为静音，绝不崩。"""

    def __init__(self):
        self.ok = False
        self.muted = False
        self.sounds = {}
        try:
            import numpy as np
        except Exception:
            self.np = None
            return
        self.np = np
        try:
            if not pygame.mixer.get_init():
                # pre_init 必须排在 pygame.init() 之前才生效，见调用处
                return
        except Exception:
            return
        try:
            self.sounds = {
                "move": self._tone(300, 240, 0.045, 0.16, "square"),
                "push": self._tone(180, 130, 0.075, 0.24, "saw"),
                "blocked": self._tone(150, 110, 0.06, 0.20, "square"),
                "undo": self._tone(420, 620, 0.07, 0.18, "sine"),
                "redo": self._tone(620, 420, 0.07, 0.18, "sine"),
                "placed": self._tone(660, 880, 0.10, 0.22, "sine"),
                "win": self._chord([523, 659, 784, 1047], 0.42),
                "ui": self._tone(520, 700, 0.05, 0.16, "sine"),
            }
            self.ok = True
        except Exception:
            self.ok = False

    def _tone(self, f0, f1, dur, vol, wave="square", lp=1):
        np = self.np
        n = max(1, int(44100 * dur))
        freq = np.linspace(f0, f1, n)
        phase = np.cumsum(freq) * 2 * np.pi / 44100
        if wave == "square":
            sig = np.sign(np.sin(phase))
        elif wave == "saw":
            sig = 2 * ((phase / (2 * np.pi)) % 1) - 1
        elif wave == "noise":
            sig = np.random.uniform(-1, 1, n)
        else:
            sig = np.sin(phase)
        if lp > 1:
            sig = np.convolve(sig, np.ones(lp) / lp, mode="same")
        env = np.exp(-np.linspace(0, 4.6, n))
        data = np.int16(np.clip(sig * env * vol, -1, 1) * 32767)
        return pygame.sndarray.make_sound(
            np.ascontiguousarray(np.column_stack((data, data))))

    def _chord(self, freqs, dur):
        np = self.np
        n = int(44100 * dur)
        t = np.arange(n) / 44100
        sig = np.zeros(n)
        for i, f in enumerate(freqs):
            onset = i * 0.075
            env = np.where(t >= onset,
                           np.exp(-(t - onset) * 4.2), 0.0)
            sig += np.sin(2 * np.pi * f * t) * env
        sig /= max(1.0, len(freqs)) * 0.9
        data = np.int16(np.clip(sig * 0.32, -1, 1) * 32767)
        return pygame.sndarray.make_sound(
            np.ascontiguousarray(np.column_stack((data, data))))

    def play(self, name):
        if not self.ok or self.muted:
            return
        s = self.sounds.get(name)
        if s is not None:
            try:
                s.play()
            except Exception:
                pass


# ---------------------------------------------------------------- 字体

CJK_PATHS = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/arphic/uming.ttc",
]
CJK_FAMILIES = ("microsoftyaheiui,microsoftyahei,notosanscjksc,notosanscjk,"
                "sourcehansanssc,wqyzenhei,wenquanyimicrohei,pingfangsc,"
                "stheiti,heiti,simhei,arialunicodems")
# 界面上真正会渲染的非 ASCII 文案 —— 用它们自动拼出字形探测串。
#
# 为什么不用手写一个常量串：手写必然漏字或重复。
#   * 漏字 → 某几个汉字在某些字体下缺字形却检测不出来（显示成豆腐块）。
#   * 重复 → covers_cjk 用"位图是否互不相同"判定，重复字符必然得到相同位图，
#            于是永远判定"缺字形"，字体加载全线失败、中文界面直接退化。
#   2026-09-29 实测：手写串里「关」出现两次，27 字只得到 26 张不同位图，
#   covers_cjk 恒为 False，中文全部变成方框。
# 改为从 UI_TEXT 自动抽取 + 去重，两个坑一次解决。
UI_TEXT = (
    "推箱子SOKOBAN经典关第选择开始游戏退出的方向键移动撤销重做开本菜单"
    "已归位步数最少历史纪录新通关啦回上一页下返回静音效状态未"
    "个箱子过关用了步新纪录历次提示"
    # 符号类（与汉字完全独立的风险类别，中文字体常常只覆盖后者）。
    # 注意：'✓'(U+2713)、'▶'(U+25B6)、'◀'(U+25C0) 在微软雅黑里【没有字形】，
    # 实测它们的位图与 .notdef 方块完全一致 —— 界面上这些图形一律用
    # pygame.draw 画（见 _draw_check / _draw_arrow），不放进这个串。
    "·—！：★"
    # 其余出现在渲染文案里的字：
    "卡后是览预"
)


def _unique_chars(s):
    """按出现顺序去重，返回字符串。"""
    seen = set()
    out = []
    for c in s:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return "".join(out)


CJK_PROBE = _unique_chars(
    "".join(c for c in UI_TEXT if ord(c) > 127)
)


def _surface_bytes(surf, fmt="RGBA"):
    fn = getattr(pygame.image, "tobytes", None) or pygame.image.tostring
    return fn(surf, fmt)


def _notdef_bitmap(font, size=32):
    """取一个必定缺字形的码位（U+E000 私有区）的位图，作为 .notdef 参照。"""
    for cp in (0xE000, 0xF8FF, 0x2713):
        ch = chr(cp)
        try:
            img = font.render(ch, True, (255, 255, 255))
            if img.get_width() > 0:
                return _surface_bytes(img)
        except Exception:
            continue
    return None


def covers_cjk(font):
    """判断字体是否真的含有探测串里每个字符的字形。

    判定改成"与 .notdef 方块位图不同"，而不是"所有位图互不相同"：
      * 后者一旦串里混入一个缺字形字符，会连带把整个字体判为不合格；
      * 前者只关心"每个字符是否画出了真字形"，语义更准、也更抗误判。
    另外仍要求"真字形之间彼此不同" —— 不同汉字画成同一张位图同样不正常。
    """
    try:
        notdef = _notdef_bitmap(font)
        real = []
        for c in CJK_PROBE:
            b = _surface_bytes(font.render(c, True, (255, 255, 255)))
            if notdef is not None and b == notdef:
                return False          # 画成了豆腐块
            real.append(b)
        return len(set(real)) == len(real)
    except Exception:
        return False


def load_font(size, bold=False):
    """按 路径 → match_font → SysFont 顺序找含汉字的字体，全都验过字形。"""
    if not pygame.font.get_init():
        # 允许在没有显式 pygame.init() 的场景（自检脚本）下也能工作
        pygame.font.init()
    for path in CJK_PATHS:
        if os.path.exists(path):
            try:
                f = pygame.font.Font(path, size)
                if bold:
                    f.set_bold(True)
                if covers_cjk(f):
                    return f
            except Exception:
                pass
    for fam in CJK_FAMILIES.split(","):
        try:
            p = pygame.font.match_font(fam)
        except Exception:
            p = None
        if p:
            try:
                f = pygame.font.Font(p, size)
                if bold:
                    f.set_bold(True)
                if covers_cjk(f):
                    return f
            except Exception:
                pass
        try:
            f = pygame.font.SysFont(fam, size, bold=bold)
            if covers_cjk(f):
                return f
        except Exception:
            pass
    print("[警告] 未找到含中文字形的字体，界面中文可能显示为方框。\n"
          "       Linux 可执行： sudo apt install fonts-noto-cjk")
    return pygame.font.Font(None, size)


# ---------------------------------------------------------------- 配色（现代扁平 · 浅色）

BG = (233, 237, 243)
PANEL = (255, 255, 255)
PANEL_EDGE = (206, 214, 226)
INK = (38, 46, 60)
INK_DIM = (124, 136, 154)
ACCENT = (58, 122, 214)
ACCENT_SOFT = (206, 224, 250)
GOLD = (240, 176, 58)
GOLD_DARK = (198, 138, 34)

WALL_FACE = (88, 100, 120)
WALL_TOP = (110, 124, 146)
WALL_SIDE = (66, 76, 94)

FLOOR_A = (240, 243, 249)
FLOOR_B = (232, 236, 245)

BOX_FACE = (214, 148, 66)
BOX_TOP = (240, 186, 112)
BOX_SIDE = (170, 112, 44)
BOX_OK_FACE = (74, 166, 110)
BOX_OK_TOP = (116, 202, 148)
BOX_OK_SIDE = (48, 126, 80)

PLAYER = (58, 122, 214)
PLAYER_DARK = (38, 88, 166)

SHADOW = (28, 36, 52, 42)


# ---------------------------------------------------------------- 游戏主体

def reachable_cells(lv):
    """从玩家出发、不穿墙能走到的格子集合。地图的"内部"就是这些格子。

    墙外的空白（Microban 的矩形文本四周常有余白）不属于内部，
    画棋盘和缩略图时都必须跳过，否则会多出一片悬空的浅色方块。
    """
    seen = {lv.start_player}
    stack = [lv.start_player]
    while stack:
        x, y = stack.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if (nx, ny) in seen or lv.cell(nx, ny) == WALL:
                continue
            if not (0 <= nx < lv.w and 0 <= ny < lv.h):
                continue
            seen.add((nx, ny))
            stack.append((nx, ny))
    return seen


def draw_level_thumb(surf, lv, box):
    """在 box 区域内画一张关卡缩略图（选关页与标题页共用）。"""
    inside = reachable_cells(lv)
    xs = [x for (x, y) in inside] + [x for y in range(lv.h)
                                     for x in range(lv.w)
                                     if lv.cell(x, y) == WALL]
    ys = [y for (x, y) in inside] + [y for y in range(lv.h)
                                     for x in range(lv.w)
                                     if lv.cell(x, y) == WALL]
    if not xs:
        return
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    cw, ch = x1 - x0 + 1, y1 - y0 + 1
    ts = max(3, min(int((box.w - 16) / cw), int((box.h - 16) / ch)))
    ox = box.x + (box.w - cw * ts) // 2 - x0 * ts
    oy = box.y + (box.h - ch * ts) // 2 - y0 * ts

    for yy in range(y0, y1 + 1):
        for xx in range(x0, x1 + 1):
            c = lv.cell(xx, yy)
            is_wall = c == WALL
            if not is_wall and (xx, yy) not in inside:
                continue                       # 墙外空白不画
            r = pygame.Rect(ox + xx * ts, oy + yy * ts, ts, ts)
            if is_wall:
                pygame.draw.rect(surf, WALL_FACE, r)
            else:
                pygame.draw.rect(surf, FLOOR_A, r)
                if c == TARGET:
                    pygame.draw.circle(surf, ACCENT, r.center,
                                       max(1, ts // 4))
            if (xx, yy) in lv.start_boxes:
                pygame.draw.rect(surf, BOX_FACE, r.inflate(-2, -2),
                                 border_radius=1)
    px, py = lv.start_player
    pygame.draw.rect(surf, PLAYER,
                     pygame.Rect(ox + px * ts, oy + py * ts, ts, ts),
                     border_radius=1)


class Sokoban:

    def __init__(self, levels_raw=None, headless=False):
        self.headless = headless
        self.levels = [Level(i + 1, t)
                       for i, t in enumerate(levels_raw or LEVELS_RAW)]
        self.sfx = Sfx()
        self.font_big = load_font(46, bold=True)
        self.font_mid = load_font(26, bold=True)
        self.font_sm = load_font(19)
        self.font_tiny = load_font(16)

        self.level_idx = 0
        self.state = W_TITLE
        self.prev_state = W_TITLE
        self.msg = ""
        self.msg_until = 0

        self.rate = 0
        self._last_dir = None
        self.moves_total = 0
        self.anim = None
        self.elapsed = 0.0
        self.pulse = 0.0
        self.cleared = []            # 已通关的关卡号
        self.best = {}               # 关卡号 -> 最少步数
        self.level_scroll = 0
        self.levels_page = 0
        self.title_sel = 0
        self.auto_play = False       # 自检用：自动求解演示

        self._bg_cache = None
        self.center_on_screen()
        self.load_level(0, enter_play=False)
        self.state = W_TITLE          # 先进标题页，由玩家决定玩哪关

    # ---------------- 关卡装载 / 屏幕

    def load_level(self, idx, enter_play=True):
        """装载关卡并重置一切局面状态。

        enter_play=True 时把状态切到 W_PLAY —— 调用 load_level 的语义就是
        "开始玩这一关"。只有极少数场景（如构造后再手动设状态）需要 False。
        漏掉这一步会导致 try_move 因状态守卫直接返回 False，表现为"怎么按都不动"。
        """
        self.level_idx = max(0, min(len(self.levels) - 1, idx))
        lv = self.level
        self.boxes = set(lv.start_boxes)
        self.player = lv.start_player
        self.history = []            # [(dir, 是否推箱, 玩家旧位置, 箱子旧位置或 None)]
        self.future = []             # 撤销后存的重做栈
        self.moves_total = 0
        self.elapsed = 0.0
        self.anim = None
        self.rate = 0
        self._last_dir = None
        self._bg_cache = None
        self.center_on_screen()
        if enter_play:
            self.state = W_PLAY

    @property
    def level(self):
        return self.levels[self.level_idx]

    def center_on_screen(self):
        """棋盘居中：一切坐标从窗口实际尺寸反算，不能用常量硬推。

        用【内容包围盒】(内容 = 墙 + 可走格) 而不是整张矩形文本来定位，
        否则墙外的空白会把棋盘整体推偏（Microban 的图是矩形文本，四周常有余白）。
        """
        lv = self.level
        xs, ys = [], []
        for y in range(lv.h):
            for x in range(lv.w):
                if lv.cell(x, y) == WALL:
                    xs.append(x)
                    ys.append(y)
        if not xs:
            xs, ys = [0], [0]
        self.bbox = (min(xs), min(ys), max(xs), max(ys))
        cw = self.bbox[2] - self.bbox[0] + 1
        ch = self.bbox[3] - self.bbox[1] + 1
        avail_h = BOARD_BOTTOM - BOARD_TOP
        self.tile = max(16, min(72, int(min((WIN_W - 90) / max(1, cw),
                                           avail_h / max(1, ch)))))
        self.bx = (WIN_W - cw * self.tile) // 2 - self.bbox[0] * self.tile
        self.by = (BOARD_TOP + (avail_h - ch * self.tile) // 2
                   - self.bbox[1] * self.tile)

    def cell_xy(self, x, y):
        """格子左上角的屏幕坐标。"""
        return self.bx + x * self.tile, self.by + y * self.tile

    def cell_center(self, x, y):
        t = self.tile
        return self.bx + x * t + t / 2, self.by + y * t + t / 2

    def screen_to_cell(self, sx, sy):
        x = (sx - self.bx) // self.tile
        y = (sy - self.by) // self.tile
        return int(x), int(y)

    # ---------------- 游戏逻辑

    def try_move(self, d, ignore_anim=False):
        """返回 True 表示这一步生效（走出去或推了箱子）。

        ignore_anim=True 用于自动求解/自检：跳过滑动动画节流直接落子。
        正常交互路径不要传 True，否则按住方向键会一帧推一格。
        """
        if self.state != W_PLAY:
            return False
        if self.anim is not None and not ignore_anim:
            return False                       # 动画未结束不接受新输入
        lv = self.level
        dx, dy = DIRS[d]
        px, py = self.player
        nx, ny = px + dx, py + dy
        if lv.cell(nx, ny) == WALL:
            self.sfx.play("blocked")
            return False

        pushed_from = None
        pushed_to = None
        if (nx, ny) in self.boxes:
            bx, by = nx + dx, ny + dy
            if lv.cell(bx, by) == WALL or (bx, by) in self.boxes:
                self.sfx.play("blocked")
                return False
            pushed_from, pushed_to = (nx, ny), (bx, by)

        self.history.append((d, pushed_from, (px, py), pushed_to))
        self.future.clear()

        if pushed_from is not None:
            self.boxes.remove(pushed_from)
            self.boxes.add(pushed_to)
            self.sfx.play("push")
            was_on = pushed_from in lv.targets
            now_on = pushed_to in lv.targets
            if now_on and not was_on:
                self.sfx.play("placed")
        else:
            self.sfx.play("move")

        self.player = (nx, ny)
        self.moves_total += 1
        self.anim = {"d": d, "t": 0.0, "box_from": pushed_from,
                     "box_to": pushed_to,
                     "p_from": (px, py), "p_to": (nx, ny)}

        if is_solved(lv, self.boxes):
            self.on_solved()
        return True

    def on_solved(self):
        n = self.level.index
        if n not in self.cleared:
            self.cleared.append(n)
        b = self.best.get(n)
        if b is None or self.moves_total < b:
            self.best[n] = self.moves_total
        self.sfx.play("win")
        self.state = W_CLEAR
        self.anim = None

    def undo(self):
        """撤销一步。history 条目为 (dir, 箱子原位置|None, 玩家原位置, 箱子新位置|None)。"""
        if self.state != W_PLAY or not self.history:
            if self.state == W_PLAY:
                self.sfx.play("blocked")
            return False
        if self.anim is not None:
            self.anim = None
        d, pushed_from, p_from, pushed_to = self.history.pop()
        self.future.append((d, pushed_from, p_from, pushed_to))
        if pushed_from is not None:
            self.boxes.discard(pushed_to)
            self.boxes.add(pushed_from)
        self.player = p_from
        self.moves_total = max(0, self.moves_total - 1)
        self.sfx.play("undo")
        return True

    def redo(self):
        """重做一步 —— 必须与 undo 严格互逆。

        玩家落点分两种情况（这是最容易写错的地方）：
          * 推箱：玩家站到箱子原来那格 pushed_from
          * 空走：玩家从 p_from 沿原方向前进一格
        """
        if self.state != W_PLAY or not self.future:
            if self.state == W_PLAY:
                self.sfx.play("blocked")
            return False
        if self.anim is not None:
            self.anim = None
        d, pushed_from, p_from, pushed_to = self.future.pop()
        self.history.append((d, pushed_from, p_from, pushed_to))
        dx, dy = DIRS[d]
        if pushed_from is not None:
            self.boxes.discard(pushed_from)
            self.boxes.add(pushed_to)
            self.player = pushed_from          # 推箱后玩家占据箱子原位
        else:
            self.player = (p_from[0] + dx, p_from[1] + dy)
        self.moves_total += 1
        self.sfx.play("redo")
        if is_solved(self.level, self.boxes):
            self.on_solved()
        return True

    def restart(self):
        self.load_level(self.level_idx)
        self.sfx.play("ui")

    def next_level(self):
        if self.level_idx + 1 < len(self.levels):
            self.load_level(self.level_idx + 1)
            self.state = W_PLAY
            self.sfx.play("ui")
        else:
            self.state = W_TITLE
            self.flash("已经是最后一关啦")

    def prev_level(self):
        if self.level_idx > 0:
            self.load_level(self.level_idx - 1)
            self.state = W_PLAY
            self.sfx.play("ui")

    def flash(self, text, secs=1.8):
        self.msg = text
        self.msg_until = self.elapsed + secs

    # ---------------- 每帧更新

    def update(self, dt, keys):
        self.pulse += dt
        self.elapsed += dt
        if self.state == W_PLAY and self.anim is not None:
            self.anim["t"] += dt
            if self.anim["t"] * 1000 >= ANIM_MS:
                self.anim = None
        if self.state == W_PLAY:
            self._handle_repeat(dt, keys)

    def _handle_repeat(self, dt, keys):
        """按住方向键连续移动：首次延迟 REPEAT_DELAY 帧，之后每 REPEAT_RATE 帧一步。"""
        want = None
        for d, names in ((U, (pygame.K_UP, pygame.K_w)),
                         (D, (pygame.K_DOWN, pygame.K_s)),
                         (L, (pygame.K_LEFT, pygame.K_a)),
                         (R, (pygame.K_RIGHT, pygame.K_d))):
            if any(keys[k] for k in names):
                want = d
                break
        if want is None:
            self.rate = 0
            self._last_dir = None
            return
        if self._last_dir != want:
            self._last_dir = want
            self.rate = 0
            self.try_move(want)          # 按下立刻走一步
            return
        self.rate += 1
        if self.rate == REPEAT_DELAY or (
                self.rate > REPEAT_DELAY
                and (self.rate - REPEAT_DELAY) % REPEAT_RATE == 0):
            self.try_move(want)

    # ---------------- 事件

    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN:
            return self._on_keydown(ev)
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            return self._on_click(ev.pos)
        return False

    def _on_keydown(self, ev):
        k = ev.key
        if k == pygame.K_m:
            self.sfx.muted = not self.sfx.muted
            self.flash("已静音" if self.sfx.muted else "已开启音效")
            return True

        if self.state == W_TITLE:
            if k in (pygame.K_RETURN, pygame.K_SPACE):
                self.load_level(self.title_sel)
                self.state = W_PLAY
                self.title_sel = 0
                self.sfx.play("ui")
            elif k in (pygame.K_ESCAPE,):
                return "quit"
            elif k == pygame.K_l:
                self.state = W_LEVELS
                self.sfx.play("ui")
            return True

        if self.state == W_LEVELS:
            n = len(self.levels)
            if k in (pygame.K_RIGHT, pygame.K_d):
                self.levels_page = (self.levels_page + 1) % max(1, (n + 23) // 24)
            elif k in (pygame.K_LEFT, pygame.K_a):
                self.levels_page = (self.levels_page - 1) % max(1, (n + 23) // 24)
            elif k in (pygame.K_UP, pygame.K_w):
                self.title_sel = (self.title_sel - 6) % n
                self.levels_page = self.title_sel // 24
            elif k in (pygame.K_DOWN, pygame.K_s):
                self.title_sel = (self.title_sel + 6) % n
                self.levels_page = self.title_sel // 24
            elif k in (pygame.K_RETURN, pygame.K_SPACE):
                self.load_level(self.title_sel)
                self.state = W_PLAY
                self.sfx.play("ui")
            elif k == pygame.K_ESCAPE:
                self.state = W_TITLE
                self.sfx.play("ui")
            return True

        if self.state == W_CLEAR:
            if k in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_n):
                self.next_level()
            elif k in (pygame.K_r,):
                self.load_level(self.level_idx)
                self.state = W_PLAY
            elif k == pygame.K_p:
                self.prev_level()
            elif k == pygame.K_ESCAPE:
                self.state = W_TITLE
            return True

        if self.state == W_PLAY:
            if k == pygame.K_ESCAPE:
                self.prev_state = W_PLAY
                self.state = W_TITLE
                self.title_sel = self.level_idx
                self.sfx.play("ui")
            elif k == pygame.K_u:
                self.undo()
            elif k == pygame.K_y:
                self.redo()
            elif k == pygame.K_r:
                self.restart()
            elif k == pygame.K_n:
                self.next_level()
            elif k == pygame.K_p:
                self.prev_level()
            elif k == pygame.K_LEFT or k == pygame.K_a:
                self.try_move(L)
            elif k == pygame.K_RIGHT or k == pygame.K_d:
                self.try_move(R)
            elif k == pygame.K_UP or k == pygame.K_w:
                self.try_move(U)
            elif k == pygame.K_DOWN or k == pygame.K_s:
                self.try_move(D)
            return True

        return False

    def _on_click(self, pos):
        """点按钮（回调）或点关卡格（name/arg）。按钮位置由 draw 记录。"""
        for fn, rect in getattr(self, "_actions", []):
            if rect.collidepoint(pos):
                self.sfx.play("ui")
                fn()
                return True
        for name, rect, arg in getattr(self, "_buttons", []):
            if rect.collidepoint(pos):
                self._do_button(name, arg)
                return True
        return False

    def _back_to_menu(self):
        self.prev_state = W_PLAY
        self.state = W_TITLE
        self.title_sel = self.level_idx

    def _do_button(self, name, arg):
        self.sfx.play("ui")
        if name == "title_start":
            self.load_level(self.title_sel)
            self.state = W_PLAY
        elif name == "title_levels":
            self.state = W_LEVELS
            self.levels_page = self.title_sel // 24
        elif name == "title_quit":
            self._quit_req = True
        elif name in ("title_lv", "grid_lv"):
            self.title_sel = arg
            self.load_level(arg)
            self.state = W_PLAY
        elif name == "levels_back":
            self.state = W_TITLE
        elif name == "levels_page":
            self.levels_page = arg
        elif name == "play_menu":
            self.prev_state = W_PLAY
            self.state = W_TITLE
            self.title_sel = self.level_idx
        elif name == "clear_next":
            self.next_level()
        elif name == "clear_retry":
            self.load_level(self.level_idx)
            self.state = W_PLAY
        elif name == "clear_prev":
            self.prev_level()

    # ---------------- 绘制

    def draw(self, surf):
        self._buttons = []
        self._actions = []
        surf.blit(self._bg(), (0, 0))
        if self.state == W_TITLE:
            self._draw_title(surf)
        elif self.state == W_LEVELS:
            self._draw_levels(surf)
        else:
            self._draw_board(surf)
            self._draw_hud(surf)
            if self.state == W_CLEAR:
                self._draw_clear(surf)
        if self.msg and self.elapsed < self.msg_until:
            self._draw_toast(surf)

    def _bg(self):
        """背景一次性画好并缓存；静态区域不含动画元素。

        convert_alpha() 需要已设置 display 模式；在没有 display 的环境
        （无头自检、SDL dummy 尚未 set_mode）下退化为普通 Surface，
        否则会抛 pygame.error: No video mode has been set。
        """
        if self._bg_cache is not None:
            return self._bg_cache
        s = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        try:
            s = s.convert_alpha()
        except pygame.error:
            pass
        s.fill(BG)
        # 柔和的顶部光带
        for i in range(120):
            f = 1.0 - i / 120.0
            col = (BG[0] + int(16 * f), BG[1] + int(14 * f), BG[2] + int(10 * f))
            pygame.draw.rect(s, col, (0, i, WIN_W, 1))
        self._bg_cache = s
        return s

    def _panel(self, surf, rect, radius=14, fill=PANEL, edge=PANEL_EDGE):
        pygame.draw.rect(surf, fill, rect, border_radius=radius)
        pygame.draw.rect(surf, edge, rect, width=1, border_radius=radius)

    def _draw_check(self, surf, cx, cy, r, color):
        """画对勾（两条线）。用图形而非 '✓' 字符 —— 微软雅黑对 U+2713
        没有字形，会渲染成豆腐块（实测 U+2713 与 U+25B6 位图完全相同）。"""
        pts = [(cx - r, cy), (cx - r * 0.25, cy + r * 0.7), (cx + r, cy - r * 0.7)]
        pygame.draw.lines(surf, color, False, pts, max(2, int(r * 0.5)))

    def _draw_arrow(self, surf, cx, cy, size, color, direction="right"):
        """画三角箭头。同理不用 '▶' / '◀'（缺字形）。"""
        h = size
        w = size * 0.85
        if direction == "right":
            pts = [(cx - w / 2, cy - h / 2), (cx + w / 2, cy),
                   (cx - w / 2, cy + h / 2)]
        else:
            pts = [(cx + w / 2, cy - h / 2), (cx - w / 2, cy),
                   (cx + w / 2, cy + h / 2)]
        pygame.draw.polygon(surf, color, pts)

    def text(self, surf, font, s, pos, color=INK, anchor="topleft"):
        img = font.render(s, True, color)
        r = img.get_rect()
        setattr(r, anchor, pos)
        surf.blit(img, r)
        return r

    def _button(self, surf, rect, label, font=None, name=None, arg=None,
                kind="primary", enabled=True, small=False):
        font = font or self.font_sm
        mx, my = pygame.mouse.get_pos()
        hover = enabled and rect.collidepoint(mx, my)
        if not enabled:
            fill, edge, col = (236, 239, 245), (218, 223, 232), (168, 176, 190)
        elif kind == "primary":
            base = ACCENT
            fill = (base[0] + 18, base[1] + 18, base[2] + 16) if hover else base
            edge, col = ACCENT, (255, 255, 255)
        elif kind == "gold":
            fill = GOLD if not hover else (248, 190, 80)
            edge, col = GOLD_DARK, (60, 42, 12)
        else:
            fill = (255, 255, 255) if not hover else (244, 247, 252)
            edge, col = (206, 214, 226), INK
        sh = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pygame.draw.rect(sh, SHADOW, (0, 3, rect.w, rect.h - 3),
                         border_radius=12)
        surf.blit(sh, (rect.x, rect.y))
        pygame.draw.rect(surf, fill, rect, border_radius=12)
        pygame.draw.rect(surf, edge, rect, width=1, border_radius=12)
        self.text(surf, font, label, rect.center, col, "center")
        if name:
            self._buttons.append((name, rect, arg))
        return rect

    # ------- 棋子绘制

    def _draw_floor(self, surf, x, y, t):
        px, py = self.cell_xy(x, y)
        base = FLOOR_A if (x + y) % 2 == 0 else FLOOR_B
        pygame.draw.rect(surf, base, (px, py, t, t))

    def _draw_wall(self, surf, x, y, t):
        px, py = self.cell_xy(x, y)
        outer = pygame.Rect(px, py, t, t)
        pygame.draw.rect(surf, WALL_FACE, outer)
        inset = max(2, t // 10)
        pygame.draw.rect(surf, WALL_TOP, (px + inset, py + inset,
                                          t - inset * 2, t - inset * 2))
        pygame.draw.rect(surf, WALL_SIDE, (px + inset, py + t - inset * 2,
                                           t - inset * 2, inset))
        pygame.draw.rect(surf, WALL_FACE, (px + inset, py + inset,
                                           t - inset * 2, t - inset * 2), width=1)

    def _draw_target(self, surf, x, y, t, off=(0.0, 0.0)):
        cx, cy = self.cell_center(x, y)
        cx += off[0]
        cy += off[1]
        k = 0.5 + 0.5 * math.sin(self.pulse * 2.4 + (x * 0.7 + y * 1.3))
        rad = int(t * (0.20 + 0.035 * k))
        ring = ACCENT_SOFT
        pygame.draw.circle(surf, (218, 230, 248), (int(cx), int(cy)), rad)
        pygame.draw.circle(surf, ring, (int(cx), int(cy)), rad, width=max(2, t // 22))

    def _round_box(self, surf, rect, face, top, side, radius):
        pygame.draw.rect(surf, side, (rect.x, rect.y + rect.h - radius,
                                      rect.w, radius), border_radius=radius // 2)
        pygame.draw.rect(surf, face, rect, border_radius=radius)
        inner = rect.inflate(-radius, -radius)
        pygame.draw.rect(surf, top, (inner.x, inner.y, inner.w, max(3, inner.h // 3)),
                         border_radius=max(2, radius // 3))
        pygame.draw.rect(surf, side, rect, width=1, border_radius=radius)

    def _draw_box(self, surf, x, y, t, off=(0.0, 0.0), on_target=False):
        px, py = self.cell_xy(x, y)
        px += off[0]
        py += off[1]
        m = max(2, int(t * 0.11))
        rect = pygame.Rect(px + m, py + m, t - m * 2, t - m * 2)
        sh = pygame.Surface((t, t), pygame.SRCALPHA)
        pygame.draw.rect(sh, SHADOW, (m + 1, m + 4, t - m * 2, t - m * 2),
                         border_radius=8)
        surf.blit(sh, (px, py))
        if on_target:
            self._round_box(surf, rect, BOX_OK_FACE, BOX_OK_TOP,
                            BOX_OK_SIDE, max(4, t // 8))
        else:
            self._round_box(surf, rect, BOX_FACE, BOX_TOP, BOX_SIDE,
                            max(4, t // 8))
        # 十字捆扎带，扁平风里很好认
        band = max(2, t // 16)
        bc = (255, 255, 255, 90)
        bw = pygame.Surface((rect.w, band), pygame.SRCALPHA)
        bw.fill(bc)
        surf.blit(bw, (rect.x, rect.centery - band // 2))
        bh = pygame.Surface((band, rect.h), pygame.SRCALPHA)
        bh.fill(bc)
        surf.blit(bh, (rect.centerx - band // 2, rect.y))

    def _draw_player(self, surf, x, y, t, off=(0.0, 0.0), on_target=False):
        px, py = self.cell_xy(x, y)
        px += off[0]
        py += off[1]
        m = max(3, int(t * 0.16))
        face = pygame.Rect(px + m, py + m, t - m * 2, t - m * 2)
        if on_target:
            face = pygame.Rect(px + m, py + m, t - m * 2, t - m * 2)
        r = max(6, face.w // 2)
        cx, cy = face.centerx, face.centery
        # 身体（圆角方） + 头（圆） → 一眼是小人
        body = pygame.Rect(cx - r, cy - r // 6, r * 2, r * 1.5)
        pygame.draw.rect(surf, PLAYER_DARK, body.move(0, 2), border_radius=r)
        pygame.draw.rect(surf, PLAYER, body, border_radius=r)
        head_r = max(5, int(r * 0.72))
        pygame.draw.circle(surf, PLAYER_DARK, (cx, cy - head_r), head_r + 1)
        pygame.draw.circle(surf, PLAYER, (cx, cy - head_r), head_r)
        # 眼睛
        er = max(1, head_r // 5)
        for sx in (-1, 1):
            pygame.draw.circle(surf, (255, 255, 255),
                               (cx + sx * max(2, head_r // 2), cy - head_r), er)
            pygame.draw.circle(surf, (40, 48, 62),
                               (cx + sx * max(2, head_r // 2), cy - head_r), max(1, er - 1))
        # 高光
        pygame.draw.circle(surf, (150, 196, 250),
                           (cx - r // 2, cy - r), max(1, r // 5))

    # ------- 棋盘

    def _playable_cells(self):
        """哪些格子在"墙围出来的内部"——只有这些才画地板。

        结果按关卡号缓存，避免每帧重复洪水填充。
        """
        if getattr(self, "_playable_cache", None) is not None \
                and getattr(self, "_playable_for", None) == self.level_idx:
            return self._playable_cache
        self._playable_cache = reachable_cells(self.level)
        self._playable_for = self.level_idx
        return self._playable_cache

    def _draw_board(self, surf):
        lv = self.level
        t = self.tile
        inside = self._playable_cells()

        # 先画一块"卡片底"：内容包围盒（墙 + 可走格）向外扩一点，
        # 让棋盘像放在一张浅色台面上，而不是悬在背景上。
        xs, ys = [], []
        for y in range(lv.h):
            for x in range(lv.w):
                if lv.cell(x, y) == WALL or (x, y) in inside:
                    xs.append(x)
                    ys.append(y)
        board = None
        if xs:
            x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
            px0, py0 = self.cell_xy(x0, y0)
            board = pygame.Rect(px0 - 8, py0 - 8,
                                (x1 - x0 + 1) * t + 16,
                                (y1 - y0 + 1) * t + 16)
            sh = pygame.Surface((board.w, board.h), pygame.SRCALPHA)
            pygame.draw.rect(sh, (26, 34, 50, 26), (0, 5, board.w, board.h),
                             border_radius=14)
            surf.blit(sh, board.topleft)
            pygame.draw.rect(surf, (255, 255, 255), board, border_radius=14)
            pygame.draw.rect(surf, (222, 228, 238), board, width=1,
                             border_radius=14)

        for y in range(lv.h):
            for x in range(lv.w):
                if lv.cell(x, y) == WALL:
                    self._draw_wall(surf, x, y, t)
                elif (x, y) in inside:
                    self._draw_floor(surf, x, y, t)

        for tx, ty in sorted(lv.targets):
            if (tx, ty) not in self.boxes:
                self._draw_target(surf, tx, ty, t)

        poff = (0.0, 0.0)
        boff = (0.0, 0.0)
        if self.anim:
            k = min(1.0, self.anim["t"] * 1000 / ANIM_MS)
            k = 1 - (1 - k) ** 3                      # ease-out
            dx, dy = DIRS[self.anim["d"]]
            poff = (dx * t * (1 - k), dy * t * (1 - k))
            boff = poff

        for bx_, by_ in sorted(self.boxes):
            self._draw_box(surf, bx_, by_, t, boff, bx_ in lv.targets
                           if self.anim is None or (bx_, by_) != self.anim["box_to"]
                           else True)

        # 正在移动的箱子单独按目标状态重画一次，避免闪色
        if self.anim and self.anim["box_to"]:
            bf = self.anim["box_to"]
            self._draw_box(surf, bf[0], bf[1], t, boff,
                           bf in lv.targets)

        px, py = self.player
        self._draw_player(surf, px, py, t, poff, (px, py) in lv.targets)

    # ------- HUD

    def _draw_hud(self, surf):
        lv = self.level
        # 顶部信息条
        bar = pygame.Rect(24, HUD_TOP, WIN_W - 48, HUD_H)
        self._panel(surf, bar, radius=16)
        self.text(surf, self.font_mid, lv.name, (bar.x + 22, bar.y + 14))
        self.text(surf, self.font_tiny,
                  f"最少 {self.best.get(lv.index, '—')} 步 · "
                  f"已通关 {len(self.cleared)}/{len(self.levels)}",
                  (bar.x + 22, bar.y + 48), INK_DIM)

        done = len(self.boxes & lv.targets)
        self.text(surf, self.font_mid, f"{done} / {lv.n_targets}",
                  (bar.right - 190, bar.y + 14), ACCENT if done == lv.n_targets else INK,
                  "topright")
        self.text(surf, self.font_tiny, "已归位",
                  (bar.right - 190, bar.y + 48), INK_DIM, "topright")

        self.text(surf, self.font_mid, f"{self.moves_total}",
                  (bar.right - 22, bar.y + 14), INK, "topright")
        self.text(surf, self.font_tiny, "步数", (bar.right - 22, bar.y + 48),
                  INK_DIM, "topright")

        # 底部按钮：宽度按【实测文本宽度】算，整排居中，
        # 不写死 bw —— 写死宽度在中文标签下必然互相压字（实测 118px 装不下
        # "下一关 N" + "菜单 ESC"，两排文字叠成一团）。
        specs = [("撤销 U", "gold", self.undo, bool(self.history)),
                 ("重做 Y", "ghost", self.redo, bool(self.future)),
                 ("重开 R", "ghost", self.restart, True),
                 ("上一关 P", "ghost", self.prev_level, self.level_idx > 0),
                 ("下一关 N", "ghost", self.next_level,
                  self.level_idx + 1 < len(self.levels)),
                 ("菜单 ESC", "ghost", self._back_to_menu, True)]
        bh = BTN_H
        gap = 10
        pad_x = 18
        widths = [self.font_sm.size(lb)[0] + pad_x * 2 for lb, _, _, _ in specs]
        total = sum(widths) + gap * (len(specs) - 1)
        x = max(24, (WIN_W - total) // 2)
        y = BTN_TOP
        for (label, kind, fn, en), bw in zip(specs, widths):
            rect = pygame.Rect(x, y, bw, bh)
            self._button(surf, rect, label, self.font_sm, kind=kind, enabled=en)
            if en:
                self._actions.append((fn, rect))
            x += bw + gap

        # 提示文字单独一行，放在按钮下方并居中，避免与按钮重叠
        hint = "方向键 / WASD 移动 · U 撤销 · Y 重做 · R 重开 · N 下一关"
        self.text(surf, self.font_tiny, hint,
                  (WIN_W // 2, y + bh + 6), INK_DIM, "midtop")

    # ------- 通关面板

    def _draw_clear(self, surf):
        veil = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        veil.fill((18, 24, 36, 130))
        surf.blit(veil, (0, 0))
        w, h = 460, 300
        rect = pygame.Rect((WIN_W - w) // 2, (WIN_H - h) // 2, w, h)
        sh = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(sh, (10, 16, 28, 70), (0, 8, w, h - 8),
                         border_radius=20)
        surf.blit(sh, rect.topleft)
        pygame.draw.rect(surf, PANEL, rect, border_radius=20)
        pygame.draw.rect(surf, PANEL_EDGE, rect, width=1, border_radius=20)

        best = self.best.get(self.level.index)
        self.text(surf, self.font_big, "过关！", (rect.centerx, rect.y + 52),
                  ACCENT, "center")
        sub = f"{self.level.name} · 用了 {self.moves_total} 步"
        self.text(surf, self.font_sm, sub, (rect.centerx, rect.y + 108),
                  INK_DIM, "center")
        if best is not None:
            star = "★ 新纪录！" if self.moves_total <= best else f"历史最少 {best} 步"
            self.text(surf, self.font_sm, star, (rect.centerx, rect.y + 140),
                      GOLD_DARK, "center")

        bw, bh = 130, 44
        gap = 14
        total = bw * 3 + gap * 2
        x = rect.centerx - total // 2
        y = rect.bottom - 76
        self._button(surf, pygame.Rect(x, y, bw, bh), "重玩 R", self.font_sm,
                     name="clear_retry", kind="ghost")
        last = self.level_idx + 1 >= len(self.levels)
        self._button(surf, pygame.Rect(x + bw + gap, y, bw, bh),
                     "回菜单" if last else "下一关 N", self.font_sm,
                     name="clear_next", kind="primary")
        self._button(surf, pygame.Rect(x + (bw + gap) * 2, y, bw, bh),
                     "上一关 P", self.font_sm, name="clear_prev", kind="ghost")

    # ------- 菜单

    def _draw_title(self, surf):
        self.text(surf, self.font_big, "推 箱 子", (WIN_W // 2, 88), INK, "center")
        self.text(surf, self.font_sm, "SOKOBAN · 经典 60 关",
                  (WIN_W // 2, 142), INK_DIM, "center")

        # 右侧：当前选择的关卡缩略预览
        pv = pygame.Rect(WIN_W - 380, 190, 340, 400)
        self._panel(surf, pv)
        self.text(surf, self.font_sm, "关卡预览", (pv.x + 20, pv.y + 16))
        lvl = self.levels[self.title_sel]
        self.text(surf, self.font_tiny,
                  f"{lvl.name} · {lvl.n_targets} 个箱子",
                  (pv.x + 20, pv.y + 46), INK_DIM)
        box = pygame.Rect(pv.x + 20, pv.y + 78, pv.w - 40, 260)
        pygame.draw.rect(surf, (244, 247, 252), box, border_radius=10)
        pygame.draw.rect(surf, (224, 230, 240), box, width=1, border_radius=10)
        draw_level_thumb(surf, lvl, box)
        r = self.text(surf, self.font_tiny,
                      "状态：" + ("已通关" if lvl.index in self.cleared else "未通关"),
                      (pv.x + 20, pv.y + 352), INK_DIM)
        if lvl.index in self.cleared:
            self._draw_check(surf, r.right + 14, r.centery, 7, (74, 166, 110))
        self.text(surf, self.font_tiny,
                  f"历史最少 {self.best.get(lvl.index, '—')} 步",
                  (pv.x + 20, pv.y + 374), INK_DIM)

        # 左侧：按钮
        bw, bh = 300, 52
        x = 90
        y0 = 226
        self._button(surf, pygame.Rect(x, y0, bw, bh), "开始游戏", self.font_sm,
                     name="title_start", kind="primary")
        self._button(surf, pygame.Rect(x, y0 + 68, bw, bh), "选择关卡", self.font_sm,
                     name="title_levels", kind="ghost")
        self._button(surf, pygame.Rect(x, y0 + 136, bw, bh), "退出", self.font_sm,
                     name="title_quit", kind="ghost")
        self.text(surf, self.font_tiny,
                  "方向键 / WASD 移动 · U 撤销 · Y 重做 · R 重开 · N 下一关 · M 静音",
                  (x, y0 + 210), INK_DIM)

    def _draw_levels(self, surf):
        self.text(surf, self.font_big, "选择关卡", (WIN_W // 2, 52), INK, "center")
        per_page = 24
        cols, rows = 6, 4
        cw, ch = 130, 108
        gap = 12
        total_w = cols * cw + (cols - 1) * gap
        x0 = (WIN_W - total_w) // 2
        y0 = 106
        page = self.levels_page
        n = len(self.levels)
        mx, my = pygame.mouse.get_pos()
        for i in range(per_page):
            idx = page * per_page + i
            if idx >= n:
                break
            r, c = divmod(i, cols)
            rect = pygame.Rect(x0 + c * (cw + gap), y0 + r * (ch + gap), cw, ch)
            done = (idx + 1) in self.cleared
            hover = rect.collidepoint(mx, my)
            pygame.draw.rect(surf, (255, 255, 255) if not hover else (240, 246, 254),
                             rect, border_radius=12)
            pygame.draw.rect(surf, ACCENT_SOFT if hover else (206, 214, 226),
                             rect, width=2 if hover else 1, border_radius=12)
            if done:
                pygame.draw.rect(surf, (74, 166, 110), (rect.x, rect.y, rect.w, 5),
                                 border_top_left_radius=12,
                                 border_top_right_radius=12)
            # 上半：关卡缩略图；下半：编号 + 状态
            thumb = pygame.Rect(rect.x + 8, rect.y + 10, rect.w - 16, 58)
            draw_level_thumb(surf, self.levels[idx], thumb)
            num_col = (48, 126, 80) if done else INK
            self.text(surf, self.font_sm, str(idx + 1),
                      (rect.centerx - (7 if done else 0), rect.bottom - 22),
                      num_col, "center")
            if done:
                self._draw_check(surf, rect.centerx + 12, rect.bottom - 22, 6,
                                 (74, 166, 110))
            self._buttons.append(("grid_lv", rect, idx))

        # 页码（箭头用图形绘制，不用 '◀' / '▶' 字符 —— 缺字形）
        pages = max(1, (n + per_page - 1) // per_page)
        y = WIN_H - 118
        bw, bh = 108, 40
        lx = WIN_W // 2 - 190
        prev_r = self._button(surf, pygame.Rect(lx, y, bw, bh), "上一页",
                              self.font_sm, name="levels_page",
                              arg=(page - 1) % pages, kind="ghost")
        self._draw_arrow(surf, prev_r.x + 20, prev_r.centery, 11, INK, "left")
        self.text(surf, self.font_sm, f"{page + 1} / {pages}",
                  (WIN_W // 2, y + 20), INK, "center")
        next_r = self._button(surf, pygame.Rect(WIN_W // 2 + 82, y, bw, bh),
                              "下一页", self.font_sm, name="levels_page",
                              arg=(page + 1) % pages, kind="ghost")
        self._draw_arrow(surf, next_r.right - 20, next_r.centery, 11, INK, "right")
        self._button(surf, pygame.Rect(WIN_W // 2 - 60, y + 54, 120, 40),
                     "返回", self.font_sm, name="levels_back", kind="primary")

    def _draw_toast(self, surf):
        img = self.font_sm.render(self.msg, True, (255, 255, 255))
        pad = 18
        w = img.get_width() + pad * 2
        h = img.get_height() + pad
        x = (WIN_W - w) // 2
        y = WIN_H - 150
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(s, (36, 46, 64, 225), (0, 0, w, h), border_radius=12)
        surf.blit(s, (x, y))
        surf.blit(img, (x + pad, y + pad // 2))


# ---------------------------------------------------------------- 交互式主循环

def run(headless=False, frames=None, init_level=None):
    if not headless:
        # mixer 的采样率必须趁着 pygame.init() 之前设定，否则波形会变调
        try:
            pygame.mixer.pre_init(44100, -16, 2, 512)
        except Exception:
            pass
    pygame.init()
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(44100, -16, 2, 512)
    except Exception:
        pass

    flags = 0
    screen = pygame.display.set_mode((WIN_W, WIN_H), flags)
    pygame.display.set_caption("推箱子 Sokoban")
    clock = pygame.time.Clock()

    game = Sokoban()
    if init_level is not None:
        game.load_level(init_level)
        game.state = W_PLAY

    running = True
    count = 0
    while running:
        dt = clock.tick(FPS) / 1000.0
        dt = min(dt, 0.05)
        keys = pygame.key.get_pressed()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            else:
                r = game.handle_event(ev)
                if r == "quit":
                    running = False
        if getattr(game, "_quit_req", False):
            running = False
            game._quit_req = False

        game.update(dt, keys)
        screen.fill(BG)
        game.draw(screen)
        if headless:
            game.screen_to_cell(0, 0)      # 触发一次换算，确保路径无异常
        pygame.display.flip()
        count += 1
        if frames is not None and count >= frames:
            running = False
    pygame.quit()
    return game


def main(argv):
    frames = None
    headless = False
    lvl = None
    if "--frames" in argv:
        i = argv.index("--frames")
        if i + 1 < len(argv):
            frames = int(argv[i + 1])
    if "--headless" in argv:
        headless = True
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    if "--level" in argv:
        i = argv.index("--level")
        if i + 1 < len(argv):
            lvl = int(argv[i + 1]) - 1
    run(headless=headless, frames=frames, init_level=lvl)


if __name__ == "__main__":
    main(sys.argv[1:])
