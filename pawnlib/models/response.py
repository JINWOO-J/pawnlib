import struct
from decimal import Decimal, InvalidOperation, getcontext, ROUND_DOWN
from pawnlib.typing.constants import const
from pawnlib.config import pawn
from pawnlib.typing.converter import  hex_to_number
from pawnlib.typing.check import is_hex, is_int, is_float


from requests.models import Response
import json


class NumericValue:
    def __init__(self, value, precision=30):
        # Set the precision for Decimal
        self.original_value = value  # Store original value
        self.decimal_value = Decimal(value)  # Convert to Decimal
        self.precision = precision  # Store precision

    def to_hex(self):
        """Convert the NumericValue to its hexadecimal representation."""
        packed_float = struct.pack('<f', float(self.decimal_value))
        return packed_float.hex()

    def quantized_value(self):
        """Return the quantized Decimal value."""
        try:
            return self.decimal_value.quantize(Decimal(f'1e-{self.precision}'), rounding=ROUND_DOWN)
        except InvalidOperation as e:
            print(f"Error during quantization: {e}")
            return self.decimal_value  # Fallback in case of error

    def __repr__(self):
        return f"NumericValue(original={self.original_value}, decimal={self.decimal_value})"


class HexValue:
    """
    HexValue class provides a way to handle and manipulate hexadecimal, integer, and float values
    with various arithmetic, bitwise, and comparison operations. It supports conversions to different
    number systems (hex, binary, octal) and JSON-compatible output.

    :param value: The initial value, which can be a hex string, integer, or float.
    :type value: str | int | float
    :param debug_info: Optional debug information for logging purposes.
    :type debug_info: Any
    :raises ValueError: If `value` is not a valid hex string, integer, or float.

    Example:

        .. code-block:: python

            from pawnlib.resource import HexValue
            hex_val1 = HexValue("0x1A")
            hex_val2 = HexValue(26)
            print(hex_val1)
            # > HexValue(hex=0x1a, decimal=26, numeric=26, tint=0.000000000026000000)

            print(hex_val2)
            # > HexValue(hex=0x1a, decimal=26, numeric=26, tint=0.000000000026000000)


            # Initializing HexValue with different types of input
            hex_val1 = HexValue("0x1A")
            hex_val2 = HexValue(26)
            hex_val3 = HexValue(30.5)

            print(hex_val1)
            # > HexValue(hex=0x1a, decimal=26, numeric=26, tint=0.000000000026000000)

            # Arithmetic operations
            result_add = hex_val1 + hex_val2         # Addition of two HexValue instances
            print(result_add)
            # > HexValue(hex=0x34, decimal=52, numeric=52, tint=0.000000000052000000)

            result_sub = hex_val1 - 5                # Subtraction with an integer
            print(result_sub)
            # > HexValue(hex=0x15, decimal=21, numeric=21, tint=0.000000000021000000)

            result_mul = hex_val2 * 3               # Multiplication with an integer
            print(result_mul)
            # > HexValue(hex=0x4e, decimal=78, numeric=78, tint=0.000000000078000000)

            result_div = hex_val3 / 2               # Division with a float
            print(result_div)
            # > HexValue(hex=0xf, decimal=15, numeric=15, tint=0.000000000015000000)
    """

    def __init__(self, value=None, debug_info=None):
        """
        Initialize a HexValue instance with a hex string, integer, or float.

        :param value: The initial value, which can be a hex string, integer, or float.
        :type value: str | int | float
        :param debug_info: Optional debug information for logging purposes.
        :type debug_info: Any
        :raises ValueError: If `value` is not a valid hex string, integer, or float.

        Example:

            .. code-block:: python

                hex_value = HexValue("0x1A")
                hex_value_int = HexValue(26)
        """
        self.hex = None
        self.debug_info = debug_info


        if value is not None:
            if isinstance(value, str) and self.is_hex(value):
                # If input is a valid hex string
                self.hex = value
                self.decimal = Decimal(self.hex_to_number(value))
                self.numeric = self.hex_to_number(value)
            elif isinstance(value, int):
                # If input is an integer
                self.numeric = value
                self.decimal = Decimal(self.numeric)
                self.hex = hex(value)
            elif isinstance(value, float):
                if value < const.ICX_IN_LOOP:
                    pawn.console.log(
                        f"[yellow][WARNING] The HexValue({value}) is a float and is less than const."
                         "ICX_IN_LOOP. Although it has been converted, it is recommended to use HexTintValue instead.[/yellow]")
                    value = int(value * const.ICX_IN_LOOP)
                self.decimal = Decimal(value)              # Maintain precision for float values
                self.numeric = value           # Convert to integer for numeric
                self.hex = hex(value)
            else:
                raise ValueError("Invalid input: must be a valid hex string, int, or float.")
            # Convert numeric value to "tint" based on a constant conversion factor
            if self.numeric > 0:
                self.tint = self.numeric / const.ICX_IN_LOOP
            else:
                self.tint = 0
        else:
            # Default values for uninitialized state
            self.decimal = None
            self.tint = None
            self.numeric = None

        self.readable_number = self.format_readable()

    def format_readable(self):
        """
        Generate a readable representation of the numeric or decimal value.

        :return: A human-friendly string representation of the number.
        :rtype: str
        """
        value = self.numeric

        # Example conversion to K, M, B, etc.
        if value >= 1e9:
            return f"{value / 1e9:.2f}B"
        elif value >= 1e6:
            return f"{value / 1e6:.2f}M"
        elif value >= 1e3:
            return f"{value / 1e3:.2f}K"
        else:
            return f"{value:.2f}"

    @staticmethod
    def hex_to_number(hex_val):
        """
        Convert a hex string to a decimal number.

        :param hex_val: The hex string to convert.
        :type hex_val: str
        :return: The integer value of the hex string.
        :rtype: int

        Example:

            .. code-block:: python

                HexValue.hex_to_number("0x1A")  # 26
        """
        return int(hex_val, 16) if isinstance(hex_val, str) else None

    def to_json(self):
        """
        Convert the HexValue to a JSON-compatible dictionary.

        :return: Dictionary with hex, decimal, numeric, and debug information.
        :rtype: dict

        Example:

            .. code-block:: python

                hex_value = HexValue("0x1A")
                print(hex_value.to_json())
                # > {'hex': '0x1a', 'decimal': '26', 'numeric': 26, 'debug_info': None}
        """
        return {
            "hex": self.to_hex(),
            "decimal": str(self.decimal),
            "numeric": self.numeric,
            "debug_info": self.debug_info
        }

    def to_hex(self):
        """
        Convert the numeric value back to a hexadecimal string.

        :return: The hexadecimal string representation.
        :rtype: str

        Example:

            .. code-block:: python

                hex_value = HexValue(26)
                print(hex_value.to_hex())  # '0x1a'
        """
        return hex(self.numeric)

    def to_binary(self):
        """Return binary representation of the hex value."""
        return bin(self.numeric) if self.numeric is not None else None

    def to_octal(self):
        """Return octal representation of the hex value."""
        return oct(self.numeric) if self.numeric is not None else None

    def to_percentage(self, total):
        """Return the percentage of this value with respect to a total."""
        if total == 0:
            raise ValueError("Total cannot be zero for percentage calculation.")
        return (self.numeric / total) * 100

    def compare_to(self, other):
        """
        Compare to another HexValue and return -1, 0, or 1.

        :param other: The other HexValue instance to compare against.
        :type other: HexValue
        :raises TypeError: If `other` is not a HexValue instance.
        :return: -1 if less than `other`, 0 if equal, 1 if greater.
        :rtype: int

        Example:

            .. code-block:: python

                hex_val1 = HexValue(20)
                hex_val2 = HexValue(30)
                print(hex_val1.compare_to(hex_val2))  # -1
        """
        if not isinstance(other, HexValue):
            raise TypeError("Comparison requires another HexValue instance.")
        return (self.numeric > other.numeric) - (self.numeric < other.numeric)

    def __repr__(self):
        debug_info_str = f", debug_info={self.debug_info}" if self.debug_info is not None else ""
        tint_str = f"{self.tint:.18f}".rstrip('0').rstrip('.') if self.tint is not None else "None"
        return (f"HexValue(hex={self.hex}, "
                f"decimal={self.decimal}, "
                f"numeric={self.numeric}, "
                f"readable_number={self.readable_number}, "  # Include readable_number here
                f"tint={tint_str}"
                f"{debug_info_str})")

    def __str__(self):
        return self.output(use_rich=False)  # User-friendly representation

    @staticmethod
    def generate_tag(text="", tag=""):
        if tag:
            return f"[{tag}]{text}[/{tag}]"
        else:
            return text

    def get_tag_if_balance(self, value="", color="gold3"):
        if self.decimal > 0:
            return f"[{color}]{value}[/{color}]"
        else:
            return self.decimal

    def output(self, use_simple=False, use_rich=True, value_color="gold3", info_color="grey53", use_tint=True, symbol="ICX"):
        """
        Format and display the HexValue with options for rich formatting and color.

        :param use_simple: If True, returns a simple string representation of the value without additional formatting.
        :type use_simple: bool
        :param use_rich: If True, applies rich formatting with colors and tags; ignored if `use_simple` is True.
        :type use_rich: bool
        :param value_color: The color for the value when rich formatting is enabled.
        :type value_color: str
        :param info_color: The color for additional information when rich formatting is enabled.
        :type info_color: str
        :param use_tint: If True, formats the output using the `tint` value (e.g., scaled by `ICX_IN_LOOP`); otherwise, uses the `decimal` value.
        :type use_tint: bool
        :param symbol: The symbol to append to the value, such as a currency or unit.
        :type symbol: str
        :return: A formatted string representation of the HexValue, optionally including rich formatting and colors.
        :rtype: str

        Example:

            .. code-block:: python

                hex_value = HexValue("0x1A")

                # Basic output without rich formatting
                print(hex_value.output(use_simple=True))
                # > '0.000000000026'

                # Rich output with color tags for value and info
                print(hex_value.output())
                # > '[gold3]0.000000000026[/gold3] ICX [grey53](Decimal)(org: 0x1a)[/grey53]'

                # Output using the decimal value without tint scaling
                print(hex_value.output(use_tint=False, symbol="ETH"))
                # > '[gold3]26[/gold3] ETH [grey53](Decimal)(org: 0x1a)[/grey53]'
        """
        _value = self.tint if use_tint else self.decimal
        if _value is None or _value == 0:
            _value = Decimal(0)

        formatted_value = f"{_value:,.18f}".rstrip('0').rstrip('.')
        if use_simple:
            return formatted_value

        if use_rich:
            value_with_tag = self.get_tag_if_balance(value=formatted_value, color=value_color)
            info_with_tag = self.generate_tag(text=f"({type(_value).__name__})(org: {self.hex})", tag=info_color)
            # return f"{formatted_value} {symbol} [{info_color}]({type(_value).__name__})(org: {self.hex})[/{info_color}]"
            return f"{value_with_tag} {symbol} {info_with_tag}"
        return f"{formatted_value} {symbol} ({type(_value).__name__})(org: {self.hex})"

    def format(self, format_type="hex", precision=4):

        """
        Format the output as hex, decimal, or scientific notation.

        :param format_type: Output format ("hex", "decimal", or "scientific").
        :type format_type: str
        :param precision: Decimal precision for `decimal` and `scientific` formats.
        :type precision: int
        :return: Formatted output.
        :rtype: str
        :raises ValueError: If `format_type` is unsupported.

        Example:

            .. code-block:: python

                hex_value = HexValue(26)
                print(hex_value.format("hex"))         # '0x1a'
                print(hex_value.format("decimal"))     # '26.0000'
                print(hex_value.format("scientific"))  # '2.60e+01'
        """

        if format_type == "hex":
            return self.to_hex()
        elif format_type == "decimal":
            return f"{self.decimal:.{precision}f}"
        elif format_type == "scientific":
            return f"{self.decimal:.{precision}e}"
        else:
            raise ValueError("Unsupported format type")

    def to_unit(self, unit_conversion_factor):
        """Convert to a different unit by specifying a conversion factor."""
        return self.numeric / unit_conversion_factor

    def __add__(self, other):
        if isinstance(other, HexValue):
            new_numeric = self.numeric + other.numeric
        elif isinstance(other, str) and self.is_hex(other):
            # If `other` is a hex string, convert it to an integer
            new_numeric = self.numeric + int(other, 16)
        elif isinstance(other, (int, float)):
            new_numeric = self.numeric + int(other)
        else:
            raise TypeError("Addition is only supported with HexValue, hex string, int, or float")
        return HexValue(new_numeric)

    def __radd__(self, other):
        return self.__add__(other)

    # Subtraction and reverse subtraction
    def __sub__(self, other):
        if isinstance(other, HexValue):
            new_numeric = self.numeric - other.numeric
        elif isinstance(other, str) and self.is_hex(other):
            # Convert hex string to integer before subtraction
            new_numeric = self.numeric - int(other, 16)
        elif isinstance(other, (int, float)):
            new_numeric = self.numeric - int(other)
        else:
            raise TypeError("Subtraction is only supported with HexValue, hex string, int, or float")
        return HexValue(new_numeric)

    def __rsub__(self, other):
        if isinstance(other, str) and self.is_hex(other):
            # Convert hex string to integer before reverse subtraction
            new_numeric = int(other, 16) - self.numeric
            return HexValue(new_numeric)
        elif isinstance(other, (int, float)):
            new_numeric = int(other) - self.numeric
            return HexValue(new_numeric)
        raise TypeError("Subtraction is only supported with HexValue, hex string, int, or float")

    # Multiplication and reverse multiplication
    def __mul__(self, other):
        if isinstance(other, HexValue):
            new_numeric = self.numeric * other.numeric
        elif isinstance(other, str) and self.is_hex(other):
            # Convert hex string to integer before multiplication
            new_numeric = self.numeric * int(other, 16)
        elif isinstance(other, (int, float)):
            new_numeric = self.numeric * int(other)
        else:
            raise TypeError("Multiplication is only supported with HexValue, hex string, int, or float")
        return HexValue(new_numeric)

    def __rmul__(self, other):
        return self.__mul__(other)

    # Division and reverse division
    def __truediv__(self, other):
        if isinstance(other, HexValue):
            if other.numeric == 0:
                raise ZeroDivisionError("Division by zero")
            new_numeric = self.numeric / other.numeric
        elif isinstance(other, str) and self.is_hex(other):
            other_numeric = int(other, 16)
            if other_numeric == 0:
                raise ZeroDivisionError("Division by zero")
            new_numeric = self.numeric / other_numeric
        elif isinstance(other, (int, float)):
            if other == 0:
                raise ZeroDivisionError("Division by zero")
            new_numeric = self.numeric / int(other)
        else:
            raise TypeError("Division is only supported with HexValue, hex string, int, or float")
        return HexValue(int(new_numeric))

    def __rtruediv__(self, other):
        if isinstance(other, str) and self.is_hex(other):
            other_numeric = int(other, 16)
            if self.numeric == 0:
                raise ZeroDivisionError("Division by zero")
            new_numeric = other_numeric / self.numeric
            return HexValue(int(new_numeric))
        elif isinstance(other, (int, float)):
            if self.numeric == 0:
                raise ZeroDivisionError("Division by zero")
            new_numeric = int(other) / self.numeric
            return HexValue(int(new_numeric))
        raise TypeError("Division is only supported with HexValue, hex string, int, or float")

    # Floor division and reverse floor division
    def __floordiv__(self, other):
        if isinstance(other, HexValue):
            new_numeric = self.numeric // other.numeric
        elif isinstance(other, str) and self.is_hex(other):
            # Convert hex string to integer before floor division
            new_numeric = self.numeric // int(other, 16)
        elif isinstance(other, int):
            new_numeric = self.numeric // other
        else:
            raise TypeError("Floor division is only supported with HexValue, hex string, or int")
        return HexValue(new_numeric)

    def __rfloordiv__(self, other):
        if isinstance(other, str) and self.is_hex(other):
            # Convert hex string to integer before reverse floor division
            new_numeric = int(other, 16) // self.numeric
            return HexValue(new_numeric)
        elif isinstance(other, int):
            new_numeric = other // self.numeric
            return HexValue(new_numeric)
        raise TypeError("Floor division is only supported with HexValue, hex string, or int")

    def __mod__(self, other):
        if isinstance(other, HexValue):
            new_numeric = self.numeric % other.numeric
        elif isinstance(other, str) and self.is_hex(other):
            new_numeric = self.numeric % int(other, 16)
        elif isinstance(other, int):
            new_numeric = self.numeric % other
        else:
            raise TypeError("Modulus is only supported with HexValue, hex string, or int")
        return HexValue(new_numeric)

    def __rmod__(self, other):
        if isinstance(other, str) and self.is_hex(other):
            new_numeric = int(other, 16) % self.numeric
            return HexValue(new_numeric)
        elif isinstance(other, int):
            new_numeric = other % self.numeric
            return HexValue(new_numeric)
        raise TypeError("Modulus is only supported with HexValue, hex string, or int")

    @classmethod
    def from_hex(cls, hex_str):
        """
        Initialize a HexValue instance from a hex string.

        :param hex_str: A valid hexadecimal string.
        :type hex_str: str
        :return: A new HexValue instance initialized with the hex string.
        :rtype: HexValue
        """
        if cls.is_hex(hex_str):
            return cls(int(hex_str, 16))
        else:
            raise ValueError("Invalid hex string")

    @staticmethod
    def is_hex(s) -> bool:
        """
        Check if a value is hexadecimal
        """
        if not isinstance(s, str):
            return False
        if s.startswith(("0x", "0X")):
            s = s[2:]  # Remove '0x' prefix for validation
        try:
            int(s, 16)
        except TypeError:
            return False
        except ValueError:
            return False
        return True

    # Exponentiation and reverse exponentiation
    def __pow__(self, exponent):
        if isinstance(exponent, HexValue):
            new_numeric = self.numeric ** exponent.numeric
        elif isinstance(exponent, str) and self.is_hex(exponent):
            # Convert hex string to integer before exponentiation
            new_numeric = self.numeric ** int(exponent, 16)
        elif isinstance(exponent, (int, float)):
            new_numeric = self.numeric ** exponent
        else:
            raise TypeError("Exponentiation requires a HexValue, hex string, int, or float exponent")
        return HexValue(int(new_numeric))

    def __rpow__(self, base):
        if isinstance(base, str) and self.is_hex(base):
            # Convert hex string to integer before reverse exponentiation
            new_numeric = int(base, 16) ** self.numeric
            return HexValue(int(new_numeric))
        elif isinstance(base, (int, float)):
            new_numeric = base ** self.numeric
            return HexValue(int(new_numeric))
        raise TypeError("Exponentiation requires a hex string, int, or float base")

    # Bitwise AND and reverse AND
    def __and__(self, other):
        if isinstance(other, HexValue):
            new_numeric = self.numeric & other.numeric
        elif isinstance(other, int):
            new_numeric = self.numeric & other
        else:
            raise TypeError("Bitwise AND is only supported with HexValue and int")
        return HexValue(hex(new_numeric))

    def __rand__(self, other):
        return self.__and__(other)

    def __eq__(self, other):
        return isinstance(other, HexValue) and self.numeric == other.numeric

    def __ne__(self, other):
        return not self == other

    def __neg__(self):
        return HexValue(hex(-self.numeric))

    def __pos__(self):
        return HexValue(hex(+self.numeric))

    def __lt__(self, other):
        if isinstance(other, HexValue):
            return self.numeric < other.numeric
        elif isinstance(other, (int, float)):
            return self.numeric < other
        raise TypeError("Comparison is only supported with HexValue, int, or float")

    def __le__(self, other):
        if isinstance(other, HexValue):
            return self.numeric <= other.numeric
        elif isinstance(other, (int, float)):
            return self.numeric <= other
        raise TypeError("Comparison is only supported with HexValue, int, or float")

    def __gt__(self, other):
        if isinstance(other, HexValue):
            return self.numeric > other.numeric
        elif isinstance(other, (int, float)):
            return self.numeric > other
        raise TypeError("Comparison is only supported with HexValue, int, or float")

    def __ge__(self, other):
        if isinstance(other, HexValue):
            return self.numeric >= other.numeric
        elif isinstance(other, (int, float)):
            return self.numeric >= other
        raise TypeError("Comparison is only supported with HexValue, int, or float")


