import pygame as pg
from typing import override

from src.scenes.scene import Scene
from src.sprites import BackgroundSprite
from src.core.services import scene_manager, input_manager, sound_manager
from src.utils import GameSettings, load_img

class DialogScene(Scene):
    def __init__(self) -> None:
        super().__init__()

        self.background = BackgroundSprite("backgrounds/background2.png")

        sheet = load_img("character/ow1.png")
        frame_w = 32
        frame_h = 32
        standing_frame = sheet.subsurface(pg.Rect(0, 0, frame_w, frame_h))
        self.npc_img = pg.transform.scale(standing_frame, (250, 250))

        self.npc_pos = (GameSettings.SCREEN_WIDTH - 260, 280)

        self.word_font  = pg.font.Font("assets/fonts/Minecraft.ttf", 24)
        self.title_font = pg.font.Font("assets/fonts/Minecraft.ttf", 30)

        self.lines: list[str] = []
        self.idx: int = 0
        self.on_finish = None
        self.return_scene: str = "game"

    @override
    def enter(self) -> None:
        sound_manager.play_bgm("RBY 102 Opening (Part 2).ogg")

    # sprite_index 参数保留也行，但不再使用
    def setup(self, lines: list[str], sprite_index: int = 1, on_finish=None):
        self.lines = lines
        self.idx = 0
        self.on_finish = on_finish

    @override
    def update(self, dt: float) -> None:
        if input_manager.key_pressed(pg.K_SPACE):
            self.idx += 1
            if self.idx >= len(self.lines):
                cb = self.on_finish
                self.on_finish = None
                if cb:
                    cb()
                    return
                scene_manager.change_scene(self.return_scene)
                return

        if input_manager.key_pressed(pg.K_ESCAPE):
            cb = self.on_finish
            self.on_finish = None
            if cb:
                cb()
                return
            scene_manager.change_scene(self.return_scene)

    def draw(self, screen: pg.Surface) -> None:
        self.background.draw(screen)
        screen.blit(self.npc_img, self.npc_pos)

        box_height = 200
        box_y = GameSettings.SCREEN_HEIGHT - box_height
        pg.draw.rect(screen, (0, 0, 0, 200), (0, box_y, GameSettings.SCREEN_WIDTH, box_height))
        pg.draw.rect(screen, (255, 255, 255), (0, box_y, GameSettings.SCREEN_WIDTH, box_height), 2)

        if self.lines and 0 <= self.idx < len(self.lines):
            surf = self.word_font.render(self.lines[self.idx], True, (255, 255, 255))
            screen.blit(surf, (30, box_y + 30))

        hint = self.word_font.render("SPACE to continue", True, (200, 200, 200))
        screen.blit(hint, (GameSettings.SCREEN_WIDTH - 250, GameSettings.SCREEN_HEIGHT - 40))