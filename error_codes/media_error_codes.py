import enum

class MediaServiceErrorCode(enum.Enum):
    MS101 = "payload is missing"
    MS102 = "Unsupported Media Type"
    MS103 = "File size must not exceed 200 KB"