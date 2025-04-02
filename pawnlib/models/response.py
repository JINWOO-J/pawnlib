import struct
from decimal import Decimal, InvalidOperation, getcontext, ROUND_DOWN
from datetime import datetime, date
from pawnlib.typing.constants import const
from pawnlib.config import pawn
import re
from rich.text import Text
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
    default_max_unit = None
    default_decimal_places = 3
    default_use_tint = True
    default_symbol = ""
    default_format_type = None

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
            if self.numeric != 0:
                self.tint = self.numeric / const.ICX_IN_LOOP
            else:
                self.tint = 0
        else:
            # Default values for uninitialized state
            self.decimal = None
            self.tint = None
            self.numeric = None
        
        if value is None:
            self.readable_number = None
        else:
            self.readable_number = self.format_readable()
            

    @classmethod
    def set_default_max_unit(cls, max_unit):
        """
        Set the default max_unit for all HexValue instances.

        :param max_unit: The maximum unit to use for formatting (e.g., 'K', 'M', 'B', 'T', 'Q').
        :type max_unit: str | None
        """
        cls.default_max_unit = max_unit.upper() if max_unit else None

    @classmethod
    def set_default_format_type(cls, format_type):
        """
        Set the default format type for all HexValue instances.
        """
        cls.default_format_type = format_type

    @classmethod
    def set_default_decimal_places(cls, decimal_places):
        """
        Set the default decimal places for all HexValue instances.
        :param decimal_places: The number of decimal places to display for values less than 1.
        :type decimal_places: int
        :return: None

        """
        cls.default_decimal_places = decimal_places

    @classmethod
    def set_default_use_tint(cls, use_tint):
        """
        Set the default use_tint for all HexValue instances.
        :param use_tint: If True, use the tint value for formatting. If False, use the numeric value.
        :type use_tint: bool
        :return: None
        """        
        cls.default_use_tint = use_tint    
    
    @classmethod
    def set_default_symbol(cls, symbol):
        """
        Set the default symbol for all HexValue instances.
        """
        cls.default_symbol = symbol
        
    def format_readable(self, max_unit=None, use_tint=None, decimal_places=None, symbol=None):
        """
        Convert the numeric value to a human-readable string, flooring the value and using the specified or default max_unit.
        For values less than 1, display with decimal places.

        :param max_unit: The maximum unit to use for formatting (e.g., 'K', 'M', 'B', 'T', 'Q'). If None, uses the class default.
        :type max_unit: str | None
        :param use_tint: If True, use the tint value for formatting. If False, use the numeric value.
        :type use_tint: bool
        :param decimal_places: The number of decimal places to display for values less than 1.
        :type decimal_places: int
        :return: A human-readable string representation of the number.
        :rtype: str
        :param symbol: The symbol to use for the value.
        :type symbol: str
        """
        value = self.numeric

        use_tint = use_tint if use_tint is not None else self.__class__.default_use_tint
        decimal_places = decimal_places if decimal_places is not None else self.__class__.default_decimal_places
        symbol = symbol if symbol is not None else self.__class__.default_symbol

        if value == 0:
            return "0"

        sign = '-' if value < 0 else ''
        value = abs(value)

        if use_tint or value > const.ICX_IN_LOOP:
            value = value / const.ICX_IN_LOOP
        
        units = [
            (1e15, 'Q'), (1e12, 'T'), (1e9, 'B'), (1e6, 'M'), (1e3, 'K'), (1, '')
        ]

        effective_max_unit = (max_unit.upper() if max_unit else self.__class__.default_max_unit) if max_unit or self.__class__.default_max_unit else None

        if effective_max_unit:
            unit_order = [unit[1] for unit in units]  # ['Q', 'T', 'B', 'M', 'K', '']
            if effective_max_unit in unit_order:
                max_index = unit_order.index(effective_max_unit)
                filtered_units = units[max_index:]
            else:
                filtered_units = units  
        else:
            filtered_units = units
        
        if value >= 1:
            for divisor, unit in filtered_units:
                if value >= divisor:
                    floored_value = int(value / divisor)
                    formatted_value = f"{floored_value:,}"
                    return f"{sign}{formatted_value}{unit}{' ' + symbol if symbol else ''}"
                
            formatted_value = f"{int(value):,}"
        else:            
            if decimal_places is None:
                formatted_value = f"{value:.18f}".rstrip('0').rstrip('.')
            else:
                formatted_value = f"{value:.{decimal_places}f}"
                # Check if it's "0.000..." (handle as a string without converting to float)
                if formatted_value.startswith("0.") and all(c == '0' for c in formatted_value[2:]):
                    formatted_value = f"{value:.18f}".rstrip('0').rstrip('.')
                else:
                    formatted_value = formatted_value.rstrip('0').rstrip('.')
                
        return f"{sign}{formatted_value}{' ' + symbol if symbol else ''}"

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
                f"readable_number={self.readable_number}, "
                f"tint={tint_str}, "
                f"default_max_unit={HexValue.default_max_unit}, "
                f"default_decimal_places={HexValue.default_decimal_places}, "
                f"default_use_tint={HexValue.default_use_tint}"
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
        if self.decimal != 0:
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

        if self.__class__.default_format_type == "readable_number":            
            return self.readable_number

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
    default_max_unit = "K"
    default_decimal_places = 3
    default_use_tint = True
    default_symbol = "ICX"

    def __init__(self, value=None, debug_info=None):
        """
        Initialize a HexTintValue instance. If the numeric value is less than 10**18,
        it scales the value by multiplying by 10**18.

        :param value: The initial value, which can be a hex string, integer, or float.
        :type value: str | int | float
        :param debug_info: Optional debug information for logging purposes.
        :type debug_info: Any
        """
        if value is None:
            raise ValueError("Value cannot be None")        

        scale_factor = const.ICX_IN_LOOP        

        if isinstance(value, str):
            if value.startswith("0x"):
                try:
                    value = int(value, 16) / scale_factor
                except ValueError:
                    raise ValueError(f"Invalid hex string: {value}")
            else:
                raise ValueError(f"String value must be a hex string starting with '0x', got: {value}")
        elif not isinstance(value, (int, float)):
            raise ValueError(f"Value must be str, int, or float, got: {type(value)}")

        

        if isinstance(value, (int, float)) and value < scale_factor:
            value = int(value * scale_factor)

        super().__init__(value, debug_info)  # Initialize as HexValue

    def __repr__(self):
        debug_info_str = f", debug_info={self.debug_info}" if self.debug_info is not None else ""
        tint_str = f"{self.tint:.18f}".rstrip('0').rstrip('.') if self.tint is not None else "None"
        return (f"HexTintValue(hex={self.hex}, "
                f"decimal={self.decimal}, "
                f"numeric={self.numeric}, "
                f"readable_number={self.readable_number}, "
                f"tint={tint_str}, "
                f"default_max_unit={HexTintValue.default_max_unit}, "
                f"default_decimal_places={HexTintValue.default_decimal_places}, "
                f"default_use_tint={HexTintValue.default_use_tint}, "
                f"default_symbol={HexTintValue.default_symbol}"
                f"{debug_info_str})")


