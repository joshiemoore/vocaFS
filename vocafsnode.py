class VocaFSNode:
    def __init__(self):
        self.parent_inode = None
        self.mode = None
        self.size = 0
        self.ctime = None
        self.mtime = None
        self.atime = None
        self.uid = None
        self.gid = None
        self.rdev = 0
        self.target = 0
        self.name = ''
