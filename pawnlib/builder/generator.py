from pawnlib.config.globalconfig import pawnlib_config as pawn
from pawnlib.output.file import open_file, write_file, check_file_overwrite
from pawnlib.output.color_print import *
from jinja2 import Template
from PyInquirer import prompt, print_json
import os
from pyfiglet import Figlet


def generate_banner(
        app_name="default_app",
        version="0.0.0",
        author="Unknown author",
        description="",
        font="big",
        return_type="string",

    ):
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
                # 'default': 'default_app',
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
                'default': os.getlogin(),
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
        self.answers = prompt(questions)
        # dump(self.answers)  # use the answers as input for your app
        #http://www.figlet.org/examples.html

    def load_template(self):
        self.template = open_file(f"{self.template_dir}/{self.template_name}")
        # dump(self.template)

    def get_main_filename(self):
        return f"{self.cwd}/{self.answers.get('app_name', self.app_name)}.py"

    def generate_file_from_template(self):
        self.set_user_input()
        if self.answers.get("app_name", None) is None or self.answers.get("app_name", None) == "":
            self.answers['app_name'] = self.app_name

        print(f"pawn.verbose = {pawn.verbose}")
        if pawn.verbose > 2:
            cprint("answers")
            dump(self.answers)

        self.answers['banner'] = generate_banner(
            app_name=self.answers.get("app_name"),
            author=self.answers.get("author"),
            # font="graffiti",
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
        # with open(app_filename, "w") as app:
        #     app.write(res)

    def run(self):
        self.generate_file_from_template()
        return f"{self.cwd}/{self.answers['app_name']}.py"

