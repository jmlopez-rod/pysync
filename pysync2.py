#!/usr/bin/python3
"""
pysync is a script to sync directories using rsync.
Visit the pysync repo for more information.

- pysync: http://jmlopez-rod.github.com/pysync
- rsync: http://rsync.samba.org/

License: http://creativecommons.org/licenses/by-sa/3.0/
"""
import os
import sys
import time
import json
import traceback
import inspect
import socket
import optparse
from datetime import datetime
from subprocess import Popen, PIPE
from collections import OrderedDict


COLORS = True
SETTINGS = f'{os.environ["HOME"]}/.pysync/pysync.json'


class BreakIteration(Exception):
    def __init__(self, left):
        Exception.__init__(self)
        self.left = left


class Issue(Exception):
    def __init__(self, message, description=None, cause=None, **kwargs):
        Exception.__init__(self)
        self.message = message
        self.description = description
        self.cause = cause
        self.data = kwargs.get('data')
        self.include_traceback = kwargs.get('include_traceback', True)
        if self.include_traceback:
            frame = inspect.currentframe()
            try:
                self.traceback = [
                    y
                    for x in traceback.format_stack(frame)[:-1]
                    for y in x.splitlines()
                ]
            finally:
                del frame

    def to_dict(self):
        obj = OrderedDict([('message', self.message)])
        if self.description:
            obj['description'] = self.description
        if self.data:
            obj['data'] = self.data
        if self.include_traceback:
            obj['traceback'] = self.traceback
        if self.cause:
            if isinstance(self.cause, Issue):
                obj['cause'] = self.cause.to_dict()
            else:
                obj['cause'] = repr(self.cause)
        return obj

    def __str__(self):
        return json.dumps(self.to_dict(), indent=2)


class Either:
    def __init__(self, right, val):
        self.right = right
        self.value = val

    def __iter__(self):
        if self.right:
            yield self.value
        else:
            raise BreakIteration(self)

    def iter(self):
        if self.right:
            yield self.value

    def swap(self):
        self.right = not self.right
        return self

    def flat_map(self, fct):
        return fct(self.value) if self.right else self

    def flat_map_left(self, fct):
        return fct(self.value) if not self.right else self


class Left(Either):
    def __init__(self, val):
        Either.__init__(self, False, val)


class Right(Either):
    def __init__(self, val):
        Either.__init__(self, True, val)


def eval_iteration(comp):
    try:
        return Right(comp()[0])
    except BreakIteration as ex:
        return ex.left


def read_json(filename):
    try:
        return Right(json.loads(open(filename).read()))
    except Exception as ex:
        return Left(Issue(
            message='failed to read json file',
            data={'filename': filename},
            cause=ex,
        ))


def to_json(data):
    try:
        return Right(json.dumps(data, indent=2))
    except Exception as ex:
        return Left(Issue(
            message='failed to serialize json data',
            data={'data': data},
            cause=ex,
        ))

def write_text(text, filename):
    try:
        text_file = open(filename, "wt")
        text_file.write(text)
        text_file.close()
        return Right(True)
    except Exception as ex:
        return Left(Issue(
            message='failed to write to file',
            data={'filename': filename},
            cause=ex,
        ))


def write_json(data, filename):
    return eval_iteration(lambda: [
        True
        for jstr in to_json(data)
        for _ in write_text(jstr, filename)
    ])


def cstr(color, msg):
    return f'{color}{msg}\033[0m' if COLORS else msg


class C:
    bold = '\033[1m'
    red = '\033[31m'
    green = '\033[32m'
    yellow = '\033[33m'
    blue = '\033[34m'
    magenta = '\033[35m'
    cyan = '\033[36m'
    gray = '\033[38;5;242m'
    bd_red = '\033[1;31m'
    bd_green = '\033[1;32m'
    bd_yellow = '\033[1;33m'
    bd_blue = '\033[1;34m'
    bd_magenta = '\033[1;35m'
    bd_cyan = '\033[1;36m'


def error(msg, issue=None):
    print(f'{cstr(C.bd_red, "error:")} {msg}')
    if issue:
        print(issue)
    return 1

def warning(msg):
    print(f'{cstr(C.bd_yellow, "warning:")} {msg}')


class Pair:
    def __init__(self, name, local, remote, date_created=None, last_synced=None):
        self.name = name
        self.local = local
        self.remote = remote
        self.date_created = date_created or int(datetime.timestamp(datetime.now()))
        self.id = hex(self.date_created)
        self.date_synced = last_synced or None

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'local': self.local,
            'remote': self.remote,
            'date_created': self.date_created,
            'date_synced': self.date_synced,
        }

    def __str__(self):
        lbr = cstr(C.bold, '[')
        rbr = cstr(C.bold, ']')
        name = cstr(C.green, self.name)
        local = cstr(C.cyan, self.local)
        remote = cstr(C.magenta, self.remote)
        sync_date = cstr(C.red, '     Never Synced     ')
        if self.date_synced:
            date_fmt = '%b/%d/%Y - %H:%M:%S'
            sync_date = datetime \
                .fromtimestamp(self.date_synced) \
                .strftime(date_fmt) 
            sync_date = cstr(C.gray, sync_date)
        return ''.join([
            f"{lbr} {sync_date} {rbr}"
            f"{lbr} {name} {rbr}",
            f" {local} <==> {remote}"
        ])


