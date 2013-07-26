"""
quickunit.utils
~~~~~~~~~~~~~~~

:copyright: 2012 DISQUS.
:license: Apache 2.0
"""
import os
import os.path


def is_py_script(filename):
    "Returns True if a file is a python executable."
    if not os.path.exists(filename) and os.path.isfile(filename):
        return False
    elif filename.endswith(".py"):
        return True
    elif not os.access(filename, os.X_OK):
        return False
    else:
        try:
            with open(filename, "r") as fp:
                first_line = fp.readline().strip()
            return "#!" in first_line and "python" in first_line
        except StopIteration:
            return False


def clean_bytecode_extension(filename):
    """
    Replaces Python bytecode extensions (``.pyc``) with their source extension.
    """
    path, extension = os.path.splitext(filename)
    if extension == '.pyc':
        filename = '%s.py' % path
    return filename
