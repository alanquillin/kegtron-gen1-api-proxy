import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from uuid import UUID

from lib.util import (
    camel_to_snake, 
    snake_to_camel, 
    random_string, 
    flatten_dict,
    str_to_bool,
    dt_str_now,
    add_query_string,
    get_query_string_params_from_url,
    is_valid_uuid,
    dict_to_camel_case,
    string_to_bytes
)


class TestCamelToSnake:
    def test_simple_camel_case(self):
        assert camel_to_snake("camelCase") == "camel_case"
        assert camel_to_snake("CamelCase") == "camel_case"
        
    def test_multiple_words(self):
        assert camel_to_snake("thisIsALongCamelCase") == "this_is_a_long_camel_case"
        
    def test_already_snake_case(self):
        assert camel_to_snake("snake_case") == "snake_case"
        
    def test_single_word(self):
        assert camel_to_snake("word") == "word"
        assert camel_to_snake("Word") == "word"


class TestSnakeToCamel:
    def test_simple_snake_case(self):
        assert snake_to_camel("snake_case") == "snakeCase"
        
    def test_multiple_words(self):
        assert snake_to_camel("this_is_snake_case") == "thisIsSnakeCase"
        
    def test_single_word(self):
        assert snake_to_camel("word") == "word"
        
    def test_leading_uppercase(self):
        assert snake_to_camel("SNAKE_CASE") == "snakeCase"


class TestRandomString:
    def test_length(self):
        result = random_string(10)
        assert len(result) == 10
        
    def test_different_results(self):
        result1 = random_string(10)
        result2 = random_string(10)
        assert result1 != result2
        
    def test_character_set(self):
        result = random_string(100)
        for char in result:
            assert char.isalnum()


class TestFlattenDict:
    def test_simple_flatten(self):
        data = {"a": 1, "b": 2}
        result = flatten_dict(data)
        assert result == {"a": 1, "b": 2}
        
    def test_nested_dict(self):
        data = {
            "parent": {
                "child": {
                    "grandchild": "value"
                }
            }
        }
        result = flatten_dict(data)
        assert result == {"parent.child.grandchild": "value"}
        
    def test_with_parent_name(self):
        data = {"key": "value"}
        result = flatten_dict(data, parent_name="root")
        assert result == {"root.key": "value"}
        
    def test_custom_separator(self):
        data = {"parent": {"child": "value"}}
        result = flatten_dict(data, sep="_")
        assert result == {"parent_child": "value"}
        
    def test_mixed_types(self):
        data = {
            "string": "value",
            "number": 42,
            "nested": {
                "bool": True,
                "list": [1, 2, 3]
            }
        }
        result = flatten_dict(data)
        assert result == {
            "string": "value",
            "number": 42,
            "nested.bool": True,
            "nested.list": [1, 2, 3]
        }
        
    def test_with_key_converter(self):
        data = {"parent": {"child": "value"}}
        result = flatten_dict(data, key_converter=str.upper)
        assert result == {"PARENT.CHILD": "value"}


class TestStrToBool:
    def test_true_values(self):
        assert str_to_bool("true") == True
        assert str_to_bool("True") == True
        assert str_to_bool("TRUE") == True
        assert str_to_bool("t") == True
        assert str_to_bool("T") == True
        assert str_to_bool("yes") == True
        assert str_to_bool("YES") == True
        assert str_to_bool("y") == True
        assert str_to_bool("1") == True
        
    def test_false_values(self):
        assert str_to_bool("false") == False
        assert str_to_bool("False") == False
        assert str_to_bool("no") == False
        assert str_to_bool("0") == False
        assert str_to_bool("anything") == False


class TestDtStrNow:
    def test_returns_iso_format(self):
        with patch('lib.util.utcnow_aware') as mock_utcnow:
            mock_dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            mock_utcnow.return_value = mock_dt
            result = dt_str_now()
            assert result == "2024-01-01T12:00:00+00:00"


class TestAddQueryString:
    def test_add_to_url_without_params(self):
        url = "https://example.com/path"
        params = {"key": "value"}
        result = add_query_string(url, params)
        assert result == "https://example.com/path?key=value"
        
    def test_add_to_url_with_params(self):
        url = "https://example.com/path?existing=param"
        params = {"key": "value"}
        result = add_query_string(url, params)
        assert "existing=param" in result
        assert "key=value" in result
        
    def test_empty_params(self):
        url = "https://example.com/path"
        result = add_query_string(url)
        assert result == "https://example.com/path"
        
    def test_list_values(self):
        url = "https://example.com/path"
        params = {"key": ["val1", "val2"]}
        result = add_query_string(url, params)
        assert "key=val1" in result
        assert "key=val2" in result


class TestGetQueryStringParamsFromUrl:
    def test_single_param(self):
        url = "https://example.com/path?key=value"
        result = get_query_string_params_from_url(url)
        assert result == {"key": ["value"]}
        
    def test_multiple_params(self):
        url = "https://example.com/path?key1=val1&key2=val2"
        result = get_query_string_params_from_url(url)
        assert result == {"key1": ["val1"], "key2": ["val2"]}
        
    def test_no_params(self):
        url = "https://example.com/path"
        result = get_query_string_params_from_url(url)
        assert result == {}
        
    def test_duplicate_keys(self):
        url = "https://example.com/path?key=val1&key=val2"
        result = get_query_string_params_from_url(url)
        assert result == {"key": ["val1", "val2"]}


