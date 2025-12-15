import pygame as pg
from src.utils import load_img


class BattleAnimation:
    def __init__(
        self,
        sheet_path: str,
        frame_w: int,
        frame_h: int,
        frame_count: int,
        *,
        scale_to: tuple[int, int] | None = None,
        flip_x: bool = False,
        fps: float = 6.0,
    ) -> None:
        """
        從一張橫向 spritesheet 切出 frame_count 張圖，然後依 fps 播放。
        這裡假設你的 idle 圖是：4 格橫排，每格 96x96。
        """
        self.frames: list[pg.Surface] = []
        self.frame_index: int = 0
        self.frame_time: float = 1.0 / fps
        self.time_acc: float = 0.0

        sheet = load_img(sheet_path)

        for i in range(frame_count):
            rect = pg.Rect(i * frame_w, 0, frame_w, frame_h)
            frame = sheet.subsurface(rect).copy()
            if scale_to is not None:
                frame = pg.transform.scale(frame, scale_to)
            if flip_x:
                frame = pg.transform.flip(frame, True, False)
            self.frames.append(frame)

        if not self.frames:
            raise ValueError(f"SimpleAnim: no frames from {sheet_path}")
        
    def reset(self) -> None:
        self.frame_index = 0
        self.time_acc = 0.0

    def update(self, dt: float) -> None:
        self.time_acc += dt
        while self.time_acc >= self.frame_time:
            self.time_acc -= self.frame_time
            self.frame_index = (self.frame_index + 1) % len(self.frames)

    def get_image(self) -> pg.Surface:
        return self.frames[self.frame_index]