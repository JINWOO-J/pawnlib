import json
import os
import operator as _operator
from pawnlib.config import pawnlib_config as pawn, pconf
from pawnlib.typing import is_hex, is_int, is_float, FlatDict, Namespace, sys_exit, is_valid_token_address, is_valid_private_key
from pawnlib.output.file import get_file_list
from InquirerPy import prompt, inquirer, get_style
from InquirerPy.validator import NumberValidator
from prompt_toolkit.validation import ValidationError, Validator, DynamicValidator
from prompt_toolkit.shortcuts import prompt as toolkit_prompt
import string
from typing import Callable
all_special_characters = string.punctuation

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal


class PromptWithArgument:
    def __init__(self, argument="", min_length=1, max_length=1000, verbose=1,  **kwargs):
        self.argument = argument
        self._options = kwargs
        self.argument_name = ""
        self.argument_value = ""
        self.func_name = ""
        self.min_length = min_length
        self.max_length = max_length
        self.verbose = verbose
        self._args = None

        self._arg_missing_word = "DO_NOT_SET_THE_ARG"

        self.unnecessary_options = {
            "fuzzy": ["name", "type"],
            "select": ["type"],
            "checkbox": ["name"],
        }

        self.message_prefix_text = {
            "prompt": "Input the",
            "fuzzy": "Select the",
            "checkbox": "Choice the",
        }

        self.default_options = dict(
            checkbox=dict(
                enabled_symbol="✅",
                disabled_symbol="◻️ ",
                validate=lambda result: len(str(result)) >= 1,
                invalid_message="should be at least 1 selection",
                instruction="(select at least 1)",
            ),
            select=dict(
                # pointer="➡️ ",
                pointer=" 👉"
            )
        )

    def _prepare(self, **options):
        self._parse_options(**options)
        self._set_style()
        self._set_default_options()

    def _set_style(self, style_type='fuzzy'):
        default_style = {
            "input": "#98c379 bold",
            "answer": "#61afef bold",
            "long_instruction": "#96979A italic",
            "instruction": "italic bold #b6b8ba",
            "question": "italic bold #ffffff",
            "fuzzy_info": "#474747",
        }
        if self.func_name == 'fuzzy':
            self._options['style'] = get_style(default_style, style_override=False)
        elif self.func_name == 'prompt':
            self._options['style'] = {
                # "questionmark": "#ffffff",
                # "answer": "#000000",
                "answer": default_style.get('answer'),
                "question": default_style.get('question'),
                "input": default_style.get('input'),
                "long_instruction": default_style.get('long_instruction'),
            }
        elif self.func_name == 'checkbox':
            self._options['style'] = get_style(default_style, style_override=False)

        # self._options.update(mark_options)

    def _set_default_options(self):
        common_mark_options = dict(
            qmark="[❓]",
            amark="[❓]",
        )
        if self.func_name and self.default_options.get(self.func_name):
            _default_option = self.default_options[self.func_name]
            _default_option.update(common_mark_options)
            for key, value in _default_option.items():
                if  key not in self._options:
                    self._options[key] = value

    def _extract_option_to_variable(self, keys=None):
        for key in keys:
            if self._options.get(key):
                print(key)
                setattr(self, key, self._options.pop(key))

    def _parse_options(self, **options):
        # _arg_missing_word = "DO_NOT_SET_THE_ARG"
        try:
            self._args = pconf().data.args
        except Exception as e:
            self._args = None
            pawn.console.debug(f"[yellow] Error parsing - {e}")

        try:
            category = f"[{self._args.subparser_name.upper()}]"
        except:
            category = ""

        if options:
            self._options = options

        if self._options.get('message', self._arg_missing_word) == self._arg_missing_word and self._options.get('name'):
            self._options['message'] = f"{self.message_prefix_text.get(self.func_name, 'Input')} {self._options.get('name').title()}"

        if not self._options:
            raise ValueError(f"Required argument, {self._options}")
        self._extract_option_to_variable(["min_length", "max_length", "argument", ])

        if self.argument:
            self.argument_name = self.argument
            self.argument_name_real = self.argument.replace("_", "-")
            if self._args:
                self.argument_value = self._args.__dict__.get(self.argument_name, self._arg_missing_word)

            _default_value = self._options.get('default')
            # if self._options.get('verbose'):
            if self.verbose:
                self._options['instruction'] = self._options.get('instruction', "") + f"( --{self.argument_name_real} )"

        # if _arg_missing_word == self.argument_value:
        #     raise ValueError(f"Cannot find argument in args. {self.argument}")

        if not self._options.get('invalid_message', None):
            self._options['invalid_message'] = "minimum 1 selection"
        if not self._options.get('validate', None):
            self._options['validate'] = lambda result: len(str(result)) >= 1

        self._options['message'] = f"{category} {self._options.get('message', 'undefined message')}"

        if self.func_name == "prompt":
            if self._options.get('type', self._arg_missing_word) == self._arg_missing_word:
                self._options['type'] = "input"
            # else:
            #     if self._options['type'] == "list":
            #         self._options['type'] = "select"

            # _options = dict(
            #     qmark="[❓]",
            #     amark="[❓]",
            # )
            # self._options.update(_options)
        self._remove_unnecessary_options()

    def _remove_unnecessary_options(self):
        if self.unnecessary_options.get(self.func_name):
            for param in self.unnecessary_options[self.func_name]:
                if param in self._options:
                    del self._options[param]

    def _push_argument(self, result="", target_args=None):
        try:
            if not target_args:
                target_args = pconf().data.args
            setattr(target_args, self.argument, result)
        except:
            pawn.console.debug(f"args not found, {target_args}, {self.argument}, {result}")

    def _skip_if_value_in_args(self):
        if self.argument_value:
            return True

    def _common_executes_decorator(func):
        def executor(self, *args, **kwargs):
            # pawn.console.debug(f"Starting executor - {func.__name__}")
            self.func_name = func.__name__
            self._prepare()

            # if self.argument_value == self._arg_missing_word:
            #     self.argument_value = ""
            if not self.argument_value or self.argument_value == "" or self.argument_value == self._arg_missing_word:
                result = func(self, *args, **kwargs)
                if self.argument_value != self._arg_missing_word:
                    self._push_argument(result)
            else:
                self.argument_real_name = self.argument_name.replace("_", "-")
                if self.verbose > 0:
                    if self._options.get('type') == "password" and not pawn.get("PAWN_DEBUG"):
                        _argument_value = f"{len(self.argument_value)*'*'}"
                    else:
                        _argument_value = self.argument_value
                    pawn.console.debug(f"Skipped [yellow]{self._options.get('name','')}[/yellow]"
                                     f"prompt cause args value exists. --{self.argument_real_name}={_argument_value}")
                self._check_force_validation(name=self.argument_real_name, value=self.argument_value)
                result = self._check_force_filtering(name=self.argument_real_name, value=self.argument_value)
            return result
        return executor

    def _check_force_validation(self, name=None, value=None):
        try:
            _validator = self._options.get('validate')
            if _validator:
                # pawn.console.debug(f"force validation name={name} value={value}")
                if getattr(_validator, 'validate', None):
                    document = Namespace(**dict(text=value, cursor_position=name))
                    _validator.validate(document)
        except ValidationError as e:
            sys_exit(f"[bold]Failed to validate[/bold] : {e}")

    def _check_force_filtering(self, name=None, value=None):
        try:
            _filtering = self._options.get('filter')
            if _filtering:
                pawn.console.debug(f"force filtering name={name} value={value} return={_filtering(value)}")
                return _filtering(value)
        except ValidationError as e:
            sys_exit(f"[bold]Failed to filtering : {e}")
        return value

    @_common_executes_decorator
    def fuzzy(self, **kwargs):
        if kwargs:
            self._prepare(**kwargs)
        if not self.argument_value:
            _prompt = inquirer.fuzzy(**self._options)
            input_value = _prompt.execute()
            # self._push_argument(result=input_value)
            return input_value
        else:
            pawn.console.debug(f"Skipped prompt, {self.argument_name}={self.argument_value}")
            return False

    @_common_executes_decorator
    def prompt(self, *args, **kwargs):
        _args_options_name = self._options.get('name', '')
        if args:
            answer = prompt(*args)
        else:
            style = None
            self._set_style(style_type="prompt")
            if self._options.get('style'):
                style = self._options.pop('style')
            pawn.console.log(f"self._options={self._options},  style={style}")
            answer = prompt(questions=self._options, style=style, style_override=False)
            if answer.get('name'):
                return answer['name']
            elif answer.get(_args_options_name, '__NOT_DEFINED__') != "__NOT_DEFINED__" :
                return answer[_args_options_name]
            elif len(answer) > 0:
                return answer[0]
            else:
                pawn.console.log(f"[red] Parse Error on prompt, answer={answer}")

    @_common_executes_decorator
    def checkbox(self, *args, **kwargs):

        return inquirer.checkbox(
            **self._options
        ).execute()

    @_common_executes_decorator
    def select(self, *args, **kwargs):

        return inquirer.select(
            **self._options
        ).execute()


