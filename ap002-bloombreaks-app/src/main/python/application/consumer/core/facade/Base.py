from types import SimpleNamespace

class BaseService:
    def __init__(self, db):
        self.db = db

    def _dict_to_namespace(self, request):
        # Recursively converts dictionary requests to SimpleNameSpace
        if isinstance(request, dict):
            return SimpleNamespace(**{k: self._dict_to_namespace(v) for k, v in request.items()})
        elif isinstance(request, list):
            return [self._dict_to_namespace(i) for i in request]
        return request
