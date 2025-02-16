from lxml import etree
import re

def extract_sources(ts_file, output_file):
    # 解析 .ts 文件
    tree = etree.parse(ts_file)
    messages = tree.findall('.//message')

    # 提取源文本，并确保每个源文本单独占一行
    source_texts = []
    for msg in messages:
        source = msg.find('source')
        if source is not None and source.text:
            # 替换换行符为通配符（例如用空格或其他字符替代）
            cleaned_text = re.sub(r'\s+', ' ', source.text.strip())  # 用空格替代多个空白字符
            source_texts.append(cleaned_text)

    # 将源文本写入输出文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(source_texts))  # 每个文本之间用换行符分隔

# 示例使用
extract_sources('en.ts', 'output.txt')
