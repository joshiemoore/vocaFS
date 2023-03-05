#!/usr/bin/env python3

import argparse
from collections import defaultdict
import errno
import os
import pyfuse3
import stat
import time
import trio

from vocafsnode import VocaFSNode


MAX_INODES = 65535


class VocaFS(pyfuse3.Operations):
    def __init__(self, inode_dict=None):
        super(pyfuse3.Operations, self).__init__()
        self.inode_open_count = defaultdict(int)
        if inode_dict:
            self.inode_dict = inode_dict
        else:
            root_dir = VocaFSNode()
            root_dir.mode = (stat.S_IFDIR | 0o755)
            root_dir.size = 0
            cur_time_ns = time.time_ns()
            root_dir.ctime = cur_time_ns
            root_dir.mtime = cur_time_ns
            root_dir.atime = cur_time_ns
            root_dir.uid = os.getuid()
            root_dir.gid = os.getgid()
            self.inode_dict = {
                pyfuse3.ROOT_INODE: root_dir
            }

    def get_inode(self):
        for i in range(1, MAX_INODES):
            if not i in self.inode_dict:
                return i
        return None
    
    async def _create(self, inode_p, name, mode, ctx, rdev=0, target=None):
        # TODO verify parent is not unlinked

        inode = self.get_inode()
        # TODO verify we got an inode
        fsnode = VocaFSNode()
        self.inode_dict[inode] = fsnode

        fsnode.name = name
        fsnode.parent_inode = inode_p
        cur_time_ns = time.time_ns()
        fsnode.uid = ctx.uid
        fsnode.gid = ctx.gid
        fsnode.mode = mode
        fsnode.ctime = cur_time_ns
        fsnode.mtime = cur_time_ns
        fsnode.atime = cur_time_ns
        fsnode.rdev = rdev
        fsnode.target = target

        return await self.getattr(inode)

    async def _remove(self, inode_p, name, entry):
        for inode_key in self.inode_dict:
            if self.inode_dict[inode_key].parent_inode == entry.st_ino:
                raise pyfuse3.FUSEError(errno.ENOTEMPTY)
        delete_inodes = [key for key in self.inode_dict if self.inode_dict[key].parent_inode == inode_p and self.inode_dict[key].name == name]
        for key in delete_inodes:
            del self.inode_dict[key]

    async def getattr(self, inode, ctx=None):
        entry = pyfuse3.EntryAttributes()
        try:
            fsnode = self.inode_dict[inode]
        except KeyError:
            raise pyfuse3.FUSEError(errno.ENOENT)

        entry.st_ino = inode
        entry.generation = 0
        entry.entry_timeout = 300
        entry.attr_timeout = 300
        entry.st_blksize = 512
        entry.st_blocks = 1
        if fsnode.mode is not None:
            entry.st_mode = fsnode.mode
        if fsnode.size is not None:
            entry.st_size = fsnode.size
        if fsnode.ctime is not None:
            entry.st_ctime_ns = fsnode.ctime
        if fsnode.mtime is not None:
            entry.st_mtime_ns = fsnode.mtime
        if fsnode.atime is not None:
            entry.st_atime_ns = fsnode.atime
        if fsnode.uid is not None:
            entry.st_uid = fsnode.uid
        if fsnode.gid is not None:
            entry.st_gid = fsnode.gid

        return entry

    async def setattr(self, inode, attr, fields, fh, ctx):
        fsnode = self.inode_dict[inode];
        if fields.update_size:
            # TODO
            pass
        if fields.update_mode:
            fsnode.mode = attr.st_mode
        if fields.update_uid:
            fsnode.uid = attr.str_uid
        if fields.update_gid:
            fsnode.gid = attr.str_gid
        if fields.update_ctime:
            fsnode.ctime = attr.st_ctime_ns
        if fields.update_mtime:
            fsnode.mtime = attr.st_mtime_ns
        if fields.update_atime:
            fsnode.atime = attr.st_atime_ns

        return await self.getattr(inode)

    async def lookup(self, inode_p, name, ctx=None):
        inode = None
        if name == '.':
            inode = inode_p
        elif name == '..':
            inode = self.inode_dict[inode_p].parent_inode
        else:
            for inode_key in self.inode_dict.keys():
                fsnode = self.inode_dict[inode_key]
                if fsnode.parent_inode == inode_p and fsnode.name == name:
                    inode = inode_key
                    break
        if not inode:
            raise pyfuse3.FUSEError(errno.ENOENT)
        return await self.getattr(inode, ctx=ctx)

    async def mknod(self, inode_p, name, mode, rdev, ctx):
        return await self._create(inode_p, name, mode, ctx=ctx, rdev=rdev)

    async def mkdir(self, inode_p, name, mode, ctx):
        return await self._create(inode_p, name, mode, ctx=ctx)

    async def opendir(self, inode, ctx):
        return inode

    async def readdir(self, inode_p, off, token):
        for inode_key in self.inode_dict:
            fsnode = self.inode_dict[inode_key]
            if fsnode.parent_inode == inode_p and inode_key > off:
                pyfuse3.readdir_reply(token, fsnode.name, await self.getattr(inode_key), inode_key)

    async def create(self, inode_parent, name, mode, flags, ctx):
        entry = await self._create(inode_parent, name, mode, ctx)
        self.inode_open_count[entry.st_ino] += 1
        return (pyfuse3.FileInfo(fh=entry.st_ino), entry)

    async def unlink(self, inode_p, name, ctx):
        entry = await self.lookup(inode_p, name)
        if stat.S_ISDIR(entry.st_mode):
            raise pyfuse3.FUSEError(errno.EISDIR)
        await self._remove(inode_p, name, entry)

    async def rmdir(self, inode_p, name, ctx):
        entry = await self.lookup(inode_p, name)
        if not stat.S_ISDIR(entry.st_mode):
            raise pyfuse3.FUSEError(errno.ENOTDIR)
        await self._remove(inode_p, name, entry)

    async def open(self, inode, flags, ctx):
        self.inode_open_count[inode] += 1
        return pyfuse3.FileInfo(fh=inode)

    async def release(self, fh):
        self.inode_open_count[fh] -= 1

    async def access(self, inode, mode, ctx):
        return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mountpoint', type=str,
        help='Where to mount the file system')
    parser.add_argument('--debug-fuse', action='store_true', default=False,
        help='Enable FUSE debugging output')
    args = parser.parse_args()

    # TODO load inode dict from inodes.json

    vocafs = VocaFS()
    fuse_options = set(pyfuse3.default_options)
    if args.debug_fuse:
        fuse_options.add('debug')
    pyfuse3.init(vocafs, args.mountpoint, fuse_options)
    try:
        trio.run(pyfuse3.main)
    except:
        pyfuse3.close(unmount=False)
        raise

    pyfuse3.close()
