class Node:
    def __init__(self, content, node_type):
        self.content = content
        self.node_type = node_type
        self.position = (0, 0)
        self.connections = []

    def connect_to(self, other_node):
        self.connections.append(other_node)