class CompareValidator(NumberValidator):
    """
    Validator that compares the input value with the given operator and length.

    :param operator: Comparison operator. Allowed operators are '!=', '==', '>=', '<=', '>', and '<'.
    :type operator: Literal["!=", "==", ">=", "<=", ">", "<"]
    :param length: Length of the input value.
    :type length: int
    :param message: Error message to display when the validation fails.
    :type message: str
    :param float_allowed: Flag to allow float input values.
    :type float_allowed: bool
    :param value_type: Type of the input value. Allowed types are 'number', 'string', and 'min_max'.
    :type value_type: str
    :param min_value: Minimum value for 'min_max' value type.
    :type min_value: int
    :param max_value: Maximum value for 'min_max' value type.
    :type max_value: int

    Example:

        .. code-block:: python

            validator = CompareValidator(
                operator=">=",
                length=3,
                message="Input should be a number greater than or equal to 3",
                float_allowed=True,
                value_type="number",
                min_value=3
            )

            validator.validate(document)
    """
    def __init__(
            self,
            operator: Literal["!=", "==", ">=", "<=", ">", "<"] = ">=",
            length: int = 0,
            message: str = "Input should be a ",
            float_allowed: bool = False,
            value_type="number",
            min_value: int = 0,
            max_value: int = 0,

    ) -> None:
        super().__init__(message, float_allowed)

        self._allowed_operators = ["!=", "==", ">=", "<=", ">", "<"]

        if operator not in self._allowed_operators:
            raise ValueError(f"Invalid operator, allows={self._allowed_operators}")

        self._message = f"{message} <{value_type.title()}> {operator}"
        if length:
            self._message = f"{self._message} {length}"
        self._float_allowed = float_allowed
        self._operator = operator
        self._length = length
        self._value_type = value_type

        self._min = min_value
        self._max = max_value

    def raise_error(self, document, message=""):
        """
        Raises a ValidationError with the given error message.

        :param document: The document being validated.
        :type document: Any
        :param message: The error message to display.
        :type message: str
        """
        _message = f"{self._message}, {message}"
        raise ValidationError(
            message=_message, cursor_position=document.cursor_position
        )

    def _numberify(self, value):
        """
        Converts the input value to a number.

        :param value: The input value to convert.
        :type value: Any
        :return: The converted number.
        :rtype: Union[int, float]
        """
        if is_float(value) or is_int(value):
            if self._float_allowed:
                number = float(value)
            else:
                number = int(value)
        else:
            number = len(value)
        return number

    def _max_min_operator(self, value=0):
        """
        Checks if the input value is within the given min and max values.

        :param value: The input value to check.
        :type value: Union[int, float]
        :return: True if the value is within the min and max values, False otherwise.
        :rtype: bool
        """
        if self._max > 0 and self._min > 0:
            if value > self._max or value < self._min:
                return False
            else:
                return True
        elif self._max > 0:
            if value > self._max:
                return False
        else:
            return True

    def validate(self, document) -> None:
        """
        Validates the input document.

        :param document: The document to validate.
        :type document: Any
        """
        try:
            text_length = self._numberify(document.text)
            if self._value_type == "number":
                if not get_operator_truth(text_length, self._operator, self._length):
                    self.raise_error(document)
            elif self._value_type == "string":
                if not get_operator_truth(len(document.text), self._operator, self._length):
                    self.raise_error(document)
            elif self._value_type == "min_max":
                if self._max_min_operator(text_length):
                    return
                else:
                    self.raise_error(document, message=f"input_length={text_length}, min={self._min}, max={self._max}")

        except ValueError as e:
            self.raise_error(document, message=f"{e}")


