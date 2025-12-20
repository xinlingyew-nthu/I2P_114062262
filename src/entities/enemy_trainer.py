from __future__ import annotations
import pygame
from enum import Enum
from dataclasses import dataclass
from typing import override

from .entity import Entity
from src.sprites import Sprite,Animation
from src.core import GameManager
from src.core.services import input_manager, scene_manager
from src.utils import GameSettings, Direction, Position, PositionCamera
from src.scenes.game_scene import GameScene   



class EnemyTrainerClassification(Enum):
    STATIONARY = "stationary"

@dataclass
class IdleMovement:
    def update(self, enemy: "EnemyTrainer", dt: float) -> None:
        return

class EnemyTrainer(Entity):
    classification: EnemyTrainerClassification
    max_tiles: int | None
    _movement: IdleMovement
    warning_sign: Sprite
    detected: bool
    los_direction: Direction

    @override
    def __init__(
        self,
        x: float,
        y: float,
        game_manager: GameManager,
        classification: EnemyTrainerClassification = EnemyTrainerClassification.STATIONARY,
        max_tiles: int | None = 2,
        facing: Direction | None = None,
        sprite_index: int = 1,  
        is_shop: bool = False,
    ) -> None:
        super().__init__(x, y, game_manager)
        self.sprite_index = sprite_index
        self.is_shop = is_shop
        self.animation = Animation(
            f"character/ow{sprite_index}.png",
            ["down", "left", "right", "up"],
            4,
            (GameSettings.TILE_SIZE, GameSettings.TILE_SIZE),
        )
        self.classification = classification
        self.max_tiles = max_tiles
        if classification == EnemyTrainerClassification.STATIONARY:
            self._movement = IdleMovement()
            if facing is None:
                raise ValueError("Idle EnemyTrainer requires a 'facing' Direction at instantiation")
            self._set_direction(facing)
        else:
            raise ValueError("Invalid classification")
        self.warning_sign = Sprite("exclamation.png", (GameSettings.TILE_SIZE // 2, GameSettings.TILE_SIZE // 2))
        self.warning_sign.update_pos(Position(x + GameSettings.TILE_SIZE // 4, y - GameSettings.TILE_SIZE // 2))
        self.detected = False
        self.font = pygame.font.Font("assets/fonts/Minecraft.ttf", 18)

    @override
    def update(self, dt: float) -> None:
        self._movement.update(self, dt)
        self._has_los_to_player()
        if self.detected and input_manager.key_pressed(pygame.K_SPACE):
            # scene_manager.change_scene(
            #     "battle")
            game_scene = scene_manager.get_scene("game")
            if self.is_shop:
                # 這個 NPC 是 shop
                # 如果你的 GameScene.open_shop 有收 trainer，就保留 (self)
                # 如果沒有，就改成 game_scene.open_shop()
                game_scene.open_shop(self)
            else:
                # 其他 NPC：進入 battle scene
                game_scene.start_battle_with_trainer(self)

        self.animation.update_pos(self.position)

            
        # player_mon_data = self.game_manager.get_active_player_monster() 
        # enemy_mon_data = self.game_manager.get_enemy_monster_for_battle(enemy_id) 

    #     if player_mon_data and enemy_mon_data:
    #         scene_manager.change_scene(
    #             "battle", 
    #             player_monster=player_mon_data, #作为关键字参数传入
    #             enemy_monster=enemy_mon_data     #作为关键字参数传入
    # )
            #     player_monster=your_mon,
            #     enemy_monster=enemy.monster_list[0]
            # )
        self.animation.update_pos(self.position)

    @override
    def draw(self, screen: pygame.Surface, camera: PositionCamera) -> None:
        super().draw(screen, camera)
        if self.detected:
            self.warning_sign.draw(screen, camera)
        if GameSettings.DRAW_HITBOXES:
            los_rect = self._get_los_rect()
            if los_rect is not None:
                pygame.draw.rect(screen, (255, 255, 0), camera.transform_rect(los_rect), 1)
        #出現字體
        if self.detected:
            # 1) 畫驚嘆號
            self.warning_sign.draw(screen, camera)

            # 2) 畫 "Press SPACE to enter"
            text_surf = self.font.render("Press SPACE to enter", True, (255, 255, 0))

            # 把 EnemyTrainer 的 rect 從世界座標轉換成畫面座標
            trainer_rect_screen = camera.transform_rect(self.animation.rect)

            # 讓文字在 NPC 頭上置中
            text_x = trainer_rect_screen.centerx - text_surf.get_width() // 2
            text_y = trainer_rect_screen.top - text_surf.get_height() - 50  # 往上 4px

            screen.blit(text_surf, (text_x, text_y))

        if GameSettings.DRAW_HITBOXES:
            los_rect = self._get_los_rect()
            if los_rect is not None:
                pygame.draw.rect(
                    screen, (255, 255, 0),
                    camera.transform_rect(los_rect), 1
                )


    def _set_direction(self, direction: Direction) -> None:
        self.direction = direction
        if direction == Direction.RIGHT:
            self.animation.switch("right")
        elif direction == Direction.LEFT:
            self.animation.switch("left")
        elif direction == Direction.DOWN:
            self.animation.switch("down")
        else:
            self.animation.switch("up")
        self.los_direction = self.direction

    def _get_los_rect(self) -> pygame.Rect | None:
        '''
        TODO: Create hitbox to detect line of sight of the enemies towards the player
        '''
        base_rect=self.animation.rect
        size=GameSettings.TILE_SIZE

        #enemy 面向
        if self.los_direction==Direction.UP:
            return pygame.Rect(base_rect.x,base_rect.y-size,base_rect.width,size)
        if self.los_direction==Direction.DOWN:
            return pygame.Rect(base_rect.x,base_rect.y+base_rect.height,base_rect.width,size)       
        if self.los_direction==Direction.RIGHT:
            return pygame.Rect(base_rect.x-size,base_rect.y,base_rect.width,size)            
        if self.los_direction==Direction.LEFT:
            return pygame.Rect(base_rect.x+base_rect.width,base_rect.y,base_rect.width,size)                    
        return None

    def _has_los_to_player(self) -> None:
        player = self.game_manager.player
        if player is None:
            self.detected = False
            return
        #敵人前面
        los_rect = self._get_los_rect()
        if los_rect is None:
            self.detected = False
            return
        '''
        TODO: Implement line of sight detection
        If it's detected, set self.detected to True
        '''
        player_rect=player.animation.rect
        #重叠
        if los_rect.colliderect(player_rect):
            self.detected = True
        else:    
            self.detected = False

    @classmethod
    @override
    def from_dict(cls, data: dict, game_manager: GameManager) -> "EnemyTrainer":
        classification = EnemyTrainerClassification(data.get("classification", "stationary"))
        max_tiles = data.get("max_tiles")
        facing_val = data.get("facing")
        facing: Direction | None = None
        if facing_val is not None:
            if isinstance(facing_val, str):
                facing = Direction[facing_val]
            elif isinstance(facing_val, Direction):
                facing = facing_val
        if facing is None and classification == EnemyTrainerClassification.STATIONARY:
            facing = Direction.DOWN
        is_shop = bool(data.get("is_shop", False))
        sprite_index=int(data.get("sprite",1))
        return cls(
            data["x"] * GameSettings.TILE_SIZE,
            data["y"] * GameSettings.TILE_SIZE,
            game_manager,
            classification,
            max_tiles,
            facing,
            sprite_index,
            is_shop
        )

    @override
    def to_dict(self) -> dict[str, object]:
        base: dict[str, object] = super().to_dict()
        base["classification"] = self.classification.value
        base["facing"] = self.direction.name
        base["max_tiles"] = self.max_tiles
        base["sprite"] = self.sprite_index 
        base["is_shop"] = self.is_shop 
        return base