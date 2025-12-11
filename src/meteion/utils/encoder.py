from json import JSONEncoder


class CommandEncoder(JSONEncoder):
    """JSON encoder for Command objects"""
    
    def default(self, o):
        return o.as_dict()