class HexTintValue(HexValue):
    def __init__(self, value=None, debug_info=None):
        """
        Initialize a HexTintValue instance. If the numeric value is less than 10**18,
        it scales the value by multiplying by 10**18.

        :param value: The initial value, which can be a hex string, integer, or float.
        :type value: str | int | float
        :param debug_info: Optional debug information for logging purposes.
        :type debug_info: Any
        """
        scale_factor = const.ICX_IN_LOOP
        if value and value < scale_factor:
            value = int(value *  scale_factor)
        super().__init__(value, debug_info)  # Initialize as HexValue

    def __repr__(self):
        debug_info_str = f", debug_info={self.debug_info}" if self.debug_info is not None else ""
        tint_str = f"{self.tint:.18f}".rstrip('0').rstrip('.') if self.tint is not None else "None"
        return (f"HexTintValue(hex={self.hex}, "
                f"decimal={self.decimal}, "
                f"numeric={self.numeric}, "
                f"readable_number={self.readable_number}, "
                f"tint={tint_str}"
                f"{debug_info_str})")


# class HexValueParser:
#
#     EXCLUDED_KEYS = {"logsBloom", "txHash", "data", "blockHash"}
#     def __new__(cls, data):
#         return cls.parse(data)
#     @staticmethod
#     def parse(data, debug_info=None):
#         """Recursively convert lists or dicts to HexResponse instances if they are hex strings."""
#         if data is None:
#             return None
#         elif isinstance(data, list):
#             return [HexValueParser.parse(item, debug_info) for item in data]
#         # elif isinstance(data, dict):
#         #     return {key: HexValueParser.parse(value, debug_info) for key, value in data.items()}
#         elif isinstance(data, dict):
#             pawn.console.log(data)
#             return {key: HexValueParser.parse(value, debug_info) if key not in HexValueParser.EXCLUDED_KEYS else value
#                     for key, value in data.items()}
#         elif isinstance(data, str) and HexValue.is_hex(data):  # Only convert if it's a hex string
#             return HexValue(data, debug_info)
#         else:
#             return data  # Return as-is if it's not a hex string


