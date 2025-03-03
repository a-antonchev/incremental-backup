#!/bin/env python3

# usage: backup [date_recovery]
# если date_recovery не задана, то восстановление на последнюю дату архивации

import os
import os.path
import pathlib
import tarfile
import subprocess
import sys
import csv
import glob


def mount_dir(mount_command):
    try:
        subprocess.run(
            mount_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        print('INFO: Mount success')
    except KeyboardInterrupt:
        print('KeyboardInterrupt')
    except subprocess.CalledProcessError as err:
        print(f'ERR: Error mount {mount_point}')
        print(err.__str__())
        sys.exit(2)

def get_snapshot_dates(snapshot_dir):
    return sorted([el.split('.')[0] for el in os.listdir(snapshot_dir)])

def unpack_archive(backup_file, restore_dir):
    with tarfile.open(backup_file, 'r:gz') as f:
        f.extractall(restore_dir)

mount_point = '/mnt/store/'
backup_dir = f'{mount_point}Backup/test/'
restore_dir = '/media/antonchev/USB-накопитель/test_restore/'
snapshot_dir = f'{backup_dir}snapshots/'
mount_command = ['sudo', 'mount', '-U', '01DB2557286B1350', mount_point, '-o', 'uid=1000,gid=1000']

if not os.path.ismount(mount_point):
    print('INFO: Mount point not exists')
    mount_dir(mount_command)    

if len(sys.argv) == 1:
    shapshots_dates = get_snapshot_dates(snapshot_dir)
elif sys.argv[1] not in get_snapshot_dates(snapshot_dir):
    print(f'ERROR: Incorrect restore date {sys.argv[1]}')
    sys.exit(2)
else:
    shapshots_dates = [el for el in get_snapshot_dates(snapshot_dir) if el <= sys.argv[1]]

pathlib.Path(restore_dir).mkdir(parents=True, exist_ok=True)

print(f'INFO: restore on date {max(shapshots_dates)}')
for date in shapshots_dates:
    tar_files_for_date = glob.glob(f'{backup_dir}{date}*.tar.gz')
    for file in tar_files_for_date:
        print(f'INFO: Unpack file {file}')
        unpack_archive(file, restore_dir)   
    del_files_for_date = glob.glob(f'{backup_dir}{date}.deleted.csv')
    for file in del_files_for_date:
        with open(file, 'r', newline=None) as f:
            reader = csv.reader(f)
            for row in reader:
                print(f'INFO: Delete file {row}')
                pathlib.Path(f'{restore_dir}{"".join(row)[1:]}').unlink()
print(f'INFO: Unpacking is finished')