class NumberCompareValidator(CompareValidator):
    """
    A validator that compares a number with a given operator.

    :param operator: A string representing the operator. Default is "".
    :param length: An integer representing the length of the input. Default is 0.
    :param message: A string representing the error message. Default is "Input should be a ".
    :param float_allowed: A boolean representing whether float input is allowed. Default is False.

    Example:

        .. code-block:: python

            validator = NumberCompareValidator(operator=">", length=0, message="Input should be a number", float_allowed=True)
            validator.validate(5) # >> True
            validator.validate("5.0") # >> True
            validator.validate("abc") # >> False
    """

    def __init__(self, operator="", length: int = 0, message: str = "Input should be a ", float_allowed: bool = False) -> None:
        super().__init__(operator=operator, length=length, message=message, float_allowed=float_allowed, value_type="number")


class StringCompareValidator(CompareValidator):
    """
    A validator that compares a string with a given operator.

    :param operator: A string representing the operator. Default is "".
    :param length: An integer representing the length of the input. Default is 0.
    :param message: A string representing the error message. Default is "Input should be a ".
    :param float_allowed: A boolean representing whether float input is allowed. Default is False.

    Example:

        .. code-block:: python

            validator = StringCompareValidator(operator=">", length=0, message="Input should be a string", float_allowed=False)
            validator.validate("abc") # >> True
            validator.validate(123) # >> False
            validator.validate("abcdefg") # >> False
    """

    def __init__(self, operator="", length: int = 0, message: str = "Input should be a ", float_allowed: bool = False) -> None:
        super().__init__(operator=operator, length=length, message=message, float_allowed=float_allowed, value_type="string")