class HexValueParser:
    EXCLUDED_KEYS = {"logsBloom", "txHash", "data", "blockHash"}
    def __new__(cls, data):
        return cls.parse(data)

    @staticmethod
    def parse(data, debug_info=None):
        """Recursively convert lists or dicts to HexResponse instances if they are hex strings, except for excluded keys."""
        if data is None:
            return None
        elif isinstance(data, list):
            # Recursively parse each item in the list
            return [HexValueParser.parse(item, debug_info) for item in data]
        elif isinstance(data, dict):
            # Parse each key-value pair in the dict, skipping excluded keys and their nested structures
            parsed_data = {}
            for key, value in data.items():
                if key in HexValueParser.EXCLUDED_KEYS:
                    parsed_data[key] = value  # Skip parsing for excluded keys
                else:
                    parsed_data[key] = HexValueParser.parse(value, debug_info)
            return parsed_data
        elif isinstance(data, str) and HexValue.is_hex(data):
            # Only convert if it's a hex string and not in EXCLUDED_KEYS
            return HexValue(data, debug_info)
        else:
            # Return the data as-is if it's not a hex string
            return data



class HttpResponse:
    def __init__(self, status_code=999, response=None, error=None, elapsed=None, success=False):
        self.status_code = status_code
        self.response = response
        self.error = error
        self.elapsed = elapsed
        self.success = success
        self.response_time = elapsed
        self.reason = ""
        self.result = ""
        self.text = ""
        self.json = {}

        if getattr(response, "text", ""):
            self.response = response.text

        if self.response and self.response.json:
            self.json = self.response.json
        else:
            self.json = {}

        if self.error:
            self.ok = False
        else:
            self.ok = True

    def __str__(self):
        return f"<HttpResponse> status_code={self.status_code}, response={self.response}, error={self.error}"

    def __repr__(self):
        return f"<HttpResponse> {self.status_code}, {self.response}, {self.error}"

    def as_dict(self):
        return self.__dict__


