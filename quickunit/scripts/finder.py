import fnmatch
import os

from quickunit.filechecker import FileChecker
from quickunit.vcs import git


def main(test_paths, pattern='*', root=None, parent_branch=None, rules=None):
    # store a list of filenames that should be accepted
    file_checker = FileChecker(rules, root)

    file_list = git.parse_commit(parent=parent_branch)
    for c_file in file_list:
        file_checker.add(c_file.filename)
    file_checker.compile()

    if root:
        os.chdir(root)

    matches = []
    for path in test_paths:
        for root, dirnames, filenames in os.walk(path):
            for filename in fnmatch.filter(filenames, pattern):
                filepath = os.path.join(root, filename)
                if file_checker[filepath] is not False:
                    matches.append(filepath)

    return '\n'.join(matches)


if __name__ == '__main__':
    import pkg_resources

    from optparse import OptionParser

    version = pkg_resources.get_distribution('quickunit').version

    parser = OptionParser(version=version)
    parser.add_option("--root", dest='root')
    parser.add_option("--pattern", dest='pattern', default='*')
    parser.add_option("--parent-branch", dest='parent_branch')
    parser.add_option("--rule", dest='rules', action='append')
    (opts, args) = parser.parse_args()

    if not args:
        parser.error("You must specify test directories")

    print main(args, **vars(opts))
