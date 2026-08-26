from enum import Enum

class LoginOption(Enum):
    EMAIL = "EMAIL"
    USERNAME = "USERNAME"

class Role(Enum):
   SUPER_ADMIN = "SUPER_ADMIN"
   ADMIN = "ADMIN"
   EXECUTIVE = "EXECUTIVE"
   USER = "USER"