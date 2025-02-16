import paho.mqtt.client as mqtt
import threading
import time

class MQTTClient:
    def __init__(self, broker='localhost', port=1883, client_id="chat_client", username=None, password=None):
        self.broker = broker
        self.port = port
        self.client_id = client_id
        self.username = username
        self.password = password
        # 使用 CallbackAPIVersion.VERSION2 创建客户端
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id)
        self.is_connected = False
        self.on_message_received = None  # 消息接收回调函数
        self.on_connection_status_change = None  # 连接状态变化回调函数
        self.group = None  # 用于存储组名（MQTT 主题）

        # 设置 MQTT 回调函数
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        # 设置用户名和密码
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        """MQTT 连接成功时的回调函数"""
        if reason_code == 0:
            print(f"Connected to MQTT Broker: {self.broker}:{self.port}")
            self.is_connected = True
            if self.on_connection_status_change:
                self.on_connection_status_change(True)  # 调用连接成功的回调
            if self.group:
                self.client.subscribe(self.group)  # 订阅组（主题）
        else:
            print(f"Connection failed with reason code {reason_code}")
            if self.on_connection_status_change:
                self.on_connection_status_change(False)  # 调用连接失败的回调

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        """MQTT 断开连接时的回调函数"""
        print(f"Disconnected from MQTT Broker: {self.broker}:{self.port}")
        self.is_connected = False
        if self.on_connection_status_change:
            self.on_connection_status_change(False)  # 调用连接断开的回调

    def _on_message(self, client, userdata, message):
        """接收到消息时的回调函数"""
        if self.on_message_received:
            self.on_message_received(message.payload.decode())  # 调用消息接收回调

    def connect(self, group):
        """连接到 MQTT Broker 并订阅组（主题）"""
        self.group = group
        try:
            self.client.connect(self.broker, self.port, keepalive=60)  # 连接 Broker
            self.client.loop_start()  # 启动网络循环（非阻塞）
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            if self.on_connection_status_change:
                self.on_connection_status_change(False)  # 调用连接失败的回调
            return False

    def send_message(self, message):
        """发送消息到组（主题）"""
        if self.is_connected and self.group and message:
            try:
                self.client.publish(self.group, message)  # 发布消息到主题
            except Exception as e:
                print(f"Failed to send message: {e}")
                self.close()

    def close(self):
        """关闭 MQTT 连接"""
        if self.is_connected:
            self.client.loop_stop()  # 停止网络循环
            self.client.disconnect()  # 断开连接
            self.is_connected = False
            print("MQTT connection closed.")
            if self.on_connection_status_change:
                self.on_connection_status_change(False)  # 调用连接断开的回调

    def heartbeat(self):
        """发送心跳包（可选）"""
        try:
            self.send_message("HEARTBEAT")  # 发送心跳包
        except Exception as e:
            print(f"Heartbeat error: {e}")
            