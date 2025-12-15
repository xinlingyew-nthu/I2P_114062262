import random, copy
import pygame as pg
from typing import override

from src.sprites import BackgroundSprite
from src.interface.components import Button
from src.scenes.scene import Scene
from src.utils import GameSettings, load_img
from src.core.services import scene_manager, sound_manager, input_manager
from src.data.monster_data import element_from_str, get_element_multiplier
from src.sprites.battleanimation import BattleAnimation
from src.utils.definition import Monster, Item
from src.data.monster_data import MONSTER_DATA
from src.sprites import Sprite

class BushScene(Scene):

    def __init__(self) -> None:
        super().__init__()
        self.background=BackgroundSprite("backgrounds/background1.png")
        self.command_buttons:dict[str,Button] = {}
        # self.font: pg.font.Font | None = None
        # self.word_font: pg.font.Font | None = None

        # 戰鬥相關
        self.state: str = "idle"
        self.player_mon: Monster | None = None
        self.wild_mon: Monster | None = None
        self.dmg: int = 20
        self.message_text: str | None = None
        self.last_damage_info = None

        # 圖片
        self.player_sprite: pg.Surface | None = None
        self.wild_sprite: pg.Surface | None = None

        #animation
        self.player_anim_idle: BattleAnimation | None = None
        self.player_anim_attack: BattleAnimation | None = None
        self.player_anim: BattleAnimation | None = None

        self.wild_anim_idle: BattleAnimation | None = None
        self.wild_anim_attack: BattleAnimation | None = None
        self.wild_anim: BattleAnimation | None = None

        self.player_icon_small: pg.Surface | None = None
        self.wild_icon_small: pg.Surface | None = None

        # HP Banner + 血條
        banner_image = load_img("UI/raw/UI_Flat_Banner03a.png")
        self.info_banner = pg.transform.scale(banner_image, (400, 100))
        self.hp_fill_img = load_img("UI/raw/UI_Flat_BarFill01a.png")

        #element icon
        self.element_icons: dict[str, pg.Surface] = {
            "grass": load_img("element/grass.png"),
            "fire": load_img("element/fire.png"),
            "water": load_img("element/water.png"),
            "ice": load_img("element/ice.png"),
        }

        #狀態
        self.btn_w=140
        self.btn_h=40
        self.gap=30
        self.intro_done = False
        self.y=650
        self.btn_x=350
        
        names=["Fight","Bag","Switch","Run","Catch"]
        for i ,name in enumerate(names):
            self.x=self.btn_x +i * (self.btn_w+self.gap)
        
            button=Button(
                "UI/raw/UI_Flat_Button01a_4.png",
                "UI/raw/UI_Flat_Button01a_1.png",
                self.x,self.y,self.btn_w,self.btn_h,
                lambda n =name :self.handle_command(n)
            )
            self.command_buttons[name]=button

        #banner       
        banner_image=load_img("UI/raw/UI_Flat_Banner03a.png")
        self.info_banner=pg.transform.scale(banner_image,(400,100))

        #back button
        btn_w, btn_h = 180, 60
        btn_x = GameSettings.SCREEN_WIDTH // 2 - btn_w // 2
        btn_y = GameSettings.SCREEN_HEIGHT // 2 + 40
        self.result_button = Button(
            "UI/button_play.png",
            "UI/button_play_hover.png",
            btn_x, btn_y, btn_w, btn_h,
            lambda: scene_manager.change_scene("game")
        )

        self.state = "intro"
        self.message :str | None=None
        self.message_timer:float=0.0

        self.victory_banner = Sprite("UI/raw/UI_Flat_Banner02a.png", (400, 110))
        self.loss_banner    = Sprite("UI/raw/UI_Flat_Banner01a.png", (400, 110))

        self.bag=None
        self.state_before_bag=None  # 記錄進 Bag 前的狀態（通常是 "command"）

        #bag
        flat_bag_w, flat_bag_h = 800, 600
        self.overlay_flat_bag_size = (flat_bag_w, flat_bag_h)
        self.overlay_flat_bag_sprite = Sprite(
            "UI/raw/UI_Flat_Frame01a.png",
            self.overlay_flat_bag_size
        )        
        flat_bag_x = (GameSettings.SCREEN_WIDTH  - flat_bag_w) // 2
        flat_bag_y = (GameSettings.SCREEN_HEIGHT - flat_bag_h) // 2
        self.bag_back_button = Button(
            "UI/button_back.png",
            "UI/button_back_hover.png",
            flat_bag_x + flat_bag_w - 80,   # 右下角一點
            flat_bag_y + flat_bag_h - 80,
            60, 60,
            lambda: self._close_bag()
        )
        #toast
        self.toasts: list[dict] = []
        self.toast_duration = 0.5

        #font
        self.title_font = pg.font.Font("assets/fonts/Minecraft.ttf", 30)
        self.word_font = pg.font.Font("assets/fonts/Minecraft.ttf", 24)

        #switch
        self.switch_buttons: list[dict] = []
        self.switch_scroll = 0
        self.switch_min_scroll = 0
        self.switch_max_scroll = 0

        # 目前選到哪一隻（只用來預覽，不會立即上場）
        self.switch_selected_mon: dict | None = None
        self.switch_preview_anim: BattleAnimation | None = None

        # 右下角「Switch」確認按鈕（位置先給 0,0，畫的時候再調整）
        self.switch_confirm_button = Button(
            "UI/button_play.png",
            "UI/button_play_hover.png",
            100, 0,            # 位置之後在 draw 裡調整
            60, 60,
            lambda: self._confirm_switch_selected_mon()
        )
        self.switch_close_button = Button(
            "UI/button_x.png",
            "UI/button_x_hover.png",
            0, 0,          # 位置之後在 draw 裡面再更新
            40, 40,
            lambda: self._close_switch_overlay()
        )

        #run
        self.run_confirm_open = False
        self.run_prev_state: str | None = None

        self.run_close_button = Button(
            "UI/button_x.png",
            "UI/button_x_hover.png",
            GameSettings.SCREEN_WIDTH // 2 + 160,
            GameSettings.SCREEN_HEIGHT // 2 - 120,
            40, 40,
            lambda: self._close_run_confirm()
        )

        self.run_ok_button = Button(
            "UI/raw/UI_Flat_Button01a_4.png",
            "UI/raw/UI_Flat_Button01a_1.png",
            GameSettings.SCREEN_WIDTH // 2 - 80,
            GameSettings.SCREEN_HEIGHT // 2 + 40,
            160, 50,
            lambda: scene_manager.change_scene("game")  # 確定逃跑
        )


    def _close_bag(self):
        self.state = self.state_before_bag or "command"
        self.state_before_bag = None

    def _open_run_confirm(self):
        if self.run_confirm_open:
            return
        self.run_prev_state = self.state
        self.run_confirm_open = True

    def _close_run_confirm(self):
        self.run_confirm_open = False
        if self.run_prev_state is not None:
            self.state = self.run_prev_state

    def enter(self):
        sound_manager.play_bgm("RBY 110 Battle! (Wild Pokemon).ogg")
    
    def exit(self):
        print("Exiting Battle Scene")

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
        gap = 8
        for idx, toast in enumerate(reversed(self.toasts)):
            surf = self.word_font.render(toast["text"], True, (255, 255, 255))
            padding = 6
            bg_rect = surf.get_rect()
            bg_rect.width += padding * 2
            bg_rect.height += padding * 2
            bg_rect.bottomright = (
                GameSettings.SCREEN_WIDTH - 20,
                base_y - idx * (bg_rect.height + gap),
            )
            pg.draw.rect(screen, (0, 0, 0), bg_rect)
            screen.blit(surf, (bg_rect.x + padding, bg_rect.y + padding))

    def setup(self, player_mon: dict, wild_mon: dict,bag):
        #每次進戰鬥都重置 run confirm 視窗
        self.run_confirm_open = False
        self.run_prev_state = None      

        # （順便把 state_before_bag / switch 也清乾淨，避免殘留）
        self.state_before_bag = None
        self.switch_selected_mon = None
        self.switch_preview_anim = None
        self.switch_buttons.clear()
        self.switch_scroll = 0  

        self.player_mon = player_mon
        self.wild_mon=wild_mon
        self.bag = bag
        if "max_hp" in self.wild_mon:
            self.wild_mon["hp"] = self.wild_mon["max_hp"]
        #bush mons  

        # wild_template = random.choice(MONSTER_DATA)
        # self.wild_mon = copy.deepcopy(wild_template)
        # self.wild_mon["hp"] = self.wild_mon["max_hp"]        

        base_player_img = load_img(self.player_mon["sprite_path"])
        base_wild_img = load_img(self.wild_mon["sprite_path"]) 

        self.player_sprite = pg.transform.flip(
            pg.transform.scale(base_player_img, (220, 220)),
            True,
            False,
        )
        self.wild_sprite = pg.transform.scale(base_wild_img, (220, 220))

        self.player_icon_small = pg.transform.scale(base_player_img, (40, 40))
        self.wild_icon_small = pg.transform.scale(base_wild_img, (40, 40))

        # 初始狀態：野生寶可夢出現
        self.state = "intro"
        self.message_text =(f"A wild {self.wild_mon['name']} appears! "
    "(Press SPACE)")
        #animation
        self.player_anim_idle = self._build_idle_anim(self.player_mon, is_player=True)
        self.player_anim_attack = self._build_attack_anim(self.player_mon, is_player=True)
        self.player_anim = self.player_anim_idle

        self.wild_anim_idle = self._build_idle_anim(self.wild_mon, is_player=False)
        self.wild_anim_attack = self._build_attack_anim(self.wild_mon, is_player=False)
        self.wild_anim = self.wild_anim_idle    

    def _build_idle_anim(self, mon: dict, is_player: bool) -> BattleAnimation | None:
        sheet_path = mon.get("battle_idle_path")
        if not sheet_path:
            return None

        frame_w, frame_h = 96, 96  # 如果你的 idle sheet 格數不一樣再改
        return BattleAnimation(
            sheet_path,
            frame_w,
            frame_h,
            frame_count=4,
            scale_to=(350, 350),
            flip_x=is_player,
            fps=6.0,
        )
    #evolve
    def _refresh_player_visuals(self):
        if self.player_mon is None:
            return

        # 重新載入圖片
        base_img = load_img(self.player_mon["sprite_path"])

        self.player_sprite = pg.transform.flip(
            pg.transform.scale(base_img, (220, 220)),
            True, False
        )
        self.player_icon_small = pg.transform.scale(base_img, (40, 40))

        # 重新建動畫
        self.player_anim_idle = self._build_idle_anim(self.player_mon, is_player=True)
        self.player_anim_attack = self._build_attack_anim(self.player_mon, is_player=True)
        self.player_anim = self.player_anim_idle

    def _build_attack_anim(self, mon: dict, is_player: bool) -> BattleAnimation | None:
        sheet_path = mon.get("battle_attack_path")
        if not sheet_path:
            return None

        frame_w, frame_h = 96, 96
        return BattleAnimation(
            sheet_path,
            frame_w,
            frame_h,
            frame_count=4,
            scale_to=(350,350),   # 想攻擊時放大一點可以改成 (250, 250)
            flip_x=is_player,
            fps=8.0,               # 攻擊快一點
        )
        

    def handle_command(self,name:str):
        if self.state != "command":
            return
        
        if name=="Fight":
            self._start_player_attack()
            
        if name=="Bag":
            if self.bag is not None:
                self.state_before_bag=self.state
                self.state="bag"

        if name=="Switch":
            self._open_switch_overlay()

        if name=="Run":
            scene_manager.change_scene("game")
        
        if name=="Catch":
            self._try_catch()


    def deal_damage(self, attacker, defender):
        atk = attacker.get("attack", 10)
        dfs = defender.get("defense", 5)
        base = max(1, atk - dfs // 2)

        # --- 元素倍率 ---
        atk_el = element_from_str(attacker.get("element", "grass"))
        def_el = element_from_str(defender.get("element", "grass"))
        elem_mul = get_element_multiplier(atk_el, def_el)

        # --- Strength buff ---
        str_mul = 1.0
        if attacker.get("buff_strength_pending", False):
            str_mul = 1.5          # 你想要的 +50%
            attacker["buff_strength_pending"] = False  # 用完一次就清掉

        # --- Defense buff ---
        def_mul = 1.0
        if defender.get("buff_defense_pending", False):
            def_mul = 0.5          # 你想要的 -50% 傷害
            defender["buff_defense_pending"] = False   # 用完一次就清掉

        # === 逐步計算 ===
        # 1) base -> element
        dmg_after_elem = max(1, int(base * elem_mul))
        elem_bonus = dmg_after_elem - base

        # 2) 加上 strength
        dmg_after_str = max(1, int(dmg_after_elem * str_mul))
        str_bonus = dmg_after_str - dmg_after_elem

        # 3) 加上 defense（通常是負的）
        dmg_after_def = max(1, int(dmg_after_str * def_mul))
        def_bonus = dmg_after_def - dmg_after_str   # 通常 <= 0

        final = max(1, dmg_after_def)
        defender["hp"] = max(0, defender["hp"] - final)

        # 存給 draw() 用來顯示
        self.last_damage_info = {
            "attacker": attacker.get("name", "???"),
            "defender": defender.get("name", "???"),
            "base": base,
            "elem_bonus": elem_bonus,
            "str_bonus": str_bonus,
            "def_bonus": def_bonus,
            "final": final,
            "elem_mul": elem_mul,
            "str_mul": str_mul,
            "def_mul": def_mul,
        }

        return final

    def _start_player_attack(self):
        if self.player_anim_attack is not None:
            self.player_anim = self.player_anim_attack
            self.player_anim.reset()
        self.deal_damage(self.player_mon, self.wild_mon)

        if self.wild_mon["hp"] <= 0:
            # 打到 0，也可以視為「超好抓」
            self.state = "catchable"
            self.message_text = (
                f"{self.player_mon['name']} attacks! "
                f"{self.wild_mon['name']} is very weak now... "
                "Press ENTER to throw a Pokéball or ESC to run."
            )
            return

        # 否则：显示伤害与敌人剩余 HP
        self.state = "player_attack"
        self.message_text = None


    def _start_enemy_attack(self) -> None:
        if self.wild_anim_attack is not None:
            self.wild_anim = self.wild_anim_attack
            self.wild_anim.reset()
        self.deal_damage(self.wild_mon, self.player_mon)
        if self.player_mon["hp"] <= 0:
            self._enter_fail()
            return
        # self.message_timer = 3.0
        self.state = "enemy_attack"   
        self.message_text = None

    def _enter_caught(self):
        self.state = "caught"
        self.message_text = None
        self.message_timer = 0.0
        sound_manager.play_bgm("RBY 108 Victory! (Trainer).ogg")

    def _enter_fail(self):
        self.state = "fail"
        self.message_text = None
        self.message_timer = 0.0

    def _try_catch(self) -> None:
        assert self.wild_mon is not None

        has_ball=False
        if self.bag is not None:
            for item in self.bag._items_data:
                if item["name"] == "Pokeball" and item["count"]>0:
                    has_ball=True
                    item["count"] -=1
        if not has_ball:
            self.message_text = "You don't have any Pokeball..."
            return

        

        # 血量越少，抓到機率越高
        ratio = self.wild_mon["hp"] / max(1, self.wild_mon["max_hp"])
        # 30% ~ 100% 之間：滿血大約 30%，殘血接近 100%
        catch_chance = 0.3 + (1.0 - ratio) * 0.7
        catch_chance = max(0.3, min(0.99, catch_chance))

        r = random.random()

        if r < catch_chance and self.bag is not None:
            # 成功捕捉：整包複製 wild_mon，保留動畫設定
            new_mon: Monster = copy.deepcopy(self.wild_mon)
        
            new_mon["hp"] = new_mon.get("max_hp", new_mon.get("hp", 1))

            self.bag.add_monster(new_mon)

            self.state = "caught"
            self.message_text = (
                f"You caught {self.wild_mon['name']}! "
                "It has been added into your bag. "
            )
        else:
            # 捕捉失敗 → 野怪等一下打你
            self.state = "catch_fail"
            self.message_text =f"{self.wild_mon['name']} broke free and attack you! (Press SPACE)"

    def _get_switch_monsters(self) -> list[dict]:
        if self.bag is None:
            return []
        mons = getattr(self.bag, "_monsters_data", [])
        result = []
        for m in mons:
            # 你如果不想顯示 HP=0 的可以改成：if m.get("hp", 0) > 0:
            result.append(m)
        return result

    def _open_switch_overlay(self) -> None:
        mons = self._get_switch_monsters()
        # 只有一隻就沒得換
        if len(mons) <= 1:
            self.add_toast("No other monsters to switch.")
            return

        self.state = "switch"
        self.switch_scroll = 0
        self.switch_selected_mon = None
        self.switch_preview_anim = None
        self._rebuild_switch_buttons()

    def _close_switch_overlay(self) -> None:
        self.state = "command"
        self.switch_selected_mon = None
        self.switch_preview_anim = None
        self.switch_buttons.clear()

    def _rebuild_switch_buttons(self) -> None:
        self.switch_buttons.clear()

        mons = self._get_switch_monsters()
        if not mons:
            self.switch_min_scroll = 0
            self.switch_max_scroll = 0
            return

        flat_w, flat_h = self.overlay_flat_bag_size
        flat_x = (GameSettings.SCREEN_WIDTH  - flat_w) // 2
        flat_y = (GameSettings.SCREEN_HEIGHT - flat_h) // 2

        list_x = flat_x + 40
        list_y_top = flat_y + 40
        btn_w = 250
        btn_h = 80
        gap = 10

        total_height = len(mons) * (btn_h + gap)
        visible_height = flat_h - 80
        self.switch_min_scroll = 0
        self.switch_max_scroll = max(0, total_height - visible_height)

        for i, mon in enumerate(mons):
            y = list_y_top + i * (btn_h + gap) - self.switch_scroll

            btn = Button(
                "UI/raw/UI_Flat_Button01a_4.png",
                "UI/raw/UI_Flat_Button01a_1.png",
                list_x, y, btn_w, btn_h,
                lambda idx=i: self._on_click_switch_monster(idx)
            )
            self.switch_buttons.append({
                "button": btn,
                "monster": mon,
            })

    def _on_click_switch_monster(self, idx: int) -> None:
        mons = self._get_switch_monsters()
        if not (0 <= idx < len(mons)):
            return
        mon = mons[idx]

        self.switch_selected_mon = mon
        self.switch_preview_anim = self._build_idle_anim(mon, is_player=True)
        if self.switch_preview_anim is not None:
            self.switch_preview_anim.reset()

    def _confirm_switch_selected_mon(self) -> None:
        if self.switch_selected_mon is None:
            self.add_toast("Select a monster first!")
            return

        mon = self.switch_selected_mon

        # 不要換成自己
        if mon is self.player_mon:
            self.add_toast("This monster is already in battle.")
            return

        # 不要換上已經倒下的怪
        if mon.get("hp", 0) <= 0:
            self.add_toast("You can't switch to a fainted monster.")
            return

        # --- 真的把這隻當作上場怪 ---
        self.player_mon = mon

        base_player_img = load_img(mon["sprite_path"])
        self.player_sprite = pg.transform.flip(
            pg.transform.scale(base_player_img, (220, 220)),
            True, False
        )
        self.player_icon_small = pg.transform.scale(base_player_img, (40, 40))

        self.player_anim_idle = self._build_idle_anim(self.player_mon, is_player=True)
        self.player_anim_attack = self._build_attack_anim(self.player_mon, is_player=True)
        self.player_anim = self.player_anim_idle

        # 關掉 switch overlay，回到 command 狀態
        self.state = "command"
        self.message_text = f"Go! {mon['name']}!"
        
    def _fit_to_box(self, surf: pg.Surface, max_w: int, max_h: int) -> pg.Surface:
        w, h = surf.get_size()
        if w == 0 or h == 0:
            return surf
        scale = min(max_w / w, max_h / h, 1.0)  # ✅ 只縮小不放大，避免超出框
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        return pg.transform.smoothscale(surf, (new_w, new_h))

    @override
    def update(self, dt: float) -> None:
        # ESC 隨時可以離開
        if self.run_confirm_open:
            self.run_close_button.update(dt)
            self.run_ok_button.update(dt)

            if input_manager.key_pressed(pg.K_ESCAPE):
                self._close_run_confirm()
            return

        # 動畫更新
        if self.player_anim is not None:
            self.player_anim.update(dt)
        if self.wild_anim is not None:
            self.wild_anim.update(dt)

        self._update_toasts(dt)

        if self.player_mon is None or self.wild_mon is None:
            return
        

        #抓成功或失敗的界面
        if self.state in ("caught", "fail"):
            self.result_button.update(dt)
            return

        # 狀態機
        if self.state == "intro":
            if input_manager.key_pressed(pg.K_SPACE):
                # 一開始讓野怪先攻擊
                self._start_enemy_attack()
                return
        #swutch
        if self.state == "switch":
            # 滾輪捲動
            if input_manager.mouse_wheel != 0:
                self.switch_scroll -= input_manager.mouse_wheel * 30
                if self.switch_scroll < self.switch_min_scroll:
                    self.switch_scroll = self.switch_min_scroll
                if self.switch_scroll > self.switch_max_scroll:
                    self.switch_scroll = self.switch_max_scroll
                self._rebuild_switch_buttons()

            # 更新每個按鈕（包含 hover / click）
            for info in self.switch_buttons:
                info["button"].update(dt)

            # 右側預覽動畫
            if self.switch_preview_anim is not None:
                self.switch_preview_anim.update(dt)

            # 右下角 Switch 確認按鈕
            self.switch_confirm_button.update(dt)
            # 右上角 X 關閉按鈕
            self.switch_close_button.update(dt)

            # 按 ESC 關閉 overlay（回到 command）
            if input_manager.key_pressed(pg.K_ESCAPE):
                self._close_switch_overlay()

            return
        #bag
        if self.state == "bag":
            if self.bag is not None:
                # 把滑鼠滾輪事件交給 Bag
                self.bag.update(dt)

            # 更新返回按鈕（檢查滑鼠 hover / click）
                if input_manager.mouse_pressed(1):        # <-- 這行名字請照你的實作調整
                    mouse_pos = input_manager.mouse_pos     # <-- 同上
                    result = self.bag.handle_click(mouse_pos)
                    if result is not None:
                        # 有用到道具 / 或失敗訊息，用 toast 顯示
                        self.add_toast(result.get("message", ""))
                        if result.get("used"):
                            self._refresh_player_visuals()

            # 更新返回按鈕（檢查滑鼠 hover / click）
            self.bag_back_button.update(dt)
            return

        if self.state == "command":
            # 更新按钮 hover / click
            for btn in self.command_buttons.values():
                btn.update(dt)    
                      
            if input_manager.key_pressed(pg.K_f):
                self._start_player_attack()
                return

            # ENTER：丟球抓
            if input_manager.key_pressed(pg.K_RETURN):
                self._try_catch()
                return

            # esc：逃跑
            if input_manager.key_pressed(pg.K_ESCAPE):
                self._open_run_confirm()
                return

        
        if self.state in ("player_attack", "enemy_attack"):
            if input_manager.key_pressed(pg.K_SPACE):
                    # 倒數結束，決定下一步
                    if self.state == "player_attack":
                        if self.player_anim_idle is not None:
                            self.player_anim = self.player_anim_idle
                            self.player_anim.reset()
                        # 玩家攻擊文字結束 → 敵人攻擊
                        self._start_enemy_attack()
                    elif self.state == "enemy_attack":
                        if self.wild_anim_idle is not None:
                            self.wild_anim = self.wild_anim_idle
                            self.wild_anim.reset()
                        # 敵人攻擊文字結束 → 回到玩家行動
                        self.state = "command"
                        self.message_text = (               "Press F to Fight, ENTER to Catch, ESC to Run."
                        )
            return   
        


        elif self.state == "catch_fail":
            # 捕捉失敗 → 按 SPACE 觸發敵人攻擊
            if input_manager.key_pressed(pg.K_SPACE):
                self._start_enemy_attack()
            return

        elif self.state in ("fail", "caught"):
            if input_manager.key_pressed(pg.K_RETURN):
                scene_manager.change_scene("game")
            return

        elif self.state == "catchable":
            # 野生寶可夢血量極低，只能選抓或逃跑
            if input_manager.key_pressed(pg.K_RETURN):
                self._try_catch()
                return
            if input_manager.key_pressed(pg.K_ESCAPE):
                scene_manager.change_scene("game")
                return


    def draw_hp_box(self, screen: pg.Surface, mon: Monster,
                    x: int, y: int,
                    small_icon: pg.Surface) -> None:
        # Banner
        banner_rect = self.info_banner.get_rect(topleft=(x-40, y))
        screen.blit(self.info_banner, banner_rect)

        # 2. Monster Icon 
        icon_size = 60
        # 如果是放在右邊的敵人，我們可以考慮把 icon 放在右側，但為了模仿 Bag，我們先統一放左側
        icon_x = banner_rect.left +30
        icon_y = banner_rect.top + (banner_rect.height - icon_size) // 2 - 10
        
        # 縮放小圖示 
        scaled_icon = pg.transform.scale(small_icon, (icon_size, icon_size))
        screen.blit(scaled_icon, (icon_x, icon_y))

        # Name
        text_x = icon_x + icon_size + 16
        text_y = banner_rect.top + 20
        name_surf = self.word_font.render(mon["name"], True, (0, 0, 0))
        screen.blit(name_surf, (text_x, text_y))

        # 等級 Level (模仿 Bag 放在右側)
        level = self.word_font.render(f"Lv.{mon['level']}", True, (0, 0, 0))
        # 稍微靠左一點，避免超出 Banner
        screen.blit(level, (banner_rect.right - 80, text_y))

        # HP Bar (這是最精華的部分，直接用 Bag 的邏輯)
        bar_w = 220
        bar_h = 18
        bar_x = icon_x+72+24
        bar_y = banner_rect.bottom -45

        # 畫外框 (白底 + 黑框)
        pg.draw.rect(screen, (255, 255, 255), (bar_x, bar_y, bar_w, bar_h))
        pg.draw.rect(screen, (0, 0, 0), (bar_x, bar_y, bar_w, bar_h), 2)

        # 計算血量比例
        ratio = max(0.0, min(1.0, mon["hp"] / max(1, mon["max_hp"])))
        inner_w = int((bar_w - 4) * ratio)

        # 畫血條填滿
        if inner_w > 0:
            fill_scaled = pg.transform.scale(self.hp_fill_img, (inner_w, bar_h - 4))
            screen.blit(fill_scaled, (bar_x + 2, bar_y + 2))

        # HP 數值文字
        hp_text = self.word_font.render(f"{mon['hp']}/{mon['max_hp']}", True, (0, 0, 0))
        screen.blit(hp_text, (bar_x + 100, bar_y - 22))

        #elementicon
        el_key = str(mon.get("element", "grass")).lower()
        el_img = self.element_icons.get(el_key)
        if el_img is not None:
            el_size = 32
            el_surf = pg.transform.scale(el_img, (el_size, el_size))
            el_x = banner_rect.left + 90
            el_y = banner_rect.bottom - el_size - 20
            screen.blit(el_surf, (el_x, el_y))

    @override
    def draw(self, screen: pg.Surface) -> None:
        # 簡單背景：深綠色代表草叢
        self.background.draw(screen)
        
        # ground_y = 400
        # player_x = 180
        # player_y = ground_y - self.player_sprite.get_height()
        # screen.blit(self.player_sprite, (player_x,player_y))

        # enemy_x = GameSettings.SCREEN_WIDTH - 220 - self.wild_sprite.get_width()
        # enemy_y = ground_y - self.wild_sprite.get_height() - 30  
        # screen.blit(self.wild_sprite, (enemy_x,enemy_y)
        ground_y = 500

        if self.player_anim is not None:
            img_player = self.player_anim.get_image()
        else:
            img_player = self.player_sprite

        player_x = 180
        player_y = ground_y - img_player.get_height()
        screen.blit(img_player, (player_x, player_y))

        if self.wild_anim is not None:
            img_enemy = self.wild_anim.get_image()
        else:
            img_enemy = self.wild_sprite

        enemy_x = GameSettings.SCREEN_WIDTH - 220 - img_enemy.get_width()
        enemy_y = ground_y - img_enemy.get_height() - 30  
        screen.blit(img_enemy, (enemy_x, enemy_y))

        # info player
        self.draw_hp_box(
            screen,
            self.player_mon,
            x=40,
            y=GameSettings.SCREEN_HEIGHT - 260,   
            small_icon=self.player_icon_small
        )
        #info enemy
        self.draw_hp_box(
            screen,
            self.wild_mon,
            x=GameSettings.SCREEN_WIDTH - 380,
            y=40,
            small_icon=self.wild_icon_small
        )


        
        #對話框
        pg.draw.rect(screen,(0,0,0),(0,600,GameSettings.SCREEN_WIDTH,220))

        if self.state in ("player_attack", "enemy_attack") and self.last_damage_info:
            info = self.last_damage_info
            white = (255, 255, 255)

            base = info["base"]
            e_bonus = info["elem_bonus"]
            s_bonus = info["str_bonus"]
            d_bonus = info["def_bonus"]
            final = info["final"]

            # 顏色：正 = 紅，負 = 藍，0 = 灰
            def bonus_color(val: int) -> tuple[int, int, int]:
                if val > 0:
                    return (255, 80, 80)
                if val < 0:
                    return (80, 160, 255)
                return (200, 200, 200)

            x = 50
            y = 625

            # 前半句
            part1 = self.word_font.render(
                f"{info['attacker']} attacks! Damage: ", True, white
            )
            screen.blit(part1, (x, y))
            x += part1.get_width()

            # base
            p_base = self.word_font.render(str(base), True, white)
            screen.blit(p_base, (x, y))
            x += p_base.get_width()

            # element bonus
            p_plus1 = self.word_font.render(" + ", True, white)
            screen.blit(p_plus1, (x, y))
            x += p_plus1.get_width()

            p_elem = self.word_font.render(str(e_bonus), True, bonus_color(e_bonus))
            screen.blit(p_elem, (x, y))
            x += p_elem.get_width()

            # strength bonus
            p_plus2 = self.word_font.render(" + ", True, white)
            screen.blit(p_plus2, (x, y))
            x += p_plus2.get_width()

            p_str = self.word_font.render(str(s_bonus), True, bonus_color(s_bonus))
            screen.blit(p_str, (x, y))
            x += p_str.get_width()

            # defense bonus
            p_plus3 = self.word_font.render(" + ", True, white)
            screen.blit(p_plus3, (x, y))
            x += p_plus3.get_width()

            p_def = self.word_font.render(str(d_bonus), True, bonus_color(d_bonus))
            screen.blit(p_def, (x, y))
            x += p_def.get_width()

            # = final
            part2 = self.word_font.render(f" = {final}", True, white)
            screen.blit(part2, (x, y))
            x += part2.get_width()

            # 小提示
            p_hint = self.word_font.render("  [PRESS SPACE]", True, (200, 200, 200))
            screen.blit(p_hint, (x, y))

            return
        # if self.state == "catch_fail":
        #     text = self.word_font.render(
        #         f"A wild {self.wild_mon['name']} appears! "
        #         "(Press SPACE)",
        #         True, (255, 255, 255)
        #     )
        # 3. caught / fail 畫結果 Banner + 按鈕
        if self.state in ("caught", "fail"):
            overlay = pg.Surface(
                (GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT),
                pg.SRCALPHA
            )
            overlay.fill((0, 0, 0, 160))
            screen.blit(overlay, (0, 0))

            if self.state == "caught":
                banner_sprite = self.victory_banner
                text_str = "Caught!"
            else:
                banner_sprite = self.loss_banner
                text_str = "Fail"

            banner_rect = banner_sprite.image.get_rect()
            banner_rect.center = (
                GameSettings.SCREEN_WIDTH // 2,
                GameSettings.SCREEN_HEIGHT // 2 - 60
            )
            banner_sprite.rect = banner_rect
            screen.blit(banner_sprite.image, banner_sprite.rect)

            title = self.title_font.render(text_str, True, (0, 0, 0))
            text_x = banner_rect.centerx - title.get_width() // 2
            text_y = banner_rect.centery - title.get_height() // 2
            screen.blit(title, (text_x, text_y))

            self.result_button.draw(screen)
            btn_label = self.word_font.render("Return", True, (0, 0, 0))
            br = self.result_button.hitbox
            bl_x = br.x + br.width // 2 - btn_label.get_width() // 2
            bl_y = br.y + br.height // 2 - btn_label.get_height() // 2 - 50
            screen.blit(btn_label, (bl_x, bl_y))
            self._draw_toasts(screen)
            # 不 return，讓下面的 message_text 依然可以畫

        # 4. Bag 畫面：蓋掉其他東西，然後 return
        if self.state == "bag" and self.bag is not None:
            overlay = pg.Surface(
                (GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT),
                pg.SRCALPHA
            )
            overlay.fill((0, 0, 0, 150))
            screen.blit(overlay, (0, 0))

            flat_bag_w, flat_bag_h = self.overlay_flat_bag_size
            flat_bag_x = (GameSettings.SCREEN_WIDTH - flat_bag_w) // 2
            flat_bag_y = (GameSettings.SCREEN_HEIGHT - flat_bag_h) // 2
            self.overlay_flat_bag_sprite.rect.topleft = (flat_bag_x, flat_bag_y)
            screen.blit(self.overlay_flat_bag_sprite.image, self.overlay_flat_bag_sprite.rect)

            self.bag.draw(screen)
            self.bag_back_button.draw(screen)
            self._draw_toasts(screen)
            return
        #switch
        if self.state == "switch":
            # 半透明背景
            overlay = pg.Surface(
                (GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT),
                pg.SRCALPHA
            )
            overlay.fill((0, 0, 0, 150))
            screen.blit(overlay, (0, 0))

            # 中央外框（跟 Bag 共用）
            flat_w, flat_h = self.overlay_flat_bag_size
            flat_x = (GameSettings.SCREEN_WIDTH  - flat_w) // 2
            flat_y = (GameSettings.SCREEN_HEIGHT - flat_h) // 2
            self.overlay_flat_bag_sprite.rect.topleft = (flat_x, flat_y)
            screen.blit(self.overlay_flat_bag_sprite.image, self.overlay_flat_bag_sprite.rect)

            close_size = 40
            cx = flat_x + flat_w - close_size - 10   # 右邊往內縮 10px
            cy = flat_y + 10                          # 上面往下 10px

            br = self.switch_close_button.hitbox
            br.x = cx
            br.y = cy

            self.switch_close_button.draw(screen)

            # 左側：怪物列表
            self.switch_close_button.draw(screen)
            list_view_rect = pg.Rect(flat_x + 40, flat_y + 40, 250, flat_h - 80)

            prev_clip = screen.get_clip()
            screen.set_clip(list_view_rect)

            # 左側：怪物列表
            for info in self.switch_buttons:
                btn = info["button"]
                mon = info["monster"]
                btn.draw(screen)
                if not btn.hitbox.colliderect(list_view_rect):
                    continue

                btn.draw(screen)

                # 在按鈕上畫怪物圖與名字
                rect = btn.hitbox
                # 小圖示
                try:
                    icon_img = load_img(mon["sprite_path"])
                    icon_img = pg.transform.scale(icon_img, (56, 56))
                    screen.blit(icon_img, (rect.x + 8, rect.y + rect.height//2 - 28))
                except:
                    pass

                # 名字 & 等級
                name_surf = self.word_font.render(mon["name"], True, (0, 0, 0))
                screen.blit(name_surf, (rect.x + 80, rect.y + 12))

                lvl_surf = self.word_font.render(f"Lv.{mon['level']}", True, (0, 0, 0))
                screen.blit(lvl_surf, (rect.x + 80, rect.y + 36))
            screen.set_clip(prev_clip)


            # 右側：選中的怪物預覽 & 屬性
            if self.switch_selected_mon is not None:
                mon = self.switch_selected_mon

                el = str(mon.get("element", "grass")).lower()
                if el == "grass":
                    bg_color = (120, 200, 150)
                elif el == "water":
                    bg_color = (120, 170, 240)
                elif el == "fire":
                    bg_color = (240, 140, 120)
                elif el == "ice":
                    bg_color = (220, 240, 255)
                else:
                    bg_color = (200, 200, 200)

                preview_rect = pg.Rect(flat_x + 340, flat_y + 60, flat_w - 380, 260)
                pg.draw.rect(screen, bg_color, preview_rect, border_radius=16)

                if self.switch_preview_anim is not None:
                    img = self.switch_preview_anim.get_image()
                else:
                    img = load_img(mon["sprite_path"])
                    img = pg.transform.scale(img, (180, 180))

                img = self.switch_preview_anim.get_image() if self.switch_preview_anim else load_img(mon["sprite_path"])
                img = self._fit_to_box(img, preview_rect.width - 20, preview_rect.height - 20)

                img_rect = img.get_rect(center=preview_rect.center)
                screen.blit(img, img_rect.topleft)   

                # 下方屬性文字
                attr_y = preview_rect.bottom + 20
                line_gap = 30

                line1 = self.word_font.render(
                    f"{mon['name']} Lv.{mon['level']}", True, (0, 0, 0)
                )
                screen.blit(line1, (preview_rect.x + 10, attr_y))

                line2 = self.word_font.render(
                    f"HP: {mon['hp']}/{mon['max_hp']}", True, (0, 0, 0)
                )
                screen.blit(line2, (preview_rect.x + 10, attr_y + line_gap))

                #血條
                bar_w = preview_rect.width - 20   # 比預覽框稍微窄一點
                bar_h = 18
                bar_x = preview_rect.x + 10
                bar_y = attr_y + line_gap - 90   # 稍微往上靠近 HP 文字

                # 外框
                pg.draw.rect(screen, (255, 255, 255), (bar_x, bar_y, bar_w, bar_h))
                pg.draw.rect(screen, (0, 0, 0), (bar_x, bar_y, bar_w, bar_h), 2)

                ratio = max(0.0, min(1.0, mon["hp"] / max(1, mon["max_hp"])))
                inner_w = int((bar_w - 4) * ratio)

                if inner_w > 0:
                    fill_scaled = pg.transform.scale(self.hp_fill_img, (inner_w, bar_h - 4))
                    screen.blit(fill_scaled, (bar_x + 2, bar_y + 2))

                atk = mon.get("attack", 0)
                dfs = mon.get("defense", 0)
                atk_buff = mon.get("buff_strength_pending", False)
                dfs_buff = mon.get("buff_defense_pending", False)

                enemy_def = self.wild_mon.get("defense", 0) if self.wild_mon else 0  # ✅ 取野怪 DEF

                atk_text = f"ATK: {atk}  vs DEF: {enemy_def}" + ("  (+)" if atk_buff else "")
                dfs_text = f"DEF: {dfs}" + ("  (+)" if dfs_buff else "")

                line3 = self.word_font.render(atk_text, True, (0, 0, 0))
                line4 = self.word_font.render(dfs_text, True, (0, 0, 0))
                screen.blit(line3, (preview_rect.x + 10, attr_y + 2*line_gap))
                screen.blit(line4, (preview_rect.x + 10, attr_y + 3*line_gap))

                # 右下角 Switch 按鈕位置
                btn_w, btn_h = 60, 60
                btn_x = flat_x + flat_w - btn_w -10
                btn_y = flat_y + flat_h - btn_h - 40

                br = self.switch_confirm_button.hitbox
                br.x = btn_x
                br.y = btn_y

                self.switch_confirm_button.draw(screen)

                tip = self.word_font.render(
                    "Click a monster, then press Switch. ESC to cancel.",
                    True, (0, 0, 0)
                )
                screen.blit(tip, (flat_x + 40, flat_y + flat_h - 50))

                self._draw_toasts(screen)
                return

            # 如果還沒選怪
            tip = self.word_font.render(
                "Click a monster to switch. ESC to cancel.",
                True, (0, 0, 0)
            )
            screen.blit(tip, (flat_x + 40, flat_y + flat_h - 50))
            self._draw_toasts(screen)
            return
                
        # 5. command 狀態：畫按鈕 & 固定提示
        if self.state == "command":
            # 固定提示字串
            # hint = "PRESS F to Fight, ENTER to Catch, ESC to Run"
            # hint_surf = self.word_font.render(hint, True, (255, 255, 255))
            # screen.blit(hint_surf, (50, 625))

            for name, btn in self.command_buttons.items():
                btn.draw(screen)
                text = self.word_font.render(name, True, (0, 0, 0))
                rect = btn.hitbox
                text_x = rect.x + rect.width  // 2 - text.get_width()  // 2
                text_y = rect.y + rect.height // 2 - text.get_height() // 2
                screen.blit(text, (text_x, text_y))

        # 6. 最後統一畫 message_text（intro / 攻擊 / 抓失敗 / 抓成功 / 沒球 等等）
        if self.message_text:
            msg_surf = self.word_font.render(self.message_text, True, (255, 255, 255))
            # 如果在 command 狀態，你已經畫了一行 hint 上面那句，
            # 這裡可以稍微往上/往下移一點；先簡單放在 655
            screen.blit(msg_surf, (50, 625))
        self._draw_toasts(screen)

        #run
        if self.run_confirm_open:
            overlay = pg.Surface(
                (GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT),
                pg.SRCALPHA
            )
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))

            box_w, box_h = 420, 220
            box_x = GameSettings.SCREEN_WIDTH // 2 - box_w // 2
            box_y = GameSettings.SCREEN_HEIGHT // 2 - box_h // 2

            pg.draw.rect(screen, (245, 245, 245), (box_x, box_y, box_w, box_h))
            pg.draw.rect(screen, (0, 0, 0), (box_x, box_y, box_w, box_h), 3)

            title = self.title_font.render("Run from battle?", True, (0, 0, 0))
            screen.blit(title, (box_x + 20, box_y + 20))

            msg = self.word_font.render("Press button below to confirm.", True, (0, 0, 0))
            screen.blit(msg, (box_x + 20, box_y + 70))

            #run
            self.run_close_button.draw(screen)
            self.run_ok_button.draw(screen)

            ok_text = self.word_font.render("Run", True, (0, 0, 0))
            ok_rect = self.run_ok_button.hitbox
            screen.blit(
                ok_text,
                (ok_rect.centerx - ok_text.get_width() // 2,
                ok_rect.centery - ok_text.get_height() // 2)
            )



        
        # 底下訊息框（只用字）
        # if self.font is not None and self.message_text:
        #     text_surf = self.font.render(self.message_text, True, (255, 255, 255))
        #     text_rect = text_surf.get_rect(
        #         center=(GameSettings.SCREEN_WIDTH // 2, GameSettings.SCREEN_HEIGHT - 80)
        #     )
        #     screen.blit(text_surf, text_rect)