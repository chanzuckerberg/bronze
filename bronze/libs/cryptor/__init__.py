import base64
import json


__all__ = [
    'decrypt_from_environment_variable_with_base64',
]


def decrypt_from_environment_variable_with_base64(base64string: str):
    """Decrypt from a string."""
    return json.loads(base64.b64decode(base64string))
