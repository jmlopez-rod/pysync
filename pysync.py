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
import json
import traceback
import inspect
import socket
import optparse
from datetime import datetime
from subprocess import Popen, PIPE, STDOUT
from collections import OrderedDict

VERSION = '2.0.0'
COLORS = True
ANSWER_YES = False
PYSYNC = f'{os.environ["HOME"]}/.pysync'
SETTINGS = f'{PYSYNC}/pysync.json'
try:
    PROG = os.path.basename(__file__)
except:
    PROG = 'pysync.py'


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
        sync_date = cstr(C.gray, '     Never Synced     ')
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
    local = os.path.abspath(local)
    if local[-1] != '/':
        local += '/'

    if os.path.isdir(remote):
        remote = os.path.abspath(remote)
    else:
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
    pair = Pair(name, local, remote)
    open(f'{PYSYNC}/{pair.id}.txt', 'w').close()
    return Right(pair)


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
        warning(f'See "{PROG} -h" to learn how to add an entry.')
    return 0


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
    if ANSWER_YES:
        return Right(True)
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


def reset_entry(entries, index):
    entries[index].date_synced = None
    return write_json([x.to_dict() for x in entries], SETTINGS)


def update_entry_name(entries, index, name):
    entries[index].name = name
    return write_json([x.to_dict() for x in entries], SETTINGS)


def print_status(status):
    print(f'{cstr(C.bd_blue, "STATUS:")} {cstr(C.blue, status)}')


def eval_cmd(cmd):
    process = Popen(
        cmd,
        shell=True,
        universal_newlines=True,
        executable="/bin/bash",
        stdout=PIPE,
        stderr=STDOUT
    )
    out, _ = process.communicate()
    if process.returncode == 0:
        return Right(out.strip())
    return Left(Issue(
        message='command returned a non zero exit code',
        data={'cmd': cmd, 'output': out}
    ))


def parse_incoming_output(out):
    temp_files = out.split('\n')[1:-3]
    incoming = []
    remote_missing = []
    for line in temp_files:
        items = line.split('<>')
        if len(items) > 1:
            fname, time = items
            incoming.append((fname, datetime.strptime(time, '%Y/%m/%d-%H:%M:%S')))
        else:
            action = line.split(' ', 1)
            if len(action) > 1:
                remote_missing.append(action[1])
    return Right((incoming, remote_missing))


def fetch_incoming(entry):
    print_status('Receiving list of incoming files...')
    cmd = ' '.join(['rsync',
        '-navz',
        '--delete',
        '--exclude .DS_Store',
        '--out-format="%n<>%M"',
        f'{entry.remote} {entry.local}'
    ])
    return eval_iteration(lambda: [
        (incoming, remote_missing)
        for out in eval_cmd(cmd)
        for incoming, remote_missing in parse_incoming_output(out)
    ])


def print_info(index, fpath, msg, color=None):
    txt = cstr(color, msg) if color else msg
    print(f'{index} {cstr(C.cyan, fpath)} {txt}')


def print_msg(msg):
    print(msg)
    return Right(0)


def write_exclusions(entry, incoming):
    if incoming:
        print_status(f'Analysing {len(incoming)} incoming files to avoid erroneous overwriting...')
    exclude_list = []
    total = cstr(C.blue, len(incoming))
    date_synced = datetime(1,1,1)
    if entry.date_synced:
        date_synced = datetime.fromtimestamp(entry.date_synced)
    for index, in_file in enumerate(incoming):
        fname = in_file[0]
        num = f'[{index+1}/{total}]:'
        file_path = f'{entry.local}{fname}'
        if os.path.isfile(file_path):
            local_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            if local_time > date_synced:
                if in_file[1] > date_synced:
                    (dir_name, file_name) = os.path.split(fname)
                    host = socket.gethostname()
                    time = local_time.strftime("%Y_%m_%d-%H_%M_%S")
                    new_name = f'{dir_name}/{file_name}-{host}-{time}'
                    os.rename(file_path, f'{entry.local}{new_name}')
                    print_info(num, fname, f'renamed to {new_name}', C.yellow)
                else:
                    print_info(num, fname, 'has been modified locally', C.red)
            else:
                print_info(num, fname, 'has not been modified')
        elif os.path.isdir(file_path):
            print_info(num, fname, 'is an existing directory')
        else:
            print_info(num, fname, 'may be excluded', C.yellow)
            exclude_list.append(fname)
    with open(f'{PYSYNC}/potential_exclusions.txt', 'w') as fp:
        fp.write('\n'.join(exclude_list))

    # To find lines common to two files
    # http://www.unix.com/shell-programming-scripting/144741-simple-script-find-common-strings-two-files.html
    command = f'grep -Fxf {PYSYNC}/potential_exclusions.txt {PYSYNC}/{entry.id}.txt > {PYSYNC}/exclude.txt'
    os.system(command)
    return Right(True)


