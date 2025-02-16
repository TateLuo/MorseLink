import random
import pygame
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QPainter, QImage


class MorseCodeVisualizer(QWidget):
    def __init__(self, num_channels=11, parent=None):
        super().__init__(parent)
        self.num_channels = num_channels  # 通道数量
        self.background_color = (211, 211, 211)
        self.block_color = (0, 0, 0)
        self.speed = 3  # 黑块的移动速度

        # 初始化 Pygame
        pygame.init()
        self.screen = None  # Pygame Surface
        self.channel_blocks = [[] for _ in range(self.num_channels)]  # 每个通道的黑块
        self.channel_generating = [False] * self.num_channels  # 每个通道的生成状态

        # QTimer 控制刷新
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.gameLoop)
        self.timer.start(15)

        self.update_dimensions()

    def update_dimensions(self):
        """更新通道宽度、间隔等参数"""
        self.width = self.size().width()
        self.height = self.size().height()
        self.channel_width = self.width / (2 * self.num_channels - 1)  # 通道宽度
        self.spacing = self.channel_width  # 通道间隔
        self.screen = pygame.Surface((self.width, self.height))  # 重置 Pygame Surface

    def resizeEvent(self, event):
        """窗口大小改变时更新参数"""
        super().resizeEvent(event)
        self.update_dimensions()

    def draw_channel_scale(self):
        """绘制通道刻度尺和中间通道的高亮背景"""
        font = pygame.font.SysFont("Arial", 12)
        scale_color = (0, 0, 0)
        highlight_color = (173, 216, 230)
        line_height = 15

        middle_channel = self.num_channels // 2
        for channel in range(self.num_channels):
            x = channel * 2 * self.channel_width

            if channel == middle_channel:
                highlight_rect = pygame.Rect(x, 0, self.channel_width, line_height)
                pygame.draw.rect(self.screen, highlight_color, highlight_rect)

            pygame.draw.line(self.screen, scale_color, (x, 0), (x, line_height), 2)

            text = font.render(str(channel), True, scale_color)
            text_rect = text.get_rect(center=(x + self.channel_width / 2, line_height + 10))
            #self.screen.blit(text, text_rect)

    def gameLoop(self):
        """主循环，更新和绘制黑块"""
        self.screen.fill(self.background_color)

        self.draw_channel_scale()

        # 更新和绘制黑块
        for channel_idx, channel in enumerate(self.channel_blocks):
            for block in channel[:]:
                block.update(self.speed)
                block.draw(self.screen)
                if block.rect.y > self.height:
                    channel.remove(block)

            # 如果通道正在生成黑块，则添加新黑块
            if self.channel_generating[channel_idx]:
                new_block = BlackBlock(
                    width=self.channel_width,
                    height=3,
                    radius=5,
                    x=channel_idx * 2 * self.channel_width,
                    y=0,
                    color=self.block_color
                )
                channel.append(new_block)

        self.update()

    def paintEvent(self, event):
        """将 Pygame Surface 绘制到 QWidget 上"""
        painter = QPainter(self)
        image = QImage(self.screen.get_buffer().raw, self.width, self.height, QImage.Format_RGB32)
        painter.drawImage(0, 0, image)

    def start_generating(self, channel):
        """开始生成黑块"""
        if 0 <= channel < self.num_channels:
            self.channel_generating[channel] = True

    def stop_generating(self, channel):
        """停止生成黑块"""
        if 0 <= channel < self.num_channels:
            self.channel_generating[channel] = False

    def generate_blocks(self, channel_idx = 5, count = 1, height=3, radius=0):
        """在指定通道，生成指定长度的黑块，且启用碰撞检测"""
        if 0 <= channel_idx < self.num_channels:
            # 获取指定通道的黑块列表
            channel = self.channel_blocks[channel_idx]

            # 生成指定数量的黑块
            for _ in range(count):
                new_block = BlackBlock(
                    width=self.channel_width,
                    height=height,
                    radius=radius,
                    x=channel_idx * 2 * self.channel_width,
                    y=0,
                    color=self.block_color
                )

                # 检查是否可以放置，避免与现有方块重叠
                if not self.can_place_block(channel, new_block):
                    # 如果不可以放置，移动现有方块以便有空间
                    self.move_blocks_down(channel, height)

                # 将新黑块加入通道
                channel.append(new_block)
                
    def can_place_block(self, channel, new_block):
        """检查新方块是否可以放置，避免与现有方块重叠"""
        for block in channel:
            if block.rect.colliderect(new_block.rect):
                return False
        return True

    def move_blocks_down(self, channel, new_block_height):
        """将现有方块下移以让出位置给新方块"""
        for block in channel:
            block.rect.y += new_block_height




class BlackBlock:
    """黑块类，表示一个移动的黑块"""
    def __init__(self, width, height, radius, x, y, color):
        self.rect = pygame.Rect(x, y, width, height)
        self.radius = radius
        self.color = color

    def draw(self, screen):
        """绘制黑块"""
        pygame.draw.rect(screen, self.color, self.rect, border_radius=self.radius)

    def update(self, speed):
        """更新黑块位置"""
        self.rect.y += speed
