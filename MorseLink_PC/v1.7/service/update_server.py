from flask import Flask, jsonify, request, send_from_directory
import json
import os

app = Flask(__name__)

# 存储文件路径
VERSION_FILE = 'version_info.json'
DATABASE_FILE = 'database.db'  # 数据库文件路径
NEW_VERSION_FILE = 'morselink.exe' #用于更新的最新版本

# 加载版本信息
def load_version_info():
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'version': '1.3.0',
        'downloadurl': 'http://example.com/download',
        'announcement': '欢迎使用我的应用程序！',
        'is_update_available': False,
        'show_announcement': True
    }

# 保存版本信息
def save_version_info(version_info):
    with open(VERSION_FILE, 'w', encoding='utf-8') as f:
        json.dump(version_info, f, ensure_ascii=False, indent=4)

# 初始化版本信息
version_info = load_version_info()

@app.route('/version', methods=['GET'])
def get_version_info():
    """获取当前版本信息、公告和更新状态"""
    return jsonify(version_info)

@app.route('/version', methods=['POST'])
def update_version_info():
    """更新版本信息、公告和更新状态"""
    data = request.json
    if 'version' in data and data['version']:
        version_info['version'] = data['version']
    if 'downloadurl' in data and data['downloadurl']:
        version_info['downloadurl'] = data['downloadurl']
    if 'announcement' in data and data['announcement']:
        version_info['announcement'] = data['announcement']
    if 'is_update_available' in data:
        version_info['is_update_available'] = data['is_update_available']
    if 'show_announcement' in data:
        version_info['show_announcement'] = data['show_announcement']
    
    save_version_info(version_info)
    return jsonify({'message': '版本信息、公告和更新状态更新成功'}), 200

@app.route('/download/database', methods=['GET'])
def download_database():
    """下载数据库文件"""
    return send_from_directory(directory='.', path=DATABASE_FILE, as_attachment=True)

@app.route('/download/newVersion', methods=['GET'])
def download_new_version_file():
    """下载新版本文件"""
    return send_from_directory(directory='.', path=NEW_VERSION_FILE, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