class HTTPStatus:
    STATUS_CODES = {
        100: "Continue",
        101: "Switching Protocols",
        102: "Processing",
        200: "OK",
        201: "Created",
        202: "Accepted",
        203: "Non-Authoritative Information",
        204: "No Content",
        205: "Reset Content",
        206: "Partial Content",
        207: "Multi-Status",
        208: "Already Reported",
        226: "IM Used",
        300: "Multiple Choices",
        301: "Moved Permanently",
        302: "Found",
        303: "See Other",
        304: "Not Modified",
        305: "Use Proxy",
        307: "Temporary Redirect",
        308: "Permanent Redirect",
        400: "Bad Request",
        401: "Unauthorized",
        402: "Payment Required",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        406: "Not Acceptable",
        407: "Proxy Authentication Required",
        408: "Request Timeout",
        409: "Conflict",
        410: "Gone",
        411: "Length Required",
        412: "Precondition Failed",
        413: "Payload Too Large",
        414: "URI Too Long",
        415: "Unsupported Media Type",
        416: "Range Not Satisfiable",
        417: "Expectation Failed",
        418: "I'm a teapot",
        421: "Misdirected Request",
        422: "Unprocessable Entity",
        423: "Locked",
        424: "Failed Dependency",
        425: "Too Early",
        426: "Upgrade Required",
        428: "Precondition Required",
        429: "Too Many Requests",
        431: "Request Header Fields Too Large",
        451: "Unavailable For Legal Reasons",
        500: "Internal Server Error",
        501: "Not Implemented",
        502: "Bad Gateway",
        503: "Service Unavailable",
        504: "Gateway Timeout",
        505: "HTTP Version Not Supported",
        506: "Variant Also Negotiates",
        507: "Insufficient Storage",
        508: "Loop Detected",
        510: "Not Extended",
        511: "Network Authentication Required",
    }

    def __init__(self, code):
        self.code = code

    def get_description(self):
        return f"{self.code} {self.STATUS_CODES.get(self.code, 'Unknown Status')}"

    def __repr__(self):
        return f"{self.code} {self.STATUS_CODES.get(self.code, 'Unknown Status')}"


