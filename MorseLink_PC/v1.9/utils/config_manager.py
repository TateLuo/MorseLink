import json
import logging
import os
from urllib.parse import urlparse

from PySide6.QtCore import QLocale, QSettings


logger = logging.getLogger(__name__)


class ConfigManager:
    def __init__(self, config_file="config.ini", db_dir="resources/config"):
        self.config_file = os.path.join(db_dir, config_file)
        os.makedirs(db_dir, exist_ok=True)
        self.settings = QSettings(self.config_file, QSettings.IniFormat)
        self.initialize_config()
        self._migrate_legacy_server_settings()

    def initialize_config(self):
        """Ensure all required keys exist with sensible defaults."""
        default_language = self._detect_default_language()
        default_values = {
            "Version/current_version": "1.2.0",
            "Version/first_run_status": True,
            "SelfInfo/my_call": "None",
            "SelfInfo/password": "None",
            "Time/dot_time": 110,
            "Time/dash_time": 300,
            "Time/letter_interval_duration_time": 150,
            "Time/word_interval_duration_time": 320,
            # Legacy server keys (kept for backward compatibility)
            "server/url": "117.72.10.141",
            "server/port": 1883,
            "server/customized_url": "117.72.10.141",
            # New server keys
            "server/scheme": "mqtt",
            "server/host": "117.72.10.141",
            "server/active_port": 1883,
            "server/customized_endpoints": "mqtt://117.72.10.141:1883",
            "server/tls_ca_certs": "",
            "server/tls_insecure": True,
            "server/channel_name": 7000,
            "Setting/language": default_language,
            "Setting/buzz_freq": 800,
            "Setting/autokey_status": False,
            "Setting/keyer_mode": "straight",
            "Setting/single_dual_policy": "dah_priority",
            "Setting/paddle_memory_enabled": True,
            "Setting/rx_tx_lock_tail_ms": 800,
            "Setting/keyborad_key": "81,87",
            "Setting/send_buzz_status": True,
            "Setting/receive_buzz_status": True,
            "Setting/translation_visibility": True,
            "Setting/visualizer_visibility": True,
            "Setting/sender_font_size": 15,
            "Auth/type": "plain",
            "Auth/token": "",
            "Decoder/wpm": 20,
            "Decoder/version": "1.0.0",
            "Decoder/dot_duration": 100.0,
            "Decoder/dash_threshold": 200.0,
            "Decoder/speed_profile": json.dumps([]),
            "Decoder/history": json.dumps([]),
        }

        for key, value in default_values.items():
            if not self.settings.contains(key):
                self.set_value(key, value)
        self.settings.sync()

    @staticmethod
    def _detect_default_language() -> str:
        """Pick language for first run from system locale."""
        try:
            locale_name = str(QLocale.system().name() or "").strip().lower()
        except Exception:
            locale_name = ""

        if locale_name.startswith("en"):
            return "en"
        if locale_name.startswith("zh"):
            return "zh"
        return "zh"

    @staticmethod
    def _as_bool(value, default=False):
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        return str(value).strip().lower() in ("true", "1", "yes", "on")

    def get_value(self, key, default=None, value_type=str):
        """Read config value and safely coerce type."""
        try:
            self.settings.sync()
            value = self.settings.value(key, default)
            if value is None:
                return default
            if value_type == bool:
                return self._as_bool(value, default if isinstance(default, bool) else False)
            if value_type == int:
                return int(float(value))
            if value_type == float:
                return float(value)
            if value_type == str:
                return str(value).strip().strip('"').strip("'")
            return value_type(value)
        except Exception as e:
            logger.warning("Failed to read config key %s: %s", key, e)
            return default

    def set_value(self, key, value):
        if value is None:
            value = ""
        self.settings.setValue(key, value)

    def sync(self):
        self.settings.sync()

    @staticmethod
    def _safe_int(value, default):
        try:
            return int(float(value))
        except Exception:
            return default

    @staticmethod
    def _normalize_host_text(host_text: str) -> str:
        return str(host_text or "").strip().strip('"').strip("'")

    @staticmethod
    def _normalize_scheme(scheme: str, default: str = "mqtt") -> str:
        value = str(scheme or "").strip().lower()
        if value in ("mqtt", "mqtts"):
            return value
        return default

    @staticmethod
    def _default_port_for_scheme(scheme: str) -> int:
        return 8883 if str(scheme).lower() == "mqtts" else 1883

    def _parse_server_endpoint(
        self,
        raw_value: str,
        default_scheme: str = "mqtt",
        default_port: int | None = None,
    ):
        text = self._normalize_host_text(raw_value)
        scheme = self._normalize_scheme(default_scheme, "mqtt")
        fallback_port = self._safe_int(
            default_port,
            self._default_port_for_scheme(scheme),
        )

        if not text:
            return scheme, "", fallback_port

        has_scheme = "://" in text
        source = text if has_scheme else f"{scheme}://{text}"
        try:
            parsed = urlparse(source)
            parsed_scheme = self._normalize_scheme(parsed.scheme, scheme)
            host = (parsed.hostname or "").strip()
            if parsed.port is not None:
                port = int(parsed.port)
            elif has_scheme:
                port = self._default_port_for_scheme(parsed_scheme)
            else:
                port = fallback_port
            return parsed_scheme, host, port
        except Exception:
            return scheme, text, fallback_port

    def _parse_host_port(
        self,
        raw_value: str,
        default_port: int = 1883,
        default_scheme: str = "mqtt",
    ):
        _, host, port = self._parse_server_endpoint(raw_value, default_scheme, default_port)
        return host, port

    def _normalize_endpoint(self, scheme: str, host: str, port: int) -> str:
        scheme = self._normalize_scheme(scheme, "mqtt")
        host = self._normalize_host_text(host)
        port = self._safe_int(port, self._default_port_for_scheme(scheme))
        return f"{scheme}://{host}:{port}" if host else ""

    def _split_endpoint(self, endpoint: str):
        scheme, host, port = self._parse_server_endpoint(
            endpoint,
            self.get_server_scheme(),
            self.get_server_active_port(),
        )
        return scheme, host, self._safe_int(port, self._default_port_for_scheme(scheme))

    def _normalize_endpoints_string(
        self,
        value: str,
        default_port: int = 1883,
        default_scheme: str = "mqtt",
    ) -> str:
        raw = self._normalize_host_text(value)
        if not raw:
            return ""
        seen = set()
        endpoints = []
        for token in raw.split(","):
            token = self._normalize_host_text(token)
            if not token:
                continue
            scheme, host, port = self._parse_server_endpoint(token, default_scheme, default_port)
            endpoint = self._normalize_endpoint(scheme, host, port)
            if not endpoint:
                continue
            low = endpoint.lower()
            if low in seen:
                continue
            seen.add(low)
            endpoints.append(endpoint)
        return ",".join(endpoints)

    def _migrate_legacy_server_settings(self):
        default_port = self._safe_int(self.settings.value("server/port", 1883), 1883)
        default_scheme = "mqtts" if default_port == 8883 else "mqtt"

        scheme_exists = self.settings.contains("server/scheme")
        host_exists = self.settings.contains("server/host")
        port_exists = self.settings.contains("server/active_port")
        if not scheme_exists or not host_exists or not port_exists:
            old_url = self.get_value("server/url", "117.72.10.141", str)
            scheme, host, port = self._parse_server_endpoint(old_url, default_scheme, default_port)
            if not host:
                host = "117.72.10.141"
            self.set_value("server/scheme", scheme)
            self.set_value("server/host", host)
            self.set_value("server/active_port", port)

        endpoints_exists = self.settings.contains("server/customized_endpoints")
        if not endpoints_exists:
            old_custom = self.get_value("server/customized_url", "", str)
            normalized = self._normalize_endpoints_string(
                old_custom,
                self.get_server_active_port(),
                self.get_server_scheme(),
            )
            if not normalized:
                scheme = self.get_server_scheme()
                host = self.get_server_host()
                port = self.get_server_active_port()
                normalized = self._normalize_endpoint(scheme, host, port)
            self.set_value("server/customized_endpoints", normalized)

        # Keep legacy keys in sync for compatibility with any untouched callers.
        scheme = self.get_server_scheme()
        host = self.get_server_host()
        if host:
            legacy_url = host if scheme == "mqtt" else f"{scheme}://{host}"
        else:
            legacy_url = ""
        self.set_value("server/url", legacy_url)
        self.set_value("server/port", self.get_server_active_port())
        self.set_value("server/customized_url", self.get_server_customized_endpoints())

        # TLS migration: old versions only had tls_insecure.
        if not self.settings.contains("server/tls_use_cert"):
            insecure = self.get_value("server/tls_insecure", True, bool)
            self.set_value("server/tls_use_cert", not bool(insecure))
        else:
            use_cert = self.get_value("server/tls_use_cert", False, bool)
            self.set_value("server/tls_insecure", not bool(use_cert))

        self.settings.sync()

    # Decoder data
    def get_history(self):
        return json.loads(self.get_value("Decoder/history", "[]", value_type=str))

    def set_history(self, history):
        self.set_value("Decoder/history", json.dumps(history))

    def get_wpm(self):
        return self.get_value("Decoder/wpm", value_type=int)

    def set_wpm(self, value):
        self.set_value("Decoder/wpm", int(value))

    def get_dot_duration(self):
        return self.get_value("Decoder/dot_duration", value_type=float)

    def set_dot_duration(self, value):
        self.set_value("Decoder/dot_duration", float(value))

    def get_dash_threshold(self):
        return self.get_value("Decoder/dash_threshold", value_type=float)

    def set_dash_threshold(self, value):
        self.set_value("Decoder/dash_threshold", float(value))

    def get_speed_profile(self):
        return json.loads(self.get_value("Decoder/speed_profile", "[]", value_type=str))

    def set_speed_profile(self, profile):
        self.set_value("Decoder/speed_profile", json.dumps(profile))

    def get_version(self):
        return self.get_value("Decoder/version", value_type=str)

    def set_version(self, version):
        self.set_value("Decoder/version", version)

    # Identity
    def get_my_call(self):
        return self.get_value("SelfInfo/my_call", value_type=str)

    def set_my_call(self, value):
        self.set_value("SelfInfo/my_call", value)

    def get_password(self):
        return self.get_value("SelfInfo/password", value_type=str)

    def set_password(self, value):
        self.set_value("SelfInfo/password", value)

    # App version
    def get_first_run_status(self):
        return self.get_value("Version/first_run_status", value_type=bool)

    def set_first_run_status(self, value):
        self.set_value("Version/first_run_status", value)

    def get_current_version(self):
        return self.get_value("Version/current_version", value_type=str)

    def set_current_version(self, value):
        self.set_value("Version/current_version", value)

    # TX timings (global)
    def get_dot_time(self):
        return self.get_value("Time/dot_time", value_type=int)

    def set_dot_time(self, value):
        self.set_value("Time/dot_time", int(value))

    def get_dash_time(self):
        return self.get_value("Time/dash_time", value_type=int)

    def set_dash_time(self, value):
        self.set_value("Time/dash_time", int(value))

    def get_letter_interval_duration_time(self):
        return self.get_value("Time/letter_interval_duration_time", value_type=int)

    def set_letter_interval_duration_time(self, value):
        self.set_value("Time/letter_interval_duration_time", int(value))

    def get_word_interval_duration_time(self):
        return self.get_value("Time/word_interval_duration_time", value_type=int)

    def set_word_interval_duration_time(self, value):
        self.set_value("Time/word_interval_duration_time", int(value))

    # Server (new APIs)
    def get_server_scheme(self):
        value = self.get_value("server/scheme", "", str).lower()
        if value in ("mqtt", "mqtts"):
            return value

        candidates = (
            self.get_value("server/host", "", str),
            self.get_value("server/url", "", str),
            self.get_value("server/customized_endpoints", "", str),
            self.get_value("server/customized_url", "", str),
        )
        for candidate in candidates:
            text = self._normalize_host_text(candidate)
            if "://" not in text:
                continue
            scheme, _, _ = self._parse_server_endpoint(text, "mqtt", 1883)
            self.set_value("server/scheme", scheme)
            self.settings.sync()
            return scheme

        inferred_port = self._safe_int(
            self.settings.value(
                "server/active_port",
                self.settings.value("server/port", 1883),
            ),
            1883,
        )
        inferred_scheme = "mqtts" if inferred_port == 8883 else "mqtt"
        self.set_value("server/scheme", inferred_scheme)
        self.settings.sync()
        return inferred_scheme

    def set_server_scheme(self, value):
        self.set_value("server/scheme", self._normalize_scheme(value, "mqtt"))

    def get_server_host(self):
        current_scheme = self.get_server_scheme()
        current_port = self.get_server_active_port()

        raw_host = self.get_value("server/host", "", str)
        if raw_host:
            parsed_scheme, parsed_host, parsed_port = self._parse_server_endpoint(
                raw_host,
                current_scheme,
                current_port,
            )
            if parsed_host and (
                parsed_host != raw_host
                or parsed_port != current_port
                or parsed_scheme != current_scheme
            ):
                self.set_value("server/scheme", parsed_scheme)
                self.set_value("server/host", parsed_host)
                legacy_url = parsed_host if parsed_scheme == "mqtt" else f"{parsed_scheme}://{parsed_host}"
                self.set_value("server/url", legacy_url)
                self.set_value("server/active_port", parsed_port)
                self.set_value("server/port", parsed_port)
                self.settings.sync()
            return parsed_host or raw_host

        # Fallback for older configs
        legacy_url = self.get_value("server/url", "117.72.10.141", str)
        parsed_scheme, parsed_host, parsed_port = self._parse_server_endpoint(
            legacy_url,
            current_scheme,
            current_port,
        )
        if parsed_host:
            self.set_value("server/scheme", parsed_scheme)
            self.set_value("server/host", parsed_host)
            legacy_url = parsed_host if parsed_scheme == "mqtt" else f"{parsed_scheme}://{parsed_host}"
            self.set_value("server/url", legacy_url)
            self.set_value("server/active_port", parsed_port)
            self.set_value("server/port", parsed_port)
            self.settings.sync()
        return parsed_host or "117.72.10.141"

    def set_server_host(self, value):
        scheme, host, port = self._parse_server_endpoint(
            value,
            self.get_server_scheme(),
            self.get_server_active_port(),
        )
        if not host:
            return
        self.set_value("server/scheme", scheme)
        self.set_value("server/host", host)
        legacy_url = host if scheme == "mqtt" else f"{scheme}://{host}"
        self.set_value("server/url", legacy_url)
        self.set_value("server/active_port", port)
        self.set_value("server/port", port)

    def get_server_active_port(self):
        default_port = self._default_port_for_scheme(self.get_server_scheme())
        port = self.get_value("server/active_port", None, int)
        if port is None:
            port = self.get_value("server/port", default_port, int)
            self.set_value("server/active_port", port)
            self.settings.sync()
        return max(1, min(65535, int(port)))

    def set_server_active_port(self, value):
        default_port = self._default_port_for_scheme(self.get_server_scheme())
        port = max(1, min(65535, self._safe_int(value, default_port)))
        self.set_value("server/active_port", port)
        self.set_value("server/port", port)

    def get_server_customized_endpoints(self):
        default_port = self.get_server_active_port()
        default_scheme = self.get_server_scheme()
        value = self.get_value("server/customized_endpoints", "", str)
        if value:
            normalized = self._normalize_endpoints_string(value, default_port, default_scheme)
            if normalized != value:
                self.set_value("server/customized_endpoints", normalized)
                self.set_value("server/customized_url", normalized)
                self.settings.sync()
            return normalized

        legacy = self.get_value("server/customized_url", "", str)
        normalized = self._normalize_endpoints_string(legacy, default_port, default_scheme)
        if not normalized:
            normalized = self._normalize_endpoint(default_scheme, self.get_server_host(), default_port)
        self.set_value("server/customized_endpoints", normalized)
        self.set_value("server/customized_url", normalized)
        self.settings.sync()
        return normalized

    def set_server_customized_endpoints(self, value):
        normalized = self._normalize_endpoints_string(
            value,
            self.get_server_active_port(),
            self.get_server_scheme(),
        )
        self.set_value("server/customized_endpoints", normalized)
        self.set_value("server/customized_url", normalized)

    # Legacy server APIs kept for compatibility
    def get_server_url(self):
        return self.get_server_host()

    def set_server_url(self, value):
        self.set_server_host(value)

    def get_server_port(self):
        return self.get_server_active_port()

    def set_server_port(self, value):
        self.set_server_active_port(value)

    def get_server_customized_url(self):
        return self.get_server_customized_endpoints()

    def set_server_customized_url(self, value):
        self.set_server_customized_endpoints(value)

    def get_server_customized_port(self):
        return str(self.get_server_active_port())

    def set_server_customized_port(self, value):
        self.set_server_active_port(value)

    def get_server_channel_name(self):
        return self.get_value("server/channel_name", value_type=int)

    def set_server_channel_name(self, value):
        self.set_value("server/channel_name", value)

    def get_server_tls_ca_certs(self):
        return self.get_value("server/tls_ca_certs", "", str)

    def set_server_tls_ca_certs(self, value):
        self.set_value("server/tls_ca_certs", str(value or "").strip())

    def get_server_tls_use_cert(self):
        if self.settings.contains("server/tls_use_cert"):
            return self.get_value("server/tls_use_cert", False, bool)

        # Compatibility fallback: old config only had tls_insecure.
        insecure = self.get_value("server/tls_insecure", True, bool)
        use_cert = not bool(insecure)
        self.set_value("server/tls_use_cert", use_cert)
        self.settings.sync()
        return use_cert

    def set_server_tls_use_cert(self, value):
        use_cert = bool(value)
        self.set_value("server/tls_use_cert", use_cert)
        # Keep old key synchronized for backward compatibility.
        self.set_value("server/tls_insecure", not use_cert)

    def get_server_tls_insecure(self):
        if self.settings.contains("server/tls_insecure"):
            insecure = self.get_value("server/tls_insecure", False, bool)
            if not self.settings.contains("server/tls_use_cert"):
                self.set_value("server/tls_use_cert", not bool(insecure))
                self.settings.sync()
            return insecure

        insecure = not bool(self.get_server_tls_use_cert())
        self.set_value("server/tls_insecure", insecure)
        self.settings.sync()
        return insecure

    def set_server_tls_insecure(self, value):
        insecure = bool(value)
        self.set_value("server/tls_insecure", insecure)
        self.set_value("server/tls_use_cert", not insecure)

    # Auth extension
    def get_auth_type(self):
        value = self.get_value("Auth/type", "plain", str).lower()
        return value if value in ("plain", "jwt") else "plain"

    def set_auth_type(self, value):
        value = str(value or "plain").lower()
        if value not in ("plain", "jwt"):
            value = "plain"
        self.set_value("Auth/type", value)

    def get_auth_token(self):
        return self.get_value("Auth/token", "", str)

    def set_auth_token(self, value):
        self.set_value("Auth/token", value)

    # General settings
    def get_language(self):
        return self.get_value("Setting/language", value_type=str)

    def set_language(self, value):
        self.set_value("Setting/language", value)

    def get_buzz_freq(self):
        return self.get_value("Setting/buzz_freq", value_type=int)

    def set_buzz_freq(self, value):
        self.set_value("Setting/buzz_freq", int(value))

    def get_autokey_status(self):
        return self.get_value("Setting/autokey_status", value_type=bool)

    def set_autokey_status(self, value):
        self.set_value("Setting/autokey_status", bool(value))

    def get_keyer_mode(self):
        return self.get_value("Setting/keyer_mode", value_type=str)

    def set_keyer_mode(self, value):
        self.set_value("Setting/keyer_mode", value)

    def get_single_dual_policy(self):
        return self.get_value("Setting/single_dual_policy", value_type=str)

    def set_single_dual_policy(self, value):
        self.set_value("Setting/single_dual_policy", value)

    def get_paddle_memory_enabled(self):
        return self.get_value("Setting/paddle_memory_enabled", value_type=bool)

    def set_paddle_memory_enabled(self, value):
        self.set_value("Setting/paddle_memory_enabled", bool(value))

    def get_rx_tx_lock_tail_ms(self):
        return self.get_value("Setting/rx_tx_lock_tail_ms", value_type=int)

    def set_rx_tx_lock_tail_ms(self, value):
        self.set_value("Setting/rx_tx_lock_tail_ms", int(value))

    def get_keyborad_key(self):
        value = self.get_value("Setting/keyborad_key", value_type=str)
        return value or "81,87"

    def set_keyborad_key(self, value):
        self.set_value("Setting/keyborad_key", value)

    def get_send_buzz_status(self):
        return self.get_value("Setting/send_buzz_status", value_type=bool)

    def set_send_buzz_status(self, value):
        self.set_value("Setting/send_buzz_status", bool(value))

    def get_receive_buzz_status(self):
        return self.get_value("Setting/receive_buzz_status", value_type=bool)

    def set_receive_buzz_status(self, value):
        self.set_value("Setting/receive_buzz_status", bool(value))

    def get_translation_visibility(self):
        return self.get_value("Setting/translation_visibility", value_type=bool)

    def set_translation_visibility(self, value):
        self.set_value("Setting/translation_visibility", bool(value))

    def get_visualizer_visibility(self):
        return self.get_value("Setting/visualizer_visibility", value_type=bool)

    def set_visualizer_visibility(self, value):
        self.set_value("Setting/visualizer_visibility", bool(value))

    def get_sender_font_size(self):
        return self.get_value("Setting/sender_font_size", value_type=int)

    def set_sender_font_size(self, value):
        self.set_value("Setting/sender_font_size", int(value))
