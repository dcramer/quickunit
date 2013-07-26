import fnmatch
import os

from quickunit.filechecker import FileChecker
from quickunit.vcs import get_vcs


def run(test_paths, pattern='*', root=None, parent_branch=None, rules=None):
    # store a list of filenames that should be accepted
    file_checker = FileChecker(rules, root)

    if root is None:
        root = ''

    root = os.path.realpath(root)

    os.chdir(root)

    vcs = get_vcs(root)

    file_list = vcs.parse_commit(parent=parent_branch)
    if not file_list:
        return ''

    for c_file in file_list:
        file_checker.add(c_file.filename)

    matches = []
    for path in test_paths:
        for f_root, _, filenames in os.walk(path):
            for filename in fnmatch.filter(filenames, pattern):
                filepath = os.path.join(f_root, filename)
                if file_checker[filepath] is not False:
                    matches.append(filepath)

    return '\n'.join(matches)


def main():
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

    print run(args, **vars(opts))


if __name__ == '__main__':
    main()
