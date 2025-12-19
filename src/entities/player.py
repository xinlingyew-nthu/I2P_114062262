from __future__ import annotations
import pygame as pg
from .entity import Entity
from src.core.services import input_manager
from src.utils import Position, PositionCamera, GameSettings, Logger
from src.core import GameManager
import math
from typing import override

class Player(Entity):
    speed: float = 4.0 * GameSettings.TILE_SIZE
    game_manager: GameManager

    def __init__(self, x: float, y: float, game_manager: GameManager) -> None:
        self.teleport_cooldown = 0.0
        super().__init__(x, y, game_manager)



    @override
    def update(self, dt: float) -> None:
        dis = Position(0, 0)
        # 減少冷卻時間
        forced=getattr(self,"forced_dir",None)
        if forced is not None:
            # forced_dir = (fx, fy) 其中 fx/fy 是 -1/0/1
            dis.x, dis.y = forced

        else:
            if input_manager.key_down(pg.K_LEFT) or input_manager.key_down(pg.K_a):
                dis.x -= 1
            if input_manager.key_down(pg.K_RIGHT) or input_manager.key_down(pg.K_d):
                dis.x += 1
            if input_manager.key_down(pg.K_UP) or input_manager.key_down(pg.K_w):
                dis.y -= 1
            if input_manager.key_down(pg.K_DOWN) or input_manager.key_down(pg.K_s):
                dis.y += 1

            # 原本的 key_down 判斷全部留著
                
        '''
        [TODO HACKATHON 2]
        Calculate the distance change, and then normalize the distance
        '''

        facing: str | None = None
        if dis.y < 0:
            facing = "up"
        elif dis.y > 0:
            facing = "down"
        elif dis.x < 0:
            facing = "left"
        elif dis.x > 0:
            facing = "right"
        
        if facing is not None:
            self.animation.switch(facing)

            # moving=True
        # self.animation.update_pos(self.position)
        # if moving:
        #     self.animation.update(dt)

        l=math.hypot(dis.x,dis.y)

        if l >0:
            dis.x=(dis.x/l) * self.speed * dt
            dis.y=(dis.y/l) * self.speed * dt
            moving=True
        else:
            moving=False

        ''''
        [TODO HACKATHON 4]
        Check if there is collision, if so try to make the movement smooth
        Hint #1 : use entity.py _snap_to_grid function or create a similar function
        Hint #2 : Beware of glitchy teleportation, you must do
                    1. Update X
                    2. If collide, snap to grid
                    3. Update Y
                    4. If collide, snap to grid
                  instead of update both x, y, then snap to grid
        '''

        new_x=dis.x+self.position.x 
        new_y=dis.y+self.position.y
        current_map=self.game_manager
        self.animation.rect.topleft = (new_x,self.position.y)
        #test_rect_x=pg.Rect(new_x,self.position.y,self.animation.rect.width,self.animation.rect.height)
        # test_rect_x = self.animation.rect.copy()
        # test_rect_x.topleft = (round(new_x), round(self.position.y))

        if current_map.check_collision(self.animation.rect) :
        #or any(test_rect_x.colliderect(enemy.animation.rect) for enemy in self.game_manager.current_enemy_trainers):
            self.position.x=self._snap_to_grid(self.position.x)
        else:
            self.position.x=new_x
        #rect_y = pg.Rect(
         #   round(self.position.x),
          #  round(new_y),
           ##GameSettings.TILE_SIZE
        #)
        self.animation.rect.topleft = (self.position.x,new_y)
        #test_rect_y=pg.Rect(new_y,self.position.x,self.animation.rect.width,self.animation.rect.height)
        if current_map.check_collision(self.animation.rect) :
        #or any(test_rect_y.colliderect(enemy.animation.rect) for enemy in self.game_manager.current_enemy_trainers):
            self.position.y=self._snap_to_grid(self.position.y)
        else:
            self.position.y=new_y

        #idle
        if moving:
            self.animation.update(dt)
        else:
            self.animation.accumulator=0.0

        # Check teleportation
        # tp = self.game_manager.current_map.check_teleport(self.position)
        # if tp:
        #     dest = tp.destination
        #     self.game_manager.switch_map(dest)
        # self.teleport_cooldown = 0.0
        self.teleport_cooldown = max(0.0, self.teleport_cooldown - dt)
        if self.teleport_cooldown <= 0:
            tp = self.game_manager.current_map.check_teleport(self.animation.rect)
            if tp:
                dest = tp.destination

                tile = GameSettings.TILE_SIZE

                self.teleport_cooldown = 0.2 

                # 回到大地圖 map.tmx 的時候，依照「從哪裡來」決定出生點
                if dest == "map.tmx":
                    # 從 gym 出來 → 出現在 gym 門口外面
                    if self.game_manager.current_map_key == "gym.tmx":
                        # 用你在 Tiled 看到的「gym 門口外面那格」tile 座標替換
                        gym_out_x, gym_out_y = 24, 24   # 例子：自己改
                        self.game_manager.next_spawn = Position(
                            gym_out_x * tile,
                            gym_out_y * tile
                        )
                    

                    # 從家出來 → 出現在家門口外面
                    elif self.game_manager.current_map_key == "home.tmx":
                        # 用你在 Tiled 看到的「家門口外面那格」tile 座標替換
                        home_out_x, home_out_y = 16, 29  # 例子
                        self.game_manager.next_spawn = Position(
                            home_out_x * tile,
                            home_out_y * tile
                        )
                    elif self.game_manager.current_map_key == "beach.tmx":
                        beach_out_x, beach_out_y = 15, 37   # 換成你在 map.tmx 裡看到的那格
                        self.game_manager.next_spawn = Position(
                            beach_out_x * tile,
                            beach_out_y * tile
                        )
                # 其他傳送就用原本 spawn
                self.game_manager.switch_map(dest)
            # if tp:
            #     self.game_manager.switch_map(tp.destination)
            #     self.teleport_cooldown = 0.2  

                
        super().update(dt)

    @override
    def draw(self, screen: pg.Surface, camera: PositionCamera) -> None:
        super().draw(screen, camera)
        
    @override
    def to_dict(self) -> dict[str, object]:
        return super().to_dict()
    
    @property
    @override
    def camera(self) -> PositionCamera:
        #1 讓角色在中間
        cam_x=int(self.position.x)-GameSettings.SCREEN_WIDTH // 2
        cam_y=int(self.position.y)-GameSettings.SCREEN_HEIGHT // 2
        #2 算地圖大小
        current_map=self.game_manager.current_map
        pixel_w=current_map.tmxdata.width *GameSettings.TILE_SIZE
        pixel_h=current_map.tmxdata.height *GameSettings.TILE_SIZE
        #3 計算camera可以移動的就
        max_x=max(0,pixel_w-GameSettings.SCREEN_WIDTH)
        max_y=max(0,pixel_h-GameSettings.SCREEN_HEIGHT)
        #4 clamp限制範圍
        if cam_x <0:
            cam_x=0
        elif cam_x>max_x:
            cam_x=max_x
        if cam_y <0:
            cam_y=0
        elif cam_y>max_y:
            cam_y=max_y   
        return PositionCamera(cam_x,cam_y)     

        # return PositionCamera(int(self.position.x) - GameSettings.SCREEN_WIDTH // 2, 
        # int(self.position.y) - GameSettings.SCREEN_HEIGHT // 2)
            
    @classmethod
    @override
    def from_dict(cls, data: dict[str, object], game_manager: GameManager) -> Player:
        return cls(data["x"] * GameSettings.TILE_SIZE, data["y"] * GameSettings.TILE_SIZE, game_manager)

