#!/bin/env python3

# Каталог для записи архива располагался на диске, который не монтировался автоматически при запуске системы

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
    res = [el[0] for el in files]
    return res


def error_handler(error):
    logger.error(error)
    sys.exit(2)


def get_files_from_source(source_path):
    # не заходим в каталоги, которые являются символическими ссылками;
    # файлы-символические ссылки записываем в архив (при желании это можно изменить, добавив проверку на символическую ссылку)
    # из атрибутов файла контролируем только mtime (возможно добавить запись и других атрибутов, дополнительно нужно изменить логику проверки на изменение атрибутов)
    # используем os.walk(), так как версия виртуального окружения Python=3.10.16 (не включает pathlib.Path.walk())
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
    with tarfile.open(backup_file, 'w:gz') as f:
        for row in files_in_source:
            f.add(row)


def save_snapshot(files, snapshot_file):
    with open(snapshot_file, 'w', newline='') as f:
        writer = csv.writer(f, delimiter=',', quoting=csv.QUOTE_NONNUMERIC)
        # writer = csv.writer(f)
        for row in files:
            writer.writerow(row)


def get_file_attrs_from_last_shapshot(snapshot_dir):
    snapshot_files = glob.glob(f'{snapshot_dir}*snapshot.csv')
    prev_snapshot_file = f'{os.path.dirname(snapshot_dir)}/{max([os.path.basename(path) for path in snapshot_files])}'
    with open(prev_snapshot_file, 'r') as f:
        reader = csv.reader(f, delimiter=',', quoting=csv.QUOTE_NONNUMERIC)
        res = [row for row in reader]
    return res


def list_to_dict(lst):
    return {el[0]: [el[1]] for el in lst}

mount_point = '/mnt/store/'
source_path = '/media/antonchev/USB/'
backup_dir = f'{mount_point}Backup//'
snapshot_dir = f'{backup_dir}snapshots/'
log_file = 'backup.log'
today = datetime.strftime(datetime.today(), '%Y-%m-%d')
# today = '2025-02-26'
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
    logger.info('INFO: Mount point not exists, mounting.')
    mount_dir(mount_command)

pathlib.Path(backup_dir).mkdir(parents=True, exist_ok=True)
snapshot_file = f'{snapshot_dir}{today}.snapshot.csv'

if os.path.exists(snapshot_file):
    logger.warning(f'Archive for the {today} has already been created, skip.')
    sys.exit(3)

files_in_source = get_files_from_source(source_path)
filenames_in_source = get_filenames(files_in_source)

if not glob.glob(f'{backup_dir}*base*.tar.gz'):
    backup_file = f'{backup_dir}{today}.base.tar.gz'
    logger.info(f'Create full archive {backup_file}.')
    create_archive(filenames_in_source, backup_file) # create full (base) archive
    logger.info(f'Create to-date snapshot {snapshot_file}.')
    save_snapshot(files_in_source, snapshot_file)
else:
    # провести сравнение файлов в последнем снапшотt и файлов в исходной директории на

    # 1. удаленные файлы
    files_in_last_shapshot = get_file_attrs_from_last_shapshot(snapshot_dir)
    filenames_in_last_snapshot = get_filenames(files_in_last_shapshot)
    deleted_files = set(filenames_in_last_snapshot).difference(
        set(filenames_in_source))
    if deleted_files:
        deleted_files = [[el] for el in deleted_files]
        snapshot_file = f'{backup_dir}{today}.deleted.csv'
        logger.info(f'Exists deleted files: create snapshot {pathlib.Path(snapshot_file).name}.')
        save_snapshot(deleted_files, snapshot_file)

    # 2. добавленные файлы
    added_files = set(filenames_in_source).difference(
        set(filenames_in_last_snapshot))
    if added_files:
        backup_file = f'{backup_dir}{today}.added.tar.gz'
        logger.info(
            f'Exists added files: create archive {pathlib.Path(backup_file).name}.')
        create_archive(added_files, backup_file)

    # 3. модифицированные
    modified_files = set(filenames_in_source).intersection(
        filenames_in_last_snapshot)
    files_in_source_dict = list_to_dict(files_in_source)
    files_in_last_shapshot_dict = list_to_dict(files_in_last_shapshot)
    # при записи других атрибутов файла, кроме mtime, требуется изменить логику проверки изменения атрибутов здесь:
    modified_files = [
        file for file in modified_files if files_in_source_dict[file][0] !=
        files_in_last_shapshot_dict[file][0]
    ]
    if modified_files:
        backup_file = f'{backup_dir}{today}.modified.tar.gz'
        logger.info(f'Exists modified files: create archive {pathlib.Path(backup_file).name}.')
        create_archive(modified_files, backup_file)

    snapshot_file = f'{snapshot_dir}{today}.snapshot.csv'
    logger.info(f'Create to-date snapshot {pathlib.Path(snapshot_file).name}.')
    save_snapshot(files_in_source, snapshot_file)
