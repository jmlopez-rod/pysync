#!/usr/bin/python2.7
#
#  pysync.py
#
#  Description: pysync is a script to sync folders using rsync. For info
#  on how pysync is used visit the pysync website.
#
#  pysync: http://jmlopez-rod.github.com/pysync
#  rsync: http://rsync.samba.org/
#
#  Version 0.0.1 - November 12, 2012
#          0.0.2 - November 13, 2012 - Found bug when checking directories
#                                      in the incoming list.
#          0.0.3 - December 4, 2013 - Got rid of some extra spaces. 
#                                     The code needs a lot of work,
#                                     As of now pylint gives pysync a
#                                     score of 5.66/10.
#
#  License: http://creativecommons.org/licenses/by-sa/3.0/
#  Written by Manuel Lopez
##############################################################################

try:
    import cPickle as pickle
except:
    import pickle
import os
import time
import socket
import optparse
from datetime import datetime
from subprocess import Popen, PIPE

##############################################################################
# VARIABLES
##############################################################################

HOME = os.environ['HOME']
PYSYNC = list()

##############################################################################
# UTILITIES
##############################################################################

def BD(txt): return "\033[1m"+txt+"\033[0m"

def RC(txt): return "\033[31m"+txt+"\033[0m"
def GC(txt): return "\033[32m"+txt+"\033[0m"
def YC(txt): return "\033[33m"+txt+"\033[0m"
def BC(txt): return "\033[34m"+txt+"\033[0m"
def MC(txt): return "\033[35m"+txt+"\033[0m"
def CC(txt): return "\033[36m"+txt+"\033[0m"

def BRC(txt): return "\033[1;31m"+txt+"\033[0m"
def BGC(txt): return "\033[1;32m"+txt+"\033[0m"
def BYC(txt): return "\033[1;33m"+txt+"\033[0m"
def BBC(txt): return "\033[1;34m"+txt+"\033[0m"
def BMC(txt): return "\033[1;35m"+txt+"\033[0m"
def BCC(txt): return "\033[1;36m"+txt+"\033[0m"

def error(txt):
    print BRC('ERROR: '), RC(txt)

def warning(txt):
    print BYC('WARNING: '), YC(txt)

def print_pair(index):
    v = PYSYNC[index]
    txt = BD('[ ') + GC('%d' % index) + BD(' ][ ')
    if v[3] == datetime(1,1,1):
        syncDate = '     Never Synced     '
    else:
        syncDate = v[3].strftime("%b/%d/%Y - %H:%M:%S")
    txt += RC(syncDate) + BD(']')
    if v[0] != "":
        txt += BD('[ ') + GC('"%s"' % v[0]) + BD(']: ')
    else:
        txt += BD(': ')
    print txt + CC(v[1]) + " <==> " + CC(v[2])

def store_pysync():
    global PYSYNC
    FILE = open('%s/.pysync/pysync' % HOME, 'w')
    pickle.dump(PYSYNC, FILE)
    FILE.close()

def load_pysync():
    global PYSYNC
    FILE = open('%s/.pysync/pysync' % HOME, 'r')
    PYSYNC = pickle.load(FILE)
    FILE.close()

##############################################################################
# FUNCTIONS
##############################################################################

def register(local, remote, name):
    global PYSYNC
    if not os.path.isdir(local):
        error('directory "%s" does not exist in this machine.' % local)
        exit(1)
    if local[-1] != '/':
        local += '/'
    if not os.path.isdir(remote):
        tmp = remote.split(':')
        if len(tmp) == 1:
            error('The remote path you provided does not exist')
            exit(1)
        exit_code = os.system("ssh %s 'cd %s'" % (tmp[0], tmp[1]))
        if exit_code != 0:
            msg = 'SSH returned error code: %d. ' \
                  'Verify hostname and remote directory.' % exit_code
            error(msg)
            exit(exit_code)
    if remote[-1] != '/':
        remote += '/'
    PYSYNC.append([name, local, remote, datetime(1,1,1)])
    store_pysync()
    open('%s/.pysync/%d.txt' % (HOME, len(PYSYNC)-1), 'w').close()
    msg = 'Registration successful. Run "pysync.py -s %d" to ' \
          'sync your entry.' % (len(PYSYNC)-1)
    print BC(msg)
    exit(0)

