## Scripts for creating an incremental archive for the current date and restoring it to a specified date

### backup.py
Creating an incremental archive for the current date.
A "snapshot" of the files and their attributes is created. When creating an archive, the current
file parameters in the source directory are compared with the parameters that are recorded in the "snapshot".
A separate "snapshot" is created for deleted files, which deletes files during recovery,
and separate archives are created for newly added and modified files.
For modified files, only the mtime parameter is controlled, and it is possible to add control for other attributes.
(see the get_files_from_source function, additionally you need to change the logic of checking for attribute changes).

### restore.py
Restore files to a specified date.
Sequential file recovery by going through the archives, starting from the earliest and ending
with the archive on the date set by the user.
The base copy is restored first, for each subsequent archive, the files that
were deleted in the source directory are deleted, new files are added and the modified ones are overwritten.

Only standard libraries are used for the python script, but just in case, the files are posted:

requirements.txt (to create an environment on pip)
requirements.yml (for conda)

