from enum import Enum

class LoginOption(Enum):
    EMAIL = "EMAIL"
    USERNAME = "USERNAME"

class Role(Enum):
   SUPER_ADMIN = "SUPER_ADMIN"
   ADMIN = "ADMIN"
   EXECUTIVE = "EXECUTIVE"
   USER = "USER"

class AvailableFilterLookups(Enum):
    bank_name = "bank_name"
    state = "state"
    district = "district"
    city = "city"
    property_type = "property_type"
    emd = "emd"
    reserve_price = "reserve_price"
    increment_price = "increment_price"
    property_sub_type = "property_sub_type"

class IdentityGenerationModules(Enum):
   property_id = "property_id"
   property_unique_id = "property_unique_id"
   auction_id = "auction_id"

class AllowedImageExtensions(Enum):
    jpeg = "image/jpeg"
    png = "image/png"
    webp = "image/webp"

MAX_FILE_SIZE = 200 * 1024