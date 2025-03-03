#!/bin/env python3

# A script for creating an incremental archive for the current date.

import os
import os.path
import pathlib
from datetime import datetime
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
        subprocess.run(mount_command,
                       stdin=subprocess.PIPE,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE,
                       check=True)
        logger.info('Mount success.')
    except KeyboardInterrupt:
        logger.warning('KeyboardInterrupt.')
        sys.exit(2)
    except subprocess.CalledProcessError as err:
        logger.error(f'Error mount {mount_point}')
        logger.error(err.__str__())
        sys.exit(2)


def get_filenames(files):
    """
    Get a list of file names from a list of file attributes.

    Parameters
    ----------
    files : list
        A list of file attributes, e.g. [[/path/to/file1, mtime1], [/path/to/file2, mtime2]]

    Returns
    -------
    list
        A list of file names, e.g. [/path/to/file1, /path/to/file2]
    """
    res = [el[0] for el in files]
    return res


def error_handler(error):
    """
    Log an error and exit the program.

    Parameters
    ----------
    error : os.error
        An error from os.walk
    """
    logger.error(error)
    sys.exit(2)


def get_files_from_source(source_path):
    
    """
    Walk through a source directory and return a list of file attributes.

    Parameters
    ----------
    source_path : str
        A path to the source directory

    Returns
    -------
    list
        A list of file attributes, e.g. [[/path/to/file1, mtime1], [/path/to/file2, mtime2]]

    Notes
    -----
    The function uses os.walk with followlinks=False and onerror=error_handler.
    If an error occurs during the walk, the function logs the error and exits the program.
    """
    try:
        res = []
        for dir, _, files in os.walk(source_path,
                                     followlinks=False,
                                     onerror=error_handler):
            for file in files:
                full_path = os.path.join(dir, file)
                mtime = float(pathlib.Path(full_path).stat().st_mtime)
                res.append([full_path, mtime])
        return res
    except Exception as err:
        logger.error(f'Unexpected error {err}')
        sys.exit(2)


def create_archive(files_in_source, backup_file):
    """
    Create an archive with the given files.

    Parameters
    ----------
    files_in_source : list
        A list of file paths to add to the archive
    backup_file : str
        The path to the archive file to create

    Notes
    -----
    The function uses tarfile.open with 'w:gz' mode and calls add() for each file
    in the list.
    """
    with tarfile.open(backup_file, 'w:gz') as f:
        for row in files_in_source:
            f.add(row)


def save_snapshot(files, snapshot_file):
    """
    Save a snapshot of the current state of the source directory to a file.

    Parameters
    ----------
    files : list
        A list of file paths and their attributes, e.g. [[/path/to/file1, mtime1], [/path/to/file2, mtime2]]
    snapshot_file : str
        The path to the file to save the snapshot

    Notes
    -----
    The function uses csv.writer with delimiter=',' and quoting=csv.QUOTE_NONNUMERIC.
    """
    with open(snapshot_file, 'w', newline='') as f:
        writer = csv.writer(f, delimiter=',', quoting=csv.QUOTE_NONNUMERIC)
        for row in files:
            writer.writerow(row)


def get_file_attrs_from_last_shapshot(snapshot_dir):
    """
    Get the file attributes from the last snapshot file in snapshot_dir.
    
    Parameters
    ----------
    snapshot_dir : str
        The directory containing the snapshot files
    
    Returns
    -------
    list
        A list of file attributes, e.g. [[/path/to/file1, mtime1], [/path/to/file2, mtime2]]
    """
    snapshot_files = glob.glob(f'{snapshot_dir}*snapshot.csv')
    prev_snapshot_file = f'{os.path.dirname(snapshot_dir)}/{max([os.path.basename(path) for path in snapshot_files])}'
    with open(prev_snapshot_file, 'r') as f:
        reader = csv.reader(f, delimiter=',', quoting=csv.QUOTE_NONNUMERIC)
        res = [row for row in reader]
    return res


def list_to_dict(lst):
    """
    Convert a list of lists into a dictionary where each key is the first element
    of a list and the value is a list containing the second element of the list.

    Parameters
    ----------
    lst : list
        A list of lists containing two elements, e.g. [[/path/to/file1, mtime1], [/path/to/file2, mtime2]]

    Returns
    -------
    dict
        A dictionary with file names as keys and a list of one element (the mtime) as the value, e.g. {/path/to/file1: [mtime1], /path/to/file2: [mtime2]}
    """
    return {el[0]: [el[1]] for el in lst}