def write_removals(entry, remote_missing):
    if remote_missing:
        print_status(f'Analysing {len(remote_missing)} local files to avoid erroneous removal...')
    removal_list = []
    total = cstr(C.blue, len(remote_missing))
    date_synced = datetime(1,1,1)
    if entry.date_synced:
        date_synced = datetime.fromtimestamp(entry.date_synced)
    for index, fname in enumerate(remote_missing):
        num = f'[{index+1}/{total}]:'
        file_path = f'{entry.local}{fname}'
        if os.path.isfile(file_path):
            local_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            if local_time > date_synced:
                print_info(num, fname, 'has been modified - will stay')
            else:
                print_info(num, fname, ' may require deletion', C.yellow)
                removal_list.append(fname)
        else:
            print_info(num, fname, 'may require directory deletion', C.yellow)
            removal_list.append(fname)
    with open(f'{PYSYNC}/potential_removals.txt', 'w') as fp:
        fp.write('\n'.join(removal_list))

    command = f'grep -Fxf {PYSYNC}/potential_removals.txt {PYSYNC}/{entry.id}.txt > {PYSYNC}/remove.txt'
    os.system(command)
    return Right(True)


def sync_remote_to_local(entry):
    print_status('Calling rsync: REMOTE to LOCAL (UPDATE/NO DELETION)')
    cmd = ' '.join(['rsync',
        '-razuv',
        '--progress',
        f'--exclude-from {PYSYNC}/exclude.txt',
        f'{entry.remote} {entry.local}'
    ])
    exit_code = os.system(cmd)
    if exit_code != 0:
        return Left(Issue(
            message='rsync REMOTE -> LOCAL failure',
            data={'exit_code': exit_code},
        ))
    return Right(True)


def clean_local_directory(entry):
    lines = open(f'{PYSYNC}/remove.txt').readlines()
    if lines:
        print_status(f'Deleting {len(lines)} local files/directories')
    index = 0
    total = cstr(C.blue, len(lines))
    for line in reversed(lines):
        index += 1
        num = f'[{index+1}/{total}]:'
        fname = f'{entry.local}{line[0:-1]}'
        if fname[-1] == '/':
            try:
                os.rmdir(fname)
                print_info(num, fname, 'has been deleted')
            except OSError:
                print_info(num, fname, 'failed to deleted', C.red)
        else:
            try:
                os.remove(fname)
                print_info(num, fname, 'has been deleted')
            except OSError:
                print_info(num, fname, 'failed to deleted', C.red)
    return Right(True)


def sync_local_to_remote(entry):
    print_status('Calling rsync: LOCAL to REMOTE (DELETION)')
    cmd = ' '.join(['rsync',
        '-razuv',
        '--progress',
        '--delete',
        f'{entry.local} {entry.remote}'
    ])
    exit_code = os.system(cmd)
    if exit_code != 0:
        return Left(Issue(
            message='rsync LOCAL -> REMOTE failure',
            data={'exit_code': exit_code},
        ))
    return Right(True)


def record_sync(entries, index):
    now = datetime.now()
    print_status(f'Saving sync date: {now.strftime("%b/%d/%Y - %H:%M:%S")}')
    entries[index].date_synced = int(datetime.timestamp(now))
    return write_json([x.to_dict() for x in entries], SETTINGS)


def take_snapshot(entry):
    print_status(f'Creating snapshot of {entry.local}')
    cmd = ''.join([
        f'cd {entry.local}; ',
        # Make find show slash after directories
        #  http://unix.stackexchange.com/a/4857
        'find . -type d -exec sh -c \'printf "%s/\\n" "$0"\' {} \; -or -print',
        # Need to delete ./ from the path:
        #  http://stackoverflow.com/a/1571652/788553
        f' | sed s:"./":: > {PYSYNC}/{entry.id}.txt'
    ])
    print(cmd)
    exit_code = os.system(cmd)
    if exit_code != 0:
        return Left(Issue(
            message='failure storing snapshot',
            data={
                'exit_code': exit_code,
                'cmd': cmd,
            },
        ))
    return Right(True)


def sync_entry(index, entries):
    entry = entries[index]
    if ANSWER_YES:
        print(entry_str(index, entry))
    return eval_iteration(lambda: [
        True
        for incoming, remote_missing in fetch_incoming(entry)
        for _ in write_exclusions(entry, incoming)
        for _ in write_removals(entry, remote_missing)
        for _ in sync_remote_to_local(entry)
        for _ in clean_local_directory(entry)
        for _ in sync_local_to_remote(entry)
        for _ in record_sync(entries, index)
        for _ in take_snapshot(entry)
    ])