class MinMaxValidator(CompareValidator):
    """
    A validator that checks whether a number is within a given range.

    :param min_value: An integer representing the minimum value. Default is 0.
    :param max_value: An integer representing the maximum value. Default is 0.
    :param message: A string representing the error message. Default is "Input should be a ".
    :param float_allowed: A boolean representing whether float input is allowed. Default is False.

    Example:

        .. code-block:: python

            validator = MinMaxValidator(min_value=0, max_value=10, message="Input should be between 0 and 10", float_allowed=True)
            validator.validate(5) # >> True
            validator.validate(15) # >> False
            validator.validate("5.0") # >> True
            validator.validate("abc") # >> False
    """

    def __init__(self, min_value: int = 0, max_value: int = 0, message: str = "Input should be a ", float_allowed: bool = False) -> None:
        super().__init__(min_value=min_value, max_value=max_value, message=message, float_allowed=float_allowed, value_type="min_max")


class HexValidator(CompareValidator):
    def __init__(self, message: str = "Input should be a ", allow_none: bool = False, value_type: str = "Hex", value_length: int =1) -> None:
        self.allow_none = allow_none
        self.value_type = value_type
        self.value_length = value_length
        super().__init__(message=message,  value_type=value_type)

    def validate(self, document) -> None:
        """
        Validates whether the input is a valid Hex.

        :param document: The input to validate.
        :type document: Any

        :raises ValueError: If the input is not a valid private key.

        Example:

            .. code-block:: python

                validator = HexValidator(value_type="TX hash", value_length=64)
                validator.validate("4a3c6a7b9d9a51f4e8a46e8b8d2a6f3c2f2b7e3e8b75a8c9e7d6f5a4c3b2a19d")
                # >> None

        """
        try:
            text = document.text

            if self.allow_none and not text:
                return
            elif not is_hex(text):
                self.raise_error(document, message=f"{self.value_type}. '{document.text}' is not Hex ")
            elif not len(text) == self.value_length:
                self.raise_error(document, message=f"{self.value_type}. Length should be {self.value_length}. len={len(text)}")
        except ValueError:
            self.raise_error(document)


