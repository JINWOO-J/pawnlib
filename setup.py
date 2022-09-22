import setuptools
import os
from codecs import open
from setuptools.command.install import install


class PostInstallCommand(install):
    """Post-installation for installation mode."""
    def run(self):
        print("PostInstallCommand"*10)
        install.run(self)
        # PUT YOUR POST-INSTALL SCRIPT HERE or CALL A FUNCTION


class InstallCommand(install):
    user_options = install.user_options + [
        ('engine=', None, '<description for this custom option>'),
    ]

    def initialize_options(self):
        install.initialize_options(self)
        self.engine = None

    def finalize_options(self):
        print("value of engine is", self.engine)
        install.finalize_options(self)

    def run(self):
        print("InstallCommand"*10)
        print(self.engine)
        install.run(self)


here = os.path.abspath(os.path.dirname(__file__))
about = {}
print(os.path.join(here, 'pawnlib', '__version__.py'))

with open(os.path.join(here, 'pawnlib', '__version__.py'), 'r', 'utf-8') as f:
    exec(f.read(), about)

with open('README.md', 'r', 'utf-8') as f:
    readme = f.read()

setuptools.setup(
    name=about['__title__'],
    version=about['__version__'],
    license=about['__license__'],
    author=about['__author__'],
    author_email=about['__author_email__'],
    description=about['__description__'],
    long_description=readme,
    long_description_content_type='text/markdown',
    python_requires=">=3.7",
    url=about['__url__'],
    # packages=setuptools.find_packages(),
    include_package_data=True,
    packages=setuptools.find_packages(exclude=["setup", "tests", "test_*", "venv"]),
    install_requires=open('requirements.txt').read(),
    # cmdclass={'install': InstallCommand},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent"
    ],
    entry_points=dict(
        console_scripts=[
            'pawns=pawnlib.cli.main_cli:main'
        ],
    ),
)
