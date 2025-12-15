import pygame as pg
import json
from src.utils import GameSettings,load_img 
from src.utils.definition import Monster, Item
from src.core.services import input_manager
from src.sprites import Sprite
from src.data.monster_data import get_proto_by_id, build_monster, MONSTER_DATA
MAX_LEVEL = 50


class Bag:
    _monsters_data: list[Monster]
    _items_data: list[Item]

    def __init__(self, monsters_data: list[Monster] | None = None, items_data: list[Item] | None = None):
        self._monsters_data = monsters_data if monsters_data else []
        self._items_data = items_data if items_data else []
        self.scroll=0
        self.mon_scroll = 0
        self.item_scroll = 0
        #font
        self.title_font=pg.font.Font("assets/fonts/Minecraft.ttf", 30)
        self.text_font=pg.font.Font("assets/fonts/Minecraft.ttf", 20)
        self.hp_fill_img = load_img("UI/raw/UI_Flat_BarFill01a.png")

        #banner
        banner=load_img("UI/raw/UI_Flat_Banner03a.png")

        self.monster_banner=pg.transform.scale(banner,(360,100))
        self.item_banner=pg.transform.scale(banner,(300,70))       

        #scroll
        self.scroll = 0
        self.min_scroll = -500   # 你原本在 GameScene clamp 的值
        self.max_scroll = 0   

        #element icon
        self.element_icons = {
            "grass": load_img("element/grass.png"),
            "fire": load_img("element/fire.png"),
            "water": load_img("element/water.png"),
            "ice": load_img("element/ice.png"),
        }        
        self.element=load_img("element/element.png")

        #item click monster
        self.selected_mon_idx: int | None = None   
        self.selected_item_idx: int | None = None

    #抓monster了放進包包
    def add_monster(self, monster: Monster) -> None:
        self._monsters_data.append(monster) 
        
    #用道具
    def use_item(self,name,amount)->bool:
        for item in self._items_data:
            if item ["name"] == name and item["count"] >= amount:
                item["count"]-=amount
                if item["count"] <=0:
                    self._items_data.remove(item)
                    return True
                return False
    def handle_click(self, mouse_pos: tuple[int, int]):
        mx, my = mouse_pos

        # 先算出 bag 的位置（跟 draw 一樣）
        flat_bag_w, flat_bag_h = 800, 600
        flat_bag_x = (GameSettings.SCREEN_WIDTH  - flat_bag_w) // 2
        flat_bag_y = (GameSettings.SCREEN_HEIGHT - flat_bag_h) // 2 

        # monster
        monster_x = flat_bag_x + 40
        monster_y = flat_bag_y + 90
        gap = 10
        clicked_mon = None

        if self._monsters_data:
            banner_h = self.monster_banner.get_height()
            current_y = monster_y + self.mon_scroll
            for idx, mons in enumerate(self._monsters_data):
                rect = pg.Rect(
                    monster_x,
                    current_y,
                    self.monster_banner.get_width(),
                    banner_h
                )
                if rect.collidepoint(mx, my):
                    clicked_mon = idx
                    break
                current_y += banner_h + gap

        # item
        items_x = flat_bag_x + 440
        items_y = flat_bag_y + 110
        gap = 8
        clicked_item = None

        if self._items_data:
            banner_h = self.item_banner.get_height()
            y = items_y + self.item_scroll
            for idx, it in enumerate(self._items_data):
                rect = pg.Rect(
                    items_x,
                    y,
                    self.item_banner.get_width(),
                    banner_h
                )
                if rect.collidepoint(mx, my):
                    clicked_item = idx
                    break
                y += banner_h + gap

        

        # 更新選取
        if clicked_mon is not None and self.selected_item_idx is not None:
            self.selected_mon_idx = clicked_mon
            result = self._apply_item_to_monster(self.selected_item_idx,
                                                self.selected_mon_idx)
            # 用完清空，避免之後誤觸
            self.selected_mon_idx = None
            self.selected_item_idx = None
            return result

        # 情況 2：本來就有選 monster，這次點到 item -> 直接用
        if clicked_item is not None and self.selected_mon_idx is not None:
            self.selected_item_idx = clicked_item
            result = self._apply_item_to_monster(self.selected_item_idx,
                                                self.selected_mon_idx)
            self.selected_mon_idx = None
            self.selected_item_idx = None
            return result

        # 情況 3：只有選東西，還沒配對完成，就先記住
        if clicked_mon is not None:
            self.selected_mon_idx = clicked_mon
        if clicked_item is not None:
            self.selected_item_idx = clicked_item

        return None
    # def handle_event(self, event: pg.event.Event):

    #     if event.type == pg.MOUSEWHEEL:
    #         self.scroll += event.y * 30

    #         # 做 clamp，避免滑太多
    #         if self.scroll > self.max_scroll:
    #             self.scroll = self.max_scroll
    #         if self.scroll < self.min_scroll:
    #             self.scroll = self.min_scroll


    def update(self, dt: float):
        w = input_manager.mouse_wheel
        if w == 0:
            return

        mx, my = input_manager.mouse_pos

        flat_bag_w, flat_bag_h = 800, 600
        flat_bag_x = (GameSettings.SCREEN_WIDTH - flat_bag_w) // 2
        flat_bag_y = (GameSettings.SCREEN_HEIGHT - flat_bag_h) // 2

        monster_rect = pg.Rect(flat_bag_x + 40,  flat_bag_y + 90,  360, 480)
        item_rect    = pg.Rect(flat_bag_x + 440, flat_bag_y + 110, 300, 480)

        delta = w * 30

        if item_rect.collidepoint(mx, my):
            self.item_scroll += delta
        elif monster_rect.collidepoint(mx, my):
            self.mon_scroll += delta  

    MAX_LEVEL = 50

    def _level_up_mon(self, mon: dict) -> tuple[bool, str]:
        lvl = int(mon.get("level", 1))
        if lvl >= MAX_LEVEL:
            return False, "Max level reached (50)"

        proto = get_proto_by_id(mon.get("id", -1))
        if proto is None:
            return False, "Error: monster proto not found"

        #保留血量比例
        old_ratio = mon.get("hp", 0) / max(1, mon.get("max_hp", 1))

        new_mon = build_monster(proto, lvl + 1)
        new_mon["hp"] = max(1, int(new_mon["max_hp"] * old_ratio))

        mon.clear()
        mon.update(new_mon)
        return True, f"{mon['name']} leveled up to Lv.{mon['level']}!"


    def _evolve_mon(self, mon: dict) -> tuple[bool, str]:
        nxt = mon.get("evolve_to", None)
        if nxt is None:
            return False, "Can't evolve"

        proto = get_proto_by_id(nxt)
        if proto is None:
            return False, "Error: evolve target not found"

        old_ratio = mon.get("hp", 0) / max(1, mon.get("max_hp", 1))

        # 等級不變，只換 proto（更強的 base） → 也會套你的成長公式
        new_mon = build_monster(proto, int(mon.get("level", 1)))
        new_mon["hp"] = max(1, int(new_mon["max_hp"] * old_ratio))

        old_name = mon.get("name", "")
        mon.clear()
        mon.update(new_mon)
        return True, f"{old_name} evolved into {mon['name']}!"

    def _apply_item_to_monster(self, item_idx: int, mon_idx: int) -> dict:
        if not (0 <= item_idx < len(self._items_data)):
            return {"used": False, "message": "Invalid item."}
        if not (0 <= mon_idx < len(self._monsters_data)):
            return {"used": False, "message": "Invalid target."}

        item = self._items_data[item_idx]
        mon = self._monsters_data[mon_idx]
        name = item.get("name", "")
        msg = ""
        used = False

        # 保證有 hp / max_hp 欄位
        hp = mon.get("hp", 0)
        max_hp = mon.get("max_hp", hp)


     # 回滿 HP，不超過 max（並要求只能用一次）
        if name == "Heal Potion":
            missing = max_hp - hp

            if missing <= 0:
                # 已經滿血
                msg = "Full Health"
            elif missing <= 100:
                # 不夠扣 100，但還是可以用，直接補到滿
                mon["hp"] = max_hp
                used = True
                msg = f"{mon['name']} Full Healed!"
            else:
                # 缺血 >= 100，就正常 +100
                mon["hp"] = hp + 100
                used = True
                msg = f"{mon['name']} heal 100 HP!"

        # 下一次攻擊增加 50%
        elif name == "Strength Potion":
            if mon.get("buff_strength_pending", False):
                # 已經吃過 Strength
                return {"used": False, "message": "Attack has been used"}
            mon["buff_strength_pending"] = True
            used = True
            msg = "Attack used"

        # ========== Defense Potion ==========
        elif name == "Defense Potion":
            if mon.get("buff_defense_pending", False):
                return {"used": False, "message": "Defense has been used"}
            mon["buff_defense_pending"] = True
            used = True
            msg = "Defense used"

        # ========== Level Up ==========
        elif name == "Level Up":
            used, msg = self._level_up_mon(mon)

        # ========== Evolve Stone ==========
        elif name == "Evolve Stone":
            used, msg = self._evolve_mon(mon)

        else:
            # 其他道具一律沒效果（如果你只留三種 Potion 就不會走到這裡）
            return {"used": False, "message": "Nothing happened"}

        # ===== 扣道具 =====
        if used:
            item["count"] -= 1
            if item["count"] <= 0:
                self._items_data.pop(item_idx)
                self.selected_item_idx = None

        return {"used": used, "message": msg}   

    def draw(self, screen: pg.Surface):
        #flat
        flat_bag_w,flat_bag_h=800,600
        flat_bag_x = (GameSettings.SCREEN_WIDTH  - flat_bag_w) // 2
        flat_bag_y = (GameSettings.SCREEN_HEIGHT - flat_bag_h) // 2 
        #text
        title_bag=self.title_font.render("BAG",True,(0,0,0))
        screen.blit(title_bag,(flat_bag_x+30,flat_bag_y+20))

        #monster
        monster_x=flat_bag_x+40
        monster_y=flat_bag_y+90
        gap= 10
        monster_list_h = 480

        monster_clip_rect = pg.Rect(monster_x, monster_y, 360, monster_list_h)
        original_clip = screen.get_clip()

        
        # if not self._monsters_data:
        #     text=font.render("no monster",True,(0,0,0))
        #     screen.blit(text,(monster_x,monster_y))
        title_mons=self.title_font.render("Monster" , True,(0,0,0))
        screen.blit(title_mons,(flat_bag_x+40,flat_bag_y+60))      
        screen.set_clip(monster_clip_rect)  
        if self._monsters_data:
            banner_h=self.monster_banner.get_height()
            total_monster_height=len(self._monsters_data)*(banner_h + gap)-gap
            max_scroll_limit = 0
            min_scroll_limit=min(0,monster_list_h-total_monster_height)

            self.min_scroll=min_scroll_limit
            self.max_scroll=max_scroll_limit

            self.mon_scroll = max(self.min_scroll, min(self.max_scroll, self.mon_scroll))
            current_y = monster_y + self.mon_scroll
            for mons in self._monsters_data:
                #banner
                banner_rect=self.monster_banner.get_rect()
                banner_rect.topleft=(monster_x,current_y)
                screen.blit(self.monster_banner,banner_rect)
                #monster icon
                icon_size=72
                icon_x=banner_rect.left +20
                icon_y=banner_rect.top+(banner_rect.height-icon_size) //2 -10               
                icon_img = load_img(mons["sprite_path"])
                icon_img = pg.transform.scale(icon_img, (icon_size, icon_size))
                screen.blit(icon_img, (icon_x, icon_y)) 
                #name
                text_x=icon_x+icon_size+16
                text_y=banner_rect.top +12
                name=self.text_font.render(mons["name"],True,(0,0,0))
                screen.blit(name,(text_x,text_y))    
                #lvl
                level=self.text_font.render(f"Lv.{mons["level"]}",True,(0,0,0))         
                screen.blit(level,(banner_rect.right-80,text_y))
                #element icon
                el_key = str(mons.get("element", "grass")).lower()
                el_img = self.element_icons.get(el_key)
                if el_img is not None:
                    el_size = 24
                    el_surf = pg.transform.scale(el_img, (el_size, el_size))
                    # 放在怪物名字旁邊，例如：
                    ex = icon_x 
                    ey = icon_y
                    screen.blit(el_surf, (ex, ey))
                # e_x=flat_bag_x-100
                # e_y=flat_bag_y
                # el_i=self.element
                # screen.blit(el_i,(e_x,e_y))
                #hp
                if "hp" in mons and "max_hp" in mons:
                    bar_w=220
                    bar_h=18
                    bar_x=text_x
                    bar_y=banner_rect.bottom-49

                    pg.draw.rect(screen,(255,255,255),(bar_x,bar_y,bar_w,bar_h))
                    pg.draw.rect(screen,(0,0,0),(bar_x,bar_y,bar_w,bar_h),2)

                    ratio=max(0.0,min(1,mons["hp"]/max(1,mons["max_hp"])))
                    inner_w=int((bar_w-4) *ratio)

                    if inner_w > 0:
                        fill_img_scaled = pg.transform.scale(
                            self.hp_fill_img,
                            (inner_w, bar_h - 4)          
                        )
                        screen.blit(fill_img_scaled, (bar_x + 2, bar_y + 2))

                    #文字hp
                    hp_text=self.text_font.render(f"{mons['hp']}/{mons['max_hp']}" , True,(0,0,0))
                    screen.blit(hp_text,(bar_x +60,bar_y-22))
                else:
                    no_mons=self.text_font.render("No Monsters alive",True,(0,0,0))
                    screen.blit(no_mons,(monster_x,monster_y))

                current_y += banner_rect.height + gap
        screen.set_clip(original_clip)

        if self.element is not None:
            # 想多大就自己調，120~150 差不多
            icon_size = 140
            panel_surf = pg.transform.scale(self.element, (icon_size, icon_size))

            # 左下角：跟整個畫面對齊，不跟 flat 綁死
            x = 20
            y = GameSettings.SCREEN_HEIGHT - icon_size - 20
            screen.blit(panel_surf, (x, y))

        #item
        items_x = flat_bag_x + 440
        items_y = flat_bag_y + 110 
        item_list_h = 480

        item_clip_rect = pg.Rect(items_x, items_y, 300, item_list_h)       

        # 标题
        items_title = self.title_font.render("Items", True, (0, 0, 0))
        screen.blit(items_title, (items_x, flat_bag_y + 60))
        screen.set_clip(item_clip_rect)    

        banner_h = self.item_banner.get_height()

        gap = 8    
        icon_size = 40
        if self._items_data:
            # banner_h = self.item_banner.get_height()
            total_item_height = len(self._items_data) * (banner_h + gap) - gap
        else:
            total_item_height=0
        item_max_scroll = 0
        item_min_scroll = min(0, item_list_h - total_item_height)

        # ✅ 先 clamp
        self.item_scroll = max(item_min_scroll, min(item_max_scroll, self.item_scroll))

        # ✅ 再算 y
        y = items_y + self.item_scroll
        if self._items_data:
            for it in self._items_data:
                # banner 
                banner_rect = self.item_banner.get_rect()
                banner_rect.topleft = (items_x, y)
                screen.blit(self.item_banner, banner_rect)

                # 图标
                icon_x = banner_rect.left + 30
                icon_y = banner_rect.top + (banner_rect.height - icon_size) // 2


                item_img = load_img(it["sprite_path"])
                item_img = pg.transform.scale(item_img, (icon_size, icon_size))
                screen.blit(item_img, (icon_x, icon_y))


                # 名称
                name_surf = self.text_font.render(it["name"], True, (0, 0, 0))
                screen.blit(name_surf, (icon_x + icon_size + 12, icon_y + 6))

                # 4) 数量 
                count_surf = self.text_font.render(f"x{it['count']}", True, (0, 0, 0))
                screen.blit(count_surf, (banner_rect.right - 70, icon_y + 6))

                y += banner_rect.height + gap     

        screen.set_clip(original_clip)           


        # if not self._monsters_data:
        #     text=font.render("no monster",True,(0,0,0))
        #     screen.blit(text,(list_x,y))
        #     y +=line_h
        # if self._monsters_data:
        #     m=self._monsters_data[0]

        # else:
        #     for mons in self._monsters_data:
        #         icon_path=mons["sprite_path"]
        #         name=mons["name"]
        #         level=mons["level"]
        #         hp=mons["hp"]
        #         max_hp=mons["max_hp"]
        #         banner=Sprite
        #         line=f"{name} Lv.{level} hp{hp} / {max_hp}"
        #         icon=load_img(icon_path)
        #         icon=pg.transform.scale(icon,(64,64))
        #         screen.blit(icon,(list_x,y))                
        #         monster_info=font.render(line,True,(0,0,0))
        #         screen.blit(monster_info,(list_x,y))
                
        #         y += line_h
        #空一行
        # y += line_h

        # #item
        # items_x=flat_bag_x+420
        # yi=list_y+line_h
        # title_item=font.render("Items" , True,(0,0,0))
        # screen.blit(title_item,(items_x,yi))
        # yi += line_h
        

        # if not self._items_data:
        #     text=font.render("no item",True,(0,0,0))
        #     screen.blit(text,(items_x,yi))
        # else:
        #     for i in self._items_data:
        #         name=i["name"]
        #         count=i["count"]
        #         line=f"{name} x{count}"
        #         items_info=font.render(line,True,(0,0,0))
        #         screen.blit(items_info,(items_x,yi))
        #         yi += line_h

    def to_dict(self) -> dict[str, object]:
        return {
            "monsters": list(self._monsters_data),
            "items": list(self._items_data)
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "Bag":
        monsters = data.get("monsters") or []
        items = data.get("items") or []
        bag = cls(monsters, items)
        return bag