"""Simple handling of backup of media files.

Creates a file with _bup ending if not already avaliable.
"""
import os
from shutil import copy2

BACKUP_FILE_SUFFIX = "_bup"


class BackupError(Exception):
    "Problem in moving file to backup location."


def make_backup(filepath):
    "Copy filepath to backuppath. Raise BackupError if not possible."
    backup_path = filepath + BACKUP_FILE_SUFFIX
    if os.path.exists(backup_path):
        raise BackupError("Backup file %s already exists" %
                          backup_path)
    try:
        copy2(filepath, backup_path)
    except IOError as err:
        raise BackupError("IOError %s" % err)
