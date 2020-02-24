class ResponseStatusError(Exception):
    def __init__(self, status_code, description):
        self.status_code = status_code
        self.description = description