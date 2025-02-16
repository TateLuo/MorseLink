from lxml import etree

def fill_translations(ts_file):
    # 解析 .ts 文件
    tree = etree.parse(ts_file)
    messages = tree.findall('.//message')

    for msg in messages:
        source_text = msg.find('source').text
        translation = msg.find('translation')
        
        # 将源文本填入 translation 字段
        translation.text = source_text

    # 保存修改后的 .ts 文件
    tree.write(ts_file, encoding='utf-8', xml_declaration=True)

# 示例使用
fill_translations('en.ts')
