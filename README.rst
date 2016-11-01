Backuper
========
GTK script for rdiff-backup.

Made for several mirrors, but currently only capable of one.

.. figure:: https://raw.githubusercontent.com/rcrowther/Backuper/master/text/backuper.jpg
    :width: 200 px
    :alt: Backuper screenshot
    :align: center

    The commandline ain't easy, either

This interface was difficult to write, is waiting for a repository
upgrade to rdiff-backup, and incomplete. It only handles one folder
for source and backup, though it can establish new backup folders/mirrors.

Delete older savepoints must work by time, and can get confused. To fix, delete 
all savepoints and start again. Or establish a new backup.


Requires
~~~~~~~~
Python3, GTK environment, 'rdiff-backup', and some setup. Instructions included.