def create_pair(local, remote, name):
    if not os.path.isdir(local):
        return Left(Issue(
            message='local directory does not exist',
            data={'local': local},
        ))
    if local[-1] != '/':
        local += '/'
    if not os.path.isdir(remote):
        tmp = remote.split(':')
        if len(tmp) == 1:
            return Left(Issue(
                message='non-local remote directories are of the form hostname:dir',
                data={'remote': remote},
            ))
        exit_code = os.system("ssh %s 'cd %s'" % (tmp[0], tmp[1]))
        if exit_code != 0:
            return Left(Issue(
                message='verify hostname and remote directory',
                data={
                    'remote': remote,
                    'ssh_exit_code': exit_code,
                },
            ))
    if remote[-1] != '/':
        remote += '/'
    return Right(Pair(name, local, remote))


def register(entries, local, remote, name):
    entry_either = get_entry(entries, name) \
        .swap() \
        .flat_map_left(lambda _: Left(Issue(f'{name} is already registered')))
    return eval_iteration(lambda: [
        True
        for _ in entry_either
        for new_entry in create_pair(local, remote, name)
        for _ in write_json(
            [x.to_dict() for x in (entries + [new_entry])],
            SETTINGS
        )
    ])


def get_entry(entries, name):
    entry = next((x for x in entries if x.name == name), None)
    if not entry:
        if not name.isdigit():
            return Left(Issue(f'"{name}" is not a valid entry name'))
        index = int(name)
        if index < 0 or index >= len(entries):
            return Left(Issue(
                message=f'{index} is not a valid pair number',
                data={'total': len(entries)}
            ))
    else:
        index = entries.index(entry)
    entry = entries[index]
    return Right([index, entry])


def should_proceed(prompt):
    print(prompt)
    choice = input(cstr(C.bold, '[yes/no] => ')).lower()
    if choice in ['yes', 'y']:
        return Right(True)
    elif choice in ['no', 'n']:
        return Right(False)
    return Left(Issue("Please respond with 'yes' or 'no'"))


def remove_entry(entries, index):
    del entries[index]
    return write_json([x.to_dict() for x in entries], SETTINGS)


def remove_entry_data(entry):
    data = f'{os.environ["HOME"]}/.pysync/{entry.id}.txt'
    try:
        os.remove(data)
    except FileNotFoundError:
        pass
    except:
        warning(f'Unable to remove {data}. This may need to be done manually.')
    return Right(True)


def unregister(entries, name):
    return eval_iteration(lambda: [
        True
        for index, entry in get_entry(entries, name)
        for choice in should_proceed('\n'.join([
            cstr(C.yellow, 'Are you sure you want to delete this entry:'),
            entry_str(index, entry)
        ]))
        for _ in (remove_entry(entries, index) if choice else Right(True))
        for _ in remove_entry_data(entry)
    ])


def reset_sync_date(entries, name):
    pass


def entry_str(index, entry):
    lbr = cstr(C.bold, '[')
    rbr = cstr(C.bold, ']')
    return f'{lbr} {index} {rbr}{entry}'


def print_entries(entries):
    if entries:
        for i, entry in enumerate(entries):
            print(entry_str(i, entry))
    else:
        warning('The list of directories is empty.')
        warning('See "pysync.py -h" to learn how to add an entry.')
    return 0


def parse_args():
    usage = inspect.cleandoc("""%prog local remote name
        %prog [options]

        http://jmlopez-rod.github.com/pysync

        Add entry:
            $ %prog /home/jmlopez/Dir jmlopez@hostname:/home/jmlopez/Dir dir

        List entries:
            $ %prog

        Sync all:
            $ %prog all

        Sync:
            $ %prog 0 
            or
            $ %prog dir
            or
            $ %prog -s 0
            or
            $ %prog -s dir
        """
    )
    desc = ''
    ver = "%%prog %s" % '2.0.0'
    parser = optparse.OptionParser(usage=usage, description=desc, version=ver)
    parser.add_option('-R', '--remove', 
        dest='rm_num',
        default=None, metavar='RM_NUM',
        help='Remove entry')
    parser.add_option('-r', '--reset', 
        dest='reset_num',
        default=None, metavar='RESET_NUM',
        help='Reset last sync date on entry')
    parser.add_option('-s', '--sync',
        dest='pair_num',
        default=None, metavar='PAIR_NUM',
        help='Sync the entry number or alias')
    parser.add_option('-m', '--mod-alias',
        dest='mod_alias',
        default=None, metavar='ALIAS',
        help='Modify ALIAS of entry (Requires use of -s)')
    return parser.parse_args()


def handle(either, err_msg):
    return 0 if either.right else error(err_msg, either.value)


def main():
    pysync_dir = f'{os.environ["HOME"]}/.pysync'
    if not os.path.isdir(pysync_dir):
        os.makedirs(pysync_dir)

    (options, args) = parse_args()
    if len(args) > 3:
        return error('pysync.py takes at most 3 arguments. See pysync.py -h')
    if len(args) == 2:
        return error('Provide an alias for the entry. See pysync.py -h')
    
    entries = []
    if os.path.isfile(SETTINGS):
        result = read_json(SETTINGS)
        if not result.right:
            return error('Unable to read entries', result.value)
        entries = [
            Pair(x['name'], x['local'], x['remote'], x['date_created'], x['date_synced'])
            for x in result.value
        ]

    if len(args) == 3:
        result = register(entries, args[0], args[1], args[2])
        return handle(result, 'Unable to register entry')
    
    if options.rm_num is not None:
        result = unregister(entries, options.rm_num)
        return handle(result, 'Unable to remove entry.')

    if options.reset_num is not None:
        return reset_sync_date(entries, options.reset_num)

    return print_entries(entries)


if __name__ == '__main__':
    sys.exit(main())
