from json import JSONEncoder


class CommandEncoder(JSONEncoder):
    def default(self, o):
        return o.as_dict()

