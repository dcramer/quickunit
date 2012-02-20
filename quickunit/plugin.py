"""
quickunit.plugin
~~~~~~~~~~~~~~~~

:copyright: 2012 DISQUS.
:license: BSD
"""

from __future__ import absolute_import

import inspect
import logging
import os
import simplejson
import sys

from coverage import coverage
from coverage.report import Reporter
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

    def _setup_coverage(self):
        instance = coverage(include=os.path.join(os.getcwd(), '*'))
        #instance.collector._trace_class = ExtendedTracer
        instance.use_cache(False)
        instance.exclude('#pragma[: ]+[nN][oO] [cC][oO][vV][eE][rR]')
        return instance

    def options(self, parser, env):
        Plugin.options(self, parser, env)
        parser.add_option("--quickunit-prefix", dest="quickunit_prefix", action="append")
        parser.add_option("--quickunit-output", dest="quickunit_output")

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

        self.pending_files = set()

        # diff is a mapping of filename->set(linenos)
        self.diff_data = defaultdict(set)

        self.cov_data = defaultdict(lambda: defaultdict(set))

        # the root directory of our diff (this is basically cwd)
        self.root = None

        report_output = options.quickunit_output
        if not report_output or report_output == '-':
            self.report_file = None
        elif report_output.startswith('sys://'):
            pipe = report_output[6:]
            assert pipe in ('stdout', 'stderr')
            self.report_file = getattr(sys, pipe)
        else:
            self.report_file = open(report_output, 'w')

    def begin(self):
        # If we're recording coverage we need to ensure it gets reset
        self.coverage = self._setup_coverage()

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

            # we dont care about missing coverage for new code, and there
            # wont be any "existing coverage" to check for
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
                if lineno in diff_data:
                    # Remove it from the coverage data
                    for prefix in self.prefixes:
                        if filename.startswith(prefix):
                            self.tests_run.add(filename)
                    return True

        for prefix in self.prefixes:
            if filename.startswith(prefix):
                self.tests_run.add(filename)
                for pending in self.pending_files:
                    if filename.startswith(pending):
                        return True

        return False

    def startTest(self, test):
        self.coverage.start()

    def stopTest(self, test):
        cov = self.coverage
        cov.stop()

        # this must have been imported under a different name
        # if self.discover and test_name not in self.pending_funcs:
        #     self.logger.warning("Unable to determine origin for test: %s", test_name)
        #     return

        # initialize reporter
        rep = Reporter(cov)

        # process all files
        rep.find_code_units(None, cov.config)

        # Compute the standard deviation for all code executed from this test
        linenos = []
        for filename in cov.data.measured_files():
            linenos.extend(cov.data.executed_lines(filename).values())

        # We're recording so fetch the test data
        test_ = test.test
        test_name = self._get_name_from_test(test_)

        cov_data = self.cov_data[test_name]
        for cu in rep.code_units:
            # if sys.modules[test_.__module__].__file__ == cu.filename:
            #     continue
            filename = cu.name + '.py'
            linenos = cov.data.executed_lines(cu.filename)

            diff = self.diff_data[filename]
            cov_linenos = [l for l in linenos if l in diff]
            if cov_linenos:
                cov_data[filename].update(cov_linenos)

        cov.erase()

    def report(self, stream):
        if not self.verbosity:
            return

        self._report_test_coverage(stream)

    def _report_test_coverage(self, stream):
        diff_data = self.diff_data
        cov_data = self.cov_data

        covered = 0
        total = 0
        missing = defaultdict(set)
        data = defaultdict(dict)

        for test, coverage in cov_data.iteritems():
            for filename, covered_linenos in coverage.iteritems():
                if filename in self.tests_run:
                    continue
                linenos = diff_data[filename]

                total += len(linenos)
                covered += len(covered_linenos)

                missing[filename] = linenos.difference(covered_linenos)

                data[test][filename] = dict((k, 1) for k in covered_linenos)
                data[test][filename].update(dict((k, 0) for k in missing[filename]))

        if self.report_file:
            self.report_file.write(simplejson.dumps({
                'stats': {
                    'covered': covered,
                    'total': total,
                },
                'tests': data,
            }))
            self.report_file.close()
        # elif total:
        #     stream.writeln('Coverage Report')
        #     stream.writeln('-' * 70)
        #     stream.writeln('Coverage against diff is %.2f%% (%d / %d lines)' % (covered / float(total) * 100, covered, total))
        #     if missing:
        #         stream.writeln()
        #         stream.writeln('%-35s   %s' % ('Filename', 'Missing Lines'))
        #         stream.writeln('-' * 70)
        #         for filename, linenos in sorted(missing.iteritems()):
        #             if not linenos:
        #                 continue
        #             stream.writeln('%-35s   %s' % (filename, ', '.join(map(str, sorted(linenos)))))
