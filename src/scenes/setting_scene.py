'''
[TODO HACKATHON 5]
Try to mimic the menu_scene.py or game_scene.py to create this new scene
'''
import pygame as pg

from typing import override
from src.scenes.scene import Scene
from src.utils import GameSettings
from src.sprites import BackgroundSprite
from src.interface.components import Button
from src.core.services import scene_manager, input_manager, sound_manager
from src.sprites import BackgroundSprite, Sprite


class SettingScene(Scene):
    background: BackgroundSprite
    back_button: Button

    def __init__(self) -> None:
        super().__init__()

        self.background = BackgroundSprite("backgrounds/background1.png")

        flat_w,flat_h=800,600
        self.overlay_flat_size=(flat_w,flat_h)
        self.overlay_flat_sprite=Sprite("UI/raw/UI_Flat_Frame03a.png",self.overlay_flat_size)

        #checkbox
        self.checkbox_size=32
        self.checkbox_x = GameSettings.SCREEN_WIDTH  // 2-150
        self.checkbox_y = GameSettings.SCREEN_HEIGHT // 2 -100
        self.is_muted = GameSettings.MUTE_BGM
        # self.is_muted = False
        # GameSettings.MUTE_BGM = self.is_muted
        self.checkbox_button=Button(
            "UI/raw/UI_Flat_ToggleOff02a.png",
            "UI/raw/UI_Flat_ToggleOff02a.png",
            self.checkbox_x,self.checkbox_y,self.checkbox_size,self.checkbox_size,
            lambda: self.checkbox_check()
        )           

        #slider
        self.slider_size_width=300
        self.slider_size_height=50

        
        self.slider_x=GameSettings.SCREEN_HEIGHT // 2+100
        self.slider_y=GameSettings.SCREEN_HEIGHT//2
        self.slider_value = int(GameSettings.AUDIO_VOLUME * 100)
        self.slider_touch=False

        self.slider_bar_sprite = Sprite(
            "UI/raw/UI_Flat_Bar13a.png",
            (self.slider_size_width, self.slider_size_height)
        )
        self.slider_fill_sprite = Sprite(
            "UI/raw/UI_Flat_BarFill01f.png",
            (self.slider_size_width, self.slider_size_height)
        )

        self.dot_width = 32
        self.dot_height = 32
        self.slider_dot_sprite = Sprite(
            "UI/raw/UI_Flat_Handle03a.png",
            (self.dot_width, self.dot_height)
        )
        self.word = pg.font.Font("assets/fonts/Minecraft.ttf", 25)

        # self.word=pg.font.SysFont("arial",25)

        self.px = GameSettings.SCREEN_WIDTH // 2 -350
        self.py = GameSettings.SCREEN_HEIGHT * 3 // 4

        self.back_button = Button(
            "UI/button_back.png",          
            "UI/button_back_hover.png",    
            self.px,                            
            self.py,                            
            50, 50,                      
            lambda: scene_manager.change_scene("menu"),   
        )
    def checkbox_check(self):
        self.is_muted = not self.is_muted
        img=(
        "UI/raw/UI_Flat_ToggleOn02a.png" if self.is_muted else "UI/raw/UI_Flat_ToggleOff02a.png"            
        )
        sprite=Sprite(img,(32,32))
        self.checkbox_button.img_button_default=sprite
        self.checkbox_button.img_button_hover=sprite     
        self.checkbox_button.img_button = sprite   

        GameSettings.MUTE_BGM = self.is_muted

        if self.is_muted:
            sound_manager.pause_all()
        else:
            sound_manager.resume_all()
            # if sound_manager.current_bgm is not None:
            #     sound_manager.current_bgm.set_volume(self.slider_value/100)
            sound_manager.set_bgm_volume(self.slider_value/100)
        

    @override
    def enter(self) -> None:
        pass

    @override
    def exit(self) -> None:
        self.is_muted = GameSettings.MUTE_BGM

        # 2. 根據目前狀態更新 checkbox 的圖示
        img = (
            "UI/raw/UI_Flat_ToggleOn02a.png" if self.is_muted
            else "UI/raw/UI_Flat_ToggleOff02a.png"
        )
        sprite = Sprite(img, (32, 32))
        self.checkbox_button.img_button_default = sprite
        self.checkbox_button.img_button_hover = sprite
        self.checkbox_button.img_button = sprite

    @override
    def update(self, dt: float) -> None:

        if input_manager.key_pressed(pg.K_ESCAPE):
            # scene_manager.change_scene("menu")
            self.back_button.on_click()
            return
        
        self.back_button.update(dt)
        self.checkbox_button.update(dt)
        mouse_x,mouse_y=pg.mouse.get_pos()
        mouse_down=pg.mouse.get_pressed()[0] # 左鍵
        #checkbox
        # if self.checkbox_rect.collidepoint(mouse_x,mouse_y):
        #     if mouse_down and not self.checkbox_mouse:
        #         self.checkbox_check=not self.checkbox_check
        #         if self.checkbox_check:
        #             sound_manager.pause_all()
        #         else:
        #             sound_manager.play_bgm(self.slider_value/100)
        #         print("Mute :",self.checkbox_check)

        #slider
        slider_rect=pg.Rect(
            self.slider_x,
            self.slider_y,
            self.slider_size_width,
            self.slider_size_height
        )

        dot_center_x=self.slider_x+int(self.slider_value / 100* self.slider_size_width) 
        dot_rect = pg.Rect(
            dot_center_x - self.dot_width // 2,
            self.slider_y - (self.dot_height - self.slider_size_height) // 2,
            self.dot_width,
            self.dot_height
        )
        

        if mouse_down:
            if (not self.slider_touch) and (
                dot_rect.collidepoint(mouse_x, mouse_y)
                or slider_rect.collidepoint(mouse_x, mouse_y)
            ):
                self.slider_touch = True
            
            if self.slider_touch:
                mouse_x_clamped = max(self.slider_x,
                                      min(self.slider_x + self.slider_size_width, mouse_x))
                ratio = (mouse_x_clamped - self.slider_x) / self.slider_size_width
                self.slider_value = int(ratio * 100)

                if not self.is_muted and sound_manager.current_bgm is not None:
                    sound_manager.set_bgm_volume(self.slider_value/100)
                    GameSettings.AUDIO_VOLUME = self.slider_value / 100
                    # sound_manager.toggle_mute()
        else:
            self.slider_touch = False
        
        self.checkbox_mouse=mouse_down


    @override
    def draw(self, screen: pg.Surface) -> None:
        self.background.draw(screen)
        flat_w, flat_h = self.overlay_flat_size
        flat_x = (GameSettings.SCREEN_WIDTH  - flat_w) // 2
        flat_y = (GameSettings.SCREEN_HEIGHT - flat_h) // 2      
        self.overlay_flat_sprite.rect.topleft=(flat_x,flat_y)
        screen.blit(self.overlay_flat_sprite.image, self.overlay_flat_sprite.rect) 

        #mute
        self.checkbox_button.draw(screen)
        mute="ON" if self.is_muted else "OFF"
        text_muted = self.word.render(f"Mute:{mute}",True,(0,0,0))
        screen.blit(
            text_muted,
            (self.checkbox_x+self.checkbox_size-50,self.checkbox_y-50)
        )

        #slider
        bar_rect = pg.Rect(
            self.slider_x,
            self.slider_y,
            self.slider_size_width,
            self.slider_size_height
        )        
        screen.blit(self.slider_bar_sprite.image, bar_rect)
        fill_width = int(self.slider_size_width * self.slider_value / 100)
        if fill_width > 0:
            fill_dest_rect = pg.Rect(
                self.slider_x,
                self.slider_y,
                fill_width,
                self.slider_size_height
            )
            fill_src_rect = pg.Rect(
                0, 0,
                fill_width,
                self.slider_size_height
            )
            screen.blit(self.slider_fill_sprite.image, fill_dest_rect, area=fill_src_rect)
        dot_center_x = self.slider_x + int(self.slider_value / 100 * self.slider_size_width)
        dot_rect = pg.Rect(
            dot_center_x - self.dot_width // 2,
            self.slider_y - (self.dot_height - self.slider_size_height) // 2,
            self.dot_width,
            self.dot_height
        )
        self.slider_dot_sprite.rect = dot_rect
        screen.blit(self.slider_dot_sprite.image, self.slider_dot_sprite.rect)

        #volume字體
        text_volume = self.word.render(f"Volume : {self.slider_value}%",True,(0,0,0))
        screen.blit(
            text_volume,
            (self.slider_x,self.slider_y-50)
        )
        text_esc=self.word.render(f"Tap ESC can back",True,(0,0,0))
        screen.blit(
        text_esc,
        (self.px+55,self.py+35)
            )                    

        self.back_button.draw(screen)        