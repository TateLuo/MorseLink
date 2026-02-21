from dataclasses import dataclass


@dataclass
class AuthProfile:
    auth_type: str = "plain"
    username: str = ""
    password: str = ""
    token: str = ""

