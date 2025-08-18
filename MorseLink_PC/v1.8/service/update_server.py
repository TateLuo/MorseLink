from flask import Flask, jsonify, request, send_from_directory
import json
import os
import logging
from threading import Lock

app = Flask(__name__)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 存储在线客户端和线程锁
online_clients = set()
client_lock = Lock()

# 存储文件路径
VERSION_FILE = 'version_info.json'
DATABASE_FILE = 'database.db'
NEW_VERSION_FILE = 'morselink.exe'

# 加载版本信息
def load_version_info():
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'version': '1.3.0',
        'downloadurl': 'http://example.com/download',
        'announcement': '欢迎使用我们的应用程序！',
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

@app.route('/api/mqtt/webhook', methods=['POST'])
def mqtt_webhook():
    """处理MQTT连接事件（核心逻辑版）"""
    try:
        data = request.get_json()
        
        # 基础验证
        if not data:
            logger.warning("收到空请求")
            return jsonify({"error": "Empty request body"}), 400
        
        event = data.get('event')
        clientid = data.get('clientid')

        # 强制字段校验
        if not event or not clientid:
            missing = []
            if not event: missing.append("event")
            if not clientid: missing.append("clientid")
            logger.error(f"缺少必要字段: {missing}")
            return jsonify({"error": f"Missing fields: {missing}"}), 400

        # 处理事件
        with client_lock:
            if event == "client.connected":
                online_clients.add(clientid)
                logger.info(f"[连接] 客户端: {clientid} | 当前在线: {len(online_clients)}")
                
            elif event == "client.disconnected":
                if clientid in online_clients:
                    online_clients.remove(clientid)
                logger.info(f"[断开] 客户端: {clientid} | 剩余在线: {len(online_clients)}")
                
            else:
                logger.warning(f"未知事件类型: {event}")
                return jsonify({"error": "Invalid event type"}), 400

        return jsonify({
            "status": "success",
            "clientid": clientid,
            "online_count": len(online_clients)
        }), 200

    except Exception as e:
        logger.error(f"处理失败: {str(e)}")
        return jsonify({"error": "Server error"}), 500

@app.route('/api/mqtt/online-users', methods=['GET'])
def get_online_users():
    """获取当前在线用户数量"""
    with client_lock:
        return jsonify({
            "count": len(online_clients)  # 仅返回数量字段
        }), 200
        
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
