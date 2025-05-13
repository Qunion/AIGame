class Segment:
    def __init__(self, title):
        self.title = title
        self.nodes = []
        self.position = (0, 0)

    def add_node(self, node):
        self.nodes.append(node)