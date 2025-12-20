import random
import copy
import pygame as pg

from src.utils import GameSettings, load_img
from src.interface.components.button import Button
from src.core.services import input_manager
from src.sprites import Sprite
from src.data.monster_data import MONSTER_DATA, build_monster


class Shop:
    def __init__(self, game_manager):
        self.game_manager=game_manager
        self.overlay_open = False

        #scroll
        self.scroll=0
        self.min_scroll=0
        self.max_scroll=0

        #buy or sell
        self.mode="buy"

        #overlay
        flat_shop_w,flat_shop_h=800,600
        self.overlay_flat_shop_size=(flat_shop_w,flat_shop_h)
        self.overlay_flat_shop_sprite=Sprite("UI/raw/UI_Flat_Frame02a.png",self.overlay_flat_shop_size)    

        self.overlay_flat_shop_sprite.rect.center = (
            GameSettings.SCREEN_WIDTH // 2,
            GameSettings.SCREEN_HEIGHT // 2
        )   

        #banner
        banner=load_img("UI/raw/UI_Flat_Banner03a.png")
        self.monster_banner = pg.transform.scale(banner, (600, 100))
        self.item_banner = pg.transform.scale(banner, (600, 70))

        #back
        flat_x, flat_y, flat_w, flat_h = self._flat_rect_values()
        back_w, back_h = 50, 50
        back_x = flat_x + 20
        back_y = flat_y + flat_h - back_h - 20
        self.overlay_button_back = Button(
            "UI/button_back.png",
            "UI/button_back_hover.png",
            back_x,
            back_y,
            back_w,
            back_h,
            lambda: self.close_overlay(),
        )
        #restock
        self.button_force_restock = Button(
            "ui/button_play.png",
            "ui/button_play_hover.png",
            flat_x + flat_w - 80,
            flat_y + flat_h - 80,
            48,
            48,
            self.force_restock
        )
        self.monster_stock = 3              # 目前剩幾隻可買
        self.monster_stock_max = 3          # 一次補滿幾隻
        self.monster_restock_cd = 60.0      # 秒
        self.monster_restock_timer = 0.0  

        self.monster_generated = False

        #buy / sell tab button
        tab_w, tab_h = 120, 40
        tab_y = flat_y + 20
        self.button_buy_tab = Button(
            "UI/raw/UI_Flat_Button01a_3.png",
            "UI/raw/UI_Flat_Button01a_1.png",
            flat_x + 40,
            tab_y,
            tab_w,
            tab_h,
            lambda: self._switch_mode("buy"),
        )
        self.button_sell_tab = Button(
            "UI/raw/UI_Flat_Button01a_3.png",
            "UI/raw/UI_Flat_Button01a_1.png",
            flat_x + 40 + tab_w + 20,
            tab_y,
            tab_w,
            tab_h,
            lambda: self._switch_mode("sell"),
        )        

        #buy info
        self.shop_monster :list[dict]=[]
        self.items_for_sale :list[dict] =[

            {"name": "Pokeball", "price": 5, "sprite_path": "ingame_ui/ball.png"},

            {"name": "Heal Potion", "price": 10, "sprite_path": "ingame_ui/potion.png",},

            {"name": "Strength Potion", "price": 15, "sprite_path": "ingame_ui/options1.png"},

            {"name": "Defense Potion", "price": 15
            , "sprite_path": "ingame_ui/options2.png"},
            {"name": "Evolve Stone", "price": 500, "sprite_path": "element/involve.png"},
            {"name": "Level Up", "price": 100, "sprite_path": "element/levelup.png"},
        ]

        self.buy_monster_buttons: list[Button] = []
        self.buy_item_buttons: list[Button] = []
        self.sell_monster_buttons: list[Button] = []        


        self.font_big = pg.font.Font("assets/fonts/Minecraft.ttf", 28)
        self.font = pg.font.Font("assets/fonts/Minecraft.ttf", 22)
        self.font_small = pg.font.Font("assets/fonts/Minecraft.ttf", 18)

        # 右下角彈窗
        self.toasts: list[dict] = []  # {"text": str, "time": float}
        self.toast_duration = 0.8

        #element icon
        self.element_icons: dict[str, pg.Surface] = {
            "grass": load_img("element/grass.png"),
            "fire": load_img("element/fire.png"),
            "water": load_img("element/water.png"),
            "ice": load_img("element/ice.png"),
        }

    def _flat_rect_values(self) -> tuple[int, int, int, int]:
        flat_w, flat_h = self.overlay_flat_shop_size
        flat_x = (GameSettings.SCREEN_WIDTH - flat_w) // 2
        flat_y = (GameSettings.SCREEN_HEIGHT - flat_h) // 2
        return flat_x, flat_y, flat_w, flat_h

    def close_overlay(self):
        self.overlay_open=False
    
    def open_overlay(self):
        self.overlay_open=True
        self.scroll = 0
        self.mode = "buy"

        # #  如果正在 restock，就不要刷新怪物
        # if self.monster_stock <= 0 and self.monster_restock_timer > 0:
        #     self._rebuild_all_buttons()
        #     self._update_scroll_range()
        #     return

        # #  正常情況才生成新怪物
        # self.shop_monster.clear()
        # if MONSTER_DATA:
        #     sample_count = min(self.monster_stock_max, len(MONSTER_DATA))
        #     for proto in random.sample(MONSTER_DATA, sample_count):
        #         lvl = random.randint(1, 5)
        #         mon = build_monster(proto, lvl)
        #         self.shop_monster.append(mon)

        if not self.monster_generated:
            self.shop_monster.clear()
            sample_count = min(self.monster_stock_max, len(MONSTER_DATA))
            for proto in random.sample(MONSTER_DATA, sample_count):
                lvl = random.randint(1, 5)
                mon = build_monster(proto, lvl)
                self.shop_monster.append(mon)

            self.monster_generated = True


        self._rebuild_all_buttons()
        self._update_scroll_range()

    def force_restock(self):
        self.monster_restock_timer = self.monster_restock_cd
        self._add_toast("Force restock started!")

    def update_timer(self, dt):
        if self.monster_restock_timer > 0:
            self.monster_restock_timer -= dt
            if self.monster_restock_timer <= 0:
                self.monster_restock_timer = 0.0
                self.monster_stock = self.monster_stock_max

                # 🔄 換新一組 monster
                self.shop_monster.clear()
                sample_count = min(self.monster_stock_max, len(MONSTER_DATA))
                for proto in random.sample(MONSTER_DATA, sample_count):
                    lvl = random.randint(1, 5)
                    mon = build_monster(proto, lvl)
                    self.shop_monster.append(mon)

                self._rebuild_all_buttons()
                self._update_scroll_range()

    def _switch_mode(self,mode):
        if mode not in ("buy","sell"):
            return
        self.mode=mode
        self._rebuild_all_buttons()
        self._update_scroll_range()

    def _update_toasts(self, dt: float) -> None:
        for t in self.toasts:
            t["time"] -= dt
        self.toasts = [t for t in self.toasts if t["time"] > 0]

    def _draw_toasts(self, screen: pg.Surface) -> None:
        if not self.toasts:
            return
        base_y=GameSettings.SCREEN_HEIGHT -20
        gap=8

        for idx, toast in enumerate(reversed(self.toasts)):
            surf = self.font_small.render(toast["text"], True, (255, 255, 255))
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

    def _add_toast(self, text: str) -> None:
        self.toasts.append({"text": text, "time": self.toast_duration})
    
    def _get_coin_item(self):
        bag=self.game_manager.bag
        for item in bag._items_data:
            if item["name"] == "Coins":
                return item
        return None

    def _get_coins(self):
        coin_item=self._get_coin_item()
        return coin_item["count"] if coin_item is not None else 0
    
    def _change_coins(self,d:int): # buy de num
        bag = self.game_manager.bag
        coin_item = self._get_coin_item()
        if coin_item is None:
            if d < 0:
                return
            coin_item = {"name": "Coins", "count": 0, "sprite_path": "ingame_ui/coin.png"}
            bag._items_data.append(coin_item)

        coin_item["count"] = max(0, coin_item["count"] + d)

    def _add_item_to_bag(self,name,sprite_path,amount):
        bag = self.game_manager.bag
        for item in bag._items_data:
            if item["name"] == name:
                item["count"] += amount
                return
        bag._items_data.append({"name": name, "count": amount,"sprite_path": sprite_path})
    
    def _get_monster_price(self,monster):
        return 2*monster.get("level",1) +100

    def _get_item_price(self, item_name: str) -> int:
        for it in self.items_for_sale:
            if it["name"] == item_name:
                return it["price"]
        return 0
      

    def _buy_monster(self, mon: dict):
        if self.monster_stock <= 0:
            # 顯示剩餘時間
            left = int(self.monster_restock_timer)
            return {"message": f"Sold out. Restock in {left}s"}

        price = self._get_monster_price(mon)
        coins = self._get_coins()

        if coins < price:
            self._add_toast("Not enough coins!")
            return

        # 扣錢 + 加進 Bag
        self._change_coins(-price)
        self.game_manager.bag.add_monster(mon)
        self.monster_stock -= 1

        # 從 shop 移除這隻
        self.shop_monster.remove(mon)

        # 5) 如果剛好賣光：開始 60 秒倒數
        if self.monster_restock_timer <= 0:
            self.monster_restock_timer = self.monster_restock_cd

        self.monster_generated = True

        # 重建按鈕 & 滾動範圍
        self._rebuild_all_buttons()
        self._update_scroll_range()


        self._add_toast(f"Bought {mon['name']} - {price} coins")

    def _buy_item(self, item_cfg: dict):
        name = item_cfg["name"]
        price = item_cfg["price"]
        sprite_path = item_cfg["sprite_path"]

        coins = self._get_coins()

        if coins < price:
            self._add_toast("Not enough coins!")
            return

        self._change_coins(-price)
        self._add_item_to_bag(name, sprite_path, 1)
        self._add_toast(f"Bought {name} - {price} coins")

        self._rebuild_all_buttons()
        self._update_scroll_range()

    def _sell_monster(self, mon_to_sell: dict, price: int):
        monsters = self.game_manager.bag._monsters_data
        if mon_to_sell not in monsters:
                self._add_toast("Error: Monster not found in Bag!")
                return

        monsters.remove(mon_to_sell)
        self._change_coins(price)
        self._rebuild_all_buttons()
        self._update_scroll_range()
        self._add_toast(f"Sold {mon_to_sell['name']} +{price} coins")

    def _rebuild_all_buttons(self) -> None:
        flat_x, flat_y, flat_w, flat_h = self._flat_rect_values()

        # 更新 back 按鈕位置
        back_w, back_h = 50, 50
        self.overlay_button_back.hitbox.topleft = (flat_x + 20, flat_y + flat_h - back_h - 20)

        # tab 按鈕位置
        tab_w, tab_h = 120, 40
        tab_y = flat_y + 20
        self.button_buy_tab.hitbox.topleft = (flat_x + 40, tab_y)
        self.button_sell_tab.hitbox.topleft = (flat_x + 40 + tab_w + 20, tab_y)

        # 先清掉舊按鈕
        self.buy_monster_buttons = []
        self.buy_item_buttons = []
        self.sell_monster_buttons = []


        if self.mode == "buy":
            #  買 Monster 
            monster_x = flat_x + 40
            monster_y = flat_y + 90
            banner_w, banner_h = self.monster_banner.get_size()
            btn_w, btn_h = 40, 40

            for idx, mon in enumerate(self.shop_monster):
                y = monster_y + idx * (banner_h + 10) + self.scroll
                btn_x = monster_x + banner_w - btn_w + 50
                btn_y = y + (banner_h - btn_h) // 2

                #  用 closure 把 mon 鎖住
                # def make_cb_buy(m=mon):
                #     def _cb():
                #         self._buy_monster(m)
                #     return _cb

                btn = Button(
                    "UI/button_shop.png",
                    "UI/button_shop_hover.png",
                    btn_x,
                    btn_y,
                    btn_w,
                    btn_h,
                    lambda m=mon: self._buy_monster(m),
                )
                self.buy_monster_buttons.append(btn)

            # 買 Items 
            items_x = flat_x + 40
            items_y = flat_y + 90 + len(self.shop_monster) * (banner_h + 20) + 10
            banner_w_i, banner_h_i = self.item_banner.get_size()
            btn_w_i, btn_h_i = 40, 40

            for idx, it in enumerate(self.items_for_sale):
                y = items_y + idx * (banner_h_i + 8) + self.scroll
                btn_x = items_x + banner_w_i - btn_w_i + 50
                btn_y = y + (banner_h_i - btn_h_i) // 2

                # ✅一樣用 closure 把 item_cfg 鎖住
                # def make_cb_item(item_cfg=it):
                #     def _cb():
                #         self._buy_item(item_cfg)
                #     return _cb

                btn = Button(
                    "UI/button_shop.png",
                    "UI/button_shop_hover.png",
                    btn_x,
                    btn_y,
                    btn_w_i,
                    btn_h_i,
                    lambda item_cfg=it: self._buy_item(item_cfg),
                )
                self.buy_item_buttons.append(btn)

        elif self.mode == "sell":
            monsters = self.game_manager.bag._monsters_data
            monster_x = flat_x + 40
            monster_y = flat_y + 90
            banner_w, banner_h = self.monster_banner.get_size()
            btn_w, btn_h = 40, 40

            for idx, mon in enumerate(monsters):
                y = monster_y + idx * (banner_h + 10) + self.scroll
                btn_x = monster_x + banner_w - btn_w + 50
                btn_y = y + (banner_h - btn_h) // 2
                price = self._get_monster_price(mon) // 2

                # def make_cb_sell(i=idx, p=price):
                #     def _cb():
                #         self._sell_monster(i, p)
                #     return _cb

                btn = Button(
                    "UI/button_shop.png",
                    "UI/button_shop_hover.png",
                    btn_x,
                    btn_y,
                    btn_w,
                    btn_h,
                    lambda m=mon, p=price: self._sell_monster(m, p),
                )
                self.sell_monster_buttons.append(btn)
    def _check_button_click(self, buttons: list[Button]) -> bool:
        if input_manager.mouse_pressed(1): # 假設 input_manager 追蹤了點擊事件
            mx, my = input_manager.mouse_pos
            for btn in buttons:
                if btn.hitbox.collidepoint(mx, my):
                    # 假設 Button 類有 on_click 屬性，且它就是您傳入的 lambda
                    btn.on_click() 
                    return True # 點擊發生，立即返回 True

        # 確保按鈕被更新，以便它們能回應滑鼠懸停效果 (hover)
        for btn in buttons:
            btn.update(0) # 只更新狀態，不重複執行點擊邏輯

        return False

    def _update_scroll_range(self):
        flat_x, flat_y, flat_w, flat_h = self._flat_rect_values()

        content_top = flat_y + 80
        content_bottom = flat_y + flat_h - 50
        visible_h = content_bottom - content_top -30

        if self.mode == "buy":
            # 怪物區
            banner_w, banner_h = self.monster_banner.get_size()
            monsters_h = len(self.shop_monster) * (banner_h + 10)

            # 道具區
            banner_w_i, banner_h_i = self.item_banner.get_size()
            items_h = len(self.items_for_sale) * (banner_h_i + 8)

            if self.shop_monster and self.items_for_sale:
                items_h += 20  # 中間空一點 gap

            content_h = monsters_h + items_h
        else:
            # sell: 只有 monster 列表
            banner_w, banner_h = self.monster_banner.get_size()
            monsters = self.game_manager.bag._monsters_data
            content_h = len(monsters) * (banner_h + 10)

        # 矮於可視高：不用滾
        if content_h <= visible_h:
            self.min_scroll = 0
            self.max_scroll = 0
            self.scroll = 0
        else:
            # 可往上（負值）捲
            self.max_scroll = 0
            self.min_scroll = visible_h - content_h  # 通常是負的

            if self.scroll > self.max_scroll:
                self.scroll = self.max_scroll
            if self.scroll < self.min_scroll:
                self.scroll = self.min_scroll


    def update(self,dt):
        if not self.overlay_open:
            return

        # Time
        now = pg.time.get_ticks()

        # 第一次進來先初始化，避免跳秒
        if not hasattr(self, "_last_tick"):
            self._last_tick = now

        dt_sec = (now - self._last_tick) / 1000.0
        self._last_tick = now

        # 避免切 scene / 卡頓時一次跳太多秒（可選）
        dt_sec = min(dt_sec, 0.25)

        #back
        if input_manager.key_pressed(pg.K_ESCAPE):
            self.close_overlay()
            return
        
            
        #scroll
        if input_manager.mouse_wheel != 0:
            self.scroll += input_manager.mouse_wheel * 30

            if self.scroll > self.max_scroll:
                self.scroll = self.max_scroll
            if self.scroll < self.min_scroll:
                self.scroll = self.min_scroll

            self._rebuild_all_buttons()       

        self.overlay_button_back.update(dt)
        self.button_buy_tab.update(dt)
        self.button_sell_tab.update(dt)  
        self.button_force_restock.update(dt)

        if input_manager.mouse_pressed(1):
            mx, my = input_manager.mouse_pos
            
            # 1. 優先檢查 Tab 按鈕
            if self.button_buy_tab.hitbox.collidepoint(mx, my):
                self.button_buy_tab.on_click()
                return # 立即退出
            if self.button_sell_tab.hitbox.collidepoint(mx, my):
                self.button_sell_tab.on_click()
                return # 立即退出

            # 2. 優先檢查 Back 按鈕
            if self.overlay_button_back.hitbox.collidepoint(mx, my):
                self.overlay_button_back.on_click()
                return # 立即退出

            # 3. 檢查內容按鈕 (必須在 Tab 和 Back 之後)
            if self.mode == "buy":
                # 優先檢查 Monster 按鈕
                for btn in self.buy_monster_buttons:
                    if btn.hitbox.collidepoint(mx, my):
                        btn.on_click()
                        return # 點擊了 Monster，立即退出

                # 接著檢查 Item 按鈕
                for btn in self.buy_item_buttons:
                    if btn.hitbox.collidepoint(mx, my):
                        btn.on_click()
                        return # 點擊了 Item，立即退出
                
            elif self.mode == "sell":
                for btn in self.sell_monster_buttons:
                    if btn.hitbox.collidepoint(mx, my):
                        btn.on_click()
                        return # 點擊了 Sell，立即退出
                
                # 4. 如果沒有點擊，讓按鈕執行其正常的 update (主要用於滑鼠懸停)
                if self.mode == "buy":
                    for btn in self.buy_monster_buttons:
                        btn.update(dt) # 只更新懸停狀態
                    for btn in self.buy_item_buttons:
                        btn.update(dt)
                elif self.mode == "sell":
                    for btn in self.sell_monster_buttons:
                        btn.update(dt)    

        if self.mode == "buy":
            for btn in self.buy_monster_buttons:
                btn.update(dt)
            for btn in self.buy_item_buttons:
                btn.update(dt)
        elif self.mode == "sell":
            for btn in self.sell_monster_buttons:
                btn.update(dt)      
        # dt_sec = dt / 1000.0 if dt > 1 else dt
        # if self.monster_restock_timer > 0:
        #     self.monster_restock_timer -= dt_sec
        #     if self.monster_restock_timer <= 0:
        #         self.monster_restock_timer = 0.0
        #         self.monster_stock = self.monster_stock_max

        #         # 🔄 refresh 一整組 monster
        #         self.shop_monster.clear()
        #         sample_count = min(self.monster_stock_max, len(MONSTER_DATA))
        #         for proto in random.sample(MONSTER_DATA, sample_count):
        #             lvl = random.randint(1, 5)
        #             mon = build_monster(proto, lvl)
        #             self.shop_monster.append(mon)

        #         self.monster_generated = True
        #         self._rebuild_all_buttons()
        #         self._update_scroll_range()
        # if input_manager.mouse_pressed(1):
        #     mx, my = input_manager.mouse_pos      


        #     # 1. Back 優先
        #     if self.overlay_button_back.hitbox.collidepoint(mx, my):
        #         # 直接呼叫 Button 裡的 on_click（就是你傳進去的 lambda: self.close_overlay()）
        #         self.overlay_button_back.on_click()
        #         return

        #     # 2. BUY / SELL Tab
        #     if self.button_buy_tab.hitbox.collidepoint(mx, my):
        #         self.button_buy_tab.on_click()   # 內部是 lambda: self._switch_mode("buy")
        #         return

        #     if self.button_sell_tab.hitbox.collidepoint(mx, my):
        #         self.button_sell_tab.on_click()  # lambda: self._switch_mode("sell")
        #         return

        #     # 3. 內容區
        #     if self.mode == "buy":
        #         # 先檢查怪物按鈕
        #         for btn in self.buy_monster_buttons:

        #             if btn.hitbox.collidepoint(mx, my):
        #                 btn.on_click()   # 這裡實際會呼叫 _buy_monster(m)
        #                 return

        #         # 再檢查道具按鈕
        #         for btn in self.buy_item_buttons:

        #             if btn.hitbox.collidepoint(mx, my):
        #                 btn.on_click()   # 會呼叫 _buy_item(item_cfg)
        #                 return

        #     else:  # sell 模式
        #         for btn in self.sell_monster_buttons:

        #             if btn.hitbox.collidepoint(mx, my):
        #                 btn.on_click()   # _sell_monster(i, p)
        #                 return

        # 右下角 toast 更新
        self._update_toasts(dt)
        
        #restock
        if input_manager.mouse_pressed(1):
            mx, my = input_manager.mouse_pos
            if self.button_force_restock.hitbox.collidepoint(mx, my):
                self.button_force_restock.on_click()
                return
    
    def _draw_buy(self,screen :pg.Surface,flat_x:int,flat_y: int, flat_w: int, flat_h: int):
        monster_x = flat_x + 40
        monster_y = flat_y + 90
        # content_top = flat_y + 80
        # content_bottom = flat_y + flat_h - 40
        banner_w,banner_h=self.monster_banner.get_size()
        for idx, mon in enumerate(self.shop_monster):
            y = monster_y + idx * (banner_h + 10)+ self.scroll
            # if y + banner_h < content_top or y > content_bottom:
            #     continue
            banner_rect = self.monster_banner.get_rect(topleft=(monster_x, y))
            screen.blit(self.monster_banner, banner_rect)
        
            # Icon
            icon_size = 70
            icon_x = banner_rect.left +50
            icon_y = banner_rect.top + (banner_rect.height - icon_size) // 2 -10
            base_img = load_img(mon["sprite_path"])
            base_img = pg.transform.scale(base_img, (icon_size, icon_size))
            screen.blit(base_img, (icon_x, icon_y))

            # 名字 & 等級
            name_surf = self.font.render(mon["name"], True, (0, 0, 0))
            screen.blit(name_surf, (icon_x + icon_size + 16, banner_rect.top + 30))

            lvl_surf = self.font.render(f"Lv.{mon['level']}", True, (0, 0, 0))
            screen.blit(lvl_surf, (banner_rect.right - 80, banner_rect.top + 16))

            # 價格
            price = self._get_monster_price(mon)
            price_surf = self.font_small.render(f"${price}", True, (0, 0, 0))
            screen.blit(price_surf, (banner_rect.right - 90, banner_rect.bottom - 40))

            #element icon
            el_key = str(mon.get("element", "grass")).lower()
            el_img = self.element_icons.get(el_key)
            if el_img is not None:
                el_size = 32
                el_surf = pg.transform.scale(el_img, (el_size, el_size))
                el_x = icon_x + icon_size +125
                el_y = banner_rect.top +25
                screen.blit(el_surf, (el_x, el_y))            

        # 道具
        items_x = flat_x + 40
        items_y = flat_y + 90 + len(self.shop_monster) * (banner_h + 20) + 10
        banner_w_i, banner_h_i = self.item_banner.get_size()

        for idx, it in enumerate(self.items_for_sale):
            y = items_y + idx * (banner_h_i + 8)+ self.scroll
            # if y + banner_h_i < content_top or y > content_bottom:
            #     continue
            banner_rect = self.item_banner.get_rect(topleft=(items_x, y))
            screen.blit(self.item_banner, banner_rect)

            # Icon
            icon_size = 40
            icon_x = banner_rect.left +60
            icon_y = banner_rect.top + (banner_rect.height - icon_size) // 2 
            item_img = load_img(it["sprite_path"])
            item_img = pg.transform.scale(item_img, (icon_size, icon_size))
            screen.blit(item_img, (icon_x, icon_y))

            # 名稱
            name_surf = self.font.render(it["name"], True, (0, 0, 0))
            screen.blit(name_surf, (icon_x + icon_size + 30, banner_rect.top + 20))

            # 價格
            price = it["price"]
            price_surf = self.font_small.render(f"${price}", True, (0, 0, 0))
            screen.blit(price_surf, (banner_rect.right - 90, banner_rect.centery - 15))

    def _draw_sell(self, screen: pg.Surface, flat_x: int, flat_y: int, flat_w: int, flat_h: int) -> None:
        monsters = self.game_manager.bag._monsters_data
        monster_x = flat_x + 40
        monster_y = flat_y + 90
        banner_w, banner_h = self.monster_banner.get_size()
        # content_top = flat_y + 80
        # content_bottom = flat_y + flat_h - 40        

        if not monsters:
            text = self.font.render("No monsters to sell.", True, (0, 0, 0))
            screen.blit(text, (monster_x, monster_y))
            return

        for idx, mon in enumerate(monsters):
            y = monster_y + idx * (banner_h + 10)+ self.scroll
            # if y + banner_h < content_top or y > content_bottom:
            #     continue
            banner_rect = self.monster_banner.get_rect(topleft=(monster_x, y))
            screen.blit(self.monster_banner, banner_rect)

            icon_size = 80
            icon_x = banner_rect.left + 50
            icon_y = banner_rect.top + (banner_rect.height - icon_size) // 2 -20
            base_img = load_img(mon["sprite_path"])
            base_img = pg.transform.scale(base_img, (icon_size, icon_size))
            screen.blit(base_img, (icon_x, icon_y))

            name_surf = self.font.render(mon["name"], True, (0, 0, 0))
            screen.blit(name_surf, (icon_x + icon_size + 16, banner_rect.top +30))

            lvl_surf = self.font.render(f"Lv.{mon['level']}", True, (0, 0, 0))
            screen.blit(lvl_surf, (banner_rect.right - 80, banner_rect.top + 16))

            price = self._get_monster_price(mon) // 2
            price_surf = self.font_small.render(f"${price}", True, (0, 0, 0))
            screen.blit(price_surf, (banner_rect.right - 90, banner_rect.bottom - 40))

            # element icon
            el_key = str(mon.get("element", "grass")).lower()
            el_img = self.element_icons.get(el_key)
            if el_img is not None:
                el_size = 32
                el_surf = pg.transform.scale(el_img, (el_size, el_size))
                el_x = icon_x + icon_size +125
                el_y = banner_rect.top +25
                screen.blit(el_surf, (el_x, el_y))

    def draw(self,screen):
        #overlay
        if self.overlay_open:
            # 畫暗背景
            overlay=pg.Surface((GameSettings.SCREEN_WIDTH,GameSettings.SCREEN_HEIGHT),pg.SRCALPHA)
            overlay.fill((0,0,0,150))
            screen.blit(overlay,(0,0)) 
        

            # 3. 畫 Back 按鈕
            flat_x, flat_y, flat_w, flat_h = self._flat_rect_values()            
            self.overlay_flat_shop_sprite.rect.topleft = (flat_x, flat_y)
            self.overlay_flat_shop_sprite.draw(screen)

            # 4. 左下角提示字：之後這句會改成你說的那句
            hint_text = "ESC to close | Click to buy / sell"
            surf = self.font.render(hint_text, True, (255, 255, 255))
            rect = surf.get_rect()
            rect.left = 10
            rect.bottom = GameSettings.SCREEN_HEIGHT - 10
            screen.blit(surf, rect)  

            #標題
            title="SHOP-BUY" if self.mode =="buy" else "SHOP-SELL"   
            title_surf=self.font_big.render(title,True,(0,0,0))     
            screen.blit(title_surf,(flat_x +350, flat_y + 25))           

            coins=self._get_coins()
            coins_text=self.font.render(f"Coin : {coins}",True,(0,0,0))
            c_x=flat_x+flat_w - coins_text.get_width()-40
            c_y=flat_y +30
            screen.blit(coins_text,(c_x,c_y))

            #Tabs
            self.button_buy_tab.draw(screen)
            self.button_sell_tab.draw(screen)

            for btn, text in ((self.button_buy_tab, "BUY"), (self.button_sell_tab, "SELL")):
                t_surf = self.font_small.render(text, True, (0, 0, 0))
                br = btn.hitbox
                tx = br.x + br.width  // 2 - t_surf.get_width()  // 2
                ty = br.y + br.height // 2 - t_surf.get_height() // 2
                screen.blit(t_surf, (tx, ty))

            # 列表的可視區域
            content_rect = pg.Rect(
                flat_x + 30,         # 左邊留 30
                flat_y + 80,         # 從標題下方開始
                flat_w - 60,         # 右邊也留 30
                flat_h - 130         # 底下留空間給 back button
            )
            screen.set_clip(content_rect)

            if self.mode == "buy":
                self._draw_buy(screen, flat_x, flat_y, flat_w, flat_h)

                # 再畫 shop 按鈕（一起被 clip）
                for btn in self.buy_monster_buttons:
                    btn.draw(screen)
                for btn in self.buy_item_buttons:
                    btn.draw(screen)
            else:
                self._draw_sell(screen, flat_x, flat_y, flat_w, flat_h)

                for btn in self.sell_monster_buttons:
                    btn.draw(screen)

            screen.set_clip(None)

            #back btn
            self.overlay_button_back.draw(screen)
            self._draw_toasts(screen)
            #timer restock
            if self.monster_restock_timer > 0:
                sec = max(0, int(self.monster_restock_timer))
                timer_text = self.font_small.render(
                    f"Restock in {sec}s", True, (200, 0, 0)
                )
                screen.blit(
                    timer_text,
                    (c_x, c_y + 30)
                )
        #restock
        self.button_force_restock.draw(screen)

    