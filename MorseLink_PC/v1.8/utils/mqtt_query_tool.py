import json
import base64
import urllib.request
import urllib.error
import logging
from PyQt5.QtCore import QThread, pyqtSignal
from utils.config_manager import ConfigManager


# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class MQTTOnlineCounter:
    """
    专门用于获取 MQTT 在线用户计数的工具
    API 固定地址：http://服务器ip：服务器端口/api/mqtt/online-users
    """

    # 初始化配置文件管理器
    config_manager = ConfigManager()
    
    url = config_manager.get_server_url()  # 获取服务器地址
    
    API_URL = f"http://{url}:5000/api/mqtt/online-users"
    
    def __init__(self, username="admin", password="public"):
        """
        初始化计数器
        :param username: API 用户名，默认 "admin"
        :param password: API 密码，默认 "public"
        """
        self.auth_header = self._generate_auth_header(username, password)
    
    def _generate_auth_header(self, username, password):
        """生成 Basic 认证头"""
        auth_str = f"{username}:{password}"
        return "Basic " + base64.b64encode(auth_str.encode()).decode()
    
    def get_online_count(self):
        """
        获取 MQTT 在线用户数量
        
        :return: 成功时返回整数在线用户数，失败时返回-1
        """
        logger.info(f"Requesting online users from: {self.API_URL}")
        
        try:
            # 创建请求对象
            req = urllib.request.Request(self.API_URL)
            req.add_header("Authorization", self.auth_header)
            
            # 发送请求并处理响应
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                
                # 直接从响应中提取count值
                count = data.get("count", -1)
                
                if count >= 0:
                    logger.info(f"Success! Online users: {count}")
                    return count
                else:
                    logger.warning("Response missing 'count' field")
                    return -1
        
        except urllib.error.HTTPError as e:
            logger.error(f"HTTP Error {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            logger.error(f"Network Error: {e.reason}")
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON response")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
        
        return -1


class AsyncOnlineCounter(QThread):
    """
    异步获取在线用户计数的线程
    """
    
    # 定义信号：传递整数类型的在线用户数量
    count_received = pyqtSignal(int)  # 成功时传递正数，失败时传递-1
    
    def __init__(self, username="admin", password="public"):
        super().__init__()
        self.counter = MQTTOnlineCounter(username, password)
    
    def run(self):
        """
        线程运行方法，执行计数操作并发射信号
        """
        count = self.counter.get_online_count()
        self.count_received.emit(count)


# 使用示例
if __name__ == "__main__":
    # 同步使用示例
    print("--- 同步获取测试 ---")
    counter = MQTTOnlineCounter()
    count = counter.get_online_count()
    print(f"当前在线用户数: {'获取失败' if count < 0 else count}")
    