class PrivateKeyValidator(CompareValidator):
    """
    Validator class for private key.

    :param message: Error message to display.
    :param allow_none: If True, allows None as a valid input.
    :type message: str
    :type allow_none: bool

    Example:

        .. code-block:: python

            validator = PrivateKeyValidator()
            validator.validate("4a3c6a7b9d9a51f4e8a46e8b8d2a6f3c2f2b7e3e8b75a8c9e7d6f5a4c3b2a19d")
            # >> None

    """
    def __init__(self, message: str = "Input should be a ", allow_none: bool = False) -> None:
        self.allow_none = allow_none
        super().__init__(message=message,  value_type="PrivateKey Hex")

    def validate(self, document) -> None:
        """
        Validates whether the input is a valid private key.

        :param document: The input to validate.
        :type document: Any

        :raises ValueError: If the input is not a valid private key.

        Example:

            .. code-block:: python

                validator = PrivateKeyValidator()
                validator.validate("4a3c6a7b9d9a51f4e8a46e8b8d2a6f3c2f2b7e3e8b75a8c9e7d6f5a4c3b2a19d")
                # >> None

        """
        try:
            text = document.text

            if self.allow_none and not text:
                return
            elif not is_hex(text):
                self.raise_error(document, message=f"Invalid Private Key. '{document.text}' is not Hex ")
            elif not is_valid_private_key(text):
                self.raise_error(document, message=f"Invalid Private Key. Length should be 64. len={len(text)}")
        except ValueError:
            self.raise_error(document)


class PrivateKeyOrJsonValidator(CompareValidator):
    """
    Validator class for private key or JSON.

    :param message: Error message to display.
    :param allow_none: If True, allows None as a valid input.
    :type message: str
    :type allow_none: bool

    Example:

        .. code-block:: python

            validator = PrivateKeyOrJsonValidator()
            validator.validate('{"private_key": "4a3c6a7b9d9a51f4e8a46e8b8d2a6f3c2f2b7e3e8b75a8c9e7d6f5a4c3b2a19d"}')
            # >> None

    """
    def __init__(self, message: str = "Input should be a ", allow_none: bool = False) -> None:
        self.allow_none = allow_none
        super().__init__(message=message,  value_type="PrivateKey Hex")

    def validate(self, document) -> None:
        """
        Validates whether the input is a valid private key or JSON.

        :param document: The input to validate.
        :type document: Any

        :raises ValueError: If the input is not a valid private key or JSON.

        Example:

            .. code-block:: python

                validator = PrivateKeyOrJsonValidator()
                validator.validate('{"private_key": "4a3c6a7b9d9a51f4e8a46e8b8d2a6f3c2f2b7e3e8b75a8c9e7d6f5a4c3b2a19d"}')
                # >> None

        """
        try:
            text = document.text

            if self.allow_none and not text:
                return
            elif not is_hex(text):
                try:
                    json.loads(text)
                except ValueError:
                    self.raise_error(document, message=f"Invalid input. '{document.text}' is not Hex or JSON.")
            elif not is_valid_private_key(text):
                self.raise_error(document, message=f"Invalid Private Key. Length should be 64. len={len(text)}")
        except ValueError:
            self.raise_error(document)


class JsonValidator(CompareValidator):
    """
    Validator class for  JSON.

    :param message: Error message to display.
    :param allow_none: If True, allows None as a valid input.
    :type message: str
    :type allow_none: bool

    Example:

        .. code-block:: python

            validator = JsonValidator()
            validator.validate('{"private_key": "4a3c6a7b9d9a51f4e8a46e8b8d2a6f3c2f2b7e3e8b75a8c9e7d6f5a4c3b2a19d"}')
            # >> None

    """
    def __init__(self, message: str = "Input should be a ", allow_none: bool = False) -> None:
        self.allow_none = allow_none
        super().__init__(message=message,  value_type="JSON Validator")

    def validate(self, document) -> None:
        """
        Validates whether the input is a valid  JSON.

        :param document: The input to validate.
        :type document: Any

        :raises ValueError: If the input is not a valid JSON.

        Example:

            .. code-block:: python

                validator = JsonValidator()
                validator.validate('{"private_key": "4a3c6a7b9d9a51f4e8a46e8b8d2a6f3c2f2b7e3e8b75a8c9e7d6f5a4c3b2a19d"}')
                # >> None

        """
        try:
            text = document.text

            if self.allow_none and not text:
                return
            elif not is_hex(text):
                try:
                    json.loads(text)
                except Exception as e:
                    self.raise_error(document, message=f"Invalid JSON: {e}" )
        except ValueError:
            self.raise_error(document)


