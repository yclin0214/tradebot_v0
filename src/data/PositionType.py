from enum import Enum


class PositionType(str, Enum):
    STOCK = "STOCK"
    PUT = "PUT"
    CALL = "CALL"