def register(entries, local, remote, name):
    entry_either = get_entry(entries, name) \
        .swap() \
        .flat_map_left(lambda _: Left(Issue(f'{name} already registered')))
    return eval_iteration(lambda: [
        True
        for _ in entry_either
        for new_entry in create_pair(local, remote, name)
        for _ in write_json(
            [x.to_dict() for x in entries + [new_entry]],
            SETTINGS
        )
        for _ in print_msg(cstr(
            C.cyan,
            f'Registration successful. Run `pysync.py {name}` to sync entry.'
        ))
    ])


def unregister(entries, name):
    return eval_iteration(lambda: [
        True
        for index, entry in get_entry(entries, name)
        for choice in should_proceed('\n'.join([
            cstr(C.red, 'Are you sure you want to delete this entry:'),
            entry_str(index, entry)
        ]))
        for _ in (remove_entry(entries, index) if choice else Right(True))
        for _ in remove_entry_data(entry)
    ])


def reset_sync_date(entries, name):
    return eval_iteration(lambda: [
        True
        for index, entry in get_entry(entries, name)
        for choice in should_proceed('\n'.join([
            cstr(C.yellow, 'Are you sure you want to reset this entry:'),
            entry_str(index, entry)
        ]))
        for _ in (reset_entry(entries, index) if choice else Right(True))
        for _ in remove_entry_data(entry)
    ])


def update_name(entries, new_name, name):
    new_entry_either = get_entry(entries, new_name) \
        .swap() \
        .flat_map_left(lambda _: Left(Issue(f'{new_name} is already exists')))
    return eval_iteration(lambda: [
        True
        for _ in new_entry_either
        for index, entry in get_entry(entries, name)
        for choice in should_proceed('\n'.join([
            cstr(C.yellow, 'Are you sure you want to update the entry name?'),
            entry_str(index, entry)
        ]))
        for _ in (update_entry_name(entries, index, new_name) if choice else Right(True))
    ])


def sync(entries, name):
    return eval_iteration(lambda: [
        True
        for index, entry in get_entry(entries, name)
        for choice in should_proceed('\n'.join([
            cstr(C.yellow, 'Are you sure you want to sync the entry?'),
            entry_str(index, entry)
        ]))
        for _ in (sync_entry(index, entries) if choice else Right(True))
    ])


def parse_args():
    usage = inspect.cleandoc("""
        %prog local remote name
        %prog [options]

        http://jmlopez-rod.github.com/pysync

        Add entry:
            $ %prog /home/jmlopez/Dir jmlopez@hostname:/home/jmlopez/Dir dir

        List entries:
            $ %prog

        Sync:
            $ %prog 0

            or by name:
            $ %prog dir
        """
    )
    desc = ''
    ver = f'%prog {VERSION}'
    parser = optparse.OptionParser(usage=usage, description=desc, version=ver)
    parser.add_option('-d', '--delete',
        dest='rm_num',
        default=None, metavar='RM_NUM',
        help='Delete entry')
    parser.add_option('-r', '--reset',
        dest='reset_num',
        default=None, metavar='RESET_NUM',
        help='Reset last sync date on entry')
    parser.add_option('-n', '--name',
        dest='new_name',
        default=None, metavar='NAME',
        help='Modify NAME of entry (Requires one arg [current name])')
    parser.add_option('--no-color',
        dest='no_color',
        action="store_true",
        default=False,
        help='Print messages without color')
    parser.add_option('-y',
        dest='answer_yes',
        action="store_true",
        default=False,
        help='Skips confirmation prompt (for batch jobs)')
    parser.add_option('-l',
        dest='list_entries',
        action="store_true",
        default=False,
        help='List the available entries (useful for auto complete)')
    return parser.parse_args()


def handle(either, err_msg):
    return 0 if either.right else error(err_msg, either.value)


def main():
    global COLORS, ANSWER_YES
    pysync_dir = f'{os.environ["HOME"]}/.pysync'
    if not os.path.isdir(pysync_dir):
        os.makedirs(pysync_dir)

    (options, args) = parse_args()
    if options.no_color:
        COLORS = False

    if options.answer_yes:
        ANSWER_YES = True

    if len(args) > 3:
        return error(f'{PROG} takes at most 3 arguments. See {PROG} -h')
    if len(args) == 2:
        return error(f'Provide an alias for the entry. See {PROG} -h')

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

    if options.list_entries:
        for entry in entries:
            print(entry.name)
        return 0

    if options.rm_num is not None:
        result = unregister(entries, options.rm_num)
        return handle(result, 'Unable to remove entry.')

    if options.reset_num is not None:
        result = reset_sync_date(entries, options.reset_num)
        return handle(result, 'Unable to reset the entry.')

    if options.new_name:
        if len(args) != 1:
            return error(f'Usage: {PROG} -n [new_name] current_name')
        result = update_name(entries, options.new_name, args[0])
        return handle(result, 'Unable to update entry name.')

    if len(args) == 1:
        result = sync(entries, args[0])
        return handle(result, 'Unable to sync entry')

    return print_entries(entries)


if __name__ == '__main__':
    sys.exit(main())
