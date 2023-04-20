import json
import operator as _operator
from pawnlib.config import pawnlib_config as pawn, pconf
from pawnlib.typing import is_hex, is_int, is_float, FlatDict, Namespace, sys_exit, is_valid_token_address, is_valid_private_key
from InquirerPy import prompt, inquirer, get_style
from InquirerPy.validator import NumberValidator
from prompt_toolkit.validation import ValidationError, Validator, DynamicValidator
from prompt_toolkit.shortcuts import prompt as toolkit_prompt
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
                validate=lambda result: len(result) >= 1,
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
            self._options['validate'] = lambda result: len(result) >= 1

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
        _message = f"{self._message}, {message}"
        raise ValidationError(
            message=_message, cursor_position=document.cursor_position
        )

    def _numberify(self, value):
        if is_float(value) or is_int(value):
            if self._float_allowed:
                number = float(value)
            else:
                number = int(value)
        else:
            number = len(value)
        return number

    def _max_min_operator(self, value=0):
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
    def __init__(self, operator = "", length: int = 0, message: str = "Input should be a ", float_allowed: bool = False) -> None:
        super().__init__(operator=operator, length=length, message=message, float_allowed=float_allowed, value_type="number")


class StringCompareValidator(CompareValidator):
    def __init__(self, operator = "", length: int = 0, message: str = "Input should be a ", float_allowed: bool = False) -> None:
        super().__init__(operator=operator, length=length, message=message, float_allowed=float_allowed, value_type="string")


class MinMaxValidator(CompareValidator):
    def __init__(self, min_value: int = 0, max_value: int = 0, message: str = "Input should be a ", float_allowed: bool = False) -> None:
        super().__init__(min_value=min_value, max_value=max_value, message=message, float_allowed=float_allowed, value_type="min_max")


class PrivateKeyValidator(CompareValidator):
    def __init__(self, message: str = "Input should be a ", allow_none: bool = False) -> None:
        self.allow_none = allow_none
        super().__init__(message=message,  value_type="PrivateKey Hex")

    def validate(self, document) -> None:
        try:
            text = document.text

            # if isinstance(text, str):
            if self.allow_none and not text:
                return
            elif not is_hex(text):
                self.raise_error(document, message=f"Invalid Private Key. '{document.text}' is not Hex ")
            elif not is_valid_private_key(text):
                self.raise_error(document, message=f"Invalid Private Key. Length should be 64. len={len(text)}")
        except ValueError:
            self.raise_error(document)


class PrivateKeyOrJsonValidator(CompareValidator):
    def __init__(self, message: str = "Input should be a ", allow_none: bool = False) -> None:
        self.allow_none = allow_none
        super().__init__(message=message,  value_type="PrivateKey Hex")

    def validate(self, document) -> None:
        try:
            text = document.text

            # if isinstance(text, str):
            if self.allow_none and not text:
                return
            elif not is_hex(text):
                self.raise_error(document, message=f"Invalid Private Key. '{document.text}' is not Hex ")
            elif not is_valid_private_key(text):
                self.raise_error(document, message=f"Invalid Private Key. Length should be 64. len={len(text)}")
        except ValueError:
            self.raise_error(document)


def check_valid_private_length(text):
    private_length = 64
    if is_hex(text):
        if text.startswith("0x"):
            text = text[2:]
        if len(text) == private_length:
            return True
    return False


def get_operator_truth(inp, relate, cut):
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
    if args:
        answer = prompt(*args)
    else:
        style = None
        if kwargs.get('style'):
            style = kwargs.pop('style')
        answer = prompt(questions=kwargs, style=style)
    if answer.get('name'):
        return answer['name']

    return answer[0]


def simple_input_prompt(
        name="", default="", type="input", choices=None,
        instruction=None, long_instruction=None, validate=None, filter=None, min_length=1, max_length=1000):

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
        kwargs['validate'] = lambda result: len(result) > 1


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

