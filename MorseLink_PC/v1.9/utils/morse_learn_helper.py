import random, sys, string

from PySide6.QtCore import QCoreApplication


def _tr(text: str) -> str:
    return QCoreApplication.translate("MorseLearnHelper", text)


class MorseLearnHelper():
    
    def __init__(self):
        pass

    def generate_random_data(self, data, data_type, core_elements, core_weight, min_word_length=4, max_word_length=6, min_groups=3, max_groups=5):
        """
        根据输入的数据和数据类型生成随机数据。

        :param data: 输入的数据数组（字母数组或其他元素数组）
        :param data_type: 数据类型 ('letter' 或 'other')
        :param core_elements: 核心元素数组，必须存在于 data 数组中
        :param core_weight: 核心元素在生成时的比重（0到1之间的值）
        :param min_word_length: 生成单词的最小长度（仅适用于 'letters' 类型）
        :param max_word_length: 生成单词的最大长度（仅适用于 'letters' 类型）
        :param min_groups: 生成的组的最小数量
        :param max_groups: 生成的组的最大数量
        :return: 随机生成的单词或元素
        """
        # 确保参数是整数
        if not all(isinstance(x, int) for x in [min_word_length, max_word_length, min_groups, max_groups]):
            raise ValueError(_tr("所有长度和组数参数必须是整数"))

        if data_type == 'letter':
            # 生成随机长度的多个单词
            def generate_words():
                num_groups = random.randint(min_groups, max_groups)
                words = []
                for _ in range(num_groups):
                    word_length = random.randint(min_word_length, max_word_length)  # 随机单词长度
                    # 计算核心元素的数量
                    core_count = max(1, int(word_length * core_weight))  # 核心元素数量
                    other_count = word_length - core_count
                    
                    # 随机选择核心元素和其他元素
                    selected_core = random.choices(core_elements, k=core_count)
                    selected_other = random.choices(data, k=other_count)
                    
                    # 合并并打乱顺序
                    word = selected_core + selected_other
                    random.shuffle(word)
                    words.append(''.join(word))
                return ' '.join(words)

            return generate_words()
        else:
            # 从其他元素中随机选择，核心占比由 core_weight 控制
            def select_other_elements():
                num_items = random.randint(min_groups, max_groups)
                weight = max(0.0, min(1.0, float(core_weight)))
                core_count = max(1, int(num_items * weight))
                other_count = num_items - core_count
                
                selected_items = random.choices(core_elements, k=core_count)  # 添加核心元素
                selected_items += random.choices(data, k=other_count)  # 添加其他元素
                random.shuffle(selected_items)  # 打乱顺序
                return ' '.join(selected_items)

            return select_other_elements()
