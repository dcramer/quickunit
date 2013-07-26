import os.path
from subprocess import check_call, CalledProcessError

from collections import namedtuple


ChangedFile = namedtuple('ChangedFile', ['filename', 'is_new'])


def get_vcs(root):
    if os.path.exists(os.path.join(root, '.git')):
        import quickunit.vcs.git
        return quickunit.vcs.git

    elif os.path.exists(os.path.join(root, '.hg')):
        import quickunit.vcs.hg
        return quickunit.vcs.hg

    DEVNULL = open('/dev/null')

    try:
        check_call('hg status', cwd=root, shell=True, stdout=DEVNULL, stderr=DEVNULL)
    except CalledProcessError:
        pass
    else:
        import quickunit.vcs.hg
        return quickunit.vcs.hg

    try:
        check_call('git status', cwd=root, shell=True, stdout=DEVNULL, stderr=DEVNULL)
    except CalledProcessError:
        pass
    else:
        import quickunit.vcs.git
        return quickunit.vcs.git

    raise NotImplementedError('We didnt try hard enough to figure out the vcs of %r' % (os.path.realpath(root),))
