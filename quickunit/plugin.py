"""
quickunit.plugin
~~~~~~~~~~~~~~~~

:copyright: 2011 DISQUS.
:license: BSD
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

        git diff origin/master

    If you run with the discover flag, it will attempt to discovery
    any tests that are required to run to test the changes in your current
    branch, against those of origin/master.

    """
    score = 1000
    name = 'quickunit'

    def options(self, parser, env):
        Plugin.options(self, parser, env)
        parser.add_option("--quickunit-prefix", dest="quickunit_prefix", default="tests/unit/")

    def configure(self, options, config):
        Plugin.configure(self, options, config)
        if not self.enabled:
            return

        self.prefix = options.quickunit_prefix
        self.parent = 'master'

        self.logger = logging.getLogger(__name__)

        self.pending_files = set()

        # diff is a mapping of filename->set(linenos)
        self.diff_data = defaultdict(set)

        # the root directory of our diff (this is basically cwd)
        self.root = None

    def begin(self):
        # XXX: this is pretty hacky
        proc = Popen(['git', 'merge-base', 'HEAD', self.parent], stdout=PIPE, stderr=STDOUT)
        self.parent_revision = proc.stdout.read().strip()

        # pull in our diff
        # git diff `git merge-base HEAD master`
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

            # we dont care about missing coverage for new code, and there
            # wont be any "existing coverage" to check for
            if is_new_file:
                continue

            self.pending_files.add(os.path.join(self.prefix, new_filename.rsplit('.', 1)[0]))

    def wantMethod(self, method):
        # only works with unittest compatible functions currently
        method = getattr(sys.modules[method.im_class.__module__], method.im_class.__name__)

        # check if this test was modified (e.g. added/changed)
        filename = inspect.getfile(method)
        if self.root and filename.startswith(self.root):
            filename = filename[len(self.root):]

        diff_data = self.diff_data[filename]
        if diff_data:
            lines, startlineno = inspect.getsourcelines(method)
            for lineno in xrange(startlineno, len(lines) + startlineno):
                if lineno in diff_data:
                    return True

        if filename.startswith(self.prefix):
            for pending in self.pending_files:
                if filename.startwith(pending):
                    return True

        return False
