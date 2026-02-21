import logging
import os
import ssl
import threading

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class MQTTClient:
    def __init__(
        self,
        broker="localhost",
        port=1883,
        client_id="chat_client",
        username=None,
        password=None,
        use_tls=False,
        tls_ca_certs=None,
        tls_insecure=False,
    ):
        self.broker = broker
        self.port = int(port)
        self.client_id = client_id
        self.username = username
        self.password = password
        self.use_tls = bool(use_tls)
        self.tls_ca_certs = str(tls_ca_certs or "").strip()
        self.tls_insecure = bool(tls_insecure)

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id)

        # External callbacks (kept backward compatible)
        self.on_message_received = None
        self.on_connection_status_change = None

        self.publish_topic = None
        self.subscribe_topics = set()
        self.is_connected = False
        self._connected_evt = threading.Event()
        self._lock = threading.RLock()
        self._closing = False
        self.last_error = ""

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)

        # Automatic reconnect backoff.
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)

    def _configure_tls(self):
        tls_version = getattr(ssl, "PROTOCOL_TLS_CLIENT", ssl.PROTOCOL_TLS)
        tls_kwargs = {"tls_version": tls_version}
        if self.tls_ca_certs:
            if not os.path.isfile(self.tls_ca_certs):
                raise FileNotFoundError(f"CA cert file not found: {self.tls_ca_certs}")
            tls_kwargs["ca_certs"] = self.tls_ca_certs
        self.client.tls_set(**tls_kwargs)
        self.client.tls_insecure_set(self.tls_insecure)

    def _safe_status_cb(self, ok: bool, detail: str | None = None):
        cb = self.on_connection_status_change
        if cb:
            try:
                cb(ok, detail)
            except TypeError:
                # Compatibility for older callback signature: cb(ok)
                cb(ok)
            except Exception:
                logger.exception("on_connection_status_change callback error")

    def _safe_msg_cb(self, text: str):
        cb = self.on_message_received
        if cb:
            try:
                cb(text)
            except Exception:
                logger.exception("on_message_received callback error")

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            with self._lock:
                self.is_connected = True
                self._connected_evt.set()
                subscribe_topics = tuple(sorted(self.subscribe_topics))
                self.last_error = ""

            logger.info("Connected to MQTT broker: %s:%s (tls=%s)", self.broker, self.port, self.use_tls)
            self._safe_status_cb(True, "")

            if subscribe_topics:
                self._subscribe_topics(subscribe_topics)
        else:
            detail = f"Connection failed, reason code: {reason_code}"
            logger.warning("Connection failed with reason code %s", reason_code)
            with self._lock:
                self.is_connected = False
                self._connected_evt.clear()
                self.last_error = detail
            self._safe_status_cb(False, detail)

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        with self._lock:
            self.is_connected = False
            self._connected_evt.clear()
            closing = self._closing

        logger.info(
            "Disconnected from MQTT broker: %s:%s (tls=%s, reason=%s)",
            self.broker,
            self.port,
            self.use_tls,
            reason_code,
        )

        if not closing:
            detail = f"Disconnected, reason code: {reason_code}"
            with self._lock:
                self.last_error = detail
            self._safe_status_cb(False, detail)

    def _on_message(self, client, userdata, message):
        try:
            text = message.payload.decode("utf-8", errors="replace")
        except Exception:
            text = str(message.payload)
        self._safe_msg_cb(text)

    @staticmethod
    def _normalize_topic(topic):
        return str(topic or "").strip()

    def _normalize_topics(self, topics):
        if topics is None:
            return set()
        if isinstance(topics, str):
            normalized = self._normalize_topic(topics)
            return {normalized} if normalized else set()
        result = set()
        for item in topics:
            normalized = self._normalize_topic(item)
            if normalized:
                result.add(normalized)
        return result

    def _subscribe_topics(self, topics):
        for topic in topics:
            try:
                result, mid = self.client.subscribe((topic, 0))
                if result != mqtt.MQTT_ERR_SUCCESS:
                    logger.warning("Subscribe failed topic=%s rc=%s mid=%s", topic, result, mid)
            except Exception:
                logger.exception("Subscribe failed topic=%s", topic)

    def _unsubscribe_topics(self, topics):
        for topic in topics:
            try:
                result, mid = self.client.unsubscribe(topic)
                if result != mqtt.MQTT_ERR_SUCCESS:
                    logger.warning("Unsubscribe failed topic=%s rc=%s mid=%s", topic, result, mid)
            except Exception:
                logger.exception("Unsubscribe failed topic=%s", topic)

    def connect(self, publish_topic, subscribe_topics=None):
        """Connect to MQTT broker and bind publish topic + subscription window."""
        normalized_publish = self._normalize_topic(publish_topic)
        if not normalized_publish:
            detail = "Publish topic cannot be empty"
            with self._lock:
                self.last_error = detail
            self._safe_status_cb(False, detail)
            return False

        normalized_subscribe = self._normalize_topics(subscribe_topics)
        if not normalized_subscribe:
            normalized_subscribe = {normalized_publish}

        with self._lock:
            self.publish_topic = normalized_publish
            self.subscribe_topics = set(normalized_subscribe)
            self._closing = False
            self._connected_evt.clear()

        try:
            if self.use_tls:
                self._configure_tls()
            self.client.connect_async(self.broker, self.port, keepalive=60)
            self.client.loop_start()
            with self._lock:
                self.last_error = ""
            return True
        except Exception as e:
            logger.exception("Connection error: %s", e)
            detail = f"Connection init failed: {e}"
            with self._lock:
                self.last_error = detail
            self._safe_status_cb(False, detail)
            return False

    def send_message(self, message):
        """Send message to publish topic."""
        if not message:
            return

        with self._lock:
            if not (self.is_connected and self.publish_topic) or self._closing:
                return
            topic = self.publish_topic

        try:
            info = self.client.publish(topic, payload=message, qos=0, retain=False)
            if info.rc != mqtt.MQTT_ERR_SUCCESS:
                logger.warning("Publish failed rc=%s", info.rc)
        except Exception as e:
            logger.exception("Failed to send message: %s", e)
            with self._lock:
                self.last_error = f"Send message failed: {e}"
            self.close()

    def set_publish_topic(self, topic):
        """Update publish topic dynamically."""
        normalized = self._normalize_topic(topic)
        if not normalized:
            return
        with self._lock:
            self.publish_topic = normalized

    def set_publish_group(self, group):
        """Backward compatible alias for older call sites."""
        self.set_publish_topic(group)

    def replace_subscriptions(self, topics):
        """Replace subscription window; applies diff when connected."""
        normalized = self._normalize_topics(topics)
        with self._lock:
            old_topics = set(self.subscribe_topics)
            self.subscribe_topics = set(normalized)
            connected = self.is_connected and (not self._closing)

        if not connected:
            return

        to_sub = sorted(normalized - old_topics)
        to_unsub = sorted(old_topics - normalized)
        if to_sub:
            self._subscribe_topics(to_sub)
        if to_unsub:
            self._unsubscribe_topics(to_unsub)

    def close(self):
        """Close MQTT connection."""
        with self._lock:
            if self._closing:
                return
            self._closing = True

        try:
            try:
                self.client.loop_stop(force=False)
            except TypeError:
                self.client.loop_stop()
            self.client.disconnect()
        except Exception:
            logger.exception("Error while closing MQTT connection")
        finally:
            with self._lock:
                self.is_connected = False
                self._connected_evt.clear()
                self.publish_topic = None
                self.subscribe_topics = set()
            logger.info("MQTT connection closed.")
            self._safe_status_cb(False, "Connection closed")

    def heartbeat(self):
        """Optional heartbeat packet."""
        try:
            self.send_message("HEARTBEAT")
        except Exception as e:
            logger.exception("Heartbeat error: %s", e)
