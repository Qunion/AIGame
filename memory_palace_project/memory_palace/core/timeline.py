class Timeline:
    def __init__(self, name):
        self.name = name
        self.segments = []

    def add_segment(self, segment):
        self.segments.append(segment)