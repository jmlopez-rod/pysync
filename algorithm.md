# Algorithm

The primary idea behind `pysync` is to use `rsync` to take care of transfering
files from one machine to another without worrying about what needs to be
updated or deleted.

`pysync` first calls `rsync` with the option `--dry-run` and `--delete` to see
what rsync would do when bringing files from the remote directory to the local
one. This gives a list of files which might be brought over and files that it
plans on deleting. `rsync` is also used with the option 
`--out-format='%n<>%M'` to display the names of the files and the last
modified date of the file.

## Incoming Files

This is a list of files that `rsync` would like to update on your local 
machine. It compares the last modified date of file in the remote
machine and the last modified date of the local machine. If the local and remote
files have a date older than the last sync date it means that the file
was modified in both machines and there might be some information that might be
lost if we use `rsync` to receive or send files. The action that I decided to
take is to rename the local file by appending the name of the machine and the
last modified date of the file. Now there won't be a conflict with the files.

Some files will may have been deleted in the remote directory. If the local
last modified date is after the last date synced then the file needs to stay.

## rsync REMOTE to LOCAL

The previous step generated the files `exclude.txt` and `remove.txt`. The
exclude file is used when tranfering files from the remote directory to the
local directory.

## Clean Local Directory

Next we iterate over the list of files and directories specified in `remove.txt`
to delete them from the system. A file/directory will only be on this list if
`rsync` detected that the file does not exist on the remote directory. This is
the reason we first do a dry run with the `--delete` option.


## Sync LOCAL to REMOTE

Now we sync the local directory to the remote with the `--delete` option so that
both local and remote have the same contents.

## Snapshot

To help keep track of the files that are meant to be in both directories we
store a list of them in a file that is managed by the entry. This file is used
in subsequent calls to `pysync` to determine the list of files to exclude and
remove.

### Naming files

`pysync` creates a list of files to exclude some files when using `rsync`. 
This puts a restriction on the name of the files: Do not use the character set
`*?[`. Otherwise you might run into problems (rsync may interpret as regex).
Try to keep the name of the files fairly simple.
