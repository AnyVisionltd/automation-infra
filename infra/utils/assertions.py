from infra.utils.exceptions import ResponseStatusError


def assert_status_code(code, response):
    if response.status_code != code:
        raise ResponseStatusError(response.status_code, response.json())