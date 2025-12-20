import pygame as pg

from src.utils import GameSettings
from src.sprites import BackgroundSprite
from src.scenes.scene import Scene
from src.interface.components import Button
from src.core.services import scene_manager, sound_manager, input_manager
from typing import override

from src.utils import load_img

class MenuScene(Scene):
    # Background Image
    background: BackgroundSprite
    # Buttons
    play_button: Button
    
    def __init__(self):
        super().__init__()
        self.background = BackgroundSprite("backgrounds/background1.png")

        px, py = GameSettings.SCREEN_WIDTH // 2, GameSettings.SCREEN_HEIGHT * 3 // 4
        self.play_button = Button(
            "UI/button_play.png", "UI/button_play_hover.png",
            px + 50, py, 100, 100,
            lambda: scene_manager.change_scene("game")
        )
        self.setting_button = Button(
            "UI/button_setting.png",
            "UI/button_setting_hover.png",
            px-100, py , 100, 100,
            lambda: scene_manager.change_scene("setting")
        )
        self.element_panel_img = load_img("element/pokemon.png")
        self.element_panel_img = pg.transform.scale(
            self.element_panel_img,
            (500, 200)   
        )



    @override
    def enter(self) -> None:
        
        sound_manager.play_bgm("RBY 101 Opening (Part 1).ogg")
        pass

    @override
    def exit(self) -> None:
        pass

    @override
    def update(self, dt: float) -> None:
        if input_manager.key_pressed(pg.K_SPACE):
            scene_manager.change_scene("game")
            return
        self.play_button.update(dt)
        self.setting_button.update(dt)
    @override
    def draw(self, screen: pg.Surface) -> None:
        self.background.draw(screen)
        self.play_button.draw(screen)
        self.setting_button.draw(screen)
        if self.element_panel_img:
            img_w = self.element_panel_img.get_width()
            img_h = self.element_panel_img.get_height()

            img_x = (GameSettings.SCREEN_WIDTH - img_w) // 2
            img_y = (GameSettings.SCREEN_HEIGHT - img_h) // 2 - 80

            screen.blit(self.element_panel_img, (img_x, img_y))

        self.play_button.draw(screen)
        self.setting_button.draw(screen)