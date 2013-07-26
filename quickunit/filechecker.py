import os.path
import re

from quickunit.utils import clean_bytecode_extension


class FileChecker(dict):
    def __init__(self, rules, root=None):
        self.rules = rules
        self.changed_files = set()
        self.root = root
        self.compiled = False
        dict.__init__(self)

    def __missing__(self, filepath):
        self[filepath] = self.check(filepath)
        return self[filepath]

    def compile(self):
        self.compiled = True

        if self.root is None:
            try:
                filepath = self.changed_files.pop()
            except IndexError:
                self.root = ''
            else:
                self.changed_files.add(filepath)
                self.root = os.path.abspath(filepath)[:-len(filepath)]

        rules = []
        for filepath in self.changed_files:
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
            for rule in self.rules:
                rules.append(re.compile(rule.format(**params)))
        self.rules = rules

    def add(self, filepath):
        if self.compiled:
            raise Exception('The rules for this FileChecker are already compiled and files can no longer be added')
        self.changed_files.add(filepath)

    def check(self, filepath):
        filepath = clean_bytecode_extension(filepath)

        # check if this test was modified (e.g. added/changed)
        if self.root and filepath.startswith(self.root):
            filepath = filepath[len(self.root):]

        # if the filepath is actually the changed file
        if filepath in self.changed_files:
            return None

        for rule in self.rules:
            if rule.search(filepath):
                return None

        return False
