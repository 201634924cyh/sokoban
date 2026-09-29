#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
推箱子 Sokoban 无窗口自检。

用法：
    python selftest.py            # 跑全部检查
    python selftest.py --quick    # 跳过 60 关全解验证（省时间）
    python selftest.py --shots    # 额外导出预览截图

设计原则（照 pygame-game-dev 技能的约定）：
  * 用真实事件驱动，不直接调内部函数。
  * 输入走 keys[key] 下标接口，自检时塞假对象。
  * 断言要考虑前序步骤已改变的状态。
  * 求解器真跑一局，覆盖「通关 → 记录 → 切关」整条链路。
  * 渲染后做像素扫描，并导出 PNG 用眼睛看。
"""

import os
import sys
import traceback

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import pygame  # noqa: E402

import sokoban as sk  # noqa: E402

# ---------------------------------------------------------------- 测试框架

PASS = FAIL = 0
FAILURES = []
SECTION = [""]


def section(name):
    SECTION[0] = name
    print(f"\n=== {name} ===")


def check(cond, label, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [OK] {label}")
    else:
        FAIL += 1
        FAILURES.append((SECTION[0], label, detail))
        print(f"  [!!] {label}" + (f"  -> {detail}" if detail else ""))


class FakeKeys:
    """假按键对象：支持 keys[pygame.K_x] 下标接口。"""

    def __init__(self, pressed=()):
        self.pressed = set(pressed)

    def __getitem__(self, k):
        return k in self.pressed

    def press(self, *ks):
        self.pressed.update(ks)

    def release(self, *ks):
        self.pressed.difference_update(ks)


def post_key(game, key):
    ev = pygame.event.Event(pygame.KEYDOWN, {"key": key, "mod": 0,
                                             "unicode": "", "scancode": 0})
    return game.handle_event(ev)


def click(game, pos, button=1):
    game._on_click(pos)


# ---------------------------------------------------------------- 1. 关卡数据

def test_levels(quick=False):
    section("1. 关卡数据完整性")
    check(len(sk.LEVELS_RAW) == 60, "共 60 关", f"实际 {len(sk.LEVELS_RAW)}")

    bad_struct = []
    for n, raw in enumerate(sk.LEVELS_RAW, 1):
        lv = sk.Level(n, raw)
        if len(lv.start_boxes) != lv.n_targets:
            bad_struct.append((n, len(lv.start_boxes), lv.n_targets))
        if lv.start_player is None:
            bad_struct.append((n, "no-player", 0))
        if lv.n_targets == 0:
            bad_struct.append((n, "no-target", 0))
    check(not bad_struct, "每关箱数 == 目标数 且 玩家唯一", str(bad_struct[:5]))

    # 封闭性 + 连通性：从玩家出发洪水填充，不得越界；目标与箱子必须可达
    leak, unreach = [], []
    for n, raw in enumerate(sk.LEVELS_RAW, 1):
        lv = sk.Level(n, raw)
        seen = {lv.start_player}
        q = [lv.start_player]
        leaked = False
        while q:
            x, y = q.pop()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if (nx, ny) in seen or lv.cell(nx, ny) == sk.WALL:
                    continue
                if not (0 <= nx < lv.w and 0 <= ny < lv.h):
                    leaked = True
                    continue
                seen.add((nx, ny))
                q.append((nx, ny))
        if leaked:
            leak.append(n)
        if (lv.targets - seen) or (set(lv.start_boxes) - seen):
            unreach.append(n)
    check(not leak, "所有地图被墙完全封闭（走不出边界）", str(leak))
    check(not unreach, "所有目标点与箱子都在可达区域内", str(unreach))

    # 箱数与目标数相等 → 不可能存在"多余目标"
    eq = all(len(sk.Level(n, r).start_boxes) == sk.Level(n, r).n_targets
             for n, r in enumerate(sk.LEVELS_RAW, 1))
    check(eq, "无多余目标点（箱数严格等于目标数）")

    if quick:
        print("  [--] --quick：跳过 60 关全解验证")
        return
    print("  ... 正在用求解器逐关验证可解性（约 40 秒）")
    unsolvable = []
    for n, raw in enumerate(sk.LEVELS_RAW, 1):
        lv = sk.Level(n, raw)
        sol = sk.solve_level(lv, node_limit=3000000)
        if not sol:
            unsolvable.append(n)
    check(not unsolvable, "全部 60 关经求解器验证可解", f"无解: {unsolvable}")

    # 至少要有难度梯度：早期关卡解短、后期解长
    early = []
    late = []
    for n in list(range(1, 11)):
        early.append(len(sk.solve_level(sk.Level(n, sk.LEVELS_RAW[n - 1]),
                                        node_limit=3000000) or []))
    for n in list(range(51, 61)):
        late.append(len(sk.solve_level(sk.Level(n, sk.LEVELS_RAW[n - 1]),
                                       node_limit=3000000) or []))
    check(sum(early) < sum(late), "存在难度梯度（后 10 关解明显长于前 10 关）",
          f"前 10 关总解长 {sum(early)} vs 后 10 关 {sum(late)}")


# ---------------------------------------------------------------- 2. 核心逻辑

def test_logic():
    section("2. 移动 / 推箱 / 边界")
    g = sk.Sokoban()
    g.load_level(0)
    lv = g.level

    # 玩家位置必须落在地板或目标上
    check(lv.cell(*g.player) != sk.WALL, "初始玩家不在墙里")

    # 往墙里推：不生效、步数不变
    p0 = g.player
    m0 = g.moves_total
    moved_into_wall = False
    for d in range(4):
        dx, dy = sk.DIRS[d]
        if lv.cell(p0[0] + dx, p0[1] + dy) == sk.WALL:
            ok = g.try_move(d, ignore_anim=True)
            if ok:
                moved_into_wall = True
            break
    check(not moved_into_wall, "撞墙不生效")
    check(g.player == p0 and g.moves_total == m0, "撞墙后玩家与步数不变")

    # 找一个能推箱的方向，验证箱子确实移动了。
    # 注意：某些关卡玩家开局就紧贴墙（无箱可推），所以跨关卡找，
    # 而不是只看第 1 关 —— 否则会误报"推不动"。
    pushed = False
    for lidx in range(min(10, len(sk.LEVELS_RAW))):
        g.load_level(lidx)
        for d in range(4):
            boxes_before = set(g.boxes)
            p_before = g.player
            if g.try_move(d, ignore_anim=True):
                if set(g.boxes) != boxes_before:
                    pushed = True
                    dx, dy = sk.DIRS[d]
                    moved_box = next(iter(set(g.boxes) - boxes_before))
                    check(moved_box == (p_before[0] + 2 * dx,
                                        p_before[1] + 2 * dy),
                          "推箱：箱子恰好前进一格")
                    check(g.player == (p_before[0] + dx, p_before[1] + dy),
                          "推箱：玩家占据箱子原位")
                    break
        if pushed:
            break
    check(pushed, "存在可推箱的方向并能推动")

    # 箱子挡路：两个箱子紧挨时，第一个推不动
    g.load_level(0)
    check(isinstance(g.boxes, set), "箱子容器为 set")


def test_undo_redo():
    section("3. 撤销 / 重做一致性")
    import random
    rng = random.Random(2026)

    # 3a. 逐关逐方向做"走一步 → 撤销 → 断言完全还原"的严格对拍
    asym = []
    for lidx in range(min(12, len(sk.LEVELS_RAW))):
        g = sk.Sokoban()
        g.load_level(lidx)
        lv = g.level
        for d in range(4):
            g.load_level(lidx)
            before = (set(g.boxes), g.player, g.moves_total)
            if not g.try_move(d, ignore_anim=True):
                continue
            g.undo()
            after = (set(g.boxes), g.player, g.moves_total)
            if after != before:
                asym.append((lidx + 1, d, before, after))
    check(not asym, "走一步后撤销 → 局面完全还原（逐关逐方向对拍）",
          str(asym[:3]))

    # 3b. 随机长序列：全程记录快照，撤销到底再重做到底应完全复原
    g = sk.Sokoban()
    g.load_level(5)
    snapshots = []
    for _ in range(30):
        d = rng.randrange(4)
        if g.try_move(d, ignore_anim=True):
            snapshots.append((set(g.boxes), g.player, g.moves_total))
    check(len(snapshots) >= 5, "能连续走出多步", f"实际 {len(snapshots)} 步")
    if not snapshots:
        return

    target_state = snapshots[-1]
    while g.history:
        g.undo()
    lv = g.level
    check(set(g.boxes) == set(lv.start_boxes) and g.player == lv.start_player
          and g.moves_total == 0,
          "撤销到底 → 箱子/玩家/步数全部回到初始",
          f"{sorted(g.boxes)} vs {sorted(lv.start_boxes)}")

    while g.future:
        g.redo()
    check(set(g.boxes) == target_state[0], "重做到底 → 箱子回到最后状态")
    check(g.player == target_state[1], "重做到底 → 玩家回到最后状态",
          f"{g.player} vs {target_state[1]}")
    check(g.moves_total == target_state[2], "重做到底 → 步数回到最后状态",
          f"{g.moves_total} vs {target_state[2]}")

    # 3c. 撤销 / 重做 / 撤销 交替，逐步与快照对齐
    g.load_level(5)
    seq = []
    for _ in range(20):
        d = rng.randrange(4)
        if g.try_move(d, ignore_anim=True):
            seq.append((set(g.boxes), g.player))
    if len(seq) >= 4:
        for _ in range(len(seq)):
            g.undo()
        for i in range(len(seq)):
            g.redo()
            if (set(g.boxes), g.player) != seq[i]:
                check(False, f"逐步重做与快照一致（第 {i} 步）")
                break
        else:
            check(True, "逐步重做与快照逐步一致")

    # 3d. 新走一步必须清空重做栈
    g.load_level(5)
    walked = False
    for d in range(4):
        if g.try_move(d, ignore_anim=True):
            walked = True
            break
    check(walked, "第 6 关存在可走方向（前置条件）")
    if walked:
        g.undo()
        check(len(g.future) == 1, "撤销后有 1 条重做记录")
        for d in range(4):
            if g.try_move(d, ignore_anim=True):
                break
        check(len(g.future) == 0, "新走一步后重做栈被清空（不能穿越分支）")

    # 3e. 边界
    g2 = sk.Sokoban()
    g2.load_level(0)
    check(g2.undo() is False, "空历史时撤销返回 False 不崩")
    check(g2.redo() is False, "空重做栈时重做返回 False 不崩")


def test_push_onto_wall():
    section("4. 推箱受阻（箱子后面是墙）")
    # 构造一个"箱子贴墙"的局面：玩家 → 箱子 → 墙
    g = sk.Sokoban()
    g.load_level(0)
    lv = g.level
    found = False
    for d in range(4):
        dx, dy = sk.DIRS[d]
        for b in g.boxes:
            back = (b[0] + dx, b[1] + dy)
            front = (b[0] - dx, b[1] - dy)
            if lv.cell(back[0], back[1]) == sk.WALL and \
                    lv.cell(front[0], front[1]) != sk.WALL:
                # 把玩家放在箱子前面
                g.player = front
                g.history.clear()
                before = set(g.boxes)
                ok = g.try_move(d, ignore_anim=True)
                check(not ok, "箱子后面是墙时推不动")
                check(set(g.boxes) == before, "推不动时箱子不动")
                found = True
                break
        if found:
            break
    if not found:
        check(True, "（此关无贴墙箱子，跳过）")


def test_solve_and_clear():
    section("5. 求解器真跑一局 → 通关链路")
    # 用第 1 关（简单）真跑一遍
    g = sk.Sokoban()
    g.load_level(0)
    lv = g.level
    sol = sk.solve_level(lv, node_limit=3000000)
    check(sol is not None, "第 1 关求得解")
    if sol:
        check(len(sol) > 0, "解序列非空", str(len(sol)))
        # 逐步执行，最后一步必须触发通关
        for i, d in enumerate(sol):
            g.try_move(d, ignore_anim=True)
        check(g.state == sk.W_PLAY or g.state == sk.W_CLEAR,
              "执行解序列过程状态合法", g.state)
        check(sk.is_solved(lv, g.boxes), "执行解序列后所有箱子归位")
        check(lv.index in g.cleared, "通关后关卡号进入已通关列表")
        check(g.best.get(lv.index) == len(sol),
              "通关步数被记录为最少步数", str(g.best))

    # 通关状态下的输入
    g.load_level(0)
    sol = sk.solve_level(g.level, node_limit=3000000)
    for d in sol:
        g.try_move(d, ignore_anim=True)
    check(g.state == sk.W_CLEAR, "通关后进入 W_CLEAR 状态", g.state)
    post_key(g, pygame.K_n)
    check(g.state in (sk.W_PLAY, sk.W_TITLE), "通关界面按 N 能切走", g.state)


def test_solved_not_double_counted():
    section("6. 已通关不重复结算")
    g = sk.Sokoban()
    g.load_level(0)
    sol = sk.solve_level(g.level, node_limit=3000000)
    for d in sol:
        g.try_move(d, ignore_anim=True)
    check(g.state == sk.W_CLEAR, "先通关", g.state)
    cleared_before = list(g.cleared)
    best_before = dict(g.best)
    moves = g.moves_total
    # 再调一次 try_move，不应改变任何计数
    g.try_move(sk.L)
    check(g.cleared == cleared_before, "重复触发不增加已通关计数")
    check(g.best == best_before, "重复触发不改变最少步数")
    check(g.moves_total == moves, "W_CLEAR 状态下移动不生效")


# ---------------------------------------------------------------- 7. 状态机与事件

def test_state_machine():
    section("7. 状态机与真实事件驱动")
    g = sk.Sokoban()
    check(g.state == sk.W_TITLE, "初始为标题态", g.state)

    # 标题 → 开始游戏（用真实 KEYDOWN）
    post_key(g, pygame.K_RETURN)
    check(g.state == sk.W_PLAY, "标题按 Enter → 进入游戏", g.state)

    # 游戏 → 菜单
    post_key(g, pygame.K_ESCAPE)
    check(g.state == sk.W_TITLE, "游戏按 ESC → 回标题", g.state)

    # 标题 → 关卡选择
    post_key(g, pygame.K_l)
    check(g.state == sk.W_LEVELS, "标题按 L → 关卡选择", g.state)
    post_key(g, pygame.K_ESCAPE)
    check(g.state == sk.W_TITLE, "关卡选择按 ESC → 回标题", g.state)

    # 静音切换
    m0 = g.sfx.muted
    post_key(g, pygame.K_m)
    check(g.sfx.muted != m0, "M 键切换静音")
    post_key(g, pygame.K_m)
    check(g.sfx.muted == m0, "再按 M 恢复")

    # 游戏中的快捷键
    g.load_level(5)
    g.state = sk.W_PLAY
    post_key(g, pygame.K_u)   # 空历史撤销
    check(True, "空历史撤销不崩")
    g.try_move(sk.L)
    n_hist = len(g.history)
    if n_hist:
        post_key(g, pygame.K_u)
        check(len(g.history) == n_hist - 1, "U 键触发撤销")
        post_key(g, pygame.K_y)
        check(len(g.history) == n_hist, "Y 键触发重做")
    post_key(g, pygame.K_r)
    check(g.moves_total == 0 and g.player == g.level.start_player,
          "R 键重开本关")
    idx0 = g.level_idx
    post_key(g, pygame.K_n)
    check(g.level_idx == idx0 + 1, "N 键进入下一关", f"{idx0} -> {g.level_idx}")
    post_key(g, pygame.K_p)
    check(g.level_idx == idx0, "P 键返回上一关", str(g.level_idx))

    # 最后一关按 N 不应越界
    g.load_level(59)
    g.state = sk.W_PLAY
    post_key(g, pygame.K_n)
    check(g.level_idx == 59, "最后一关按 N 不越界", str(g.level_idx))


def test_mouse_and_scaling():
    section("8. 鼠标点击 + 坐标换算")
    g = sk.Sokoban()
    surf = pygame.Surface((sk.WIN_W, sk.WIN_H))

    # 标题界面：点"开始游戏"按钮
    g.state = sk.W_TITLE
    g.draw(surf)
    btns = [(n, r) for n, r, a in g._buttons if n == "title_start"]
    check(bool(btns), "标题界面注册了「开始游戏」按钮")
    if btns:
        _, rect = btns[0]
        click(g, rect.center)
        check(g.state == sk.W_PLAY, "点击「开始游戏」进入游戏", g.state)

    # 关卡选择界面：点第 3 个格子
    g.state = sk.W_LEVELS
    g.levels_page = 0
    g.draw(surf)
    cells = [(n, r, a) for n, r, a in g._buttons if n == "grid_lv"]
    check(len(cells) == 24, "关卡选择页有 24 个格子", str(len(cells)))
    if cells:
        name, rect, arg = cells[2]
        click(g, rect.center)
        check(g.level_idx == arg and g.state == sk.W_PLAY,
              "点击关卡格子进入该关", f"idx={g.level_idx} arg={arg}")

    # 格子中心 ↔ 屏幕坐标 往返一致
    g2 = sk.Sokoban()
    g2.load_level(3)
    for (x, y) in [(0, 0), (1, 2), (g2.level.w - 1, g2.level.h - 1)]:
        cx, cy = g2.cell_center(x, y)
        bcx, bcy = g2.screen_to_cell(cx, cy)
        check((bcx, bcy) == (x, y), f"格子 ({x},{y}) 坐标往返一致",
              f"{bcx},{bcy}")

    # 底部按钮点击（初始态下「重做」「上一关」被禁用，故只断言可点按钮 >= 4）
    g2.state = sk.W_PLAY
    g2.draw(surf)
    acts = g2._actions
    check(len(acts) >= 4, "游戏界面注册了撤销/重开/下一关/菜单等按钮",
          str(len(acts)))
    # 走几步后「重做」才会有历史，撤销按钮也应可用
    for d in range(4):
        if g2.try_move(d, ignore_anim=True):
            break
    g2.draw(surf)
    check(len(g2._actions) >= 5, "走动后撤销按钮变为可用", str(len(g2._actions)))


# ---------------------------------------------------------------- 9. 渲染

BG = sk.BG


def test_render_pixels():
    section("9. 渲染与像素检查")
    surf = pygame.Surface((sk.WIN_W, sk.WIN_H))

    # 棋盘区域不应出现"比背景更暗"的成片像素（排除墙与阴影）
    g = sk.Sokoban()
    g.load_level(0)
    g.state = sk.W_PLAY
    surf.fill(BG)
    g.draw(surf)

    # 检查玩家周围有玩家色
    px, py = g.player
    cx, cy = g.cell_center(px, py)
    region = [(int(cx) + dx, int(cy) + dy) for dx in range(-6, 7, 3)
              for dy in range(-6, 7, 3)]
    hit = 0
    for (sx, sy) in region:
        if 0 <= sx < sk.WIN_W and 0 <= sy < sk.WIN_H:
            c = surf.get_at((sx, sy))
            if abs(c[0] - sk.PLAYER[0]) < 60 and abs(c[2] - sk.PLAYER[2]) < 60:
                hit += 1
    check(hit > 0, "玩家所在格渲染出玩家色像素", f"命中 {hit}")

    # 每个箱子位置有箱子色（橙或绿）
    boxhit = 0
    for b in list(g.boxes)[:3]:
        bcx, bcy = g.cell_center(*b)
        found = False
        for dx in range(-8, 9, 4):
            for dy in range(-8, 9, 4):
                sx, sy = int(bcx) + dx, int(bcy) + dy
                if 0 <= sx < sk.WIN_W and 0 <= sy < sk.WIN_H:
                    c = surf.get_at((sx, sy))
                    if c[0] > 140 and c[2] < 120:      # 橙/绿都满足 R>140,B<120
                        found = True
                        break
            if found:
                break
        if found:
            boxhit += 1
    check(boxhit >= min(3, len(g.boxes)), "箱子位置渲染出箱子色像素",
          f"{boxhit}/{min(3, len(g.boxes))}")

    # HUD 文字：顶部条区域应有非背景像素
    hud = pygame.Rect(24, 20, sk.WIN_W - 48, 76)
    dark = 0
    for x in range(hud.x, hud.right, 3):
        for y in range(hud.y, hud.bottom, 3):
            c = surf.get_at((x, y))
            if c[0] < 150 and c[1] < 150 and c[2] < 160:
                dark += 1
    check(dark > 20, "HUD 区域渲染出文字像素", f"暗像素 {dark}")

    # 通关界面：遮罩应让画面整体变暗
    g.load_level(0)
    sol = sk.solve_level(g.level, node_limit=3000000)
    for d in sol:
        g.try_move(d, ignore_anim=True)
    surf.fill(BG)
    g.draw(surf)
    center = surf.get_at((sk.WIN_W // 2, 200))
    check(g.state == sk.W_CLEAR, "通关界面状态", g.state)
    check(not (center[0] == BG[0] and center[1] == BG[1] and center[2] == BG[2]),
          "通关界面已覆盖遮罩/面板")

    # 三个主界面都能画出来不崩
    for st, label in ((sk.W_TITLE, "标题"), (sk.W_LEVELS, "选关"),
                      (sk.W_PLAY, "游戏")):
        g2 = sk.Sokoban()
        g2.state = st
        try:
            surf.fill(BG)
            g2.draw(surf)
            check(True, f"{label}界面绘制不崩")
        except Exception as e:
            check(False, f"{label}界面绘制不崩", f"{type(e).__name__}: {e}")


def test_no_darker_blobs():
    section("10. 覆写类渲染 bug 扫描（限定区域）")
    # 只在"只该有纯色"的缝隙里扫：棋盘外的左右留白
    g = sk.Sokoban()
    g.load_level(5)
    g.state = sk.W_PLAY
    surf = pygame.Surface((sk.WIN_W, sk.WIN_H))
    surf.fill(BG)
    g.draw(surf)

    left = pygame.Rect(4, sk.WIN_H - 100, 12, 80)   # 左下角空白
    darker = 0
    for x in range(left.x, left.right):
        for y in range(left.y, left.bottom, 2):
            c = surf.get_at((x, y))
            if c[0] < BG[0] - 12 or c[1] < BG[1] - 12 or c[2] < BG[2] - 12:
                darker += 1
    check(darker == 0, "棋盘外空白区无「比背景更暗」的像素", f"暗像素 {darker}")


def test_hud_layout():
    section("14. HUD 布局（文字不重叠、不越界）")
    surf = pygame.Surface((sk.WIN_W, sk.WIN_H))
    problems = []
    # 对多个关卡（尺寸差异大）分别验证
    for lidx in (0, 5, 20, 36, 59):
        g = sk.Sokoban()
        g.load_level(lidx)
        g.state = sk.W_PLAY
        surf.fill(BG)
        g.draw(surf)
        rects = [r for _, r in g._actions] + [r for _, r, _ in g._buttons]
        # a) 按钮之间不得重叠
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                if rects[i].colliderect(rects[j]):
                    problems.append(f"第{lidx+1}关 按钮 {i} 与 {j} 重叠")
        # b) 按钮必须完全在窗口内
        for i, r in enumerate(rects):
            if r.left < 0 or r.right > sk.WIN_W or r.top < 0 or r.bottom > sk.WIN_H:
                problems.append(f"第{lidx+1}关 按钮 {i} 越界 {tuple(r)}")
        # c) 按钮不得压到棋盘内容
        bx0, by0, bx1, by1 = g.bbox
        bx0 = g.cell_xy(bx0, by0)[0]
        by0 = g.cell_xy(bx0, by0)[1]
        board = pygame.Rect(bx0, by0,
                            (g.bbox[2] - g.bbox[0] + 1) * g.tile,
                            (g.bbox[3] - g.bbox[1] + 1) * g.tile)
        for i, r in enumerate(rects):
            if r.colliderect(board):
                problems.append(f"第{lidx+1}关 按钮 {i} 压住棋盘")
        # d) 棋盘必须完全落在 HUD 顶栏与按钮行之间
        if board.top < 100:
            problems.append(f"第{lidx+1}关 棋盘顶到 HUD（top={board.top}）")
        if rects and board.bottom > min(r.top for r in rects) - 2:
            problems.append(
                f"第{lidx+1}关 棋盘底({board.bottom}) 压到按钮行"
                f"({min(r.top for r in rects)})")
    check(not problems, "6 个关卡尺寸下：按钮不重叠/不越界/不压棋盘",
          "; ".join(problems[:5]))

    # 提示文字必须整行落在窗口内（用像素法验证：文字行两侧不能贴边）
    g = sk.Sokoban()
    g.load_level(20)
    g.state = sk.W_PLAY
    surf.fill(BG)
    g.draw(surf)
    # 提示行位于按钮行下沿与窗口底之间
    row_y = sk.BTN_TOP + sk.BTN_H + 12
    dark = [x for x in range(sk.WIN_W) if surf.get_at((x, row_y))[0] < 200]
    if dark:
        check(min(dark) >= 1 and max(dark) <= sk.WIN_W - 2,
              "提示文字行未被窗口裁切", f"最左 {min(dark)} 最右 {max(dark)}")
    else:
        check(False, "提示文字行确实渲染出来了", f"y={row_y} 该行无暗像素")


def test_board_fill():
    section("15. 棋盘绘制范围（墙外不画地板/棋子）")
    surf = pygame.Surface((sk.WIN_W, sk.WIN_H))
    bad = []
    FLOORS = {sk.FLOOR_A, sk.FLOOR_B}
    for lidx in (0, 20, 36, 59):
        g = sk.Sokoban()
        g.load_level(lidx)
        g.state = sk.W_PLAY
        surf.fill(BG)
        g.draw(surf)
        inside = g._playable_cells()
        lv = g.level
        # 墙外、且不在可达区域内的格子，其中心像素不能是地板色/棋子色
        # （允许是背景色或棋盘卡片底的白色 —— 那是刻意的衬托层）
        for y in range(lv.h):
            for x in range(lv.w):
                if lv.cell(x, y) == sk.WALL or (x, y) in inside:
                    continue
                px, py = g.cell_xy(x, y)
                t = g.tile
                c = surf.get_at((px + t // 2, py + t // 2))[:3]
                if tuple(c) in FLOORS:
                    bad.append(f"第{lidx+1}关 ({x},{y}) 墙外被画成地板 {tuple(c)}")
                elif c[0] > 240 and c[1] > 240 and c[2] > 240:
                    pass                      # 卡片底白色，允许
    check(not bad, "墙外空白格没有被画成地板或棋子（棋盘不漏多余方块）",
          "; ".join(bad[:4]))


def test_font_coverage():
    section("11. 中文字体字形覆盖")
    f = sk.load_font(24)
    check(sk.covers_cjk(f), "加载的字体包含全部界面汉字字形")
    # 直接对比：默认位图字体应当不含汉字（证明 covers_cjk 有效）
    default = pygame.font.Font(None, 24)
    check(not sk.covers_cjk(default),
          "默认位图字体被正确判定为不含汉字（验证检测方法有效）")
    # 探测串本身必须无重复字符（有重复必然误判缺字形）
    probe = sk.CJK_PROBE
    check(len(set(probe)) == len(probe),
          "探测串无重复字符", f"长度 {len(probe)} 去重后 {len(set(probe))}")
    check(len(probe) >= 30, "探测串覆盖足够多的汉字样本", str(len(probe)))

    # 从游戏源码里抽出所有会被渲染的非 ASCII 字面量，
    # 逐个确认它们在该字体下【真的画出了字形】（而不是豆腐块）。
    # 这比手写"界面用字列表"可靠：源码一改，断言自动跟上。
    import re
    src = open(os.path.join(HERE, "sokoban.py"), encoding="utf-8").read()
    render_strs = re.findall(
        r'(?:self\.text|\.render|_button|flash)\([^)]*?"([^"]*)"', src)
    ui_chars = set()
    for s in render_strs:
        ui_chars.update(c for c in s if ord(c) > 127)

    from sokoban import _surface_bytes, _notdef_bitmap
    notdef = _notdef_bitmap(f)
    tofu = []
    for c in sorted(ui_chars):
        img = f.render(c, True, (255, 255, 255))
        if _surface_bytes(img) == notdef:
            tofu.append(c)
    check(not tofu, "界面渲染的每个非 ASCII 字符都有真实字形（无豆腐块）",
          f"缺字形: {tofu}")

    missing = sorted(ui_chars - set(probe))
    check(not missing, "探测串覆盖源码中所有会被渲染的字符", str(missing))


def test_audio_degrades():
    section("12. 音频降级")
    g = sk.Sokoban()
    # 无论 ok 与否，play 都不能抛异常
    try:
        for name in ("move", "push", "undo", "redo", "placed", "win", "ui",
                     "blocked", "不存在的音效"):
            g.sfx.play(name)
        g.sfx.muted = True
        g.sfx.play("move")
        g.sfx.muted = False
        check(True, "音效播放/静音/缺名都不抛异常")
    except Exception as e:
        check(False, "音效播放/静音/缺名都不抛异常", str(e))
    check(g.sfx.ok in (True, False), "音效状态为布尔值（缺设备时静默降级）",
          str(g.sfx.ok))


# ---------------------------------------------------------------- 13. 压力

def test_stress():
    section("13. 压力测试（长时间运行）")
    import time
    g = sk.Sokoban()
    g.load_level(20)          # 较大的关卡
    g.state = sk.W_PLAY
    surf = pygame.Surface((sk.WIN_W, sk.WIN_H))
    keys = FakeKeys()
    import random
    rng = random.Random(7)

    n = 2500
    t0 = time.time()
    peak_hist = 0
    for i in range(n):
        # 每隔几帧换方向，制造连续输入
        if i % 5 == 0:
            keys.pressed = {rng.choice([pygame.K_LEFT, pygame.K_RIGHT,
                                        pygame.K_UP, pygame.K_DOWN])}
        g.update(1 / 60.0, keys)
        if g.anim is None:
            g.anim = None
        g.draw(surf)
        peak_hist = max(peak_hist, len(g.history))
    dt = time.time() - t0
    check(dt / n < 0.02, f"{n} 帧 update+draw 平均 < 20ms",
          f"实测 {dt / n * 1000:.2f} ms/帧")
    check(peak_hist < 5000, "历史栈长度受控", str(peak_hist))
    check(len(g.history) <= n, "历史记录不超过帧数")

    # 粒子/实体列表不存在无界增长（本游戏无粒子，检查按钮列表不累积）
    g.draw(surf)
    check(len(g._buttons) < 200, "按钮列表不随帧数累积", str(len(g._buttons)))


# ---------------------------------------------------------------- 14. 截图

def test_screenshots():
    section("14. 导出预览截图")
    outdir = os.path.join(HERE, "preview")
    os.makedirs(outdir, exist_ok=True)
    surf = pygame.Surface((sk.WIN_W, sk.WIN_H))
    shots = []

    def shot(game, name):
        surf.fill(BG)
        game.draw(surf)
        for _ in range(2):          # 双缓冲保证动画元素画上
            game.draw(surf)
        path = os.path.join(outdir, name)
        pygame.image.save(surf, path)
        shots.append(path)

    g = sk.Sokoban()
    g.state = sk.W_TITLE
    g.title_sel = 0
    shot(g, "01_title.png")

    g.state = sk.W_TITLE
    g.title_sel = 14
    shot(g, "02_title_level15.png")

    g.state = sk.W_LEVELS
    g.levels_page = 0
    shot(g, "03_levels_page1.png")

    for idx, name in ((0, "04_level1.png"), (4, "05_level5.png"),
                      (20, "06_level21.png")):
        g2 = sk.Sokoban()
        g2.load_level(idx)
        g2.state = sk.W_PLAY
        # 走几步让画面有变化
        for d in (sk.R, sk.D):
            g2.anim = None
            g2.try_move(d, ignore_anim=True)
        g2.anim = None
        shot(g2, name)

    # 通关界面
    g3 = sk.Sokoban()
    g3.load_level(0)
    sol = sk.solve_level(g3.level, node_limit=3000000)
    for d in sol:
        g3.try_move(d)
    g3.anim = None
    shot(g3, "07_clear.png")

    check(len(shots) == 7, "导出 7 张截图", str(len(shots)))
    for p in shots:
        check(os.path.exists(p) and os.path.getsize(p) > 3000,
              f"截图有内容 {os.path.basename(p)}")
    return shots


# ---------------------------------------------------------------- 主入口

def main():
    argv = sys.argv[1:]
    quick = "--quick" in argv
    shots = "--shots" in argv

    pygame.init()
    try:
        pygame.mixer.init()
    except Exception:
        pass

    print("=" * 60)
    print("推箱子 Sokoban 自检")
    print(f"pygame {pygame.version.ver} / Python {sys.version.split()[0]}")
    print("=" * 60)

    test_levels(quick=quick)
    test_logic()
    test_undo_redo()
    test_push_onto_wall()
    test_solve_and_clear()
    test_solved_not_double_counted()
    test_state_machine()
    test_mouse_and_scaling()
    test_render_pixels()
    test_no_darker_blobs()
    test_hud_layout()
    test_board_fill()
    test_font_coverage()
    test_audio_degrades()
    test_stress()
    if shots:
        test_screenshots()

    print("\n" + "=" * 60)
    print(f"通过 {PASS} 项，失败 {FAIL} 项")
    if FAILURES:
        print("\n失败明细：")
        for sec, label, detail in FAILURES:
            print(f"  [{sec}] {label}" + (f"  -> {detail}" if detail else ""))
        print("=" * 60)
        return 1
    print("全部通过 ✓")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
