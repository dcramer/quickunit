from subprocess import Popen, PIPE, STDOUT

from quickunit.diff import DiffParser
from quickunit.vcs.base import ChangedFile


def parse_commit(parent=None):
    cmd = ['hg', 'diff']
    if parent:
        cmd.append('-r "%s"' % (parent,))

    proc = Popen(cmd, stdout=PIPE, stderr=STDOUT)
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