class ResponseWithElapsed(Response):
    success = False
    error = None
    status_code_with_message = None

    def __init__(self):
        super().__init__()
        self.success = False
        self.error = None
        self.status_code_with_message = None
        self.result = None
        self.json_content = None
        self.text_content = None

    def __repr__(self):
        return f"<Response [{HTTPStatus(self.status_code)}], {self.elapsed}ms, succ={self.success}>"

    def __str__(self):
        return f"<Response [{HTTPStatus(self.status_code)}], {self.elapsed}ms, succ={self.success}>"

    def as_dict(self):

        if not self.__dict__.get('result'):
            try:
                self.__dict__['result'] = self.__dict__['_content'].decode('utf-8')
            except:
                pass

        if self.__dict__.get('result') and isinstance(self.__dict__.get('result'), (dict, list)):
            self.__dict__['json'] = self.__dict__['result']
            self.__dict__['text'] = json.dumps(self.__dict__['result'])

        else:
            try:
                self.__dict__['json'] = json.loads(self.__dict__['result'])
            except:
                self.__dict__['json'] = {}
        return self.__dict__

    def as_simple_dict(self):
        if not hasattr(self, 'result') or self.result is None:
            try:
                self.result = self._content.decode('utf-8')
            except AttributeError:
                self.result = None

        if isinstance(self.result, (dict, list)):
            self.json_content = self.result
            self.text_content = json.dumps(self.result)
        else:
            try:
                self.json_content = json.loads(self.result)
            except (json.JSONDecodeError, TypeError):
                self.json_content = {}
            self.text_content = self.result

        return {
            "success": self.success,
            "error": self.error,
            "status_code": self.status_code,
            "elapsed": self.elapsed,
            "json": self.json_content,
            "text": self.text_content
        }

from requests import Session
class PatchedSession(Session):
    def request(self, *args, **kwargs):
        response = super().request(*args, **kwargs)
        response.__class__ = ResponseWithElapsed  # 응답 객체를 ResponseWithElapsed로 변경
        return response
