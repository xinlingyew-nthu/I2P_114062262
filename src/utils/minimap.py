import pygame as pg

class MiniMap:
    def __init__(self):
        self.pos = (10, 10)        # 左上角
        self.size = (160, 160)     # minimap 大小
        self.map_img = None
        self.world_size = (1, 1)
        self._cache = {}           # map_key -> Surface

    def build_from_map(self, current_map, world_size, map_key):
        """
        current_map : Map 物件
        world_size  : (map_pixel_w, map_pixel_h)
        map_key     : current_map.path_name
        """
        self.world_size = (
            max(1, int(world_size[0])),
            max(1, int(world_size[1]))
        )

        # ===== cache（切回同一張圖不用重算）=====
        if map_key in self._cache:
            self.map_img = self._cache[map_key]
            return

        # ===== 關鍵：直接用 map._surface =====
        if not hasattr(current_map, "_surface"):
            # 保底：畫灰底，不炸
            surf = pg.Surface(self.size, pg.SRCALPHA)
            surf.fill((80, 80, 80, 180))
            pg.draw.rect(surf, (255, 255, 255), surf.get_rect(), 2)
            self.map_img = surf
            self._cache[map_key] = surf
            return

        full_map = current_map._surface
        mw, mh = self.size

        # 縮小整張地圖
        minimap = pg.transform.smoothscale(full_map, (mw, mh)).convert_alpha()

        # 外框
        pg.draw.rect(minimap, (255, 255, 255), minimap.get_rect(), 2)

        self.map_img = minimap
        self._cache[map_key] = minimap

    def draw(self, screen, player_pos, camera_rect=None):
        if self.map_img is None:
            return

        x, y = self.pos
        screen.blit(self.map_img, (x, y))

        mw, mh = self.size
        ww, wh = self.world_size

        # ===== 玩家紅點 =====
        px = x + int(player_pos[0] / ww * mw)
        py = y + int(player_pos[1] / wh * mh)
        pg.draw.circle(screen, (255, 0, 0), (px, py), 4)

        # ===== 視角框（藍色）=====
        if camera_rect:
            rx = x + int(camera_rect.x / ww * mw)
            ry = y + int(camera_rect.y / wh * mh)
            rw = max(2, int(camera_rect.width / ww * mw))
            rh = max(2, int(camera_rect.height / wh * mh))
            pg.draw.rect(
                screen,
                (0, 200, 255),
                pg.Rect(rx, ry, rw, rh),
                2
            )
