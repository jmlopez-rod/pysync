# pysync (BETA)

`pysync` is a python script designed to work in a similar fashion as [DropBox]
using [rsync] as the main process to transfer files. 

## WARNING:

This script is still in its testing stages. Use at your own risk.

## Requirements

To use this script your system needs to have `rsync`, `grep`, `ssh` and 
`python` installed.

## Basic use

The primary idea behind `pysync` is to use `rsync` to take care of transfering
files from one machine to another without worrying about what needs to be
updated or deleted.

To get started make sure that `pysync.py` is in your `PATH`. Once this is done
you can tell `pysync` the two directories you wish to sync.

    $ pysync.py /Users/jmlopez/Dir jmlopez@ssh.math.uh.edu:/home/jmlopez/Dir

If the two directories exist then `pysync` will give you a message telling you
that the registration was successful. This may take a little while since
`pysync` uses `ssh` to attempt access the remote directory for verification
purposes.

I should note that for remote connections it would be convenient to have
password-less `ssh` since `pysync` uses `rsync` to connect to the remote
machine three times.

To check the list of recorded directories call `pysnc` again with no arguments

    jmlopez$ pysync.py
    [ 0 ][      Never Synced     ]: /Users/jmlopez/Dir/ <==> jmlopez@ssh.math.uh.edu:/home/jmlopez/Dir/
    jmlopez$ 

To sync the `0` entry do:

    pysync.py -s 0

You can add more entries by repeating the steps above. Each entry that you 
add will be listed when you call `pysync` without any arguments.

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
machine. What we do now is compare the date of file in the remote machine
and the date of the local machine. By date I mean the last modified date of
the file. If the local and remote files have a date older than the
last sync date then this means that the file was modified in both machines
and there might be some information that might be lost if we use `rsync`
to receive or send files. The action that I decided to take is to rename
the local file by appending the name of the machine and the last modified date
of the file. Now there won't be a conflict with the files.

[To be completed later]

## Naming files

`pysync` creates a list of files to exclude some files when using `rsync`. 
This puts a restriction on the name of the files: Do not use the character set
`*?[`. Otherwise you might run into problems. Try to keep the name of the files
fairly simple.

[DropBox]: https://www.dropbox.com/
[rsync]: http://rsync.samba.org/