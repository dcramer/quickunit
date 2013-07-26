"""
quickunit.plugin
~~~~~~~~~~~~~~~~

:copyright: 2012 DISQUS.
:license: Apache 2.0
"""

from __future__ import absolute_import

import inspect
import sys

from nose.plugins.base import Plugin

from quickunit.filechecker import FileChecker
from quickunit.utils import is_py_script
from quickunit.vcs import git


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

        test_name = '%s:%s.%s' % (
            test_.__module__, test_.__name__, test_method_name)

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

        self.parent_branch = options.quickunit_parent_branch
        # files which were changed as part of the diff
        self.changed_files = set()
        # store a list of filenames that should be accepted
        self.file_checker = FileChecker(rules, root)

    def begin(self):
        file_list = git.parse_commit(parent=self.parent_branch)

        for c_file in file_list:
            # Ignore non python files
            if not is_py_script(c_file.filename):
                continue

            self.file_checker.add(c_file.filename)
        self.file_checker.compile()

    def wantMethod(self, method):
        # only works with unittest compatible functions currently
        method = getattr(sys.modules[method.im_class.__module__], method.im_class.__name__)

        try:
            # check if this test was modified (e.g. added/changed)
            filename = inspect.getfile(method)
        except TypeError:
            return None

        return self.file_checker[filename]