def check_valid_private_length(text):
    """
    Check if the length of a private key is valid.

    :param text: a string representing a private key.
    :return: True if the length of the private key is valid, False otherwise.

    Example:

        .. code-block:: python

            check_valid_private_length("0x1234567890123456789012345678901234567890123456789012345678901234")
            # >> True

            check_valid_private_length("0x123456789012345678901234567890123456789012345678901234567890")
            # >> False

    """
    private_length = 64
    if is_hex(text):
        if text.startswith("0x"):
            text = text[2:]
        if len(text) == private_length:
            return True
    return False


def get_operator_truth(inp, relate, cut):
    """
    Compare two values based on a relationship operator.

    :param inp: First value to compare.
    :type inp: any
    :param relate: Relationship operator.
    :type relate: str
    :param cut: Second value to compare.
    :type cut: any
    :return: Comparison result.
    :rtype: bool

    Example:

        .. code-block:: python

            get_operator_truth(3, '>', 2)
            # >> True

            get_operator_truth('hello', 'include', 'he')
            # >> True

    """
    ops = {
        '>': _operator.gt,
        '<': _operator.lt,
        '>=': _operator.ge,
        '<=': _operator.le,
        '==': _operator.eq,
        '!=': _operator.ne,
        'include': lambda y, x: x in y,
        'exclude': lambda y, x: x not in y
    }
    return ops[relate](inp, cut)


def prompt_with_keyboard_interrupt(*args, **kwargs):
    """
    Handle keyboard interrupt with prompt.

    :param args:
    :param kwargs:
    :return:

    Example:

        .. code-block:: python

            prompt_with_keyboard_interrupt({'name': 'test'}, {})
            # >> {'test': 'value'}

            prompt_with_keyboard_interrupt([{'name': 'test'}], {})
            # >> 'value'

    """
    answer = prompt(*args, **kwargs)
    if not answer:
        raise KeyboardInterrupt
    if isinstance(args[0], dict):
        arguments = args[0]
    else:
        arguments = args[0][0]
    if isinstance(answer, dict) and len(answer.keys()) == 1 and arguments and arguments.get('name'):
        return answer.get(arguments['name'])
    return answer


def inq_prompt(*args, **kwargs):
    """
    Prompt the user for input, return the name field or the first field of the answer.

    :param args: arguments to be passed to the prompt function
    :param kwargs: keyword arguments to be passed to the prompt function
    :return: the 'name' field of the answer, or the first field if 'name' does not exist

    Example:

        .. code-block:: python

            inq_prompt(question="What's your name?")
            # >> "John Doe"

            inq_prompt(questions=[{"type": "input", "name": "username", "message": "Enter your username"}], style={'input': 'green'})
            # >> "johndoe"

    """
    if args:
        answer = prompt(*args)
    else:
        style = None
        if kwargs.get('style'):
            style = kwargs.pop('style')
        if not kwargs.get('type'):
            kwargs['type'] = "input"
        answer = prompt(questions=kwargs, style=style)
    if answer.get('name'):
        return answer['name']

    return answer[0]


