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

To get started make sure that `pysync.py` is in your `PATH`. Once this is done
you can tell `pysync` the two directories you wish to sync.

    $ pysync.py /Users/username/Dir username@server:/home/username/dir dir

The third argument should be a shortname which describes the connection between
the directories. This is used as an alias so that we may sync.

If the two directories exist then `pysync` will give you a message telling you
that the registration was successful. This may take a little while since
`pysync` uses `ssh` to attempt access the remote directory for verification
purposes.

For remote connections it would be convenient to have password-less `ssh` since
`pysync` uses `rsync` to connect to the remote machine three times.

To check the list of recorded directories call `pysync` again with no arguments

    jmlopez$ pysync.py
    [ 0 ][      Never Synced     ][dir]: /Users/username/Dir/ <==> jmlopez@server:/home/username/dir/
    jmlopez$

You can add more entries by repeating the steps above. Each entry that you
add will be listed when you call `pysync` without any arguments.

To sync an entry we can use the index or the name that was given to the entry.
The following are equivalent provided the above list.

    jmlopez$ pysync.py 0
    jmlopez$ pysync.py dir

To see a list of the possible entries we can use the `-l` option.

    jmlopez$ pysync.py -l
    dir

## Bash Complete

If using bash you can take advantage of the `-l` option to auto
complete. Add the following to your bashrc file

    complete -o default -W "\$(pysync.py -l)" pysync.py

After that you should be able to start typing `pysync.py [Tab]` to
show you all the entry names. See more on bash complete by visiting <https://tldp.org/LDP/abs/html/tabexpansion.html> or
reading the manual `man complete`.


[DropBox]: https://www.dropbox.com/
[rsync]: http://rsync.samba.org/

testing