class TestIsValidUuid:
    def test_valid_uuid4(self):
        import uuid
        valid_uuid = str(uuid.uuid4())
        assert is_valid_uuid(valid_uuid) == True
        
    def test_invalid_uuid(self):
        assert is_valid_uuid("not-a-uuid") == False
        assert is_valid_uuid("123") == False
        assert is_valid_uuid("") == False
        
    def test_wrong_version(self):
        # UUID v4 format doesn't validate against version 1
        # Using a UUID v1 to test
        import uuid
        uuid1 = str(uuid.uuid1())
        assert is_valid_uuid(uuid1, version=4) == False
        
    def test_uppercase_uuid(self):
        # The function checks exact format match, so uppercase UUID will fail
        import uuid
        valid_uuid = str(uuid.uuid4()).upper()
        assert is_valid_uuid(valid_uuid) == False
        
    def test_lowercase_uuid(self):
        import uuid
        valid_uuid = str(uuid.uuid4()).lower()
        assert is_valid_uuid(valid_uuid) == True


class TestDictToCamelCase:
    def test_simple_dict(self):
        data = {"snake_case": "value", "another_key": "value2"}
        result = dict_to_camel_case(data)
        assert result == {"snakeCase": "value", "anotherKey": "value2"}
        
    def test_nested_dict(self):
        data = {
            "parent_key": {
                "child_key": "value"
            }
        }
        result = dict_to_camel_case(data)
        assert result == {
            "parentKey": {
                "childKey": "value"
            }
        }
        
    def test_list_of_dicts(self):
        data = [
            {"snake_key": "val1"},
            {"another_snake": "val2"}
        ]
        result = dict_to_camel_case(data)
        assert result == [
            {"snakeKey": "val1"},
            {"anotherSnake": "val2"}
        ]
        
    def test_skip_none_values(self):
        data = {"key_one": "value", "key_two": None}
        result = dict_to_camel_case(data, skip_none=True)
        assert result == {"keyOne": "value"}
        
    def test_keep_none_values(self):
        data = {"key_one": "value", "key_two": None}
        result = dict_to_camel_case(data, skip_none=False)
        assert result == {"keyOne": "value", "keyTwo": None}
        
    def test_mixed_types(self):
        data = {
            "string_key": "value",
            "number_key": 42,
            "list_key": [1, 2, {"nested_key": "val"}],
            "bool_key": True
        }
        result = dict_to_camel_case(data)
        assert result == {
            "stringKey": "value",
            "numberKey": 42,
            "listKey": [1, 2, {"nestedKey": "val"}],
            "boolKey": True
        }
        
    def test_non_dict_input(self):
        assert dict_to_camel_case("string") == "string"
        assert dict_to_camel_case(42) == 42
        assert dict_to_camel_case(None) == None


class TestStringToBytes:
    def test_basic_string_conversion(self):
        """Test basic string to bytes conversion."""
        result = string_to_bytes("Hello", max_len=10)
        expected = b"Hello     "  # Padded to 10 chars
        assert result == expected
        assert len(result) == 10
    
    def test_truncation(self):
        """Test that strings longer than max_len are truncated."""
        result = string_to_bytes("This is a very long string", max_len=10)
        expected = b"This is a "
        assert result == expected
        assert len(result) == 10
    
    def test_exact_length(self):
        """Test string exactly at max_len."""
        result = string_to_bytes("Exact", max_len=5)
        expected = b"Exact"
        assert result == expected
        assert len(result) == 5
    
    def test_default_max_length(self):
        """Test default max_len of 20."""
        result = string_to_bytes("Short")
        expected = b"Short               "  # Padded to 20 chars
        assert result == expected
        assert len(result) == 20
    
    def test_empty_string(self):
        """Test empty string input."""
        result = string_to_bytes("", max_len=10)
        expected = b"          "  # 10 spaces
        assert result == expected
        assert len(result) == 10
    
    def test_custom_padding_character(self):
        """Test custom padding character."""
        result = string_to_bytes("Test", max_len=10, pad_char='_')
        expected = b"Test______"
        assert result == expected
    
    def test_different_encoding(self):
        """Test UTF-8 encoding (though function defaults to ASCII)."""
        # Note: The function currently uses ASCII by default
        # Testing with ASCII-compatible characters
        result = string_to_bytes("Test", max_len=10, encoding='utf-8')
        expected = "Test      ".encode('utf-8')
        assert result == expected
    
    def test_special_characters(self):
        """Test handling of special ASCII characters."""
        result = string_to_bytes("Beer #1", max_len=10)
        expected = b"Beer #1   "
        assert result == expected
    
    def test_numbers_in_string(self):
        """Test strings containing numbers."""
        result = string_to_bytes("Port 123", max_len=10)
        expected = b"Port 123  "
        assert result == expected
    
    def test_pad_right_true(self):
        """Test padding on the right (default behavior)."""
        result = string_to_bytes("ABC", max_len=6, pad_right=True)
        expected = b"ABC   "
        assert result == expected
    
    def test_kegtron_port_name(self):
        """Test typical Kegtron port name scenario."""
        # Kegtron expects 20-byte port names
        result = string_to_bytes("IPA Keg", max_len=20)
        expected = b"IPA Keg             "
        assert result == expected
        assert len(result) == 20
    
    def test_long_port_name_truncation(self):
        """Test that long port names are truncated to 20 chars."""
        long_name = "This is a really long beer name that exceeds limit"
        result = string_to_bytes(long_name, max_len=20)
        expected = b"This is a really lon"
        assert result == expected
        assert len(result) == 20