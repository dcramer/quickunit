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
import sys

from collections import defaultdict
from nose.plugins.base import Plugin
from subprocess import Popen, PIPE, STDOUT

from quickunit.diff import DiffParser
from quickunit.utils import is_py_script


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
        parser.add_option("--quickunit-prefix", dest="quickunit_prefix", action="append")

    def configure(self, options, config):
        Plugin.configure(self, options, config)
        if not self.enabled:
            return

        self.verbosity = options.verbosity
        if options.quickunit_prefix:
            self.prefixes = options.quickunit_prefix
            if len(self.prefixes) == 1:
                self.prefixes = self.prefixes[0].split('\n')
        else:
            self.prefixes = ["tests/"]
        self.parent = 'master'

        self.logger = logging.getLogger(__name__)

        # pending files becomes a set of directorie pieces that represent
        # the file locations changed in this diff
        # for example, if /foo/bar/baz.py was changed, pending files would contain
        # set([('foo', 'bar', 'baz')])
        self.pending_files = set()

        # diff is a mapping of filename->set(linenos)
        self.diff_data = defaultdict(set)

        # the root directory of our diff (this is basically cwd)
        self.root = None

    def begin(self):
        # XXX: this is pretty hacky
        if self.verbosity > 1:
            self.logger.info("Parsing parent commit..")
        proc = Popen(['git', 'merge-base', 'HEAD', self.parent], stdout=PIPE, stderr=STDOUT)
        self.parent_revision = proc.stdout.read().strip()
        if self.verbosity > 1:
            self.logger.info("Parent commit identified as %s", self.parent_revision)

        # pull in our diff
        # git diff `git merge-base HEAD master`
        if self.verbosity > 1:
            self.logger.info("Parsing diff..")
        proc = Popen(['git', 'diff', self.parent_revision], stdout=PIPE, stderr=STDOUT)
        diff = proc.stdout.read().strip()

        parser = DiffParser(diff)
        files = list(parser.parse())

        diff = self.diff_data
        for file in files:
            # we dont care about headers
            if file['is_header']:
                continue

            # file was removed
            if file['new_filename'] == '/dev/null':
                continue

            is_new_file = (file['old_filename'] == '/dev/null')
            if is_new_file:
                filename = file['new_filename']
                if not filename.startswith('b/'):
                    continue
            else:
                filename = file['old_filename']
                if not filename.startswith('a/'):
                    continue  # ??

            filename = filename[2:]

            if self.root is None:
                self.root = os.path.abspath(filename)[:-len(filename)]

            # Ignore non python files
            if not is_py_script(filename):
                continue

            new_filename = file['new_filename'][2:]

            # file is new, only record diff state
            for chunk in file['chunks']:
                linenos = filter(bool, (l['new_lineno'] for l in chunk if l['line']))
                diff[new_filename].update(linenos)

            if is_new_file:
                continue

            for prefix in self.prefixes:
                self.pending_files.add(os.path.join(prefix, new_filename.rsplit('.', 1)[0]))

        self.tests_run = set()

        if self.verbosity > 1:
            self.logger.info("Found %d changed file(s) and %d possible test paths..", len(diff), len(self.pending_files))

    def wantMethod(self, method):
        # only works with unittest compatible functions currently
        method = getattr(sys.modules[method.im_class.__module__], method.im_class.__name__)

        # check if this test was modified (e.g. added/changed)
        filename = inspect.getfile(method)
        if self.root and filename.startswith(self.root):
            filename = filename[len(self.root):]

        # check to see if this is a modified test
        diff_data = self.diff_data[filename]
        if diff_data:
            lines, startlineno = inspect.getsourcelines(method)
            for lineno in xrange(startlineno, len(lines) + startlineno):
                if lineno not in diff_data:
                    continue

                # Remove it from the coverage data
                for prefix in self.prefixes:
                    if filename.startswith(prefix):
                        self.tests_run.add(filename)

                return True

        filepath = os.path.join(filename.rsplit('/', 1)[0])

        for prefix in self.prefixes:
            if not filename.startswith(prefix):
                continue

            self.tests_run.add(filename)

            for pending in self.pending_files:
                # if the filename is /foo/bar/tests.py and pending is /foo/bar, run it
                # if the filename is /foo/tests.py and pending is /foo, run it
                if pending.startswith(filepath):
                    return True
                elif filepath.startswith(pending):
                    return True

        return False
