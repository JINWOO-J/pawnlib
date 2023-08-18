from pawnlib.config import pawn, pconf


class _AttributeHolder(object):
    """Abstract base class that provides __repr__.

    The __repr__ method returns a string in the format::
        ClassName(attr=name, attr=name, ...)
    The attributes are determined either by a class-level attribute,
    '_kwarg_names', or by inspecting the instance __dict__.
    """

    def __repr__(self):
        type_name = type(self).__name__
        arg_strings = []
        star_args = {}
        for arg in self._get_args():
            arg_strings.append(repr(arg))
        for name, value in self._get_kwargs():
            if name.isidentifier():
                arg_strings.append('%s=%r' % (name, value))
            else:
                star_args[name] = value
        if star_args:
            arg_strings.append('**%s' % repr(star_args))
        return '%s(%s)' % (type_name, ', '.join(arg_strings))

    def _get_kwargs(self):
        return sorted(self.__dict__.items())

    def _get_args(self):
        return []

    def _set_args(self, key, value):
        self.__dict__[key] = value

    def _update(self, **kwargs):
        self.__dict__.update(kwargs)


class Namespace(_AttributeHolder):
    """Simple object for storing attributes.

    Implements equality by attribute names and values, and provides a simple
    string representation.

    Example:

        .. code-block:: python

            from pawnlib.typing import defines

            namespace = defines.Namespace(s=2323, sdsd="Sdsd")
            namespace.s
            # >> 2323
            namespace.sdsd
            # >> 'Sdsd'
    """

    def __init__(self, **kwargs):
        for name in kwargs:
            setattr(self, name, kwargs[name])

    def __eq__(self, other):
        if not isinstance(other, Namespace):
            return NotImplemented
        return vars(self) == vars(other)

    def __contains__(self, key):
        return key in self.__dict__


def set_namespace_default_value(namespace=None, key='', default=""):
    """
    Set a default value when a key in a namespace has no value

    :param namespace:
    :param key:
    :param default:
    :return:

    Example:

        .. code-block:: python

            from pawnlib.config import pawn, pconf
            from pawnlib.typing import set_namespace_default_value

            pawn.set(
            data={"aaaa": "bbbb"}
            )
            pawn.console.log(pconf())
            undefined_key = set_namespace_default_value(
                namespace=pconf().data,
                key="cccc",
                default="ddddd"
            )
            pawn.console.log(undefined_key)

    """
    if key and hasattr(namespace, key):
        return getattr(namespace, key)
    return default


def fill_required_data_arguments(required={}):
    """
     Fill the required data arguments.

     :param required: A dictionary of required arguments.
     :type required: dict
     :return: The filled arguments.
     :rtype: argparse.Namespace

     Example:

         .. code-block:: python

             required = {"arg1": "value1", "arg2": "value2"}
             args = fill_required_data_arguments(required)
             # args.arg1 == "value1"
             # args.arg2 == "value2"

     """
    none_string = "__NOT_DEFINED_VALUE__"
    if getattr(pconf(), "data", None) and getattr(pconf().data, "args", None):
        args = pconf().data.args
        for req_key, req_value in required.items():
            args_value = getattr(args, req_key, none_string)
            if args_value == none_string:
                # pawn.console.debug(f"Define the data args -> {req_key}, {req_value}")
                setattr(args, req_key, req_value)
    else:
        # pawn.console.debug(f"New definition: {required}")
        args = Namespace(**required)
    return args
