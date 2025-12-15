from src.utils.definition import Monster
from enum import Enum,auto
import copy

class Element(Enum):
    GRASS=auto()
    FIRE=auto()
    WATER=auto()
    ICE=auto()

#   攻擊方 -> 防禦方 : 倍率
ELEMENT_EFFECTIVENESS: dict[tuple[Element, Element], float] = {
    # Fire > Grass
    (Element.FIRE, Element.GRASS): 2.0,
    (Element.GRASS, Element.FIRE): 0.5,

    # Grass > Ice
    (Element.GRASS, Element.ICE): 2.0,
    (Element.ICE, Element.GRASS): 0.5,

    # Ice > Water
    (Element.ICE, Element.WATER): 2.0,
    (Element.WATER, Element.ICE): 0.5,

    # Water > Fire
    (Element.WATER, Element.FIRE): 2.0,
    (Element.FIRE, Element.WATER): 0.5,
}

def get_element_multiplier(attacker_el: Element, defender_el: Element) -> float:
    if attacker_el == defender_el:
        return 1.0
    return ELEMENT_EFFECTIVENESS.get((attacker_el, defender_el), 1.0)

def element_from_str(s: str) -> Element:
    s = s.lower()
    if s == "grass":
        return Element.GRASS
    if s == "fire":
        return Element.FIRE
    if s == "water":
        return Element.WATER
    if s == "ice":
        return Element.ICE
    # 預設給個草，或 raise 也行
    return Element.GRASS