class HexValueParser:
    EXCLUDED_KEYS = {"logsBloom", "txHash", "data", "blockHash"}
    def __new__(cls, data, debug_info=None, attribute=None):        
        return cls.parse(data, debug_info=debug_info, attribute=attribute)

    @staticmethod
    def parse(data, debug_info=None, attribute=None):
        """Recursively convert lists or dicts to HexResponse instances if they are hex strings, except for excluded keys."""
        if data is None:
            return None
        elif isinstance(data, list):
            # Recursively parse each item in the list
            return [HexValueParser.parse(item, debug_info=debug_info, attribute=attribute) for item in data]
        elif isinstance(data, dict):            
            parsed_data = {}
            for key, value in data.items():
                if key in HexValueParser.EXCLUDED_KEYS:
                    parsed_data[key] = value
                else:
                    parsed_data[key] = HexValueParser.parse(value, debug_info=debug_info, attribute=attribute)
            return parsed_data        
        elif isinstance(data, str) and HexValue.is_hex(data):
            hex_value = HexValue(data, debug_info)
            if attribute and hasattr(hex_value, attribute):
                return getattr(hex_value, attribute)
            return hex_value
        else:            
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


class CriticalText:
    def __init__(self, column="", value="", cores=1, warning_percent=75, medium_percent=50, low_percent=30, align_space=0, limits=None):
        """
        Initialize CriticalText.

        Args:
            column (str): The column name for the metric.
            value (str): The value to evaluate.
            cores (int): Number of CPU cores for scaling certain metrics.
            warning_percent (int): Threshold percentage for warning level.
            medium_percent (int): Threshold percentage for medium level.
            low_percent (int): Threshold percentage for low level.
            align_space (int): Space for text alignment.
            limits (dict): Dictionary of column-specific limits.
        """
        self.column = column
        self.value = value
        self.number_value = self.extract_first_number(str(value))
        self.align_space = align_space
        self.limits = limits or {
            "net_in": 100,
            "net_out": 100,
            "usr": 80,
            "sys": 80,
            "mem_used": 99.5,
            "disk_rd": 400,
            "disk_wr": 400,
            "mem_%": 90,
            "load": cores,
            "i/o": cores * 2,
        }
        self.warning_percent = warning_percent
        self.medium_percent = medium_percent
        self.low_percent = low_percent

    @staticmethod
    def extract_first_number(text):
        """
        Extract the first number from a given text.

        Args:
            text (str): Input string.

        Returns:
            float: Extracted number or None if no number found.
        """
        match = re.match(r'\d+(\.\d+)?', text)
        return float(match.group()) if match else 0

    def check_limit(self):
        """
        Determine the color based on the value and defined thresholds.

        Returns:
            str: Color name or code.
        """
        limit_value = self.limits.get(self.column)
        if limit_value is not None:
            if self.number_value >= limit_value:
                return "bold red"
            elif self.number_value >= (limit_value * self.warning_percent / 100):
                return "#FF9C3F"  # Warning Orange
            elif self.number_value >= (limit_value * self.medium_percent / 100):
                return "yellow"
            elif self.number_value >= (limit_value * self.low_percent / 100):
                return "green"
        return "white"

    def return_text(self):
        """
        Generate a styled text object.

        Returns:
            Text: Styled rich Text object.
        """
        return Text(f"{self.value:>{self.align_space}}", self.check_limit())

    def __str__(self):
        """
        Generate a string representation.

        Returns:
            str: Styled text string.
        """
        return str(self.return_text())

    def __rich__(self):
        """
        Return a rich Text object for rendering.

        Returns:
            Text: Styled rich Text object.
        """
        return Text(f"{self.value:>{self.align_space}}", self.check_limit())

    def set_limits(self, new_limits):
        """
        Update limits dynamically.

        Args:
            new_limits (dict): New limits dictionary.
        """
        self.limits.update(new_limits)


def json_default_serializer(obj):
    """
    A default JSON serializer function to handle non-serializable objects.

    Example usage:
        json.dumps(data, default=json_default_serializer)

    1) HexValue objects: use `.output()`.
    2) Date/time objects: use `isoformat()`.
    3) If an object has `__json__()` or `to_dict()`, call it.
    4) Otherwise, return str(obj) (or raise TypeError if you want strict handling).
    """

    # 1) Handle HexValue
    if isinstance(obj, HexValue):
        return obj.output()

    # 2) Handle date/datetime
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    # 3) Check for other serialization methods
    if hasattr(obj, "__json__") and callable(obj.__json__):
        return obj.__json__()
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        return obj.to_dict()

    # 4) Fallback for unknown types
    #    (You could raise TypeError instead if you want stricter behavior)
    return str(obj)
