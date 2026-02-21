from __future__ import annotations

from abc import ABC, abstractmethod

from service.auth.auth_profile import AuthProfile


class CredentialStore(ABC):
    @abstractmethod
    def get_auth_profile(self) -> AuthProfile:
        raise NotImplementedError


class PlainConfigCredentialStore(CredentialStore):
    def __init__(self, config_manager):
        self.config_manager = config_manager

    def get_auth_profile(self) -> AuthProfile:
        auth_type = str(self.config_manager.get_auth_type() or "plain").lower()
        if auth_type not in ("plain", "jwt"):
            auth_type = "plain"

        return AuthProfile(
            auth_type=auth_type,
            username=str(self.config_manager.get_my_call() or ""),
            password=str(self.config_manager.get_password() or ""),
            token=str(self.config_manager.get_auth_token() or ""),
        )

