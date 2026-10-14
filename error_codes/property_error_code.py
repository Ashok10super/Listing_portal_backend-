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
    PR111 = "Property approved successfully"
    PR112 = "Property disapproved successfully"
    PR113 = "Property updated successfully"
    PR114 = "Property created successfully"
    PR115 = "Unauthorized action on property"
    PR116 = "Invalid json body"
    PR117 = "Payload not found"
    PR118 = "Mandatory field missing"
    PR119 = "Validation successful"
    PR120 = "Internal Server Error"
    PR121 = "Id fetched successfully"
    PR122 = 'Id updated successfully'
