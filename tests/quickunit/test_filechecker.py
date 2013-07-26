from unittest2 import TestCase

from quickunit.plugin import FileChecker


class FileCheckerTest(TestCase):
    def test_rules(self):
        changed_files = set([
            'foo/bar/__init__.py',
            'foo/bar/baz.py',
            'foo/bar/biz.py',
            'tests/foo/bar/test_biz.py',
            'foo/bar/phone_helpers.js'
        ])
        file_checker = FileChecker(
            rules=['tests/{path}/test_{filename}', '{basename}_test.coffee'],
            root='',
        )
        for filepath in changed_files:
            file_checker.add(filepath)

        self.assertIsNone(file_checker['tests/foo/bar/test_baz.py'])
        self.assertIsNone(file_checker['tests/foo/bar/test_biz.py'])
        self.assertFalse(file_checker['tests/foo/baz/test_bar.py'])
        self.assertIsNone(file_checker['static/coffee/tests/phone_helpers_test.coffee'])
