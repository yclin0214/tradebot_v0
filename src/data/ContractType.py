from enum import Enum


class ContractType(str, Enum):
    STOCK = "stock"
    OPTION = "option"
