import os.path

from collections import namedtuple


ChangedFile = namedtuple('ChangedFile', ['filename', 'is_new'])


def get_vcs(root):
    if os.path.exists(os.path.join(root, '.git')):
        import quickunit.vcs.git
        return quickunit.vcs.git
    elif os.path.exists(os.path.join(root, '.hg')):
        import quickunit.vcs.hg
        return quickunit.vcs.hg
    else:
        raise NotImplementedError('We didnt try hard enough to figure out the vcs of %r' % (os.path.realpath(root),))
