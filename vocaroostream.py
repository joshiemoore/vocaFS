import errno
import io
import json
import pyfuse3
import random
import requests
import string

from vocafsnode import VocaFSNode

BASE_UPLOAD_URL = 'https://upload2.vocaroo.com/apps/main-api/upload'
BASE_DOWNLOAD_URL = 'https://media1.vocaroo.com/mp3'
MP3_HEADER = b'\xFF\xFB\xA0\x40'
CHUNK_SIZE = 100000
UPLOAD_TOKEN_LEN = 22


class VocarooUploadStream(io.RawIOBase):
    def __init__(self, fsnode):
        super().__init__()
        self.fsnode = fsnode
        self.current_chunk = 0
        self.buffer = MP3_HEADER
        self.upload_token = None
        self.session = None
        self.bytes_written = 0

    def write(self, b):
        if self.closed:
            raise ValueError()
        if not self.upload_token:
            self.session = requests.Session()
            self.session.head(BASE_UPLOAD_URL + '/alive')
            self.upload_token = ''.join(random.choices(string.ascii_letters + string.digits, k=UPLOAD_TOKEN_LEN))
        return self._write(b)

    def flush(self):
        while self.buffer:
            self._upload_chunk(self.buffer[:CHUNK_SIZE])
            self.buffer = self.buffer[CHUNK_SIZE:]

    def close(self):
        if self.closed:
            return
        resp = self.session.post(BASE_UPLOAD_URL + f'/{self.upload_token}/finalize')
        if resp.status_code != 200:
            raise pyfuse3.FUSEError(errno.EIO)
        resp_data = json.loads(resp.text)
        if resp_data['status'] != 0:
            raise pyfuse3.FUSEError(errno.EIO)
        self.fsnode.media_id = resp_data['mediaId']
        self.fsnode.owner_token = resp_data['ownerToken']
        self.fsnode.size = self.bytes_written
        super().close()

    def _write(self, b):
        self.buffer += b
        while len(self.buffer) > CHUNK_SIZE:
            self._upload_chunk(self.buffer[0:CHUNK_SIZE])
            self.buffer = self.buffer[CHUNK_SIZE:]
        self.bytes_written += len(b)
        return len(b)

    def _upload_chunk(self, chunk):
        assert self.upload_token is not None
        assert len(chunk) <= 100000
        self.session.post(
            BASE_UPLOAD_URL + f'/{self.upload_token}/chunk/{self.current_chunk}',
            files={
                'chunk': (
                    'chunk',
                    chunk,
                    'application/octet-stream'
                )
            }
        )
        self.current_chunk += 1

class VocarooDownloadStream(io.RawIOBase):
    def __init__(self, fsnode):
        super().__init__()
        self.fsnode = fsnode

    def read(self, size=None):
        if not self.fsnode.media_id:
            raise pyfuse3.FUSEError(errno.ENOENT)
        resp = requests.get(
            BASE_DOWNLOAD_URL + f'/{self.fsnode.media_id}',
            headers={
                'Referer': 'https://vocaroo.com/',
                'Sec-Fetch-Dest': 'audio',
                'Sec-Fetch-Mode': 'no-cors',
                'Sec-Fetch-Site': 'same-site'
            }
        )
        if resp.status_code != 200:
            raise pyfuse3.FUSEError(errno.EIO)
        return resp.content[4:]