def unregister(num):
    global PYSYNC
    yes = ['yes','y']
    no = set(['no','n'])
    if num > -1 and num < len(PYSYNC):
        v = PYSYNC[num]
        print YC('Are you sure you want to delete this entry:')
        print_pair(num)
        choice = raw_input(BD("[yes/no] => ")).lower()
        if choice in ['yes', 'y']:
            del PYSYNC[num]
            store_pysync()
            os.remove('%s/.pysync/%d.txt' % (HOME, num))
            while num < len(PYSYNC):
                os.rename('%s/.pysync/%d.txt' % (HOME, num+1), '%s/.pysync/%d.txt' % (HOME, num))
                num += 1
        elif choice in ['no', 'n']:
            pass
        else:
            error("Please respond with 'yes' or 'no'")
        exit(0)
    error('Invalid pair number')
    exit(1)

def reset_sync_date(num):
    global PYSYNC
    yes = ['yes','y']
    no = set(['no','n'])
    if num > -1 and num < len(PYSYNC):
        v = PYSYNC[num]
        msg = 'Are you sure you want to reset the ' \
              'last sync date for this entry:'
        print YC(msg)
        print_pair(num)
        choice = raw_input(BD("[yes/no] => ")).lower()
        if choice in ['yes', 'y']:
            PYSYNC[num][3] = datetime(1, 1, 1)
            store_pysync()
            open('%s/.pysync/%d.txt' % (HOME, num), 'w').close()
        elif choice in ['no', 'n']:
            pass
        else:
            error("Please respond with 'yes' or 'no'")
        exit(0)
    error('Invalid pair number')
    exit(1)

def lock():
    print 'not implemented yet'
#  Read http://docs.python.org/2/library/stat.html#stat.S_IRUSR
#  Get current stats
#  >>> st = os.stat('instructions.txt')
#  Change them so that everone only has read access
#  >>> os.chmod('/Users/jmlopez/instructions.txt', stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
#  After upload change back.
#  >>> os.chmod('/Users/jmlopez/instructions.txt', st.st_mode)


