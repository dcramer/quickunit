import os
import os.path


def is_py_script(filename):
    "Returns True if a file is a python executable."
    if filename.endswith(".py") and os.path.exists(filename):
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
