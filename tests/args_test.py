#!/usr/bin/env python3
import sys
import argparse


def init_args():
    def parse_args_into_namespaces(parser, commands):
        """
        Split all command arguments (without prefix, like --) in
        own namespaces. Each command accepts extra options for
        configuration.
        Example: `add 2 mul 5 --repeat 3` could be used to a sequencial
                 addition of 2, then multiply with 5 repeated 3 times.
        """

        class OrderNamespace(argparse.Namespace):
            """
            Add `command_order` attribute - a list of command
            in order on the command line. This allows sequencial
            processing of arguments.
            """
            globals = None

            def __init__(self, **kwargs):
                self.command_order = []
                super(OrderNamespace, self).__init__(**kwargs)

            def __setattr__(self, attr, value):
                attr = attr.replace('-', '_')
                if value and attr not in self.command_order:
                    self.command_order.append(attr)
                super(OrderNamespace, self).__setattr__(attr, value)

        # Divide argv by commands
        split_argv = [[]]
        for c in sys.argv[1:]:
            if c in commands.choices:
                split_argv.append([c])
            else:
                split_argv[-1].append(c)

        # Globals arguments without commands
        args = OrderNamespace()
        cmd, args_raw = 'globals', split_argv.pop(0)

        args_parsed = parser.parse_args(args_raw, namespace=OrderNamespace())
        setattr(args, cmd, args_parsed)

        # Split all commands to separate namespace
        pos = 0
        while len(split_argv):
            pos += 1
            cmd, *args_raw = split_argv.pop(0)
            assert cmd[0].isalpha(), 'Command must start with a letter.'
            args_parsed = commands.choices[cmd].parse_args(args_raw, namespace=OrderNamespace())
            setattr(args, f'{cmd}~{pos}', args_parsed)

        return args

    #
    # Supported commands and options
    #
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--print', action='store_true')

    commands = parser.add_subparsers(title='Operation chain')

    cmd1_parser = commands.add_parser('add', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    cmd1_parser.add_argument('add', help='Add this number.', type=float)
    cmd1_parser.add_argument('-r', '--repeat', help='Repeat this operation N times.',
                             default=1, type=int)

    cmd2_parser = commands.add_parser('mult', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    cmd2_parser.add_argument('mult', help='Multiply with this number.', type=float)
    cmd2_parser.add_argument('-r', '--repeat', help='Repeat this operation N times.',
                             default=1, type=int)

    args = parse_args_into_namespaces(parser, commands)
    return args


#
# DEMO
#

args = init_args()

# print('Parsed arguments:')
# for cmd in args.command_order:
#     namespace = getattr(args, cmd)
#     for option_name in namespace.command_order:
#         option_value = getattr(namespace, option_name)
#         print((cmd, option_name, option_value))
#
# print('Execution:')
# result = 0
print(args)
for cmd in args.command_order:
    namespace = getattr(args, cmd)
    cmd_name, cmd_position = cmd.split('~') if cmd.find('~') > -1 else (cmd, 0)
    if cmd_name == 'globals':
        pass
    elif cmd_name == 'add':
        for r in range(namespace.repeat):
            if args.globals.print:
                print(f'+ {namespace.add}')
            result = result + namespace.add
    elif cmd_name == 'mult':
        for r in range(namespace.repeat):
            if args.globals.print:
                print(f'* {namespace.mult}')
            result = result * namespace.mult
    else:
        raise NotImplementedError(f'Namespace `{cmd}` is not implemented.')
print(10 * '-')
# print(result)
