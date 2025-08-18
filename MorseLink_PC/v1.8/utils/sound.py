import pygame, time
import numpy as np
import threading
from queue import Queue
import logging
from .config_manager import ConfigManager

# 设置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class BuzzerSimulator:
    def __init__(self):
        try:
            configer = ConfigManager()
            self.freq = configer.get_buzz_freq()
            pygame.mixer.init()
            self.sound = self.generate_beep_sound(frequency=self.freq, duration=1)
            self.is_playing = False
            self.play_thread = None
            self.stop_event = threading.Event()
            self.play_queue = Queue()
            self.playback_callback = None  # 播放状态回调
            logging.info("BuzzerSimulator initialized successfully.")
        except Exception as e:
            logging.error(f"Error initializing BuzzerSimulator: {e}")

    def generate_beep_sound(self, frequency=1000, duration=1, sample_rate=44100):
        try:
            t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
            wave = 0.5 * np.sin(2 * np.pi * frequency * t)
            sound_array = (wave * 32767).astype(np.int16)
            sound_array = np.vstack((sound_array, sound_array)).T
            sound_array = np.ascontiguousarray(sound_array)
            return pygame.sndarray.make_sound(sound_array)
        except Exception as e:
            logging.error(f"Error generating beep sound: {e}")

    def start(self, switch):
        if switch and not self.is_playing:
            self.sound.play(-1)
            self.is_playing = True
            #logging.info("Buzzer started.")
            if self.playback_callback:
                self.playback_callback("started")  # 调用回调，传递状态

    def stop(self):
        if self.is_playing:
            self.sound.stop()
            self.is_playing = False
            #logging.info("Buzzer stopped.")
            if self.playback_callback:
                self.playback_callback("stopped")  # 调用回调，传递状态

    def play_for_duration(self, duration, switch, interval=35):
        self.play_queue.put((duration, switch, interval))
        if not self.play_thread or not self.play_thread.is_alive():
            self.play_next()

    def play_next(self):
        if not self.play_queue.empty():
            duration, switch, interval = self.play_queue.get()
            self.stop_event.clear()

            def play_and_wait():
                self.start(switch)
                pygame.time.wait(int(duration))
                if not self.stop_event.is_set():
                    self.stop()
                pygame.time.wait(int(interval))
                self.play_next()

            self.play_thread = threading.Thread(target=play_and_wait)
            self.play_thread.start()

    def stop_play_for_duration(self):
        while not self.play_queue.empty():
            self.play_queue.get()
        self.stop_event.set()
        self.stop()
        logging.info("Stopped play_for_duration.")

    def generate_wave(self, frequency, duration, sample_rate=44100, volume=0.5):
            """生成指定频率和持续时间的波形"""
            t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
            wave = volume * np.sin(2 * np.pi * frequency * t)
            sound_array = (wave * 32767).astype(np.int16)
            sound_array = np.vstack((sound_array, sound_array)).T
            return sound_array

    def generate_silence(self, duration, sample_rate=44100):
        """生成指定持续时间的静音"""
        return np.zeros((int(sample_rate * duration), 2), dtype=np.int16)

    def generate_morse_sound(self, morse_code, dot_duration, dash_duration, char_interval, word_interval):
        """生成摩尔斯码对应的音频数据"""
        sample_rate = 44100
        morse_sound = []
        for symbol in morse_code:
            if symbol == '.':
                morse_sound.append(self.generate_wave(self.freq, dot_duration / 1000, sample_rate))
                morse_sound.append(self.generate_silence(dot_duration / 1000, sample_rate))  # 点后的静音
            elif symbol == '-':
                morse_sound.append(self.generate_wave(self.freq, dash_duration / 1000, sample_rate))
                morse_sound.append(self.generate_silence(dot_duration / 1000, sample_rate))  # 划后的静音
            elif symbol == '/':
                morse_sound.append(self.generate_silence(char_interval / 1000, sample_rate))  # 字符间的静音
            elif symbol == '///':
                morse_sound.append(self.generate_silence(word_interval / 1000, sample_rate))  # 单词间的静音

        if morse_sound:
            return np.concatenate(morse_sound)
        else:
            return np.zeros((0, 2), dtype=np.int16)

    def play_morse_code(self, morse_code, dot_duration, dash_duration, char_interval, word_interval):
        """生成并播放摩尔斯码音频，播放完毕后发送回调，并在播放期间发送进度"""
        try:
            sound_array = self.generate_morse_sound(morse_code, dot_duration, dash_duration, char_interval, word_interval)
            sound_array = np.ascontiguousarray(sound_array)
            self.sound_for_test_listen = pygame.sndarray.make_sound(sound_array)
            total_duration =  self.sound_for_test_listen.get_length()  # 获取音频总时长（秒）

            def check_playback():
                self.sound_for_test_listen.play()
                logging.info("Morse code playback started.")
                if self.playback_callback:
                    self.playback_callback("started")
                #播放状态为真
                self.is_playing = True

                start_time = time.time()
                last_percent = 0
                
                # 循环检测播放状态，发送进度回调
                while pygame.mixer.get_busy():
                    elapsed_time = time.time() - start_time  # 已播放时间
                    current_percent = int((elapsed_time / total_duration) * 100)  # 当前播放百分比

                    if current_percent > last_percent:
                        last_percent = current_percent
                        if self.playback_callback:
                            self.playback_callback(current_percent)

                    pygame.time.wait(100)  # 每100ms检查一次播放状态
                
                # 播放完毕后发送回调状态
                logging.info("Morse code playback finished.")
                if self.playback_callback:
                    self.playback_callback("finished")
                #播放状态为假
                self.is_playing = False

            # 启动一个线程进行播放和检查
            playback_thread = threading.Thread(target=check_playback)
            playback_thread.start()

        except Exception as e:
            logging.error(f"Error playing morse code: {e}")
    
    def stop_playing_morse_code(self):
        """停止播放摩斯电码音频并重置状态"""
        if hasattr(self, 'sound_for_test_listen'):
            self.sound_for_test_listen.stop()  # 停止播放
            logging.info("Morse code playback stopped.")
            if self.playback_callback:
                self.playback_callback("stopped")  # 调用回调，传递状态

    def set_playback_callback(self, callback):
        """设置播放状态回调函数"""
        self.playback_callback = callback


if __name__ == "__main__":
    buzzer = BuzzerSimulator()
    buzzer.play_morse_code(".-/-.../.-..", 100, 300, 200, 600)