#!/bin/env python3

# A script for restore files to a specified date.
# Usage: python3 restore.py <date>

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
    """
    Execute a mount command in a subprocess, log the result and exit the program on error.

    Parameters
    ----------
    mount_command : list
        A list of strings representing a mount command, e.g. ['sudo', 'mount', '-U', '01DB2557286B1350', '/mnt/store/']
    """
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
    """
    Get a list of snapshot dates from a snapshot directory.

    Parameters
    ----------
    snapshot_dir : str
        A path to a directory containing snapshot files

    Returns
    -------
    list
        A sorted list of snapshot dates, e.g. ['2022-01-01', '2022-01-02']
    """
    return sorted([el.split('.')[0] for el in os.listdir(snapshot_dir)])


def unpack_archive(backup_file, restore_dir):
    """
    Unpack a tar.gz archive to a directory.

    Parameters
    ----------
    backup_file : str
        A path to a tar.gz archive
    restore_dir : str
        A path to a directory to unpack the archive to
    """
    with tarfile.open(backup_file, 'r:gz') as f:
        f.extractall(restore_dir)

mount_point = '/mnt/store/'
backup_dir = f'{mount_point}Backup/test/'
restore_dir = '/media/antonchev/USB-накопитель/test_restore/'
log_file = 'backup.log'
snapshot_dir = f'{backup_dir}snapshots/'
mount_command = ['sudo', 'mount', '-U', '01DB2557286B1350',
                 mount_point, '-o', 'uid=1000,gid=1000']

# Setting the logging parameters, we are writing to the console and to a file
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

# Mounting the disk on which the archive is located
if not os.path.ismount(mount_point):
    logger.info('Mount point not exists, mounting.')
    mount_dir(mount_command)

# Creating a list of snapshots that we will use during recovery.
if len(sys.argv) == 1: # no recovery date has been set
    # Use all snapshots
    shapshots_dates = get_snapshot_dates(snapshot_dir)
elif sys.argv[1] not in get_snapshot_dates(snapshot_dir):
    # The user specified a date that is not in the snapshots list
    logger.error(f'Incorrect restore date {sys.argv[1]}.')
    sys.exit(2)
else:
    # Take all the snapshots starting from the first date and up to the date set by the user
    shapshots_dates = [el for el in get_snapshot_dates(
        snapshot_dir) if el <= sys.argv[1]]

# Create a directory to restore the archive
pathlib.Path(restore_dir).mkdir(parents=True, exist_ok=True)

logger.info(f'Restore on date {max(shapshots_dates)}.')
for date in shapshots_dates: # for each date from snapshots list
    # Use the mask to find tar archives
    tar_files_for_date = glob.glob(f'{backup_dir}{date}*.tar.gz')
    # Unpack the archives
    for file in tar_files_for_date:
        logger.info(f'Unpack file {file}.')
        unpack_archive(file, restore_dir)
    # Use the mask to find snapshot of deleted files
    del_files_for_date = glob.glob(f'{backup_dir}{date}.deleted.csv')
    # Delete files from the unpacked files
    for file in del_files_for_date:
        with open(file, 'r', newline=None) as f:
            reader = csv.reader(f)
            for row in reader:
                logger.info(f'Delete file {row}.')
                pathlib.Path(f'{restore_dir}{"".join(row)[1:]}').unlink()
logger.info(f'Restore is finished.')
