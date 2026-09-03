import enum


class PropertyErrorCode(enum.Enum):
    PR101 = "Properties fetched successfully"
    PR102 = "Property fetched successfully"
    PR103 = "Property not found"
    PR104 = "Property liked successfully"
    PR105 = "Property unliked successfully"
    PR106 = "Property already liked"
    PR107 = "Property not liked yet"
    PR108 = "Invalid query parameters"
    PR109 = "Internal Server Error"
    PR110 = "Liked properties fetched successfully"
