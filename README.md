# pysync

`pysync` is a python script designed to work in a similar fashion as [DropBox]
using [rsync] as the main process to transfer files. 

## WARNING:

This script makes system calls to `rsync` with the `--delete` option which
may result in the potential loss of data. Use at your own risk.

## Requirements

To use this script your system needs to have `rsync`, `grep`, `ssh` and 
`python3` installed.

## Basic use

The primary idea behind `pysync` is to use `rsync` to take care of transfering
files from one machine to another without worrying about what needs to be
updated or deleted.

To get started make sure that `pysync.py` is in your `PATH`. Once this is done
you can tell `pysync` the two directories you wish to sync.

    $ pysync.py /Users/username/Dir username@server:/home/username/dir dir

The third argument should be a shortname which describes the connecion between
the directories. This is used as an alias so that we may sync.

If the two directories exist then `pysync` will give you a message telling you
that the registration was successful. This may take a little while since
`pysync` uses `ssh` to attempt access the remote directory for verification
purposes.

For remote connections it would be convenient to have password-less `ssh` since
`pysync` uses `rsync` to connect to the remote machine three times.

To check the list of recorded directories call `pysnc` again with no arguments

    jmlopez$ pysync.py
    [ 0 ][      Never Synced     ][dir]: /Users/username/Dir/ <==> jmlopez@server:/home/username/dir/
    jmlopez$ 

You can add more entries by repeating the steps above. Each entry that you 
add will be listed when you call `pysync` without any arguments.

To sync an entry we can use the index or the name that was given to the entry.
The following are equivalent provided the above list.

    jmlopez$ pysync.py 0
    jmlopez$ pysync.py dir


## Algorithm

This is what `pysync` does:

Calls `rsync` with the option `--dry-run` and `--delete` to see what rsync
would do when bringing files from the remote directory to the local one.
This gives a list of files which might be brought over and files that it
plans on deleting. `rsync` is also used with the option 
`--out-format='%n<>%M'` to display the names of the files and the last
modified date of the file.

### Incoming Files

This is a list of files that `rsync` would like to update on your local 
machine. What we do is compare the last modified date of file in the remote
machine and the last modified date of the local machine. If the local and remote
files have a date older than the last sync date it means that the file
was modified in both machines and there might be some information that might be
lost if we use `rsync` to receive or send files. The action that I decided to
take is to rename the local file by appending the name of the machine and the
last modified date of the file. Now there won't be a conflict with the files.

Some files will may have been deleted in the remote directory. If the local
last modified date is after the last date synced then the file needs to stay.

### rsync REMOTE to LOCAL

The previous step generated the files `exclude.txt` and `remove.txt`. The
exclude file is used when tranfering files from the remote directory to the
local directory.


## Naming files

`pysync` creates a list of files to exclude some files when using `rsync`. 
This puts a restriction on the name of the files: Do not use the character set
`*?[`. Otherwise you might run into problems. Try to keep the name of the files
fairly simple.

[DropBox]: https://www.dropbox.com/
[rsync]: http://rsync.samba.org/