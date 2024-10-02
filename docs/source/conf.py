# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))
import os
import sys
# import sphinx_rtd_theme

sys.path.insert(0, os.path.abspath('../../'))

from pawnlib.__version__ import __version__ as VERSION

from pawnlib import *

# -- Project information -----------------------------------------------------

project = 'pawnlib'
copyright = '2022, jinwoo'
author = 'jinwoo'

# html_title = "{}".format(project)

# The full version, including alpha/beta/rc tags
release = VERSION
version = VERSION

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'myst_parser',
    'sphinx.ext.todo',
    # 'sphinx.ext.mathjax',
    # 'sphinx.ext.githubpages',
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
    "sphinx.ext.autodoc",
    "sphinx_copybutton",
    'sphinx_autodoc_defaultargs',
]

default_role = "py:obj"

html_title = 'Pawnlib v%s' % release

# Order of docs.
autodoc_member_order = "bysource"

# Removes the class values; e.g. 'Class(val, val, val):' becomes 'Class:'.
hide_class_values = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#

myst_enable_extensions = [
    "amsmath",
    "attrs_inline",
    "colon_fence",
    "deflist",
    "dollarmath",
    "fieldlist",
    "html_admonition",
    "html_image",
    "linkify",
    "replacements",
    "smartquotes",
    "strikethrough",
    "substitution",
    "tasklist",
]
source_suffix = ['.rst', '.md']
# source_suffix = {
#     '.rst': 'restructuredtext',
#     '.md': 'markdown',
# }

#source_suffix = '.rst'

# The encoding of source files.
#
# source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
# html_theme = 'furo'
html_theme = 'sphinx_rtd_theme'
# html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
pygments_style = 'sphinx'
html_theme_options = {}

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True
add_module_names = False


napoleon_include_init_with_doc = True

keep_default_values = False


autodoc_docstring_signature = True
autoclass_content = "both"
# autoclass_content = 'init'  #or 'both'
#
# autodoc_default_options = {
#     'members': True,
#     'member-order': 'bysource',
#     'special-members': '__init__',
#     'undoc-members': True,
#     'exclude-members': '__weakref__'
# }
