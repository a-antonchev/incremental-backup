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
import logging


def mount_dir(mount_command):
    try:
        subprocess.run(
            mount_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        logger.info('Mount success.')
    except KeyboardInterrupt:
        logger.warning('KeyboardInterrupt.')
    except subprocess.CalledProcessError as err:
        logger.error(f'Error mount {mount_point}')
        logger.error(err.__str__())
        sys.exit(2)


def get_snapshot_dates(snapshot_dir):
    return sorted([el.split('.')[0] for el in os.listdir(snapshot_dir)])


def unpack_archive(backup_file, restore_dir):
    with tarfile.open(backup_file, 'r:gz') as f:
        f.extractall(restore_dir)

mount_point = '/mnt/store/'
backup_dir = f'{mount_point}Backup/test/'
restore_dir = '/media/antonchev/USB-накопитель/test_restore/'
log_file = 'backup.log'
snapshot_dir = f'{backup_dir}snapshots/'
mount_command = ['sudo', 'mount', '-U', '01DB2557286B1350',
                 mount_point, '-o', 'uid=1000,gid=1000']

formatter = logging.Formatter(fmt='%(asctime)s: %(name)s: %(levelname)s - %(message)s',
                              datefmt='%Y-%m-%d %H:%M:%S')

console = logging.StreamHandler()
console.setFormatter(formatter)

file = logging.FileHandler(filename=log_file, mode='a')
file.setFormatter(formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(console)
logger.addHandler(file)

if not os.path.ismount(mount_point):
    logger.info('Mount point not exists, mounting.')
    mount_dir(mount_command)    

if len(sys.argv) == 1:
    shapshots_dates = get_snapshot_dates(snapshot_dir)
elif sys.argv[1] not in get_snapshot_dates(snapshot_dir):
    logger.error(f'Incorrect restore date {sys.argv[1]}.')
    sys.exit(2)
else:
    shapshots_dates = [el for el in get_snapshot_dates(
        snapshot_dir) if el <= sys.argv[1]]

pathlib.Path(restore_dir).mkdir(parents=True, exist_ok=True)

logger.info(f'Restore on date {max(shapshots_dates)}.')
for date in shapshots_dates:
    tar_files_for_date = glob.glob(f'{backup_dir}{date}*.tar.gz')
    for file in tar_files_for_date:
        logger.info(f'Unpack file {file}.')
        unpack_archive(file, restore_dir)
    del_files_for_date = glob.glob(f'{backup_dir}{date}.deleted.csv')
    for file in del_files_for_date:
        with open(file, 'r', newline=None) as f:
            reader = csv.reader(f)
            for row in reader:
                logger.info(f'Delete file {row}.')
                pathlib.Path(f'{restore_dir}{"".join(row)[1:]}').unlink()
logger.info(f'Restore is finished.')
