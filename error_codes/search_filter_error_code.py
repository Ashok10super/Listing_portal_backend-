import enum


class FilterLookupErrorCodes(enum.Enum):
    SF101 = "Search filter lookup is not available for this search filter"
    SF102 = "No filter found for this search filter"
    SF103 = "Filters fetched successfully"
    SF104 = "Internal server error"