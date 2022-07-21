import os


def singleton(class_):
    instances = {}

    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]

    return getinstance


@singleton
class Configure:
    def __init__(self, file_name="../config.ini", path=None, section=None):

        self.file_name = file_name
        if path:
            self.path = path
        else:
            self.path = os.path.dirname(os.path.abspath(__file__))
        self.full_path = os.path.join(self.path, self.file_name)
        self.section = section
        self.name = "default"

    def _get_config(self, ):
        self.config.optionxform = str  # change to uppercase
        self.config.read(self.full_path)
        return self._converter(self.config._sections)


if __name__ == '__main__':
    CFG = Configure()


