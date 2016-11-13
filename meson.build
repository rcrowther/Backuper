project('Backuper', 'c', version : '0.0.1')


python_dep = find_program('python3')

## Can't think how to do this
#gtk_dep = dependency('python3-gi')
#gtk_dep = find_program('GLib.py')

rdiff_backup_dep = find_program('rdiff-backup')


run_target('schema-uninstall', command : 'schema-uninstall.sh')
run_target('schema-install', command : 'schema-install.sh')

run_target('desktop-install', command : 'desktop-install')
run_target('desktop-uninstall', command : 'desktop-uninstall')

