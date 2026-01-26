# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import sys
import os

sys.path.insert(0, os.path.abspath("../../../.pai_venv/lib/python3.10/site-packages/"))
sys.path.insert(1, os.path.abspath("../../"))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Personal AI'
copyright = '2024, Skoltech Applied AI Lab'
author = 'Skoltech Applied AI Lab'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.todo',
    'rst2pdf.pdfbuilder',
    "sphinx_rtd_dark_mode",
    "nbsphinx",
    'sphinx_automodapi.automodapi',
    'sphinx_automodapi.smart_resolver'
]

# long function signature fix
autodoc_typehints = "signature"
autodoc_class_signature = "mixed"
autodoc_member_order = 'bysource'
#numpydoc_show_class_members = False

# xelatex to solve Unicode problems https://github.com/sphinx-doc/sphinx/issues/4159
latex_engine = 'xelatex'

latex_elements = {
    'fontpkg': '''
\setmainfont{FreeSerif}[
  UprightFont    = *,
  ItalicFont     = *Italic,
  BoldFont       = *Bold,
  BoldItalicFont = *BoldItalic
]
\setsansfont{FreeSans}[
  UprightFont    = *,
  ItalicFont     = *Oblique,
  BoldFont       = *Bold,
  BoldItalicFont = *BoldOblique,
]
\setmonofont{FreeMono}[
  UprightFont    = *,
  ItalicFont     = *Oblique,
  BoldFont       = *Bold,
  BoldItalicFont = *BoldOblique,
]
''',
 }

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
todo_include_todos = True
default_dark_mode = False

language = 'ru'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
