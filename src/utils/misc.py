from typing import Any, List


def prepare_str(text: List[Any]) -> str:
    resp = map(str, text)
    return '\n'.join(resp)
