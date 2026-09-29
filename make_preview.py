#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 preview/ 目录下的预览截图。

用法：
    python make_preview.py

无窗口运行（SDL dummy），产出的 PNG 可直接用于 README。
"""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import pygame  # noqa: E402

import sokoban as sk  # noqa: E402


def main():
    pygame.init()
    try:
        pygame.mixer.init()
    except Exception:
        pass

    outdir = os.path.join(HERE, "preview")
    os.makedirs(outdir, exist_ok=True)
    surf = pygame.Surface((sk.WIN_W, sk.WIN_H))

    def shot(game, name):
        surf.fill(sk.BG)
        game.draw(surf)
        game.draw(surf)          # 画两遍，确保动画层叠上
        path = os.path.join(outdir, name)
        pygame.image.save(surf, path)
        print(f"  -> {name}")
        return path

    made = []

    g = sk.Sokoban()
    g.state = sk.W_TITLE
    g.title_sel = 0
    made.append(shot(g, "01_title.png"))

    g = sk.Sokoban()
    g.state = sk.W_TITLE
    g.title_sel = 14
    made.append(shot(g, "02_title_level15.png"))

    g = sk.Sokoban()
    g.state = sk.W_LEVELS
    g.levels_page = 0
    made.append(shot(g, "03_levels_page1.png"))

    for idx, name in ((0, "04_level1.png"), (4, "05_level5.png"),
                      (20, "06_level21.png")):
        g = sk.Sokoban()
        g.load_level(idx)
        g.state = sk.W_PLAY
        for d in (sk.R, sk.D):
            g.try_move(d, ignore_anim=True)
        g.anim = None
        made.append(shot(g, name))

    # 通关画面
    g = sk.Sokoban()
    g.load_level(0)
    sol = sk.solve_level(g.level, node_limit=3000000)
    for d in sol:
        g.try_move(d, ignore_anim=True)
    g.anim = None
    made.append(shot(g, "07_clear.png"))

    print(f"\n共生成 {len(made)} 张截图 -> {outdir}")
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
