class MorseCodeTranslator:
    # 摩尔斯电码字典
    morse_code_dict = {
        # 字母（A-Z）
        '.-': 'A', '-...': 'B', '-.-.': 'C', '-..': 'D', '.': 'E', '..-.': 'F',
        '--.': 'G', '....': 'H', '..': 'I', '.---': 'J', '-.-': 'K',
        '.-..': 'L', '--': 'M', '-.': 'N', '---': 'O', '.--.': 'P',
        '--.-': 'Q', '.-.': 'R', '...': 'S', '-': 'T', '..-': 'U',
        '...-': 'V', '.--': 'W', '-..-': 'X', '-.--': 'Y', '--..': 'Z',

        # 数字（0-9）
        '-----': '0', '.----': '1', '..---': '2', '...--': '3', '....-': '4',
        '.....': '5', '-....': '6', '--...': '7', '---..': '8', '----.': '9',

        # 标点与常用符号
        '.-.-.-': '.', '--..--': ',', '..--..': '?', '.----.': "'", '-.-.--': '!',
        '-..-.': '/', '-.--.': '(', '-.--.-': ')', '.-...': '&', '---...': ':',
        '-.-.-.': ';', '-...-': '=', '.-..-.': '"', '...-..-': '$', '.--.-.': '@',
        '..--.-': '_',   # 下划线
        '.-.-..': '¶',   # 段落符号
        '...-.-': '[END]',  # 结束传输
        '-.-.-': '[START]',  # 开始传输（已修复之前的重复）

        # 新增短横线符号（非标准扩展）
        '-....-': '-',  # 唯一新增项

        # 特殊处理
        '........': '�',  # 错误指示符
        '///': ' ',       # 单词分隔符

        # 非标准扩展（其他）
        '-.-..': '¿',    # 西班牙语倒问号
        '--.-.': '¡',    # 西班牙语倒叹号
    }

    def __init__(self):
        pass  # 暂不需要

    # 只翻译单词
    def letter_to_morse(self, morse_code):
        return self.morse_code_dict.get(morse_code, '未知') 

    # 翻译句子
    def morse_to_text(self, morse_code):
        # 去掉末尾的 '///'（如果存在）
        if morse_code.endswith('///'):
            morse_code = morse_code[:-3]

        # 按照 '///' 分隔单词
        words = morse_code.split('///')
        decoded_message = []

        for word in words:
            if word:  # 确保word不为空
                letters = word.split('/')
                decoded_word = ''.join(self.morse_code_dict.get(letter, '未知') for letter in letters if letter)
                decoded_message.append(decoded_word)

        return ' '.join(decoded_message)

    
    # 加密字符串为摩尔斯代码
    def text_to_morse(self, text):
        # 将每个字符转换为摩尔斯代码，并用 '/' 分隔字母，'///' 分隔单词
        morse_message = []
        for word in text.upper().split():
            morse_word = []
            for char in word:
                # 仅在字符在字典中时才添加摩尔斯码
                for morse, letter in self.morse_code_dict.items():
                    if letter == char:
                        morse_word.append(morse)
                        break
            if morse_word:  # 仅在摩尔斯字串非空时才添加
                morse_message.append('/'.join(morse_word))
        
        return '///'.join(morse_message)

    
    # 将字母翻译回摩尔斯码
    def letter_to_morse_code(self, letter):
        for code, char in self.morse_code_dict.items():
            if char == letter.upper():
                return code
        return '未知'

