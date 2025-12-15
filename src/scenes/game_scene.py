import pygame as pg
import threading
import time
import random
import copy

from src.scenes.scene import Scene
from src.data.shop import Shop
from src.core import GameManager, OnlineManager
from src.utils import Logger, PositionCamera, GameSettings, Position,load_img
from src.interface.components.button import Button #加按鈕的class
from src.utils.minimap import MiniMap

from src.data.monster_data import MONSTER_DATA, build_monster
from src.core.services import scene_manager
from src.core.services import input_manager
from src.core.services import sound_manager
from src.sprites import Sprite
from typing import override
from src.scenes.battle_scene import BattleScene
from src.scenes.bush_scene import BushScene


class GameScene(Scene):
    game_manager: GameManager
    online_manager: OnlineManager | None
    sprite_online: Sprite
    
    def __init__(self):
        super().__init__()
        # Game Manager
        manager = GameManager.load("saves/game0.json")
        # manager = GameManager()
        if manager is None:
            Logger.error("Failed to load game manager")
            exit(1)
        self.game_manager = manager

        # tile = GameSettings.TILE_SIZE
        # self.bush_zones: dict[str, list[pg.Rect]] = {
        #     "map.tmx": [
        #         # 這裡先隨便放幾個，等下教你怎麼換成對的座標
        #         pg.Rect(26 * tile, 24 * tile, tile, tile),
        #         pg.Rect(27 * tile, 24 * tile, tile, tile),
        #         pg.Rect(28 * tile, 24 * tile, tile, tile),
        #     ],
        #     "gym.tmx": [],  # 體育館裡面先不要有草叢抓怪
        # }        
        
        # Online Manager
        if GameSettings.IS_ONLINE:
            self.online_manager = OnlineManager()
        else:
            self.online_manager = None
        self.sprite_online = Sprite("ingame_ui/options1.png", (GameSettings.TILE_SIZE, GameSettings.TILE_SIZE))

        #控制overlay的
        self.overlay_open=False
        self.overlaybag_open=False

        # 建立button
        button_x=GameSettings.SCREEN_WIDTH-80 #靠右邊
        button_y=20 #上下
        button_w=60
        button_h=60

        #模仿menuscene的
        self.overlay_button=Button(
            "UI/button_setting.png",
            "UI/button_setting_hover.png",
            button_x,button_y,button_w,button_h, #四個東西
            lambda: self.open_overlay()
        )
        
        #bag
        button_bag_x=GameSettings.SCREEN_WIDTH-150 #靠右邊
        button_bag_y=20 #上下
        button_bag_w=60
        button_bag_h=60        

        self.bag_button=Button(
            "UI/button_backpack.png",
            "UI/button_backpack_hover.png",
            button_bag_x,button_bag_y,button_bag_w,button_bag_h, #四個東西
            lambda: self.open_bag_overlay()
        )
        #bag overlay
        flat_bag_w,flat_bag_h=800,600
        self.overlay_flat_bag_size=(flat_bag_w,flat_bag_h)
        self.overlay_flat_bag_sprite=Sprite("UI/raw/UI_Flat_Frame01a.png",self.overlay_flat_bag_size)       

        #shop
        self.shop = Shop(self.game_manager)

        #overlay setting
        flat_w,flat_h=800,600
        self.overlay_flat_size=(flat_w,flat_h)
        self.overlay_flat_sprite=Sprite("UI/raw/UI_Flat_Frame03a.png",self.overlay_flat_size)

        #checkbox
        self.checkbox_size=32
        self.checkbox_x = GameSettings.SCREEN_WIDTH  // 2-150
        self.checkbox_y = GameSettings.SCREEN_HEIGHT // 2 -100
        self.is_muted = False
        GameSettings.MUTE_BGM = self.is_muted
        self.checkbox_button=Button(
            "UI/raw/UI_Flat_ToggleOff02a.png",
            "UI/raw/UI_Flat_ToggleOff02a.png",
            self.checkbox_x,self.checkbox_y,self.checkbox_size,self.checkbox_size,
            lambda: self.checkbox_check()
        )           
        
        #slider
        self.is_muted=False
        self.slider_size_width=300
        self.slider_size_height=50
      
        self.slider_x=GameSettings.SCREEN_HEIGHT // 2+100
        self.slider_y=GameSettings.SCREEN_HEIGHT//2
        self.slider_value=int(GameSettings.AUDIO_VOLUME*100)
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

        #save
        self.save_button_x=GameSettings.SCREEN_HEIGHT // 2
        self.save_button_y=GameSettings.SCREEN_WIDTH // 2-100
        self.save_button_w_h=50
        self.save_button=Button(
            "UI/button_save.png",
            "UI/button_save_hover.png",
            self.save_button_x,self.save_button_y,self.save_button_w_h,self.save_button_w_h, #四個東西
            lambda: self.save_game()
        )     

        #load          
        self.load_button_x=GameSettings.SCREEN_HEIGHT // 2+100
        self.load_button_y=GameSettings.SCREEN_WIDTH // 2 -100
        self.load_button_w_h=50
        self.load_button=Button(
            "UI/button_load.png",
            "UI/button_load_hover.png",
            self.load_button_x,self.load_button_y,self.load_button_w_h,self.load_button_w_h, #四個東西
            lambda: self.load_game()
        )            


        #返回
        self.back_button_x=GameSettings.SCREEN_WIDTH //2 +400
        self.back_button_y=GameSettings.SCREEN_HEIGHT //2 -350
        self.bacl_button_w=50
        self.bacl_button_h=50

        self.overlay_button_back=Button(
            "UI/button_back.png",
            "UI/button_back_hover.png",
            self.back_button_x,self.back_button_y,self.bacl_button_w,self.bacl_button_h,
            lambda: self.close_overlay()
        )

        #word
        self.word = pg.font.Font("assets/fonts/Minecraft.ttf", 25)
        self.small_word = pg.font.Font("assets/fonts/Minecraft.ttf", 15)

        #bush
        self.in_bush_zone = False
        self.bush_warning = Sprite("exclamation.png", (32, 32))
        self.bush_warning.rect.topleft = (0, 0)

        #shop
        self.shop_open=False
        self.current_shop_npc=None

        #toast
        self.toasts: list[dict] = []
        self.toast_duration = 0.5
        self.toast_font = pg.font.Font("assets/fonts/Minecraft.ttf", 18)
        #minimap
        self.minimap = MiniMap()
        self.map_pixel_w = 1
        self.map_pixel_h = 1        


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

        #  打開 overlay        
    def open_overlay(self):
        self.overlay_open = True
        self.overlaybag_open = False
        self.shop.overlay_open=False

    #  關閉 overlay
    def close_overlay(self):
        self.overlay_open = False
        self.overlaybag_open = False
        self.shop.overlay_open=False
    
    def open_bag_overlay(self):
        self.overlaybag_open = True
        self.overlay_open = False

    def open_bag_from_battle(self):
        self.overlay_open = False
        self.overlaybag_open = True

    def add_toast(self, text: str) -> None:
        self.toasts.append({"text": text, "time": self.toast_duration})

    def _update_toasts(self, dt: float) -> None:
        for t in self.toasts:
            t["time"] -= dt
        self.toasts = [t for t in self.toasts if t["time"] > 0]

    def _draw_toasts(self, screen: pg.Surface) -> None:
        if not self.toasts:
            return
        base_y = GameSettings.SCREEN_HEIGHT - 20
        gap = 6
        for idx, toast in enumerate(reversed(self.toasts)):
            surf = self.toast_font.render(toast["text"], True, (255, 255, 255))
            padding = 4
            bg_rect = surf.get_rect()
            bg_rect.width += padding * 2
            bg_rect.height += padding * 2
            bg_rect.bottomright = (
                GameSettings.SCREEN_WIDTH - 20,
                base_y - idx * (bg_rect.height + gap),
            )
            pg.draw.rect(screen, (0, 0, 0), bg_rect)
            screen.blit(surf, (bg_rect.x + padding, bg_rect.y + padding))


    def save_game(self):
        self.game_manager.save("saves/game0.json")

    def load_game(self):
        new_manager = GameManager.load("saves/game0.json")
        if new_manager:
            self.game_manager = new_manager
            self.slider_value=int(GameSettings.AUDIO_VOLUME*100)

            if GameSettings.MUTE_BGM:
                sound_manager.pause_all()
            else:
                sound_manager.resume_all()
                if sound_manager.current_bgm is not None:
                    sound_manager.set_bgm_volume(GameSettings.AUDIO_VOLUME)

    def start_battle_with_trainer(self, trainer):
    # 1. 取得玩家第一隻怪（你 Bag 裡的資料）
    # 1. 找一隻自己還活著的 monster
        player_mon: dict | None = None
        for m in self.game_manager.bag._monsters_data:
            if m["hp"] > 0:
                player_mon = m
                break
        if player_mon is None:
            return  # 全死掉就不開戰

        # 隨機挑怪獸種類
        proto = random.choice(MONSTER_DATA)

        # 隨機等級（0~50）
        level = random.randint(0, 50)

        # 用你的升級倍率生成真正的怪物
        enemy_mon = build_monster(proto, level)

        # 戰鬥 scene 初始化資料
        battle_scene = scene_manager.get_scene("battle")
        if isinstance(battle_scene, BattleScene):
            battle_scene.setup(player_mon, enemy_mon, self.game_manager.bag)

        # 6. 切換場景
        scene_manager.change_scene("battle")
        
    #shop
    def open_shop(self,trainer)-> None:
        self.shop.open_overlay()
        self.shop_open=True
        self.current_shop_npc=trainer    

    def close_shop(self) -> None:
        self.shop_open = False
        self.current_shop_npc = None

    @override
    def enter(self) -> None:
        sound_manager.play_bgm("RBY 103 Pallet Town.ogg")
        if self.online_manager:
            self.online_manager.enter()
        # 同步 GameScene 的 checkbox 狀態
        self.is_muted = GameSettings.MUTE_BGM
        img = (
            "UI/raw/UI_Flat_ToggleOn02a.png" if self.is_muted
            else "UI/raw/UI_Flat_ToggleOff02a.png"
        )
        sprite = Sprite(img, (32, 32))
        self.checkbox_button.img_button_default = sprite
        self.checkbox_button.img_button_hover = sprite
        self.checkbox_button.img_button = sprite
        
    @override
    def exit(self) -> None:
        if self.online_manager:
            self.online_manager.exit()

    # def shop(self,dt):
    #     bag = self.game_manager.bag
    #     items = bag._items_data  
    #     direction = input_manager.get_scroll_direction()
        

        # if not items:
        #     if input_manager.key_pressed(pg.K_ESCAPE):
        #         self.close_shop()
        #     return
                    

        
    @override
    def update(self, dt: float):
        # Check if there is assigned next scene
        self.shop.update_timer(dt)
        self.game_manager.try_switch_map()
        # 1) 先記住上一張地圖（第一次進來可能沒有）
        prev_map = getattr(self, "_minimap_prev_map", None)
        cur_map = self.game_manager.current_map.path_name

        if cur_map != prev_map:
            self._minimap_prev_map = cur_map
            m = self.game_manager.current_map

            if hasattr(m, "_surface") and m._surface is not None:
                self.map_pixel_w = m._surface.get_width()
                self.map_pixel_h = m._surface.get_height()
            else:
                # 保底，避免 crash
                self.map_pixel_w = 1
                self.map_pixel_h = 1

            self.minimap.build_from_map(
                self.game_manager.current_map,
                (self.map_pixel_w, self.map_pixel_h),
                map_key=cur_map
            )
        self._update_toasts(dt)


        #更新位置
        self.overlay_button.update(dt)
        self.bag_button.update(dt)

        # Update player and other data
        if self.game_manager.player:
            self.game_manager.player.update(dt)
        for enemy in self.game_manager.current_enemy_trainers:
            enemy.update(dt)
        

        #bush interaction
        player = self.game_manager.player
        self.in_bush_zone = False
        if player is not None:
            player_rect = player.animation.rect
            for rect in self.game_manager.current_map.bush_rects:
                if player_rect.colliderect(rect):
                    self.in_bush_zone =True
                    self.bush_warning.rect.centerx = player_rect.centerx
                    self.bush_warning.rect.bottom = player_rect.top - 10

                    if input_manager.key_pressed(pg.K_e):
                        bag = self.game_manager.bag
                        # 從背包選一隻還活著的當 player_mon
                        player_mon = None
                        for m in bag._monsters_data:
                            if m["hp"] > 0:
                                player_mon = m
                                break
                        if player_mon is None:
                            return  # 沒怪就不要進戰鬥
                        if MONSTER_DATA:
                            proto = random.choice(MONSTER_DATA)
                            level = random.randint(0, 50)
                            wild_mon = build_monster(proto, level)                  

                        bush_scene = scene_manager.get_scene("bush")
                        if isinstance(bush_scene, BushScene):
                            bush_scene.setup(player_mon, wild_mon, self.game_manager.bag)

                        scene_manager.change_scene("bush")
           
        # Update others
        
        if self.game_manager.player is not None and self.online_manager is not None:
            _ = self.online_manager.update(
                self.game_manager.player.position.x, 
                self.game_manager.player.position.y,
                self.game_manager.current_map.path_name
            )
        #esc
        if  (not self.shop.overlay_open) and input_manager.key_pressed(pg.K_ESCAPE):
            if self.overlaybag_open or self.overlay_open:
                self.overlay_button_back.on_click()
            else:
                self.open_overlay()
        #shop
        if self.shop.overlay_open:
            self.shop.update(dt)
            return
         
        #bag
        if input_manager.key_pressed(pg.K_b):
            if not self.overlay_open and not self.shop.overlay_open:
                self.open_bag_overlay()
        
        if self.overlaybag_open:
            self.overlay_button_back.update(dt)
            self.game_manager.bag.update(dt)
            if input_manager.mouse_pressed(1):
                mouse_pos = input_manager.mouse_pos
                result = self.game_manager.bag.handle_click(mouse_pos)

                # 讓 Bag 回傳的訊息顯示在右下角 toast（跟 Bush 一樣）
                if result is not None:
                    msg = result.get("message", "")
                    if msg:
                        self.add_toast(msg)

            # 更新右上角的 Back 按鈕（ESC 其實也會走 overlay_button_back.on_click）
            self.overlay_button_back.update(dt)

            #Bag 開著時，不要再更新後面地圖 / 設定 / shop 之類的
            return            
        #setting
        if self.overlay_open:
            self.overlay_button_back.update(dt)
            self.checkbox_button.update(dt)
            self.save_button.update(dt)
            self.load_button.update(dt)
        # if input_manager.key_pressed(pg.K_b):
        #     if not self.overlay_open:
        #         self.open_bag_overlay()
        # if self.overlaybag_open:
        #     self.overlay_button_back.update(dt)
        #     self.game_manager.bag.update(dt)
            # if input_manager.key_pressed(pg.K_ESCAPE):
            #     self.overlay_button_back.on_click()

        #更新剛才overlay寫的東西
        # if input_manager.key_pressed(pg.K_ESCAPE):
        #     if not self.overlay_open:
        #         self.open_overlay()
        #     if self.overlay_open:
        #         self.overlay_button_back.update(dt)
        #         self.checkbox_button.update(dt)
        #         self.save_button.update(dt)
        #         self.load_button.update(dt)
                # if input_manager.key_pressed(pg.K_ESCAPE):
                #     if self.overlay_open:
                #         self.overlay_button_back.on_click()  # 模拟按 back
                #     else:
                #         self.open_overlay()
            

        # for event in pg.event.get():

        #     if self.overlaybag_open:-
        #         self.input_manager.handle_event(event)


            # if input_manager.key_down(pg.K_DOWN):
            #     self.game_manager.bag.scroll+= scroll_speed*dt
            # if input_manager.key_down(pg.K_UP):
            #     self.game_manager.bag.scroll+= scroll_speed*dt                
            # max_scroll=0
            # min_scroll=-400 

            # if self.game_manager.bag.scroll>max_scroll:
            #     self.game_manager.bag.scroll=max_scroll
            # if self.game_manager.bag.scroll<min_scroll:
            #     self.game_manager.bag.scroll=min_scroll

        slider_rect=pg.Rect(
            self.slider_x,
            self.slider_y,
            self.slider_size_width,
            self.slider_size_height
        )
     
        #slider
        dot_center_x=self.slider_x+int(self.slider_value / 100* self.slider_size_width) 
        dot_rect = pg.Rect(
            dot_center_x - self.dot_width // 2,
            self.slider_y - (self.dot_height - self.slider_size_height) // 2,
            self.dot_width,
            self.dot_height
        )
        
        mouse_x,mouse_y=pg.mouse.get_pos()
        mouse_down=pg.mouse.get_pressed()[0]
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
        else:
            self.slider_touch = False       

        
   
        
    @override
    def draw(self, screen: pg.Surface,camera_rect=None):     
        
        if self.game_manager.player:
            '''
            [TODO ]
            Implement the camera algorithm logic here
            Right now it's hard coded, you need to follow the player's positions
            you may use the below example, but the function still incorrect, you may trace the entity.py
            
            camera = self.game_manager.player.camera
            '''
            camera = self.game_manager.player.camera
            self.camera_rect = pg.Rect(
                camera.x, camera.y,
                GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT
            )
            self.game_manager.current_map.draw(screen, camera)
            self.game_manager.player.draw(screen, camera)
        else:
            camera = PositionCamera(0, 0)
            self.game_manager.current_map.draw(screen, camera)

        for enemy in self.game_manager.current_enemy_trainers:
            enemy.draw(screen, camera)

        #畫出右上角的按鈕
        self.overlay_button.draw(screen)
        self.bag_button.draw(screen)



        if self.overlay_open:
            # 畫暗背景
            overlay=pg.Surface((GameSettings.SCREEN_WIDTH,GameSettings.SCREEN_HEIGHT),pg.SRCALPHA)
            overlay.fill((0,0,0,150))
            screen.blit(overlay,(0,0))

            # 中央 flat
            flat_w, flat_h = self.overlay_flat_size
            flat_x = (GameSettings.SCREEN_WIDTH  - flat_w) // 2
            flat_y = (GameSettings.SCREEN_HEIGHT - flat_h) // 2           
            
            #更新sprite位置
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
            text_setting=self.word.render(f"Setting",True,(0,0,0))
            screen.blit(
                text_setting,
                (flat_x+40,flat_y+40)
            )
            text_volume = self.word.render(f"Volume : {self.slider_value}%",True,(0,0,0))
            screen.blit(
                text_volume,
                (self.slider_x,self.slider_y-50)
            )            
            text_esc=self.word.render(f"Tap ESC can back",True,(0,0,0))
            screen.blit(
                text_esc,
                (flat_x+20,flat_y+550)
            )            
            self.save_button.draw(screen)
            text_save = self.word.render("Save",True,(0,0,0))
            screen.blit(
            text_save,
            (self.save_button_x+self.save_button_w_h-50,self.save_button_y-40)
            )
        
            
            self.load_button.draw(screen)
            self.load_button.draw(screen)
            text_save = self.word.render("Load",True,(0,0,0))
            screen.blit(
            text_save,
            (self.load_button_x+self.load_button_w_h-50,self.load_button_y-40)
            )
                        
                # 畫 Back 按鈕
            self.overlay_button_back.draw(screen)
        
        if self.overlaybag_open:
            overlay=pg.Surface((GameSettings.SCREEN_WIDTH,GameSettings.SCREEN_HEIGHT),pg.SRCALPHA)
            overlay.fill((0,0,0,150))
            screen.blit(overlay,(0,0))            
            #flat bag
            flat_bag_w, flat_bag_h = self.overlay_flat_size
            flat_bag_x = (GameSettings.SCREEN_WIDTH  - flat_bag_w) // 2
            flat_bag_y = (GameSettings.SCREEN_HEIGHT - flat_bag_h) // 2 
            self.overlay_flat_bag_sprite.rect.topleft=(flat_bag_x,flat_bag_y)
            screen.blit(self.overlay_flat_bag_sprite.image, self.overlay_flat_bag_sprite.rect)      
            self.game_manager.bag.draw(screen)              
            self.overlay_button_back.draw(screen)                

        #bush
        if self.overlay_open or self.overlaybag_open:
            pass
        else:
            player = self.game_manager.player
            if self.in_bush_zone and player is not None:
                camera = player.camera

                #玩家在「世界座標」的矩形
                world_rect = player.animation.rect

                # 用 camera 轉成「螢幕座標」中的中心點
                center_world = Position(world_rect.centerx, world_rect.centery)
                center_screen = camera.transform_position_as_position(center_world)

                # 做一個「螢幕上的 rect」來放頭頂位置
                screen_rect = pg.Rect(0, 0, world_rect.width, world_rect.height)
                screen_rect.center = (center_screen.x, center_screen.y)

                # 畫草叢感嘆號
                self.bush_warning.draw(screen, camera)

                # 在玩家頭上畫文字 PRESS E TO CATCH POKEMON
                hint = self.small_word.render("PRESS E TO CATCH POKEMON", True, (255, 255, 255))
                hint_rect = hint.get_rect()
                hint_rect.midbottom = (screen_rect.centerx, screen_rect.top - 40)
                screen.blit(hint, hint_rect)
  
        
        if self.online_manager and self.game_manager.player:
            list_online = self.online_manager.get_list_players()
            for player in list_online:
                if player["map"] == self.game_manager.current_map.path_name:
                    cam = self.game_manager.player.camera
                    pos = cam.transform_position_as_position(Position(player["x"], player["y"]))
                    self.sprite_online.update_pos(pos)
                    self.sprite_online.draw(screen)
        
        #shop
        if self.shop.overlay_open: self.shop.draw(screen)


        #minimap
        player = self.game_manager.player
        if player:
            player_pos = player.animation.rect.center
        else:
            player_pos = (0, 0)

        self.minimap.draw(
            screen,
            player_pos=player_pos,
            camera_rect=getattr(self, "camera_rect", None)
        )
        self._draw_toasts(screen)