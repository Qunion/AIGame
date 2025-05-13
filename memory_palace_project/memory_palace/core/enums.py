from enum import Enum

class NodeType(Enum):
    TEXT = 1
    IMAGE = 2
    AUDIO = 3
    VIDEO = 4

class OperationMode(Enum):
    VIEW = 10
    EDIT = 20
    REVIEW = 30
    RECITE = 40