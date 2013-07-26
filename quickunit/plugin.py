"""
quickunit.plugin
~~~~~~~~~~~~~~~~

:copyright: 2012 DISQUS.
:license: Apache 2.0
"""

from __future__ import absolute_import

import inspect
import logging
import os
import re
import sys

from collections import namedtuple
from nose.plugins.base import Plugin
from subprocess import Popen, PIPE, STDOUT

from quickunit.diff import DiffParser
from quickunit.utils import is_py_script, clean_bytecode_extension


ChangedFile = namedtuple('ChangedFile', ['filename', 'is_new'])

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


class QuickUnitPlugin(Plugin):
    """
    We find the diff with the parent revision for diff-tests with::

        git diff `git merge-base HEAD master`

    If you run with the discover flag, it will attempt to discovery
    any tests that are required to run to test the changes in your current
    branch, against those of the parent commit.

    """
    score = 1000
    name = 'quickunit'

    def _get_name_from_test(self, test):
        test_method_name = test._testMethodName

        # We need to determine the *actual* test path (as thats what nose gives us in wantMethod)
        # for example, maybe a test was imported in foo.bar.tests, but originated as foo.bar.something.MyTest
        # in this case, we'd need to identify that its *actually* foo.bar.something.MyTest to record the
        # proper coverage
        test_ = getattr(sys.modules[test.__module__], test.__class__.__name__)

        test_name = '%s:%s.%s' % (test_.__module__, test_.__name__,
                                                     test_method_name)

        return test_name

    def options(self, parser, env):
        Plugin.options(self, parser, env)
        parser.add_option("--quickunit-rule", dest="quickunit_rule", action="append")
        parser.add_option("--quickunit-root", dest="quickunit_root")
        parser.add_option("--quickunit-parent-branch", dest="quickunit_parent_branch")

    def configure(self, options, config):
        Plugin.configure(self, options, config)
        if not self.enabled:
            return

        rules = options.quickunit_rule
        # handle setup.cfg strangeness
        if not rules:
            rules = ['tests/{path}/test_{filename}']
        elif len(rules) == 1:
            rules = rules[0].split('\n')

        root = options.quickunit_root

        self.logger = logging.getLogger(__name__)
        self.verbosity = options.verbosity
        self.parent_branch = options.quickunit_parent_branch
        # files which were changed as part of the diff
        self.changed_files = set()
        # store a list of filenames that should be accepted
        self.file_checker = FileChecker(rules, root)

    def parse_git_commit(self):
        parent_branch = self.parent_branch or 'master'
        proc = Popen(['git', 'merge-base', 'HEAD', parent_branch], stdout=PIPE, stderr=STDOUT)

        parent_revision = proc.stdout.read().strip()

        if self.verbosity > 1:
            self.logger.info("Parent commit identified as %s", parent_revision)

        # pull in our diff
        # git diff `git merge-base HEAD master`
        proc = Popen(['git', 'diff', parent_revision], stdout=PIPE, stderr=STDOUT)
        diff = proc.stdout.read().strip()

        parser = DiffParser(diff)

        files = []
        for file in parser.parse():
            if file['is_header']:
                continue

            # file was removed
            if file['new_filename'] == '/dev/null':
                continue

            filename = file['new_filename'][2:]

            # Ignore non python files
            if not is_py_script(filename):
                continue

            is_new = (file['old_filename'] == '/dev/null')

            files.append(ChangedFile(filename, is_new))

        return files

    def begin(self):
        file_list = self.parse_git_commit()

        for c_file in file_list:
            self.file_checker.add(c_file.filename)
        self.file_checker.compile()

        if self.verbosity > 1:
            self.logger.info("Found %d changed file(s)", file_list)

    def wantMethod(self, method):
        # only works with unittest compatible functions currently
        method = getattr(sys.modules[method.im_class.__module__], method.im_class.__name__)

        try:
            # check if this test was modified (e.g. added/changed)
            filename = inspect.getfile(method)
        except TypeError:
            return None

        return self.file_checker[filename]