def sync(index):
    global PYSYNC
    alias = PYSYNC[index][0]
    local = PYSYNC[index][1]
    remote = PYSYNC[index][2]
    sync_date = PYSYNC[index][3]
    print_pair(index)

    print BBC('STATUS: ')+BC('Receiving list of incoming files...')
    inputs = '%s %s' % (remote, local)
    command = "rsync -navz --delete --exclude .DS_Store --out-format=%n<>%M "+inputs
    p = Popen(command.split(), stdout=PIPE)
    out, err = p.communicate()
    tempfiles = out.split('\n')
    tempfiles = tempfiles[1:-4]
    incoming = list()
    remote_missing = list()
    for s in tempfiles:
        v = s.split('<>')
        if len(v) > 1:
            incoming.append((v[0], datetime.strptime(v[1], '%Y/%m/%d-%H:%M:%S')))
        else:
            remote_missing.append(s.split(' ', 1)[1])

    ##########################################################################
    # INCOMING: Checking for overwriting
    ##########################################################################
    if incoming:
        print BBC('STATUS: ')+BC('Analysing ')+BBC('%d' % len(incoming))+BC(' files to avoid erroneous overwriting...')
    exclude = open('%s/.pysync/tmp.txt' % HOME , 'w')
    for in_index, in_file in enumerate(incoming):
        num = ('[%d/' % (in_index+1))+BC('%d' % len(incoming))+"]: "
        if os.path.isfile(local+in_file[0]):
            local_time = datetime.fromtimestamp(os.path.getmtime(local+in_file[0]))
            if local_time > sync_date:
                if in_file[1] > sync_date:
                    (dirName, fileName) = os.path.split(in_file[0])
                    newName = dirName+'/(%s)(%s)' % (socket.gethostname(), local_time.strftime("%Y_%m_%d-%H_%M_%S"))+fileName
                    print num+CC(in_file[0])+YC(' will be renamed to ')+CC(newName)
                    os.rename(local+in_file[0], local+newName)
                else:
                    print num+CC(in_file[0])+RC(' has been modified locally')
            else:
                print num+CC(in_file[0])+' has not been modified'
        elif os.path.isdir(local+in_file[0]):
            print num+CC(in_file[0])+' is an existing directory.'
        else:
            print num+CC(in_file[0])+YC(' may be excluded')
            exclude.write(in_file[0]+'\n')
    exclude.close()
    # To find lines common to two files
    # http://www.unix.com/shell-programming-scripting/144741-simple-script-find-common-strings-two-files.html
    command = 'grep -Fxf %s/.pysync/tmp.txt %s/.pysync/%d.txt > %s/.pysync/exclude.txt' % (HOME, HOME, index, HOME)
    exit_code = os.system(command)

    ##########################################################################
    # REMOTE_MISSING: Avoiding local deletion
    ##########################################################################
    if remote_missing:
        print BBC('STATUS: ')+BC('Analysing ')+BBC('%d' % len(remote_missing))+BC(' local files to avoid erroneous removal...')
    exclude = open('%s/.pysync/tmp.txt' % HOME , 'w')
    for i, f in enumerate(remote_missing):
        num = ('[%d/' % (i+1))+BC('%d' % len(remote_missing))+"]: "
        if os.path.isfile(local+f):
            if datetime.fromtimestamp(os.path.getmtime(local+f)) > sync_date:
                print num+CC(f)+' has been modified - will not be deleted'
            else:
                print num+CC(f)+YC(' may require deletion')
                exclude.write(f+'\n')
        else:
            print num+'Directory '+CC(f)+YC(' may require deletion')
            exclude.write(f+'\n')
    exclude.close()
    command = 'grep -Fxf %s/.pysync/tmp.txt %s/.pysync/%d.txt > %s/.pysync/remove.txt' % (HOME, HOME, index, HOME)
    exit_code = os.system(command)

    ##########################################################################
    # RSYNC: REMOTE TO LOCAL
    ##########################################################################
    print BGC('STATUS: ')+GC('Calling rsync: REMOTE to LOCAL (UPDATE/NO DELETION)')
    inputs = '%s %s' % (remote, local)
    command = ("rsync -razuv --progress --exclude-from '%s/.pysync/exclude.txt' " % HOME)+inputs
    exit_code = os.system(command)
    if exit_code != 0:
        error('rsync returned error code: %d' % exit_code)
        exit(exit_code)

    ##########################################################################
    # CLEANING LOCAL DIRECTORY
    ##########################################################################
    FILE = open('%s/.pysync/remove.txt' % HOME, 'r')
    lines = FILE.readlines()
    FILE.close
    if lines:
        print BBC('STATUS: ')+BC(' Deleting %d files/directories...' % len(lines))
    for f in reversed(lines):
        fn = local+f[0:-1]
        if fn[-1] == '/':
            try:
                os.rmdir(fn)
                print CC(fn)+' has been deleted'
            except OSError:
                print RC('Unable to delete ')+CC(fn)
        else:
            try:
                os.remove(fn)
                print CC(fn)+' has been deleted'
            except OSError:
                print RC('Unable to delete ')+CC(fn)
    FILE.close()

    ##########################################################################
    # RSYNC: LOCAL TO REMOTE
    ##########################################################################
    print BGC('STATUS: ')+GC('Calling rsync: LOCAL to REMOTE (DELETE)')
    inputs = '%s %s' % (local, remote)
    command = "rsync -razuv --delete --progress "+inputs
    exit_code = os.system(command)
    if exit_code != 0:
        error('rsync returned error code: %d' % exit_code)
        exit(exit_code)

    ##########################################################################
    # RECORDING SYNC
    ##########################################################################
    PYSYNC[index][3] = datetime.now()
    print BGC('STATUS: ')+GC('Saving sync date: %s...' % PYSYNC[index][3].strftime("%b/%d/%Y - %H:%M:%S"))
    print '\n'
    store_pysync()
    change_dir = 'cd %s;'
    # Make find show slash after directories
    #  http://unix.stackexchange.com/a/4857
    list_contents = 'find . -type d -exec sh -c \'printf "%%s/\n" "$0"\' {} \; -or -print'
    # Need to delete ./ from the path:
    #  http://stackoverflow.com/a/1571652/788553
    remove_relative = ' | sed s:"./":: > %s/.pysync/%d.txt'
    command = (change_dir+list_contents+remove_relative) % (local, HOME, index)
    exit_code = os.system(command)
    #os.remove('%s/.pysync/tmp.txt' % HOME)
    #os.remove('%s/.pysync/exclude.txt' % HOME)
    #os.remove('%s/.pysync/remove.txt' % HOME)

