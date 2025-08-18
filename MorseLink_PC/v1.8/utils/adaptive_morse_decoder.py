from collections import deque
import math
import numpy as np

class AdaptiveMorseDecoder:
    VERSION = "1.2"

    def __init__(self, initial_wpm=20, learning_window=100, sensitivity=0.3):
        """
        初始化动态解码器
        
        参数：
            initial_wpm: 初始词速（词/分钟）
            learning_window: 学习窗口大小（样本数）
            sensitivity: 学习率敏感度 (0.1~0.9)
        """
        self.wpm = initial_wpm
        self.learning_window = learning_window
        self.sensitivity = np.clip(sensitivity, 0.1, 0.9)
        
        # 初始化状态
        self._reset_to_defaults()
        
        # 初始化概率分布
        self._initialize_distributions()

    def _reset_to_defaults(self):
        """重置为默认状态"""
        self.history = deque(maxlen=self.learning_window)
        # 根据词速（WPM）计算点持续时间：1200ms / WPM，基于摩尔斯电码标准（1 WPM = 1200ms/单位时间）
        self.dot_duration = 1200 / self.wpm
        self.dash_threshold = 3 * self.dot_duration
        self.learning_coefficient = 0.7
        self.speed_profile = {
            'current': self.wpm,
            'min': self.wpm * 0.5,
            'max': self.wpm * 2.0
        }

    def _initialize_distributions(self):
        """初始化概率分布模型"""
        self.dot_dist = NormalDistribution(
            loc=self.dot_duration, 
            scale=self.dot_duration * 0.3
        )
        self.dash_dist = NormalDistribution(
            loc=self.dash_threshold,
            scale=self.dash_threshold * 0.2
        )

    def process_duration(self, duration):
        """
        处理单个持续时间样本
        
        返回：(字符, 置信度)
        """
        if len(self.history) >= 10:  # 初始缓冲期后开始学习
            self._adapt_thresholds()
            self._update_speed_profile()
        
        # 数据预处理
        filtered = self._filter_outliers(duration)
        
        # 保存到历史
        self.history.append(filtered)
        
        # 实时解码
        return self._classify_with_confidence(filtered)

    def _filter_outliers(self, duration):
        """异常值过滤"""
        if len(self.history) < 5:
            return duration
            
        median = np.median(self.history)
        mad = np.median(np.abs(self.history - median))
        
        # 使用MAD进行鲁棒过滤
        if abs(duration - median) > 3 * mad:
            return np.clip(duration, median-2*mad, median+2*mad)
        return duration

    def _adapt_thresholds(self):
        """自适应调整阈值"""
        recent_weights = np.exp(np.linspace(0, 1, len(self.history)))
        recent_weights /= recent_weights.sum()
        
        weighted_mean = np.average(list(self.history), weights=recent_weights)
        
        # 动态学习率调整
        learning_rate = self.sensitivity * (1 - np.exp(-len(self.history)/self.learning_window))
        
        # 更新点持续时间
        self.dot_duration = (self.learning_coefficient * self.dot_duration + 
                            (1 - self.learning_coefficient) * weighted_mean)
        
        # 更新划阈值（包含惯性因子）
        self.dash_threshold = (3 * self.dot_duration * 0.6 + 
                              self.dash_threshold * 0.4)
        
        # 更新概率分布
        self._initialize_distributions()

    def _update_speed_profile(self):
        """更新用户速度特征"""
        current_wpm = 1200 / self.dot_duration
        self.speed_profile['current'] = current_wpm
        self.speed_profile['min'] = min(self.speed_profile['min'], current_wpm)
        self.speed_profile['max'] = max(self.speed_profile['max'], current_wpm)

    def _classify_with_confidence(self, duration):
        """带置信度的分类"""
        dot_prob = self.dot_dist.pdf(duration)
        dash_prob = self.dash_dist.pdf(duration)
        
        total = dot_prob + dash_prob
        if total == 0:
            return ('?', 0.0)
        
        confidence = max(dot_prob, dash_prob) / total
        threshold = self.dot_duration * 2.5  # 优化分类边界
        
        if duration < threshold:
            return ('.', confidence)
        else:
            return ('-', confidence)

    def reset_learning(self):
        """重置学习状态"""
        self._reset_to_defaults()
        self._initialize_distributions()

    def get_performance_metrics(self):
        """获取系统性能指标"""
        return {
            'learning_progress': len(self.history)/self.learning_window,
            'current_speed_wpm': round(1200 / self.dot_duration, 1),
            'adaptation_factor': self._calculate_adaptation(),
            'classification_accuracy': self._estimate_accuracy()
        }

    def _calculate_adaptation(self):
        """计算系统适应度"""
        if len(self.history) < 2:
            return 0.0
        diffs = np.diff(list(self.history))
        return np.mean(np.abs(diffs)) / np.mean(self.history)

    def _estimate_accuracy(self):
        """估计分类准确率"""
        if len(self.history) < 20:
            return 0.0
            
        dot_samples = [d for d in self.history if d < self.dash_threshold]
        dash_samples = [d for d in self.history if d >= self.dash_threshold]
        
        dot_consistency = np.std(dot_samples)/np.mean(dot_samples) if dot_samples else 1.0
        dash_consistency = np.std(dash_samples)/np.mean(dash_samples) if dash_samples else 1.0
        
        return 1.0 - (0.7*min(dot_consistency, 0.5) + 0.3*min(dash_consistency, 0.5))


class NormalDistribution:
    """完全模拟 scipy.stats.norm 的接口"""
    def __init__(self, loc, scale):
        self.loc = loc
        self.scale = scale
    
    def pdf(self, x):
        """概率密度函数（与scipy计算结果一致）"""
        # 使用 NumPy 版本（推荐）
        return np.exp(-0.5*((x - self.loc)/self.scale)**2) / (self.scale * np.sqrt(2*np.pi))
        
        # 或纯Python版本（无依赖）
        # exponent = -0.5 * ((x - self.loc)/self.scale)**2
        # return math.exp(exponent) / (self.scale * math.sqrt(2 * math.pi))
    
    def cdf(self, x):
        """累积分布函数"""
        return 0.5 * (1 + math.erf((x - self.loc)/(self.scale * math.sqrt(2))))