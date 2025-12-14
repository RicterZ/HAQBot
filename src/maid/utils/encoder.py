from json import JSONEncoder


class CommandEncoder(JSONEncoder):
    def default(self, o):
        if hasattr(o, 'as_dict'):
            result = o.as_dict()
            # Recursively process nested objects in the result
            if isinstance(result, dict):
                return {k: self._process_value(v) for k, v in result.items()}
            elif isinstance(result, list):
                return [self._process_value(item) for item in result]
            return result
        return super().default(o)
    
    def _process_value(self, value):
        """Recursively process values to handle nested objects"""
        if hasattr(value, 'as_dict'):
            return self.default(value)
        elif isinstance(value, dict):
            return {k: self._process_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._process_value(item) for item in value]
        return value

