from subprocess import Popen, PIPE, STDOUT

from quickunit.diff import DiffParser
from quickunit.vcs.base import ChangedFile


def parse_commit(parent=None):
    if parent is None:
        parent = 'master'

    proc = Popen(['git', 'merge-base', 'HEAD', parent], stdout=PIPE, stderr=STDOUT)

    parent_revision = proc.stdout.read().strip()

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

        is_new = (file['old_filename'] == '/dev/null')

        files.append(ChangedFile(filename, is_new))

    return files
