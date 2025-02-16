from lxml import etree

def update_translations(ts_file, input_file):
    # 解析 .ts 文件
    tree = etree.parse(ts_file)
    messages = tree.findall('.//message')

    # 读取输入文件中的每一行
    with open(input_file, 'r', encoding='utf-8') as f:
        translations = f.readlines()

    # 遍历每个消息，将每行翻译填入 translation 字段
    for msg, translation in zip(messages, translations):
        translation_field = msg.find('translation')
        if translation_field is not None:
            translation_field.text = translation.strip()  # 去掉多余的空白字符

    # 保存修改后的 .ts 文件
    tree.write(ts_file, encoding='utf-8', xml_declaration=True)

# 示例使用
update_translations('zh_CN.ts', 'input.txt')