def simple_input_prompt(
        name="", default="", type="input", choices=None,
        instruction=None, long_instruction=None, validate=None, filter=None, min_length=1, max_length=1000):
    """
     A simple input prompt function.

     :param name: The name of the input prompt.
     :param default: The default value for the input prompt.
     :param type: The type of the input prompt.
     :param choices: The choices for the input prompt.
     :param instruction: The instruction for the input prompt.
     :param long_instruction: The long instruction for the input prompt.
     :param validate: The validation for the input prompt.
     :param filter: The filter for the input prompt.
     :param min_length: The minimum length for the input prompt.
     :param max_length: The maximum length for the input prompt.
     :return: The input prompt.

     Example:

         .. code-block:: python

             simple_input_prompt(
                 name="Your Name", default="John Doe", type="input", choices=None,
                 instruction="Please enter your name.", long_instruction="Your name will be used for personalization purposes.",
                 validate=None, filter=None, min_length=1, max_length=1000)
             # >> 'John Doe'

             simple_input_prompt(
                 name="Your Age", default="25", type="input", choices=None,
                 instruction="Please enter your age.", long_instruction="Your age will be used for age verification purposes.",
                 validate=None, filter=None, min_length=1, max_length=3)
             # >> '25'

     """

    if not name:
        raise ValueError("Required name for simple_input_prompt()" )

    if type == "list":
        _type_text = "select"
    else:
        _type_text = type

    if not name.isupper():
        name = name.title()

    _message = f"[{pconf().data.args.subparser_name.upper()}] {_type_text.title()} {name}"
    _default_message = ""

    if default:
        _default_message = ""

    options = dict(
        message=f"{_message}{_default_message}?",
        type=type,
        default=str(default),
        # validate=lambda result: len(result) >= min_length,
        # validate=lambda result: min_length <= len(result) <= max_length,
        validate=MinMaxValidator(min_value=min_length, max_value=max_length),
        invalid_message=f"should be at least {min_length} , maximum {max_length}",
        instruction=instruction,
        qmark="[❓]",
        amark="[❓]",
        style={
            # "questionmark": "#ffffff",
            # "answer": "#000000",
            "answer": "#ffffff bold",
            "question": "#ffffff bold",
            "input": "#98c379 bold",
            "long_instruction": "#96979A italic",
        }
    )

    if isinstance(choices, list):
        options['choices'] = choices
        options['type'] = "list"

    if instruction:
        options['instruction'] = instruction


    if validate:
        options['validate'] = validate

    if filter:
        options['filter'] = filter

    if long_instruction:
        options['long_instruction'] = f"💡🤔 {long_instruction}"

    return inq_prompt(
        **options
    )


def change_select_pattern(items):
    """
    Change the select pattern of items.

    :param items: The items to change the select pattern.
    :return: The items with changed select pattern.

    Example:

        .. code-block:: python

            items = {'1': 'One', '2': 'Two', '3': 'Three'}
            change_select_pattern(items)
            # >> [{'name': ' 0) 1 (One)', 'value': '1'}, {'name': ' 1) 2 (Two)', 'value': '2'}, {'name': ' 2) 3 (Three)', 'value': '3'}]

            items = [1, 2, 3]
            change_select_pattern(items)
            # >> [1, 2, 3]

    """
    result = []
    count = 0
    if isinstance(items, dict) or isinstance(items, FlatDict):
        for value, name in items.items():
            if name:
                name = f"{value} ({name})"
            else:
                name = value
            result.append({"name": f"{count:>2}) {name}", "value": value})
            count += 1
    else:
        return items
    return result


def tk_prompt(**kwargs):
    return toolkit_prompt(**kwargs)


def fuzzy_prompt(**kwargs):
    if not kwargs.get('style', None):
        kwargs['style'] = get_style(
            {
                "question": "bold #ffffff",
                # "questionmark": "#ffffff",
                # "answer": "#000000",
                "instruction": "italic bold #b6b8ba",
                "answer": "#61afef bold",
                "input": "#98c379 bold",
                "fuzzy_info": "#474747",
            },
            style_override=False
        )
    if not kwargs.get('invalid_message', None):
        kwargs['invalid_message'] = "minimum 1 selection"

    if not kwargs.get('validate', None):
        kwargs['validate'] = lambda result: len(str(result)) > 1
    answer = inquirer.fuzzy(**kwargs).execute()
    return answer


def fuzzy_prompt_to_argument(**kwargs):
    _pconf = pconf()
    _arg_missing_word = "DO_NOT_SET_THE_ARG"
    if kwargs.get("argument"):
        argument = kwargs.pop("argument")
        _argument_name = argument.replace("_", "-")
        _argument_value = pawn.data.args.__dict__.get(_argument_name, _arg_missing_word)

        if _arg_missing_word == _argument_value:
            raise ValueError(f"Can not find argument in args. {argument}")
        _default_value = kwargs.get('default')

        kwargs['instruction'] = kwargs.get('instruction', "") + f"( --{_argument_name} {_default_value})"
        if not _argument_value and argument:
            response_value = fuzzy_prompt(**kwargs)
            setattr(_pconf.data.args, argument, response_value)
            return response_value
        else:
            pawn.console.debug("")
    else:
        raise ValueError(f"Required argument, {kwargs}")


