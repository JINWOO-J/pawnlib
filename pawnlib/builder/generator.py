from pawnlib.config.globalconfig import pawnlib_config as pawn
from pawnlib.output.file import open_file, write_file, check_file_overwrite
from pawnlib.output.color_print import bcolors, cprint, dump
from jinja2 import Template

from rich.prompt import Confirm, FloatPrompt, Prompt, PromptBase

import os
from pyfiglet import Figlet


def generate_banner(
        app_name: str = "default_app",
        version: str = "{__version}",
        author: str = "Unknown author",
        description: str = "",
        font: str = "big",
        return_type: str = "string",
):
    """

    Generate the banner

    :param app_name:
    :param version:
    :param author:
    :param description:
    :param font: font name   / :refer: http://www.figlet.org/examples.html
    :param return_type: string, list
    :return:

    Example:

    .. code-block:: python

        from pawnlib.builder import generator
        banner = generator.generate_banner(app_name="pawn")
        print(banner)

    """

    result = []
    if return_type == "string":
        enter_string = "\n"
    else:
        enter_string = "\\n"
    result.append(bcolors.WHITE)
    result.append("-" * 50)
    result.append(enter_string)

    ascii_banner = Figlet(font=font)
    for text in ascii_banner.renderText(app_name).split("\n"):
        result.append(text)

    result.append(f" - Description : {description}")
    result.append(f" - Version     : {version}")
    result.append(f" - Author      : {author}")
    result.append(enter_string)
    result.append("-" * 50)
    result.append(bcolors.ENDC)
    if return_type == "string":
        return "\n".join(result)
    elif return_type == "list":
        return result


class AppGenerator:
    """

    :param app_name:
    """
    def __init__(self, app_name="new_app"):

        self.app_name = app_name
        self.cwd = os.getcwd()
        self.template_dir = f"{os.path.dirname(__file__)}/templates"
        self.template_name = "app_with_logging.tmpl"
        self.template = ""
        self.tpl_structure = {}
        self.answers = {}
        print(f"PWD = {self.cwd}")

    def set_user_input(self):
        questions = [
            {
                'type': 'input',
                'name': 'app_name',
                'message': 'What\'s your python3 app name?',
                'default': self.app_name,
            },
            {
                'type': 'input',
                'name': 'author',
                'message': 'What\'s your name?',
                'default': os.getlogin(),
            },
            {
                'type': 'input',
                'name': 'description',
                'message': 'Please explain this script.',
                'default': "This is script",
            },
            {
                'type': 'confirm',
                'name': 'confirm_dir',
                'message': f'Project directory => {self.cwd} ?',
                'default': True,
            },
            {
                'type': 'confirm',
                'name': 'use_logger',
                'message': 'Do you want to logger?',
                'default': True,
            },
            {
                'type': 'confirm',
                'name': 'use_daemon',
                'message': 'Do you want to daemon?',
                'default': False,
            },
        ]
        print("\n")

        for q in questions:
            params = dict(prompt=q.get('message'), default=q.get('default'))
            if q.get("type") == "input":
                self.answers[q.get("name")] = Prompt.ask(**params)
            if q.get("type") == "confirm":
                self.answers[q.get("name")] = Confirm.ask(**params)
        dump(self.answers)
        # dump(self.answers)  # use the answers as input for your app
        # http://www.figlet.org/examples.html

    def load_template(self):
        self.template = open_file(f"{self.template_dir}/{self.template_name}")
        # dump(self.template)

    def get_main_filename(self):
        return f"{self.cwd}/{self.answers.get('app_name', self.app_name)}.py"

    def generate_file_from_template(self):
        self.set_user_input()
        if self.answers.get("app_name", None) is None or self.answers.get("app_name", None) == "":
            self.answers['app_name'] = self.app_name

        if pawn.verbose > 2:
            cprint("answers")
            dump(self.answers)

        self.answers['banner'] = generate_banner(
            app_name=self.answers.get("app_name"),
            author=self.answers.get("author"),
            description=self.answers.get("description"),
            font="rounded",
            return_type="list"
        )
        self.load_template()

        with open(f"{self.template_dir}/{self.template_name}") as app:
            templated_dict = Template(self.template).render(
                **self.answers
            )

            app_filename = f"{self.cwd}/{self.answers['app_name']}.py"
            print(f"app_filename = {app_filename}")
            check_file_overwrite(filename=app_filename)

            if pawn.verbose > 2:
                cprint("templated_dict", "yellow")
                dump(templated_dict)

            write_file(filename=app_filename, data=templated_dict, permit="750")

    def run(self):
        self.generate_file_from_template()
        return f"{self.cwd}/{self.answers['app_name']}.py"