def sync_pair(arg):
    global PYSYNC
    if arg.isdigit():
        index = [int(arg)]
    else:
        index = [i for i, v in enumerate(PYSYNC) if v[0] == arg]
    if index:
        for i in index:
            try:
                v = PYSYNC[i]
            except IndexError:
                error('The pair number you specified is invalid.')
                exit(1)
            sync(i)
        print BBC('PYSYNC is DONE')
    else:
        warning('The arguments you provided give nothing to sync.')
        exit(0)

def sync_all():
    global PYSYNC
    if PYSYNC:
        for i,v in enumerate(PYSYNC):
            sync(i)
        print BBC('PYSYNC is DONE')
    else:
        warning('There is nothing to sync. See pysync.py -h')
        exit(0)

##############################################################################
# LOADING REGISTERED FOLDERS
##############################################################################
if not os.path.isdir('%s/.pysync' % HOME):
    os.makedirs('%s/.pysync' % HOME)

if os.path.isfile('%s/.pysync/pysync' % HOME):
    load_pysync()

################################################################################
# PARSING ARGUMENTS
################################################################################
usage = """%prog local remote [name]
       %prog [options]

pyrsync version 1.0.0
Written by Manuel Lopez (2012)
Web site: http://jmlopez-rod.github.com/pysync

Add entry:
    $ pysync.py /home/jmlopez/Dir jmlopez@hostname:/home/jmlopez/Dir

Add entry with alias:
    $ pysync.py /home/jmlopez/Dir jmlopez@hostname:/home/jmlopez/Dir dir

List entries:
    $ pysync.py

Sync all:
    $ pysync.py all

Sync:
    $ psync.py -s 0 
    or
    $ pysnc.py -s dir"""
desc = """"""
ver = "%%prog %s" % '0.0.1'

parser = optparse.OptionParser(usage=usage, description=desc, version=ver)
parser.add_option("-R", "--remove", dest="rm_num",
                  default=None, metavar="RM_NUM",
                  help="Remove entry and exit")
parser.add_option("-r", "--reset", dest="reset_num",
                  default=None, metavar="RESET_NUM",
                  help="Reset last sync date on entry and exit")
parser.add_option("-s", "--sync", dest="pair_num",
                  default=None, metavar="PAIR_NUM",
                  help="Sync the entry number or alias")
parser.add_option("-m", "--mod-alias", dest="mod_alias",
                  default=None, metavar="ALIAS",
                  help="Modify ALIAS of entry (Requires use of -s)")
# For future version:
#parser.add_option("-L", "--lock", dest="lock",
#                  action='store_true', default=False,
#                  help="Locks files specified in a list. See -f")

(options, args) = parser.parse_args()

###############################################################################
# CHECKING ARGUMENTS
###############################################################################
if len(args) > 3:
    error('pysync.py takes at most 3 arguments. See pysync.py -h')
    exit(1)
if len(args) == 3:
    register(args[0], args[1], args[2])
elif len(args) == 2:
    register(args[0], args[1], '')
elif len(args) == 1:
    if args[0] == 'all':
        sync_all()
    else:
        error('When using only one argument you must write "all"')
        exit(1)

if not options.mod_alias is None:
    if options.pair_num is None:
        error('You forgot to specify the pair number or alias to modify.')
        exit(1)
    if options.pair_num.isdigit():
        index = [int(options.pair_num)]
    else:
        index = [i for i, v in enumerate(PYSYNC) if v[0] == options.pair_num]
    if index:
        for i in index:
            try:
                v = PYSYNC[i]
            except IndexError:
                error('The pair number you specified is invalid.')
                exit(1)
            PYSYNC[i][0] = options.mod_alias
            print BBC('The alias for entry %d has been set to %s.' % (i, options.mod_alias))
        store_pysync()
    else:
        warning('There is no alias to modify.')
        exit(0)

    exit(0)

if not options.reset_num is None:
    reset_sync_date(int(options.reset_num))
    exit(0)

if not options.rm_num is None:
    unregister(int(options.rm_num))
    exit(0)

if not options.pair_num is None:
    sync_pair(options.pair_num)
    exit(0)

if PYSYNC:
    for i in xrange(len(PYSYNC)):
        print_pair(i)
else:
    warning('The list of directories is empty.')
    warning('See "pysync.py -h" to learn how to add an entry.')