def _check_undefined_dict_key(dict_item, key):
    if dict_item.get(key, '__NOT_DEFINED__KEY__') != '__NOT_DEFINED__KEY__':
        return True
    return False


def is_args_namespace():
    _pconf = pconf()
    if getattr(_pconf, "args", None):
        return True
    else:
        return False


def is_data_args_namespace():
    _pconf = pconf()
    if getattr(_pconf, "data", None) and getattr(_pconf.data, "args", None):
        return True
    else:
        return False


def select_file_prompt(path: str = "./", pattern: str = "*", message: str = "Select a file: ",
                       recursive: bool = False, **kwargs):
    """
    Prompts the user to select a file from a given directory.

    :param path: The directory to list files from. Default is current directory.
    :param pattern: The pattern to match files. Default is all files.
    :param message: The message to display to the user. Default is "Select a file: ".
    :param recursive: Whether to recursively search directories. Default is False.
    :param kwargs: Additional keyword arguments.

    :return: The selected file.

    Example:

        .. code-block:: python

            select_file_prompt(path="./my_directory", pattern="*.txt", message="Select a text file: ", recursive=True)
            # User is prompted with a list of .txt files in 'my_directory' and any subdirectories.
            # Returns the file selected by the user.

    """
    file_list = get_file_list(path=path, pattern=pattern, recursive=recursive)
    return PromptWithArgument(
        message=message,
        choices=file_list,
        instruction=f"[{len(file_list)} files available]",
        max_height="40%",
        default="",
        **kwargs
    ).fuzzy()


def parse_list(value):
    """
    Parse a comma-separated string into a Python list.

    :param value: A string to be parsed into a list
    :type value: str
    :return: A list of parsed items or the original value if not a string
    :rtype: list or any

    Example:

        .. code-block:: python

            parse_list("apple, banana, orange")
            # >> ['apple', 'banana', 'orange']

            parse_list(42)
            # >> 42

    """
    try:
        # If the value looks like a list (comma-separated), parse it into a Python list
        return [item.strip().strip(all_special_characters) for item in value.split(",")]
    except AttributeError:
        # If the value is not a string, return it as-is
        return value


def get_environment(key, default="", func: Callable = ""):
    """
    Get the value of an environment variable, optionally applying a transformation function.

    :param key: The key of the environment variable
    :param default: The default value to use if the environment variable is not set, default is an empty string
    :param func: A function to apply to the environment variable value, default is no function (identity)
    :type key: str
    :type default: Any
    :type func: Callable
    :return: The value of the environment variable after applying the transformation function
    :rtype: Any

    Example:

        .. code-block:: python

            os.environ["EXAMPLE_VARIABLE"] = "1,2,3"

            get_environment("EXAMPLE_VARIABLE")
            # >> '1,2,3'

            get_environment("EXAMPLE_VARIABLE", func=lambda x: x.split(','))
            # >> ['1', '2', '3']

            get_environment("NON_EXISTENT_VARIABLE", default="default_value")
            # >> 'default_value'

    """
    env_raw_value = os.getenv(key, default)
    if not isinstance(env_raw_value, str):
        raise ValueError(f"Environment variables must be strings. - {env_raw_value}")

    env_value = env_raw_value.strip().strip(all_special_characters)

    if func and isinstance(func, Callable):
        return func(env_value)
    elif isinstance(env_value, str) and "," in env_value:
        return parse_list(env_value)

    return env_value


def json_input_prompt(default={}, message="Edit Transaction JSON"):
    """
    Prompts the user to edit a JSON file.

    :param default: default JSON to be edited, default is an empty dictionary.
    :param message: message to be displayed while editing, default is "transaction".

    Example:

        .. code-block:: python

            default_json = {"key": "value"}
            message = "Edit JSON"
            json_input_prompt(default=default_json, message=message)

    """
    if default and isinstance(default, dict):
        _default_json = json.dumps(default, indent=4)
    else:
        _default_json = str(default)

    json_text = inq_prompt(
        type="input",
        message=f"{message} :",
        default=f"\n{_default_json}",
        long_instruction=f"Move the arrows to edit the {str(message).lower()}",
        validate=JsonValidator(),
    )
    return json.loads(json_text)
