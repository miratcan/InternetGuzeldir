import os, tempfile


class TemporaryFile:
    def __init__(self, name, io, delete):
        self.name = name
        self.__io = io
        self.__delete = delete

    def __getattr__(self, k):
        return getattr(self.__io, k)

    def __del__(self):
        if self.__delete:
            try:
                os.unlink(self.name)
            except FileNotFoundError:
                pass


def NamedTemporaryFile(mode='w+b', bufsize=-1, suffix='', prefix='tmp', dir=None, delete=True):
    if not dir:
        dir = tempfile.gettempdir()
    name = os.path.join(dir, prefix + os.urandom(8).hex() + suffix)
    if mode is None:
        return TemporaryFile(name, None, delete)
    fh = open(name, "w+b", bufsize)
    if mode != "w+b":
        fh.close()
        fh = open(name, mode)
    return TemporaryFile(name, fh, delete)
