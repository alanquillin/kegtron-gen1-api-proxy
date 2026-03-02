import random
import re
import string
from logging import getLogger
from typing import Any, Dict, List, Union
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from uuid import UUID

from lib.time import utcnow_aware

LOGGER = getLogger(__name__)


_camel_to_snake_re = re.compile(r"(?<!^)(?=[A-Z])")


def camel_to_snake(camel_str: str) -> str:
    return _camel_to_snake_re.sub("_", camel_str).lower()


def snake_to_camel(in_str: str) -> str:
    return "".join([element.title() if index > 0 else element.lower() for index, element in enumerate(in_str.split("_"))])


def random_string(length: int) -> str:

    """Return a random string of a certain length."""

    return "".join(random.SystemRandom().choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(length))


def flatten_dict(data: dict, parent_name: str = "", sep: str = ".", key_converter: callable = None, skip_key_check: callable = None) -> dict:

    """
    Flattens a dictionary to a single layer with child keys separated by `sep` charactor

    Example:
    input:
        parent_name = "root"
        data = {
            "parent_obj": {
                "child_obj": {
                    "grand_child_obj": "my value"
                }
            },
            "foo": "bar"
        }
    output:
        {
            "root.parent_obj.child_obj.grand_child_obj": "my value",
            "root.foo": "bar"
        }

    """
    if not skip_key_check:
        skip_key_check = lambda *_: False

    flattened = {}

    for key, val in data.items():
        child_name = key if not parent_name else f"{parent_name}{sep}{key}"
        if isinstance(val, dict) and not skip_key_check(child_name):
            flattened.update(flatten_dict(val, parent_name=child_name, sep=sep, key_converter=key_converter, skip_key_check=skip_key_check))
        else:
            if key_converter:
                child_name = key_converter(child_name)
            flattened[child_name] = val

    return flattened


def str_to_bool(in_str: str) -> bool:
    return in_str.lower() in ["true", "t", "yes", "y", "1"]


def dt_str_now() -> str:
    return utcnow_aware().isoformat()


def add_query_string(url, query_string_params=None):
    if query_string_params is None:
        query_string_params = {}

    parts = urlparse(url)
    query = parse_qs(parts.query)
    query.update(query_string_params)
    parts = parts._replace(query=urlencode(query, doseq=True))
    return urlunparse(parts)


def get_query_string_params_from_url(url):
    parsed_url = urlparse(url)
    return parse_qs(parsed_url.query)


def is_valid_uuid(uuid_to_test, version=4) -> bool:
    try:
        uuid_obj = UUID(uuid_to_test, version=version)
    except ValueError:
        return False

    return str(uuid_obj) == uuid_to_test

def dict_to_camel_case(data: Union[Dict, List, Any], skip_none: bool = True) -> Union[Dict, List, Any]:
    """
    Recursively transform dict keys from snake_case to camelCase.
    Optionally removes None values from the output.
    """
    if data is None:
        return None

    if isinstance(data, dict):
        transformed = {}
        for key, val in data.items():
            # Skip None values
            if val is None and skip_none == True:
                continue

            # Convert key to camelCase
            camel_key = snake_to_camel(key) if "_" in key else key

            # Recursively transform nested structures
            if isinstance(val, dict):
                val = dict_to_camel_case(val)
            elif isinstance(val, list):
                val = [dict_to_camel_case(v) if isinstance(v, (dict, list)) else v for v in val]

            transformed[camel_key] = val

        return transformed

    elif isinstance(data, list):
        return [dict_to_camel_case(item) if isinstance(item, (dict, list)) else item for item in data]

    else:
        return data