mount_point = '/mnt/store/'
source_path = '/media/antonchev/USB/'
backup_dir = f'{mount_point}Backup//'
snapshot_dir = f'{backup_dir}snapshots/'
log_file = 'backup.log'
today = datetime.strftime(datetime.today(), '%Y-%m-%d')
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

# Creating a directory to host the archive, if it did not exist.
pathlib.Path(backup_dir).mkdir(parents=True, exist_ok=True)

snapshot_file = f'{snapshot_dir}{today}.snapshot.csv'

# Checking if the archive for the current date has already been created
if os.path.exists(snapshot_file):
    logger.warning(f'Archive for the {today} has already been created, skip.')
    sys.exit(3)

# Get the list of the files in source directory, e.g. [[/path/to/file1, mtime1], [/path/to/file2, mtime2]]
files_in_source = get_files_from_source(source_path)
# Get list of file names in source directory, e.g. [/path/to/file1, /path/to/file2]
filenames_in_source = get_filenames(files_in_source)

# If the base archive was not created, create it
if not glob.glob(f'{backup_dir}*base*.tar.gz'):
    backup_file = f'{backup_dir}{today}.base.tar.gz'
    logger.info(f'Create full archive {backup_file}.')
    create_archive(filenames_in_source, backup_file)
    # create snapshot
    logger.info(f'Create to-date snapshot {snapshot_file}.')
    save_snapshot(files_in_source, snapshot_file)
else:
    # Get the list of the files in the last snapshot, e.g. [[/path/to/file1, mtime1], [/path/to/file2, mtime2]]
    files_in_last_shapshot = get_file_attrs_from_last_shapshot(snapshot_dir)
    # Get list of file names in in the last snapshot, e.g. [/path/to/file1, /path/to/file2]
    filenames_in_last_snapshot = get_filenames(files_in_last_shapshot)

    # Compare the files in the latest snapshot and the files in the source directory on:

    # 1. Deleted files are found as the difference between the set of file names
    # in the last snapshot and the set of file names in the directory to be archived
    deleted_files = set(filenames_in_last_snapshot).difference(
        set(filenames_in_source))
    
    # If there are deleted files, then create a snapshot of them
    if deleted_files:
        deleted_files = [[el] for el in deleted_files]
        snapshot_file = f'{backup_dir}{today}.deleted.csv'
        logger.info(f'Exists deleted files: create snapshot {pathlib.Path(snapshot_file).name}.')
        save_snapshot(deleted_files, snapshot_file)

    # 2. Added files are found as the difference between the set of file names
    # in the directory to be archived and the set of file names in the last snapshot
    added_files = set(filenames_in_source).difference(
        set(filenames_in_last_snapshot))
    
    # If there are added files, then create a archive of them
    if added_files:
        backup_file = f'{backup_dir}{today}.added.tar.gz'
        logger.info(
            f'Exists added files: create archive {pathlib.Path(backup_file).name}.')
        create_archive(added_files, backup_file)

    # 3. Modified files
    # First, we find common files as intersection of the snapshot and source
    modified_files = set(filenames_in_source).intersection(
        filenames_in_last_snapshot)

    # Then we get dictionaries for snapshot and source, e.g. {/path/to/file1: [mtime1], /path/to/file2: [mtime2]}
    files_in_source_dict = list_to_dict(files_in_source)
    files_in_last_shapshot_dict = list_to_dict(files_in_last_shapshot)
    
    # For each common file compare the value 'mtime' in the snapshot and source,
    # if the values ​​do not match, then add the file name to the list of modified files
    modified_files = [
        file for file in modified_files if files_in_source_dict[file][0] !=
        files_in_last_shapshot_dict[file][0]
    ]
    # If there are modified files, then create a archive of them
    if modified_files:
        backup_file = f'{backup_dir}{today}.modified.tar.gz'
        logger.info(f'Exists modified files: create archive {pathlib.Path(backup_file).name}.')
        create_archive(modified_files, backup_file)

    # Create a snapshot of source for the current date
    snapshot_file = f'{snapshot_dir}{today}.snapshot.csv'
    logger.info(f'Create to-date snapshot {pathlib.Path(snapshot_file).name}.')
    save_snapshot(files_in_source, snapshot_file)
