import random
from src.utils import load_img
from src.sprites import Sprite

class Monster:
    def __init__(self, proto: dict, level: int = 1):
        # 固定資料（從 MONSTER_DATA 拿）
        self.id = proto["id"]
        self.name = proto["name"]
        self.element = proto["element"]
        self.base_max_hp = proto["max_hp"]
        self.base_attack = proto["attack"]
        self.base_defense = proto["defense"]
        self.sprite_path = proto["sprite_path"]
        self.battle_idle_path = proto["battle_idle_path"]
        self.battle_attack_path = proto["battle_attack_path"]
        self.evolve_to = proto["evolve_to"]

        # 等級
        self.level = level

        # 計算真正能力
        self.max_hp = self.calculate_hp()
        self.attack = self.calculate_attack()
        self.defense = self.calculate_defense()
        self.current_hp = self.max_hp

        # 動畫 sprite
        self.idle_sprite = Sprite(self.battle_idle_path, size=(180, 180))
        self.attack_sprite = Sprite(self.battle_attack_path, size=(180, 180))
        self.current_sprite = self.idle_sprite

    # ====== 成長公式 ======

    def calculate_hp(self):
        return self.base_max_hp + (self.level - 1) * 8

    def calculate_attack(self):
        return self.base_attack + (self.level - 1) * 3

    def calculate_defense(self):
        return self.base_defense + (self.level - 1) * 2

    # ====== 進化 ======

    def evolve(self, MONSTER_DATA):
        if self.evolve_to is None:
            return False
        
        # 找下一隻 monster 的模板資料
        new_proto = None
        for proto in MONSTER_DATA:
            if proto["id"] == self.evolve_to:
                new_proto = proto
                break
        if new_proto is None:
            return False

        # 更新固定資料
        self.id = new_proto["id"]
        self.name = new_proto["name"]
        self.element = new_proto["element"]
        self.base_max_hp = new_proto["max_hp"]
        self.base_attack = new_proto["attack"]
        self.base_defense = new_proto["defense"]
        self.sprite_path = new_proto["sprite_path"]
        self.battle_idle_path = new_proto["battle_idle_path"]
        self.battle_attack_path = new_proto["battle_attack_path"]
        self.evolve_to = new_proto["evolve_to"]

        # 重新計算（等級不變）
        self.max_hp = self.calculate_hp()
        self.attack = self.calculate_attack()
        self.defense = self.calculate_defense()
        self.current_hp = self.max_hp

        # 換動畫 sprite
        self.idle_sprite = Sprite(self.battle_idle_path, size=(180, 180))
        self.attack_sprite = Sprite(self.battle_attack_path, size=(180, 180))
        self.current_sprite = self.idle_sprite
        
        return True
