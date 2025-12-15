import pygame as pg
from src.utils import load_sound, GameSettings

class SoundManager:
    def __init__(self):
        pg.mixer.init()
        pg.mixer.set_num_channels(GameSettings.MAX_CHANNELS)
        self.current_bgm = None
        
    def play_bgm(self, filepath: str):
        if self.current_bgm:
            self.current_bgm.stop()
        audio = load_sound(filepath)
        if GameSettings.MUTE_BGM:
            volume=0.0
        else:
            volume=GameSettings.AUDIO_VOLUME

        audio.set_volume(volume)
        audio.play(-1)
        self.current_bgm = audio
        
    def pause_all(self):
        pg.mixer.pause()

    def resume_all(self):
        pg.mixer.unpause()
        
    def play_sound(self, filepath, volume=0.7):
        sound = load_sound(filepath)
        sound.set_volume(volume)
        sound.play()

    def stop_all_sounds(self):
        pg.mixer.stop()
        self.current_bgm = None

    def set_bgm_volume(self, volume: float):
        volume = max(0.0, min(1.0, volume))
        GameSettings.AUDIO_VOLUME = volume   

        if self.current_bgm is not None:
            self.current_bgm.set_volume(volume)        