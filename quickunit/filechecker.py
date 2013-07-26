import os.path
import re

from quickunit.utils import clean_bytecode_extension


class FileChecker(dict):
    def __init__(self, rules=None, root=None):
        self.rules = rules or [
            'tests/{path}/test_{filename}',
        ]
        self.changed_files = set()
        self.compiled_rules = []
        self.root = root
        dict.__init__(self)

    def __missing__(self, filepath):
        self[filepath] = self.check(filepath)
        return self[filepath]


    def _get_root(self):
        try:
            filepath = self.changed_files.pop()
        except IndexError:
            return ''
        else:
            self.changed_files.add(filepath)
            root = os.path.abspath(filepath)[:-len(filepath)]
        self.__dict__['root'] = root
        return root

    def _set_root(self, value):
        self.__dict__['root'] = value

    root = property(_get_root, _set_root)

    def add_compiled_rules(self, filepath):
        try:
            path, filename = filepath.rsplit('/', 1)
        except ValueError:
            path, filename = '', filepath

        basename = filename.rsplit('.', 1)[0]

        params = {
            'path': path,
            'filename': filename,
            'basename': basename,
        }
        c_rules = self.compiled_rules
        for rule in self.rules:
            c_rules.append(re.compile(rule.format(**params)))

    def add(self, filepath):
        self.add_compiled_rules(filepath)
        self.changed_files.add(filepath)

    def check(self, filepath):
        filepath = clean_bytecode_extension(filepath)

        # check if this test was modified (e.g. added/changed)
        if self.root and filepath.startswith(self.root):
            filepath = filepath[len(self.root):]

        # if the filepath is actually the changed file
        if filepath in self.changed_files:
            return None

        for rule in self.compiled_rules:
            if rule.search(filepath):
                return None

        return False
