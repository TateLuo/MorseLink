import json
import base64
import urllib.request
import urllib.error
import logging
from PyQt5.QtCore import QThread, pyqtSignal

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class MQTTQueryTool:
    """
    MQTT 查询工具模块，支持 Basic 认证和动态 API 路径。
    """

    def __init__(self, username, password):
        """
        初始化工具模块。
        :param username: API 用户名
        :param password: API 密码
        """
        self.username = username
        self.password = password
        self.auth_header = self._generate_auth_header()

    def _generate_auth_header(self):
        """生成 Basic 认证头"""
        auth_str = f"{self.username}:{self.password}"
        encoded_auth = base64.b64encode(auth_str.encode()).decode()
        return f"Basic {encoded_auth}"

    def query(self, url, port, api_path="/api/v5/clients"):
        """
        查询 MQTT 信息。
        :param url: 服务器地址（如 'http://localhost'）
        :param port: 服务器端口（如 18083）
        :param api_path: API 路径，默认为 '/api/v5/clients'
        :return: 返回解析后的 JSON 数据或错误信息。
        """
        api_url = f"{url}:{port}{api_path}"
        logger.info(f"Querying API: {api_url}")

        try:
            # 创建请求对象
            req = urllib.request.Request(api_url)
            req.add_header("Content-Type", "application/json")
            req.add_header("Authorization", self.auth_header)

            # 发送请求并处理响应
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                logger.info("API query successful")
                return data

        except urllib.error.HTTPError as e:
            error_msg = f"HTTP Error: {e.code} - {e.reason}"
            logger.error(error_msg)
            return {"error": error_msg}
        except urllib.error.URLError as e:
            error_msg = f"URL Error: {e.reason}"
            logger.error(error_msg)
            return {"error": error_msg}
        except Exception as e:
            error_msg = f"Unexpected Exception: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

class AsyncMQTTQueryTool(QThread):
    """
    异步查询工具类，继承自 QThread，用于在后台执行查询操作。
    """

    # 定义一个信号，用于将查询结果传递回主线程
    data_fetched = pyqtSignal(dict)  # 传递字典格式的 JSON 数据

    def __init__(self, url, port, api_path="/api/v5/clients", username="", password=""):
        """
        初始化异步查询工具。
        :param url: 服务器地址（如 'http://localhost'）
        :param port: 服务器端口（如 18083）
        :param api_path: API 路径，默认为 '/api/v5/clients'
        :param username: API 用户名
        :param password: API 密码
        """
        super().__init__()
        self.url = url
        self.port = port
        self.api_path = api_path
        self.username = username
        self.password = password
        self.tool = MQTTQueryTool(username, password)

    def run(self):
        """
        线程运行方法，执行查询操作并发射信号。
        """
        result = self.tool.query(self.url, self.port, self.api_path)
        self.data_fetched.emit(result)