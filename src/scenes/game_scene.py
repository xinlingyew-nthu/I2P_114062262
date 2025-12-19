import pygame as pg
import threading
import time
import random
import copy

from src.scenes.scene import Scene
from src.data.shop import Shop
from src.core import GameManager, OnlineManager
from src.sprites import Animation
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
from src.scenes.dialog_scene import DialogScene
from collections import deque
from src.interface.components.chat_overlay import ChatOverlay


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
        if not hasattr(self.game_manager, "quests") or self.game_manager.quests is None:
            self.game_manager.quests = {}
        self.game_manager.quests.setdefault("beach_missing_mon", {"accepted": False, "caught": False})

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
            self.online_sprites: dict[int, Sprite] = {}
            self.online_anims: dict[int, Animation] = {}
            self.online_last_pos: dict[int, tuple[float,float]] = {}
            self.online_move_timer: dict[int, float] = {}
            self.online_facing: dict[int, str] = {} 
            self.sprite_online = Sprite("character/ow1.png", (48, 48))
            self._chat_bubbles: dict[int, tuple[str, float]] = {}
            self._bubble_lifetime = 3.0
            self._bubble_font = pg.font.Font("assets/fonts/Minecraft.ttf", 16)
            self._last_chat_id_seen = 0

            # wrapper：发送成功就立刻显示本地 bubble
            def _send_chat_and_bubble(txt: str) -> bool:
                if not self.online_manager:
                    return False
                ok = False
                try:
                    ok = self.online_manager.send_chat(txt)
                except Exception:
                    ok = False

                if ok:
                    now = time.monotonic()
                    local_pid = int(self.online_manager.player_id)
                    self._chat_bubbles[local_pid] = (txt, now + self._bubble_lifetime)

                return ok

            self._chat_overlay = ChatOverlay(
                send_callback=_send_chat_and_bubble,
                get_messages=self.online_manager.get_recent_chat
            )

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
        self.nav_map_route:list[str] =["map.tmx","beach.tmx","gym.tmx"]
        # nav button (在 bag 按鈕左邊)
        button_nav_x = GameSettings.SCREEN_WIDTH - 220   # 比 -150 再往左 70（可自己調）
        button_nav_y = 20
        button_nav_w = 60
        button_nav_h = 60
    

        self.nav_button = Button(
            "UI/raw/UI_Flat_Button02a_3.png",
            "UI/raw/UI_Flat_Button02a_1.png",
            button_nav_x, button_nav_y, button_nav_w, button_nav_h,
            lambda: self._open_nav()
        )
        self.nav_icon = load_img("UI/map.png")
        self.nav_open = False
        self.nav_frame = Sprite("UI/raw/UI_Flat_Frame02a.png", (520, 420))


        self.nav_places = [
            {"key":"home",  "label":"Home", "map":"home.tmx",  "tx": 9,  "ty": 17},
            {"key":"gym",   "label":"Gym",  "map":"gym.tmx",   "tx": 12, "ty": 12},
            {"key":"story1","label":"Story","map":"beach.tmx", "tx": 15, "ty": 10},
            {"key":"story2","label":"Story 2","map":"beach.tmx","tx": 4, "ty": 3},
        ]

        self.nav_cancel_button = Button(
            "UI/button_back.png",
            "UI/button_back_hover.png",  
            0, 0, 40, 40,
            lambda: self._cancel_nav()
        )
        self.nav_place_buttons: list[Button] = []
        self.nav_close_button = Button(
            "UI/button_x.png", "UI/button_x_hover.png",
            0, 0, 40, 40,
            lambda: self._close_nav()
        )
        self.nav_path: list[tuple[int,int]] = []
        self.nav_goal: dict | None = None          # 你点的目的地 place
        self.nav_route_maps: list[str] = []        # map bfs 得到的跨图路线
        self._nav_last_map: str | None = None      # 用来侦测换地图
        self._nav_last_player_tile: tuple[int,int] | None = None

        #dialog
        self.dialog_open = False
        self.dialog_lines = []
        self.dialog_idx = 0
        self.dialog_on_finish = None

    def checkbox_check(self):
        new_muted = not self.is_muted
        if new_muted == self.is_muted:
            return  # ✅ 没变化就别动音频

        self.is_muted = new_muted
        GameSettings.MUTE_BGM = self.is_muted

        if self.is_muted:
            sound_manager.pause_all()
        else:
            sound_manager.resume_all()
            sound_manager.set_bgm_volume(self.slider_value / 100)
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
    #overlay 优先级
    def _active_modal(self) -> str | None:
        # 越上层优先级越前面
        if self._chat_overlay and self._chat_overlay.is_open:
            return "chat"
        if self.dialog_open:
            return "dialog"
        if self.shop.overlay_open:
            return "shop"
        if self.nav_open:
            return "nav"
        if self.overlaybag_open:
            return "bag"
        if self.overlay_open:
            return "setting"
        return None

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

    def _get_tp_tile(self, tp) -> tuple[int,int] | None:
        t = GameSettings.TILE_SIZE

        # 1) tp.rect (世界座標)
        wx = wy = None

        r = getattr(tp, "rect", None)
        if r is not None:
            wx, wy = r.centerx, r.centery
        elif hasattr(tp, "x") and hasattr(tp, "y"):
            wx, wy = tp.x, tp.y
        else:
            pos = getattr(tp, "pos", None) 
            if isinstance(pos, Position):
                wx, wy = pos.x, pos.y

        if wx is None or wy is None:
            return None

        # ✅ 如果看起來是像素（很大），轉成 tile
        # 常見 map 大小 < 200 tiles，所以 px 通常會 > 200
        if wx > 200 or wy > 200:
            return int(wx // t), int(wy // t)

        # 否則當作已經是 tile
        return int(wx), int(wy)

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
        level = random.randint(1, 50)

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

        #navigate
    def _open_nav(self):
        self.nav_open = True
        self._build_nav_buttons()

    def _close_nav(self):
        self.nav_open = False

    def _cancel_nav(self):
        self.nav_goal = None
        self.nav_route_maps = []
        self.nav_path = []
        self._nav_last_map = None
        self._nav_last_player_tile = None
        self.nav_open = False   # 顺便关掉nav面板（你也可以不关）
        self.add_toast("Nav cancelled")

    def _open_dialog(self, lines, on_finish=None):
        self.dialog_open = True
        self.dialog_lines = lines
        self.dialog_idx = 0
        self.dialog_on_finish = on_finish

    def _advance_dialog(self):
        self.dialog_idx += 1
        if self.dialog_idx >= len(self.dialog_lines):
            self.dialog_open = False
            if self.dialog_on_finish:
                self.dialog_on_finish()
            self.dialog_on_finish = None

    def _recompute_nav_path(self):
        if self.nav_goal is None:
            self.nav_path = []
            return

        player = self.game_manager.player
        if player is None:
            self.nav_path = []
            return

        cur_map = self.game_manager.current_map
        cur_key = cur_map.path_name
        dest_map = self.nav_goal["map"]

        start = self._player_tile(player)

        # 决定“这张地图要走到哪里”
        if cur_key == dest_map:
            goal = (self.nav_goal["tx"], self.nav_goal["ty"])
        else:
            # 跨地图：走到下一跳地图的 teleporter
            if not self.nav_route_maps or cur_key not in self.nav_route_maps:
                self.nav_path = []
                return
            idx = self.nav_route_maps.index(cur_key)
            if idx >= len(self.nav_route_maps) - 1:
                self.nav_path = []
                return
            next_map = self.nav_route_maps[idx + 1]

            tp_goal = self._find_tp_to(cur_map, next_map)
            if tp_goal is None:
                self.nav_path = []
                return
            goal = tp_goal

        blocked = self._blocked_tiles(cur_map)
        w, h = cur_map.tmxdata.width, cur_map.tmxdata.height
        path = self._bfs(start, goal, blocked, w, h)

        self.nav_path = path

    def _find_tp_to(self, cur_map, dest_map: str):
        best_tile = None
        min_dist = float('inf')
        
        player_tile = self._tile_of_world(self.game_manager.player.position.x, self.game_manager.player.position.y)


        for tp in getattr(cur_map, "teleporters", []):
            if getattr(tp, "destination", None) == dest_map:
                tile = self._get_tp_tile(tp)
                if tile:
                    # 計算歐幾里得距離平方
                    dist = (tile[0] - player_tile[0])**2 + (tile[1] - player_tile[1])**2
                    if dist < min_dist:
                        min_dist = dist
                        best_tile = tile
        return best_tile

    def _map_bfs(self, start_map: str, goal_map: str) -> list[str]:
        # 你也可以把這些 map 名單集中管理
        all_maps = ["map.tmx", "home.tmx", "gym.tmx", "beach.tmx"]

        # 建 adjacency
        adj = {m: [] for m in all_maps}

        adj["gym.tmx"] = ["map.tmx"]
        adj["home.tmx"] = ["map.tmx"]
        adj["beach.tmx"] = ["map.tmx"]
        adj["map.tmx"] = ["gym.tmx", "home.tmx", "beach.tmx"]

        q = deque([start_map])
        prev = {start_map: None}
        while q:
            m = q.popleft()
            if m == goal_map:
                break
            for nb in adj.get(m, []):
                if nb in prev:
                    continue
                prev[nb] = m
                q.append(nb)

        if goal_map not in prev:
            return []

        route = []
        cur = goal_map
        while cur is not None:
            route.append(cur)
            cur = prev[cur]
        route.reverse()
        return route

    def _build_nav_buttons(self):
        self.nav_place_buttons.clear()

        fw, fh = self.nav_frame.image.get_size()
        fx = GameSettings.SCREEN_WIDTH // 2 - fw // 2
        fy = GameSettings.SCREEN_HEIGHT // 2 - fh // 2

        
        size = 90
        gap = 18
        start_x = fx + 40
        y = fy + 50

        for i, p in enumerate(self.nav_places):
            x = start_x + i * (size + gap)
            b = Button(
                "UI/raw/UI_Flat_Button02a_3.png",
                "UI/raw/UI_Flat_Button02a_1.png",
                x, y, size, size,
                lambda place=p: self._start_navigation(place)
            )
            self.nav_place_buttons.append(b)

    def _tile_of_world(self, x: float, y: float) -> tuple[int,int]:
        t = GameSettings.TILE_SIZE
        return int(x // t), int(y // t)

    def _player_tile(self, player) -> tuple[int,int]:
        r = player.animation.rect
        # 用脚底中心（站在地上那一点）
        wx = r.centerx
        wy = r.bottom - 2
        return self._tile_of_world(wx, wy)

    def _blocked_tiles(self, game_map) -> set[tuple[int,int]]:
        blocked = set()
        t = GameSettings.TILE_SIZE

        rects = getattr(game_map, "_collision_map", [])
        for r in rects:
            x0 = int(r.left // t)
            x1 = int((r.right - 1) // t)
            y0 = int(r.top // t)
            y1 = int((r.bottom - 1) // t)
            for tx in range(x0, x1 + 1):
                for ty in range(y0, y1 + 1):
                    blocked.add((tx, ty))

        # trainer 當障礙
        for e in self.game_manager.current_enemy_trainers:
            rr = e.animation.rect
            ex, ey = int(rr.centerx // t), int(rr.centery // t)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    blocked.add((ex + dx, ey + dy))
        return blocked

    def _bfs(self, start, goal, blocked, w, h):
        if goal is None: return []
        if start == goal: return [start]

        blocked = set(blocked)
        blocked.discard(goal) 

        q = deque([start])
        prev = {start: None}
        
        # 方向定義：前4個是軸向，後4個是斜向
        dirs = [(1,0),(-1,0),(0,1),(0,-1)]

        while q:
            x, y = q.popleft()
            for dx, dy in dirs:
                nx, ny = x + dx, y + dy
                
                if not (0 <= nx < w and 0 <= ny < h): continue
                if (nx, ny) in blocked: continue
                
                # # 如果是斜向移動，必須確保兩側的軸向格子也是空的
                # if dx != 0 and dy != 0:
                #     if (x + dx, y) in blocked or (x, y + dy) in blocked:
                #         continue

                if (nx, ny) not in prev:
                    prev[(nx, ny)] = (x, y)
                    if (nx, ny) == goal:
                        q.clear()
                        break
                    q.append((nx, ny))
        if goal not in prev:
            return []

        path = []
        cur = goal
        while cur is not None:
            path.append(cur)
            cur = prev[cur]
        path.reverse()
        return path

    def _start_navigation(self, place: dict):

        self.nav_goal = place

        cur_key = self.game_manager.current_map.path_name
        dest_map = place["map"]

        # 建跨图路线（同图就只是一张）
        if cur_key == dest_map:
            self.nav_route_maps = [cur_key]
        else:
            self.nav_route_maps = self._map_bfs(cur_key, dest_map)

        self._close_nav()
        self.add_toast(f"Route to {place['label']}")

        # 立刻算一次
        self._recompute_nav_path()

        # 记录当前 map / tile，避免下一帧重复算
        self._nav_last_map = cur_key
        if self.game_manager.player:
            self._nav_last_player_tile = self._player_tile(self.game_manager.player)

    def _build_pikachu(self) -> dict:
        return {
            "id": 999,
            "name": "Pikachu",
            "element": "electric",
            "level": 5,
            "max_hp": 200,
            "hp": 200,
            "attack": 30,
            "defense": 10,
            "sprite_path": "element/pikachu.png",

            "battle_idle_path": None,
            "battle_attack_path": None,

            "evolve_to": None,
        }
    def _remove_monster_by_id(self, mon_id: int) -> bool:
        bag = self.game_manager.bag
        before = len(bag._monsters_data)
        bag._monsters_data = [m for m in bag._monsters_data if m.get("id") != mon_id]
        return len(bag._monsters_data) != before
    
    def _near_npc(self, npc, dist_tiles: float = 1.5) -> bool:
        if self.game_manager.player is None:
            return False
        t = GameSettings.TILE_SIZE
        pr = self.game_manager.player.animation.rect
        nr = npc.animation.rect
        dx = (pr.centerx - nr.centerx) / t
        dy = (pr.centery - nr.centery) / t
        return dx*dx + dy*dy <= dist_tiles*dist_tiles
    
    def _ui_modal_open(self) -> bool:
        return (
            self.overlay_open
            or self.overlaybag_open
            or self.nav_open
            or self.shop.overlay_open
            or self.dialog_open
        )

    def _draw_hint_under_player(self, screen: pg.Surface, text: str, y_offset: int = 10) -> None:
        player = self.game_manager.player
        if player is None:
            return

        camera = player.camera

        # 玩家脚底中心（世界座标）
        r = player.animation.rect
        feet_world = Position(r.centerx, r.bottom - 2)

        # 转成屏幕座标
        feet_screen = camera.transform_position_as_position(feet_world)

        surf = self.small_word.render(text, True, (255, 255, 255))

        # 黑底让字更清楚
        pad = 6
        bg = pg.Surface((surf.get_width() + pad*2, surf.get_height() + pad*2), pg.SRCALPHA)
        bg.fill((0, 0, 0, 160))

        bg_rect = bg.get_rect(center=(feet_screen.x, feet_screen.y + y_offset))
        screen.blit(bg, bg_rect.topleft)
        screen.blit(surf, (bg_rect.x + pad, bg_rect.y + pad))

    def _online_world_pos(self, p: dict) -> tuple[float, float]:
        """把 online 回来的 x,y 转成世界像素座标(px)"""
        x = float(p["x"])
        y = float(p["y"])

        # 自动判断：如果数值很小(例如 < 200)，通常是 tile；否则是 pixel
        # 你的地图像素通常会 > 200
        if x < 200 and y < 200:
            x *= GameSettings.TILE_SIZE
            y *= GameSettings.TILE_SIZE
        return x, y

    def _dir_from_delta(self, dx: float, dy: float, last_facing: str) -> str:
        if abs(dx) < 1e-3 and abs(dy) < 1e-3:
            return last_facing

        # 模仿你 Player：先看 y，再看 x
        if dy < 0:
            return "up"
        elif dy > 0:
            return "down"
        elif dx < 0:
            return "left"
        else:
            return "right"
    def _draw_chat_bubble_for_pos(
        self,
        screen: pg.Surface,
        camera: PositionCamera,
        world_pos: Position,
        text: str,
        font: pg.font.Font
    ):
        # world -> screen
        p = camera.transform_position_as_position(world_pos)

        # above player's head
        x = int(p.x) +30
        y = int(p.y)   # 你可以调这个高度

        # 3) measure text & bubble size
        txt = font.render(text, True, (0, 0, 0))
        pad_x, pad_y = 10, 6
        bw = txt.get_width() + pad_x * 2
        bh = txt.get_height() + pad_y * 2

        rect = pg.Rect(0, 0, bw, bh)
        rect.midbottom = (x, y)

        # bubble box
        bg = pg.Surface((bw, bh), pg.SRCALPHA)
        pg.draw.rect(bg, (255, 255, 255, 230), bg.get_rect(), border_radius=10)
        pg.draw.rect(bg, (0, 0, 0, 255), bg.get_rect(), width=2, border_radius=10)
        screen.blit(bg, rect.topleft)

        # tail
        tip_x = rect.centerx
        tip_y = rect.bottom
        tri = [(tip_x - 8, tip_y), (tip_x + 8, tip_y), (tip_x, tip_y + 10)]
        pg.draw.polygon(screen, (255, 255, 255), tri)
        pg.draw.polygon(screen, (0, 0, 0), tri, width=2)

        # text
        screen.blit(txt, (rect.x + pad_x, rect.y + pad_y))

    #bubble 
    def _draw_chat_bubbles(self, screen: pg.Surface, camera: PositionCamera) -> None:
        if not self.online_manager:
            return

        # REMOVE EXPIRED BUBBLES
        now = time.monotonic()
        expired = [pid for pid, (_, ts) in self._chat_bubbles.items() if ts <= now]
        for pid in expired:
            self._chat_bubbles.pop(pid, None)

        if not self._chat_bubbles:
            return

        # DRAW LOCAL PLAYER'S BUBBLE
        local_pid = int(self.online_manager.player_id)
        if self.game_manager.player and local_pid in self._chat_bubbles:
            text, _ = self._chat_bubbles[local_pid]
            self._draw_chat_bubble_for_pos(
                screen,
                camera,
                self.game_manager.player.position,
                text,
                self._bubble_font
            )

        # DRAW OTHER PLAYERS' BUBBLES
        for pid, (text, _) in self._chat_bubbles.items():
            if pid == local_pid:
                continue

            # only visible players on this map
            p_list = self.online_manager.get_list_players()
            pinfo = next((p for p in p_list if int(p.get("id", -1)) == pid), None)
            if not pinfo or pinfo.get("map") != self.game_manager.current_map.path_name:
                continue

            pos_xy = self.online_last_pos.get(pid, None)
            if not pos_xy:
                continue
            px, py = pos_xy
            self._draw_chat_bubble_for_pos(
                screen,
                camera,
                Position(px, py),
                text,
                self._bubble_font
            )
            

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
        pass

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

        active = self._active_modal()

        # 1) dialog：只处理 dialog
        if self.dialog_open:
            if input_manager.key_pressed(pg.K_SPACE):
                self._advance_dialog()
            return

        # 2) shop：只处理 shop
        if self.shop.overlay_open:
            self.shop.update(dt)
            if input_manager.key_pressed(pg.K_ESCAPE):
                self.close_shop()   # 或 self.shop.close_overlay()
            return

        # 3) nav：只处理 nav
        if self.nav_open:
            self.nav_close_button.update(dt)
            self.nav_cancel_button.update(dt)
            for b in self.nav_place_buttons:
                b.update(dt)

            if input_manager.key_pressed(pg.K_ESCAPE):
                self._close_nav()
            return

        # 4) bag：只处理 bag
        if self.overlaybag_open:
            self.overlay_button_back.update(dt)
            self.game_manager.bag.update(dt)

            if input_manager.mouse_pressed(1):
                mouse_pos = input_manager.mouse_pos
                result = self.game_manager.bag.handle_click(mouse_pos)
                if result:
                    msg = result.get("message", "")
                    if msg:
                        self.add_toast(msg)

            if input_manager.key_pressed(pg.K_ESCAPE):
                self.close_overlay()
            return

        # 5) setting：只处理 setting
        if self.overlay_open:
            self.overlay_button_back.update(dt)
            self.checkbox_button.update(dt)
            self.save_button.update(dt)
            self.load_button.update(dt)

            if input_manager.key_pressed(pg.K_ESCAPE):
                self.close_overlay()
            return
        

        #chat
        if self._chat_overlay:
            # 只有在完全沒 UI modal 時才允許按 T 打開
            if input_manager.key_pressed(pg.K_t) and (not self._ui_modal_open()):
                if not self._chat_overlay.is_open:
                    self._chat_overlay.open()

            # 如果 chat 正在开着，ESC 只负责关 chat
            if self._chat_overlay.is_open and input_manager.key_pressed(pg.K_ESCAPE):
                # 如果 ChatOverlay 有 close() 用 close()
                if hasattr(self._chat_overlay, "close"):
                    self._chat_overlay.close()
                else:
                    self._chat_overlay.is_open = False
                return

            # 先更新 chat（让它吃键盘）
            self._chat_overlay.update(dt)

            # ✅ 只要 chat 開著：鎖住整個遊戲輸入
            if self._chat_overlay.is_open:
                return
        

        pressed_e = input_manager.key_pressed(pg.K_e)
        cur_map = self.game_manager.current_map.path_name
        player = self.game_manager.player

        #online
        if self.online_manager and self.game_manager.player:
            alive: set[int] = set()

            for p in self.online_manager.get_list_players():
                pid = int(p["id"])
                alive.add(pid)

                # 创建 anim
                if pid not in self.online_anims:
                    self.online_anims[pid] = Animation(
                        "character/ow1.png",
                        ["down", "left", "right", "up"], 4,
                        (GameSettings.TILE_SIZE, GameSettings.TILE_SIZE)
                    )
                    wx, wy = self._online_world_pos(p)
                    self.online_last_pos[pid] = (wx, wy)
                    self.online_facing[pid] = "down"

                # 不同地图：不更新动画（保留上次状态）
                if p.get("map") != self.game_manager.current_map.path_name:
                    continue

                # 统一成世界像素座标
                wx, wy = self._online_world_pos(p)

                lastx, lasty = self.online_last_pos.get(pid, (wx, wy))
                dx, dy = wx - lastx, wy - lasty

                # moving 判定：用“像素阈值”，不要用 0.001（太小）
                moved_now = (abs(dx) + abs(dy)) > 0.5
                if moved_now:
                    self.online_move_timer[pid] = 0.12  # 0.10~0.20 自己调
                else:
                    self.online_move_timer[pid] = max(0.0, self.online_move_timer.get(pid, 0.0) - dt)

                moving = self.online_move_timer.get(pid, 0.0) > 0.0

                # facing：模仿你 Player（y优先）
                facing = self._dir_from_delta(dx, dy, self.online_facing.get(pid, "down"))
                self.online_facing[pid] = facing

                anim = self.online_anims[pid]
                anim.switch(facing)
                anim.update_pos(Position(wx, wy))

                if moving:
                    anim.update(dt)
                else:
                    # 停在第一帧
                    anim.accumulator = 0.0
                    # 如果你 Animation 还有 frame_idx/current_frame 之类，也可以一起归零
                    # anim.frame_idx = 0

                self.online_last_pos[pid] = (wx, wy)
        
        # 修复：确保任务字典存在，防止 KeyError
        q = self.game_manager.quests.setdefault("beach_missing_mon", {"accepted": False, "caught": False})

        if player:
            player_rect = player.animation.rect
            t = GameSettings.TILE_SIZE
            # 定义故事剧情触发的草丛坐标 (4, 3)
            story_rect = pg.Rect(4 * t, 3 * t, t, t)

            # 1. 处理与 NPC 对话 (坐标 15, 9 附近)
            pt = self._player_tile(player)
            if cur_map == "beach.tmx" and abs(pt[0] - 15) <= 1 and abs(pt[1] - 9) <= 1:
                if pressed_e:
                    dialog_scene = scene_manager.get_scene("dialog")
                    if isinstance(dialog_scene, DialogScene):
                        if not q["accepted"]:
                            def accept(): q["accepted"] = True
                            dialog_scene.setup([
                                "Hey kid! Don't just stand there staring at the ocean!",
                                "I've lost my partner... He's yellow, fuzzy, and sparks with joy.",
                                "Last seen near the tree. Mind checking it out?",
                                "Try not to get electrocuted, alright?"], on_finish=accept)
                        elif not q["caught"]:
                            dialog_scene.setup(["He's still out there! I can hear the 'Pika' echoes!"])
                        else:
                            dialog_scene.setup(["You actually found him! You're a legend, kid!"])
                        scene_manager.change_scene("dialog")
                    return



        cur_key = self.game_manager.current_map.path_name
        if self.nav_goal is not None:
            # 地图切换：重算
            if self._nav_last_map != cur_key:
                self._nav_last_map = cur_key
                self._recompute_nav_path()

            # 玩家走到新 tile：重算
            if self.game_manager.player:
                t = self._player_tile(self.game_manager.player)
                if t != self._nav_last_player_tile:
                    self._nav_last_player_tile = t
                    self._recompute_nav_path()
                    
            if self.nav_goal is not None and self.game_manager.player:
                cur_key = self.game_manager.current_map.path_name
                dest_map = self.nav_goal["map"]

                if cur_key == dest_map:
                    player_tile = self._player_tile(self.game_manager.player)
                    goal_tile = (self.nav_goal["tx"], self.nav_goal["ty"])

                    if player_tile == goal_tile:
                        # 清掉导航
                        self.nav_goal = None
                        self.nav_route_maps = []
                        self.nav_path = []

                        self.add_toast("Arrived!")
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


        #只有完全没有 modal 打开时，才允许点右上角按钮
        if active is None:
            self.overlay_button.update(dt)
            self.bag_button.update(dt)
            self.nav_button.update(dt)
        if self.nav_button.on_click:
            pass

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
                    break

                    # if pressed_e:
                    #     bag = self.game_manager.bag
                    #     # 從背包選一隻還活著的當 player_mon
                    #     player_mon = None
                    #     for m in bag._monsters_data:
                    #         if m["hp"] > 0:
                    #             player_mon = m
                    #             break
                    #     if player_mon is None:
                    #         return  # 沒怪就不要進戰鬥
                    #     # if MONSTER_DATA:
                    #     #     proto = random.choice(MONSTER_DATA)
                    #     #     level = random.randint(0, 50)
                    #     #     wild_mon = build_monster(proto, level)                  
                    #     q = self.game_manager.quests.setdefault("beach_missing_mon", {"accepted": False, "caught": False})

                    #     cur_map = self.game_manager.current_map.path_name

        if self.in_bush_zone and pressed_e:
            bag = self.game_manager.bag
            player_mon = next((m for m in bag._monsters_data if m["hp"] > 0), None)
            if player_mon is None:
                return

            q = self.game_manager.quests.setdefault("beach_missing_mon", {"accepted": False, "caught": False})
            cur_map = self.game_manager.current_map.path_name

            t = GameSettings.TILE_SIZE
            story_rect = pg.Rect(4 * t, 3 * t, t, t)
            player_rect = self.game_manager.player.animation.rect

            #(1) 剧情草丛：beach (4,3) + 已接任务 + 未完成
            if cur_map == "beach.tmx" and q["accepted"] and (not q["caught"]) and player_rect.colliderect(story_rect):

                def _start_story_battle():
                    wild_mon = self._build_pikachu()

                    def _mark_beach_mon_caught():
                        q["caught"] = True
                        self.add_toast("Quest updated: Pikachu found!")

                    bush_scene = scene_manager.get_scene("bush")
                    if isinstance(bush_scene, BushScene):
                        bush_scene.setup(player_mon, wild_mon, bag, on_caught=_mark_beach_mon_caught)
                    scene_manager.change_scene("bush")

                dialog_scene = scene_manager.get_scene("dialog")
                if isinstance(dialog_scene, DialogScene):
                    dialog_scene.setup(
                        ["Pika... Pika", "Did you hear pikachu?", "Lets catch it!"],
                        on_finish=_start_story_battle
                    )
                    scene_manager.change_scene("dialog")
                return

            #(2) 普通草丛：随机遇敌（你原本的功能要补回来）
            proto = random.choice(MONSTER_DATA)
            level = random.randint(1, 50)
            wild_mon = build_monster(proto, level)

            bush_scene = scene_manager.get_scene("bush")
            if isinstance(bush_scene, BushScene):
                bush_scene.setup(player_mon, wild_mon, bag)
            scene_manager.change_scene("bush")
            return

            # bush_scene = scene_manager.get_scene("bush")
            # def _mark_beach_mon_caught():
            #     q["caught"] = True
            #     self.add_toast("Quest updated: Pikachu found!")

            # bush_scene = scene_manager.get_scene("bush")

            # if isinstance(bush_scene, BushScene):
            #     bush_scene.setup(player_mon, wild_mon, self.game_manager.bag, on_caught=_mark_beach_mon_caught)

            # scene_manager.change_scene("bush")

        # Update others
        
        if self.game_manager.player is not None and self.online_manager is not None:
            _ = self.online_manager.update(
                self.game_manager.player.position.x, 
                self.game_manager.player.position.y,
                self.game_manager.current_map.path_name
            )

        #buble chat
        if self.online_manager:
            try:
                msgs = self.online_manager.get_recent_chat(50)
                max_id = self._last_chat_id_seen
                now = time.monotonic()

                for m in msgs:
                    mid = int(m.get("id", 0))
                    if mid <= self._last_chat_id_seen:
                        continue

                    # TA hint uses "from"; your server might use "pid"
                    sender = int(m.get("from", m.get("pid", -1)))
                    text = str(m.get("text", ""))

                    if sender >= 0 and text:
                        self._chat_bubbles[sender] = (text, now + self._bubble_lifetime)

                    if mid > max_id:
                        max_id = mid

                self._last_chat_id_seen = max_id
            except Exception:
                pass
        # if self.online_manager:
        #     alive = set()
        #     for p in self.online_manager.get_list_players():
        #         pid = int(p["id"])
        #         alive.add(pid)
        #         if pid not in self.online_anims:
        #             self.online_anims[pid] = Animation(
        #                 "character/ow1.png",
        #                 ["down", "left", "right", "up"], 4,
        #                 (GameSettings.TILE_SIZE, GameSettings.TILE_SIZE))
        #esc
        # if input_manager.key_pressed(pg.K_ESCAPE):
        #     # dialog 你上面已經 return 了，所以這裡不管 dialog
        #     if self.nav_open:
        #         self._close_nav()
        #         return
        #     if self.shop.overlay_open:
        #         # 如果你的 shop 有 close function，用它
        #         self.shop.overlay_open = False
        #         return
        #     if self.overlaybag_open or self.overlay_open:
        #         self.close_overlay()
        #         return

        #     # ✅ 走到這裡代表沒有任何 modal
        #     self.open_overlay()
        # #shop
        # if self.shop.overlay_open:
        #     self.shop.update(dt)
        #     return
         
        # #bag
        # if input_manager.key_pressed(pg.K_b):
        #     if not self.overlay_open and not self.shop.overlay_open:
        #         self.open_bag_overlay()

        # if self.nav_open:
        #     self.nav_close_button.update(dt)
        #     self.nav_cancel_button.update(dt)
        #     for b in self.nav_place_buttons:
        #         b.update(dt)
        #     if input_manager.key_pressed(pg.K_ESCAPE):
        #         self._close_nav()
                    
        # if self.overlaybag_open:
        #     self.overlay_button_back.update(dt)
        #     self.game_manager.bag.update(dt)
        #     if input_manager.mouse_pressed(1):
        #         mouse_pos = input_manager.mouse_pos
        #         result = self.game_manager.bag.handle_click(mouse_pos)

        #         # 讓 Bag 回傳的訊息顯示在右下角 toast（跟 Bush 一樣）
        #         if result is not None:
        #             msg = result.get("message", "")
        #             if msg:
        #                 self.add_toast(msg)

            # 更新右上角的 Back 按鈕（ESC 其實也會走 overlay_button_back.on_click）
            # self.overlay_button_back.update(dt)

        #     #Bag 開著時，不要再更新後面地圖 / 設定 / shop 之類的
        #     return            
        # #setting
        # if self.overlay_open:
        #     self.overlay_button_back.update(dt)
        #     self.checkbox_button.update(dt)
        #     self.save_button.update(dt)
        #     self.load_button.update(dt)
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

        #nav 清楚路线
        if input_manager.key_pressed(pg.K_n):
            self.nav_goal = None
            self.nav_route_maps = []
            self.nav_path = []
            self.add_toast("Route cleared")

        
   
        
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
        #online manager
        if (not self._ui_modal_open()) and self.online_manager and self.game_manager.player:
            cam = self.game_manager.player.camera
            local_pid = int(self.online_manager.player_id)

            for p in self.online_manager.get_list_players():
                if p.get("map") != self.game_manager.current_map.path_name:
                    continue

                pid = int(p["id"])
                if pid == local_pid:
                    continue  

                anim = self.online_anims.get(pid)
                if anim:
                    anim.draw(screen, cam)
        #bubble chat
        if self.online_manager and self.game_manager.player:
            self._draw_chat_bubbles(screen, camera)       

        #畫出右上角的按鈕
        self.overlay_button.draw(screen)
        self.bag_button.draw(screen)

        self.nav_button.draw(screen)

        icon = pg.transform.scale(self.nav_icon, (36, 36))
        br = self.nav_button.hitbox
        screen.blit(icon, (br.x + 12, br.y + 12))


        if self.nav_open:
            overlay = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT), pg.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            screen.blit(overlay, (0, 0))

            fw, fh = self.nav_frame.image.get_size()
            fx = GameSettings.SCREEN_WIDTH // 2 - fw // 2
            fy = GameSettings.SCREEN_HEIGHT // 2 - fh // 2
            self.nav_frame.rect.topleft = (fx, fy)
            screen.blit(self.nav_frame.image, self.nav_frame.rect)

            # close X
            cr = self.nav_close_button.hitbox
            cr.x = fx + fw - 50
            cr.y = fy + 15
            self.nav_close_button.draw(screen)

            # cancel nav (back)
            br = self.nav_cancel_button.hitbox
            br.x = fx + fw - 95   # X 左边
            br.y = fy + 15
            self.nav_cancel_button.draw(screen)

            # 地點按鈕 + 地點文字
            for i, b in enumerate(self.nav_place_buttons):
                b.draw(screen)
                p = self.nav_places[i]
                rr = b.hitbox

                label = self.word.render(p["label"], True, (0,0,0))
                lx = rr.centerx - label.get_width() // 2
                ly = rr.bottom + 6
                screen.blit(label, (lx, ly))

            self._draw_toasts(screen)
            return
        
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
        #quest
        if not self._ui_modal_open() and self.game_manager.player:
            q = self.game_manager.quests.get("beach_missing_mon", None)
            cur_map = self.game_manager.current_map.path_name
            pt = self._player_tile(self.game_manager.player)

            hint_text = None

            # (A) 剧情草丛：beach (4,3) + 已接任务 + 未完成 → 最高优先
            if (
                cur_map == "beach.tmx"
                and q and q.get("accepted") and (not q.get("caught"))
                and abs(pt[0] - 4) <= 1 and abs(pt[1] - 3) <= 1
            ):
                hint_text = "PRESS E ENTER STORY"

            # (B) 任务 NPC：beach (15,9) 附近 → 次高优先
            elif cur_map == "beach.tmx" and abs(pt[0] - 15) <= 1 and abs(pt[1] - 9) <= 1:
                hint_text = "PRESS E TO TALK"

            # # (C) 一般草丛：你现在已经用 in_bush_zone 判断了 → 最低优先
            # elif self.in_bush_zone:
            #     hint_text = "PRESS E TO CATCH POKEMON"

            if hint_text:
                self._draw_hint_under_player(screen, hint_text, y_offset=18)
        
        # if self.online_manager and self.game_manager.player:
        #     cam = self.game_manager.player.camera
        #     for p in self.online_manager.get_list_players():
        #         if str(p.get("map", "")) != self.game_manager.current_map.path_name:
        #             continue

        #         pid = int(p.get("id", -1))
        #         if pid < 0:
        #             continue

        #         spr = self.online_sprites.get(pid)
        #         if spr is None:
        #             spr = Sprite("character/ow1.png", (48, 48))
        #             self.online_sprites[pid] = spr

        #         pos = cam.transform_position_as_position(Position(float(p["x"]), float(p["y"])))
        #         spr.update_pos(pos)
        #         spr.draw(screen)
        
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

        #quest
        q = self.game_manager.quests.get("beach_missing_mon", None)
        if q and q.get("accepted") and (not q.get("caught")):
            quest_surf = self.word.render("Quest: Finding Pokemon", True, (255, 255, 255))
            bg = pg.Surface((quest_surf.get_width()+20, quest_surf.get_height()+14), pg.SRCALPHA)
            bg.fill((0,0,0,160))
            screen.blit(bg, (20, GameSettings.SCREEN_HEIGHT - 60))
            screen.blit(quest_surf, (30, GameSettings.SCREEN_HEIGHT - 53))

        #draw arrow

        if self.nav_path and not self._ui_modal_open():
            camera = self.game_manager.player.camera

            pts = []
            for (tx, ty) in self.nav_path:
                wx = tx * GameSettings.TILE_SIZE + GameSettings.TILE_SIZE // 2
                wy = ty * GameSettings.TILE_SIZE + GameSettings.TILE_SIZE // 2
                p = camera.transform_position_as_position(Position(wx, wy))
                pts.append((int(p.x), int(p.y)))
        
            if len(pts) >= 2:
                dot_gap = 18   # 点与点之间的间距（像素），想更密就调小
                glow_r = 6     # 外光半径
                core_r = 3     # 内点半径

                last = pts[0]
                acc = 0.0

                for i in range(1, len(pts)):
                    x1, y1 = last
                    x2, y2 = pts[i]
                    dx, dy = x2 - x1, y2 - y1
                    seg_len = (dx*dx + dy*dy) ** 0.5
                    if seg_len == 0:
                        continue

                    ux, uy = dx / seg_len, dy / seg_len
                    dist = 0.0
                    while dist + acc <= seg_len:
                        d = dist + acc
                        px = x1 + ux * d
                        py = y1 + uy * d

                        # 外光（半透明）
                        glow = pg.Surface((glow_r*2+2, glow_r*2+2), pg.SRCALPHA)
                        pg.draw.circle(glow, (255, 255, 255, 90), (glow_r+1, glow_r+1), glow_r)
                        screen.blit(glow, (px - glow_r - 1, py - glow_r - 1))

                        # 内点（实心白）
                        pg.draw.circle(screen, (255, 255, 255), (int(px), int(py)), core_r)

                        dist += dot_gap

                    acc = (dist + acc) - seg_len
                    last = (x2, y2)
        #chat
        if self._chat_overlay:
            self._chat_overlay.draw(screen)    


          
            