# MONSTER_DATA: list[Monster] = [
#     {
#         "name": "Pikachu",
#         "hp": 100,
#         "max_hp": 100,
#         "level": 25,
#         "sprite_path": "menu_sprites/menusprite1.png",
#     },
#     {
#         "name": "Charizard",
#         "hp": 200,
#         "max_hp": 200,
#         "level": 36,
#         "sprite_path": "menu_sprites/menusprite2.png",
#     },
#     {
#         "name": "Blastoise",
#         "hp": 180,
#         "max_hp": 180,
#         "level": 32,
#         "sprite_path": "menu_sprites/menusprite3.png",
#     },
#     {
#         "name": "Venusaur",
#         "hp": 160,
#         "max_hp": 160,
#         "level": 30,
#         "sprite_path": "menu_sprites/menusprite4.png",
#     },
#     {
#         "name": "Gengar",
#         "hp": 140,
#         "max_hp": 140,
#         "level": 28,
#         "sprite_path": "menu_sprites/menusprite5.png",
#     },
#     {
#         "name": "Dragonite",
#         "hp": 220,
#         "max_hp": 220,
#         "level": 40,
#         "sprite_path": "menu_sprites/menusprite6.png",
#     },
# ]
MONSTER_DATA = [
    # 1-3 Grass evolution line
    {
        "id": 1,
        "name": "Leafmon",
        "element": "grass",
        "max_hp": 60,
        "attack": 15,
        "defense": 10,
        # "level": 1,
        "sprite_path": "menu_sprites/menusprite1.png",
        "battle_idle_path": "sprites/sprite1_idle.png",
        "battle_attack_path": "sprites/sprite1_attack.png",
        "evolve_to": 2,
    },
    {
        "id": 2,
        "name": "Leafmore",
        "element": "grass",
        "max_hp": 80,
        "attack": 22,
        "defense": 16,
        # "level": 1,
        "sprite_path": "menu_sprites/menusprite2.png",
        "battle_idle_path": "sprites/sprite2_idle.png",
        "battle_attack_path": "sprites/sprite2_attack.png",
        "evolve_to": 3,
    },
    {
        "id": 3,
        "name": "Leafmane",
        "element": "grass",
        "max_hp": 100,
        "attack": 30,
        "defense": 22,
        # "level": 1,
        "sprite_path": "menu_sprites/menusprite3.png",
        "battle_idle_path": "sprites/sprite3_idle.png",
        "battle_attack_path": "sprites/sprite3_attack.png",
        "evolve_to": None,
    },

    # 4 - Water
    {
        "id": 4,
        "name": "Pengullet",
        "element": "water",
        "max_hp": 70,
        "attack": 18,
        "defense": 12,
        # "level": 1,
        "sprite_path": "menu_sprites/menusprite4.png",
        "battle_idle_path": "sprites/sprite4_idle.png",
        "battle_attack_path": "sprites/sprite4_attack.png",
        "evolve_to": None,
    },

    # 5 - Ice (solo)
    {
        "id": 5,
        "name": "Vaelet",
        "element": "ice",
        "max_hp": 65,
        "attack": 17,
        "defense": 12,
        # "level": 1,
        "sprite_path": "menu_sprites/menusprite5.png",
        "battle_idle_path": "sprites/sprite5_idle.png",
        "battle_attack_path": "sprites/sprite5_attack.png",
        "evolve_to": None,
    },
    #6 ice
    {
        "id": 6,
        "name": "Icefox",
        "element": "ice",
        "max_hp": 60,
        "attack": 30,
        "defense": 10,
        # "level": 1,
        "sprite_path": "menu_sprites/menusprite6.png",
        "battle_idle_path": "sprites/sprite6_idle.png",
        "battle_attack_path": "sprites/sprite6_attack.png",
        "evolve_to": None,
    },

    # 7-9 Fire evolution line
    {
        "id": 7,
        "name": "Flamkit",
        "element": "fire",
        "max_hp": 60,
        "attack": 20,
        "defense": 10,
        # "level": 1,
        "sprite_path": "menu_sprites/menusprite7.png",
        "battle_idle_path": "sprites/sprite7_idle.png",
        "battle_attack_path": "sprites/sprite7_attack.png",
        "evolve_to": 8,
    },
    {
        "id": 8,
        "name": "Flamcub",
        "element": "fire",
        "max_hp": 80,
        "attack": 26,
        "defense": 16,
        # "level": 1,
        "sprite_path": "menu_sprites/menusprite8.png",
        "battle_idle_path": "sprites/sprite8_idle.png",
        "battle_attack_path": "sprites/sprite8_attack.png",
        "evolve_to": 9,
    },
    {
        "id": 9,
        "name": "Flamcry",
        "element": "fire",
        "max_hp": 100,
        "attack": 34,
        "defense": 22,
        # "level": 1,
        "sprite_path": "menu_sprites/menusprite9.png",
        "battle_idle_path": "sprites/sprite9_idle.png",
        "battle_attack_path": "sprites/sprite9_attack.png",
        "evolve_to": None,
    },

    # 10 Ice
    {
        "id": 10,
        "name": "Surfent",
        "element": "ice",
        "max_hp": 75,
        "attack": 22,
        "defense": 14,
        # "level": 1,
        "sprite_path": "menu_sprites/menusprite10.png",
        "battle_idle_path": "sprites/sprite10_idle.png",
        "battle_attack_path": "sprites/sprite10_attack.png",
        "evolve_to": None,
    },

    # 11 Grass
    {
        "id": 11,
        "name": "Sparkit",
        "element": "grass",
        "max_hp": 65,
        "attack": 18,
        "defense": 12,
        # "level": 1,
        "sprite_path": "menu_sprites/menusprite11.png",
        "battle_idle_path": "sprites/sprite11_idle.png",
        "battle_attack_path": "sprites/sprite11_attack.png",
        "evolve_to": None,
    },

    # 12-14 Water evolution line
    {
        "id": 12,
        "name": "Hydrake",
        "element": "water",
        "max_hp": 70,
        "attack": 20,
        "defense": 14,
        # "level": 1,
        "sprite_path": "menu_sprites/menusprite12.png",
        "battle_idle_path": "sprites/sprite12_idle.png",
        "battle_attack_path": "sprites/sprite12_attack.png",
        "evolve_to": 13,
    },
    {
        "id": 13,
        "name": "Hydragon",
        "element": "water",
        "max_hp": 90,
        "attack": 27,
        "defense": 18,
        # "level": 1,
        "sprite_path": "menu_sprites/menusprite13.png",
        "battle_idle_path": "sprites/sprite13_idle.png",
        "battle_attack_path": "sprites/sprite13_attack.png",
        "evolve_to": 14,
    },
    {
        "id": 14,
        "name": "Hydrorel",
        "element": "water",
        "max_hp": 110,
        "attack": 35,
        "defense": 24,
        # "level": 1,
        "sprite_path": "menu_sprites/menusprite14.png",
        "battle_idle_path": "sprites/sprite14_idle.png",
        "battle_attack_path": "sprites/sprite14_attack.png",
        "evolve_to": None,
    },

    # 15-16 Grass evolution
    {
        "id": 15,
        "name": "Florin",
        "element": "grass",
        "max_hp": 70,
        "attack": 19,
        "defense": 13,
        # "level": 1,
        "sprite_path": "menu_sprites/menusprite15.png",
        "battle_idle_path": "sprites/sprite15_idle.png",
        "battle_attack_path": "sprites/sprite15_attack.png",
        "evolve_to": 16,
    },
    {
        "id": 16,
        "name": "Floralyn",
        "element": "grass",
        "max_hp": 90,
        "attack": 26,
        "defense": 18,
        # "level": 1,
        "sprite_path": "menu_sprites/menusprite16.png",
        "battle_idle_path": "sprites/sprite16_idle.png",
        "battle_attack_path": "sprites/sprite16_attack.png",
        "evolve_to": None,
    },
]
def build_monster(proto: dict, level: int = 1) -> dict:
    mon = copy.deepcopy(proto)

    mon["level"] = level

    # 這三個是「成長公式」：你之後覺得太強太弱都可以改這裡
    base_hp = proto["max_hp"]
    base_atk = proto["attack"]
    base_def = proto["defense"]

    mon["max_hp"] = base_hp + (level - 1) * 8
    mon["attack"] = base_atk + (level - 1) * 3
    mon["defense"] = base_def + (level - 1) * 2

    mon["hp"] = mon["max_hp"]

    return mon


def get_proto_by_id(mon_id: int) -> dict | None:
    """方便 Bag 或其他地方用 ID 找模板"""
    for m in MONSTER_DATA:
        if m["id"] == mon_id:
            return m
    return None