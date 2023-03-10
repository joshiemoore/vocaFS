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

        self.name = b''
        self.media_id = None
        self.owner_token = None
        self.upload_stream = None

    def serialize(self):
        data = self.__dict__.copy()
        del data['upload_stream']
        data['name'] = data['name'].decode('utf-8')
        return data

    def deserialize(self, data):
        for key in data:
            if hasattr(self, key):
                setattr(self, key, data[key])
        self.name = str.encode(self.name)
