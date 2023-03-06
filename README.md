# vocaFS
This project implements a virtual filesystem based on libfuse which streams files to Vocaroo as "audio" instead of saving
them to a block device. As a result, we can use Vocaroo as our own free cloud storage!

vocaFS is an experimental work-in-progress prototype and should not be used for anything that actually matters. Also,
this is mostly intended as an academic exercise, not for actually abusing Vocaroo in this way.

### Usage
1. Clone this repository
2. Install requirements: `$ python3 -m pip install requirements.txt`
3. Create an empty directory to mount vocaFS to, e.g. `$ mkdir voca`
4. Run vocaFS to mount the virtual filesystem: `$ ./vocafs.py voca`

Now, when you write files into the `voca` directory, they will be streamed to Vocaroo. When you go back and read these
files later, they will be streamed from Vocaroo. Vocaroo is cloud storage!

### How does it work?
This project uses pyfuse, the Python bindings for libfuse, to implement the meat of the virtual filesystem operations.

Metadata about inodes in the filesystem will be saved to `inodes.json` in the source directory. This file mostly contains
information about directory structures and where vocaFS can find your files on Vocaroo. These files are interchangeable,
so if you send your `inodes.json` to someone else and they save it into their `vocaFS` directory, they will be able to
mount the filesystem and access all the files you have saved.

In order to get the streams to Vocaroo to work, all I had to do was append a 4-byte mp3 segment header to the beginning
of the file, and this was all it took to make Vocaroo believe we are uploading legitimate mp3 audio. But the playback
doesn't work if you try to play your uploaded file on the actual website :)

![2023-03-06-022558_559x329_scrot](https://user-images.githubusercontent.com/36491773/223045467-ff2884c8-badd-4029-ad69-f5e5da198074.png)

### Limitations
vocaFS is incomplete, and there are likely many features missing that you would expect from a normal filesystem. For example,
vocaFS does not currently support links, either hard or symbolic. Overall, you should expect instability and bugs to the
point where you should not actually try to use this as your real cloud storage solution.

### Why Python?
Rapid prototyping
