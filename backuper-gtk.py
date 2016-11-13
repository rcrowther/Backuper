#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import subprocess
from time import sleep
from gi.repository import Gio, GLib

from datetime import datetime, date, time
import os.path
import shutil
import sys



'''
GTK script for rdiff-backup.

Made for several mirrors, but currently only manages one.

Useful: rdiff-backup is not like Windows rollback. It establishes and
maintains a complete and current mirror of the selected source. It also
maintains backwards diffs ('increments'). On history recovery, the
current files are updated to one of these historic diffs, not 
'rollbacked'. This has a nice advantage of maintaining the history, so
updates from history can be tried without destroying the history itself.
The histrical updates can even be abandoned. However, you can get into
a muddle quickly, as updates from the past are brought forward without
indication or barrier.
 
This interface was difficult to write, is waiting for a repository
upgrade to rdiff-backup, and is incomplete. It only handles one folder
for source and backup, though it can establish new backup folders.

Delete older savepoints must work by time, and can get confused. Delete 
all savepoints and start again. Or establish a new backup.
'''
#rdiff-backup /home/rob/Desktop/IPbackup /home/rob/Desktop/backup

#rdiff-backup -r now --force  /home/rob/Desktop/backup /home/rob/Desktop/IPbackup
#-3D = 3 Days
#s,  m,  h,  D,  W,  M, or Y 
#2002-3-05
#--remove-older-than

#--exclude-filelist
#--exclude pattern

#success#

## TODO
# protext against shared filepaths
# Really needs the custom column renderer
# Make mirror path to labels, add file browsers?
# zero increments, hide load button
# recover from increment not matching settings error by listing increments existing
# detect settings from existing mirror (tough)
# does 'sort' sort the model?
# needs Filecooser for 'sourcePath'
# activate 'enter' on savepoint name
# 
#2001-07-15T04:09:38-07:00

GSCHEMA = "uk.co.archaicgroves.backuper-gtk"
GROUP_DATA_KEY = 'data'
# a(backupName, src, bck, last_index a(index, date, time, pointName, restoreFrom))
GROUP_SIGNATURE = "a(sssa(isssi))"

# Used by _getPaths()
SOURCE_PATH = 0
BACKUP_PATH = 1

NO_SAVEPOINT_LOADED = -1



def _rdiffBackupIsCurrent(sourceRoute, backupRoute):
    cmd = ['rdiff-backup', '--compare', sourceRoute, backupRoute]
    return subprocess.call(cmd) == 0

def _rdiffBackupListSavepoints(backupRoute):
    '''@return list of tuples date, time ('2016/10/16', '13:18'). If None
    The file is not recognised as rdiff-backup directory.
    '''
    cmd = ['rdiff-backup', '--list-increments', backupRoute]
    ret = ''
    try:
        ret = subprocess.check_output(cmd)
    except Exception as e:
        sys.stderr.write('Exception: {0}'.format(str(e)))
        return None
    # decode
    o = ret.decode("utf-8") 
    print('o:' + o)
    # split
    o = o.split()
    # unpack
    b = []
    for x in o:
        if x.startswith('increments.'):
            b.append((x[11:20].replace('-', '/'), x[22:27]))
    return b
    
    
def _rdiffLoadSavepoint(idxToEnd, backupRoute, sourceRoute):
    success = False
    #rdiff-backup  --force -r XB /home/rob/Desktop/backup /home/rob/Desktop/IPbackup
    cmd = ['rdiff-backup', "--force", '-r', str(idxToEnd) + "B", backupRoute, sourceRoute]
    print("cmd: " + " ".join(cmd))
    try:
        subprocess.call(cmd)
        success = True
    except Exception as e:
        sys.stderr.write('Exception: {0}'.format(str(e)))
        return False
                         
    return success
    
def _rdiffResetToMirror(backupRoute, sourceRoute):
    return _rdiffLoadSavepoint(0, backupRoute, sourceRoute)
 
#def _rdiffBackupRollback(idxToEnd, backupRoute, sourceRoute):
    #success = False
    ##rdiff-backup  --force -r XB /home/rob/Desktop/backup /home/rob/Desktop/IPbackup
    #cmd = ['rdiff-backup', "--force", '-r', str(idxToEnd) + "B", backupRoute, sourceRoute]
    #print("cmd: " + " ".join(cmd))
    #try:
        #subprocess.call(cmd)
        #success = True
    #except Exception as e:
        #sys.stderr.write('Exception: {0}'.format(str(e)))
        #return False
                         
    #return success
    
def _rdiffBackupCreateSavePoint(sourceRoute, backupRoute):
    success = False
    #rdiff-backup /home/rob/Desktop/IPbackup /home/rob/Desktop/backup 
    cmd = ['rdiff-backup', sourceRoute, backupRoute]
    print("cmd: " + " ".join(cmd))
    try:
        subprocess.call(cmd)
        success = True
    except Exception as e:
        sys.stderr.write('Exception: {0}'.format(str(e)))
        return False
                         
    return success

def _rdiffBackupDeleteUntil(w3Date, backupRoute):
    success = False
    #rdiff-backup  --remove-older-than XB /home/rob/Desktop/IPbackup /home/rob/Desktop/backup 
    # This only with rdiff-backup version  0.13
    #cmd = ['rdiff-backup', '--remove-older-than', str(idxToEnd) + "B", backupRoute]
    cmd = ['rdiff-backup', '--force', '--remove-older-than', w3Date, backupRoute]
    print("cmd: " + " ".join(cmd))
    try:
        subprocess.call(cmd)
        success = True
    except Exception as e:
        sys.stderr.write('Exception: {0}'.format(str(e)))
        return False
                         
    return success
    

        
class MyWindow(Gtk.Window):
    ## mirror file chooser
   
    class MirrorFolderChooserWindow(Gtk.Window):
    
        def __init__(self):
            Gtk.Window.__init__(self, title="Select mirror path")
    
            box = Gtk.Box(spacing=6)
            self.add(box)
    
    
            button2 = Gtk.Button("Choose Path")
            button2.connect("clicked", self.on_folder_clicked)
            box.add(button2)
    
        def on_folder_clicked(self, widget):
            dialog = Gtk.FileChooserDialog("Please choose a folder", self,
                Gtk.FileChooserAction.SELECT_FOLDER,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                 "Select", Gtk.ResponseType.OK))
            dialog.set_default_size(800, 400)
    
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                print("Select clicked")
                print("Folder selected: " + dialog.get_filename())
            elif response == Gtk.ResponseType.CANCEL:
                print("Cancel clicked")
    
            dialog.destroy()
        
    
    
    ## GUI mods/accessors
    
    def message(self, message):
        self.statusbar.set_text(message)

    def request(self, message):
        msg = '[<span foreground="blue">request</span>] ' + message 
        self.statusbar.set_markup(msg)
        
    def warning(self, message):
        msg = '[<span foreground="orange">warning</span>] ' + message 
        self.statusbar.set_markup(msg)
        
    def error(self, message):
        msg = '[<span foreground="red">error</span>] <span foreground="red">' + message + '</span>'
        self.statusbar.set_markup(msg)

    def clearStatus(self):
        self.statusbar.set_text('')

        
    def warningDialog(self, msg):
        dialog = Gtk.MessageDialog(
            self, 
            0, 
            Gtk.MessageType.WARNING,
            Gtk.ButtonsType.OK,
            msg
            )
            
        dialog.run()
        dialog.destroy()

    def showNewSavepointButton(self):
        self.backupNameLabel.set_text("Savepoint name:")
        self.backupName.set_text("Savepoint")
        self.button5.hide()
        self.button2.show()
        
    def showNewMirrorButton(self):
        self.backupNameLabel.set_text("New mirror name:")
        self.backupName.set_text("")
        self.button2.hide()
        self.button5.show()
        #self.show()
        
    def hideResetToMirrorButton(self):
        self.button6.hide()
            
    def showResetToMirrorButton(self):
        self.button6.show()
        
    def _guiClear(self):
        '''Used when there are no settings to work from, 
        or a new backup path is established'''
        # Clear the name
        self.backups.remove_all()
        
        # clear savepoints
        self.savePoints.clear()

        #set buttons
        self.showNewMirrorButton()
        self.hideResetToMirrorButton()
        
        # reset state
        self._savePointCount = 0
        self._savePointLoaded = NO_SAVEPOINT_LOADED

        
        
    def _getPaths(self):
        sourceRoute = self.sourcePath.get_text().strip()
        backupRoute = self.backupPath.get_text().strip()
        if sourceRoute and backupRoute:
            return (sourceRoute, backupRoute)
        else:
            return None
            
    def _pathsInfoStr(self):
        sourceRoute = self.sourcePath.get_text().strip()
        backupRoute = self.backupPath.get_text().strip()
        return "sourcePath: {0}\nbackupPath: {1}".format(sourceRoute, backupRoute)
        
        
        
    ## Stdout debug info
    
    def _printSavepoints(self, savepoints):
            print ("    savepoints:")
            for e in savepoints:
                print("    {0}:{1}:{2}".format(e[0], e[1], e[2]))
                
    def _printGroups(self, gsettingBackups):
        # a(backupName, src, bck, last index a(index, date, pointName))
        for group in gsettingBackups:
            print("Name:{0}\n    source path:{1}\n    backup path:{2}".format(group[0], group[1], group[2]))
            self._printSavepoints(group[3])
                

    def _timeToString(self, ft):
        if (ft):
            return ft.strftime("%Y/%m/%d#%H:%M")
        else:
            return 'Nothing verified'
#                    failTimeStr = self._timeToString(datetime.now())


    def _toW3Date(self, itr, forward):
        '''2002-04-26T04:22:01+07:00
        forward lets us add a minute, if calculating to delete backwards.
        '''
        if (not itr):
            #return '9999-12-31T23:59:59+00:00'
            return datetime.now().strftime("%Y-%m-%dT%H:%M:59")
        else:
            date = self.savePoints[itr][1].replace('/', '-')
            time = self.savePoints[itr][2]
            seconds = 0
            if (forward):
                seconds = '59'
            else:
                seconds = '00'
            tz = datetime.now().strftime("%z")
            if not tz:
                tz = '+00:00'
            return "{0}T{1}:{2}{3}".format(date, time, seconds, tz)
        
        
    def _currentTimeAsString(self):
        t = datetime.now()
        return t.strftime("%Y/%m/%d"), t.strftime("%H:%M")



    ## liststore helpers

    def _selectedIter(self):
        '''@return iter or None'''
        select = self.listView.get_selection()
        # (selData is tuple (model, iter))
        selData = select.get_selected()
        #if selData == None
        return selData[1]
    
    def _index(self, it):
        i = 0
        itr = self.savePoints.iter_previous(it)
        while itr != None:
            itr = self.savePoints.iter_previous(itr)
            i += 1
        return i
        
    def _indexToEndOf(self, it):
        i = 0
        itr = self.savePoints.iter_next(it)
        while itr != None:
            itr = self.savePoints.iter_next(itr)
            i += 1
        return i
        
    def _savepointLength(self):
        i = 0
        itr = self.savePoints.get_iter_first()
        while itr != None:
            itr = self.savePoints.iter_next(itr)
            i += 1
        return i
        
    def iterLast(self):
        itr = self.savePoints.get_iter_first()
        prev = itr
        while itr != None:
            prev = itr
            itr = self.savePoints.iter_next(itr)
        return prev
        
    def _settingsFromPopulation(self):
        bName = self.backups.get_active_text()
        backupName = bName if (bName) else 'default'
        srcPath = self.sourcePath.get_text()
        bckPath = self.backupPath.get_text()
        # (manual. Comprehensions and the like generate views, not the object)
        savepointData = []
        for sp in self.savePoints:
            # (index, date, time, pointName, restoreFrom)
            savepointData.append((sp[0], sp[1], sp[2], sp[3], int(sp[4])))
            
        data = [(backupName, srcPath, bckPath, savepointData)]
        #self._printSavepoints(rollbackData)
        
        # a(backupName, src, bck, last index a(index, date, time, pointName))
        gsettingBackups = GLib.Variant(GROUP_SIGNATURE, data)
        gsettings.set_value(GROUP_DATA_KEY, gsettingBackups)



    def _populateFromSettings(self):
        gsettingBackups = gsettings.get_value(GROUP_DATA_KEY)

        self._printGroups(gsettingBackups)

        # populate settings
        # a(backupName, src, bck, last index a(index, date, time, pointName))
        if (len(gsettingBackups) == 0):
            self._guiClear()
            self.message('no settings found')
        else:
            # Currently preset to load the first backup project
            #for group in gsettingRet:
            group = gsettingBackups[0]
            
            backupName = group[0]
            sourcePath = group[1]
            backupPath = group[2]
            savePoints = group[3]

            # Set the backup title
            idStr = str(0)
            self.backups.append(idStr, backupName)
            self.backups.set_active_id(idStr)
            
            #populate the settings page
            self.sourcePath.set_text(sourcePath)
            self.backupPath.set_text(backupPath)
            
            diffs = _rdiffBackupListSavepoints(backupPath)

            if diffs == None:
                # Not an rdiff-backup file.
                #establish the mirror again/new?
                self.showNewMirrorButton()
                self.hideResetToMirrorButton()
                self._savePointCount = 0
                self.warning("Backup path does not exist?")
            else:
                # GUI reset
                # show savepoint buttons, hide resetToMirrorButton
                #print("diffs:" + len(diffs))
                self.showNewSavepointButton()
                self.hideResetToMirrorButton()

                # load the savepoints from settings
                settingsLen = len(savePoints)
                backupsLen = len(diffs)
                if settingsLen != backupsLen:
                    # load no savepoints
                    # TODO Do more? approximate existing savepoints?
                    self._savePointCount = 0
                    self.warningDialog("Number of backup savepoints does not match number of setting savepoints\nbackup savepoint count: {0}\nsettings savepoint count: {1}".format(backupsLen, settingsLen))
                else:
                    self._savePointCount = settingsLen
        
                    # populate the savepoints
                    for e in savePoints:
                        # (index, date, time, pointName, restoredFrom)
                        self.savePoints.append((e[0], e[1], e[2], e[3], str(e[4])))
        
        

    ## Actions

    def _notebookSwitched(self, notebook, page, pageNum):
        # clear status
        self.clearStatus()
        
        
    def _newMirror(self, widget):
        #print("toDO")
        self.clearStatus()
        paths = self._getPaths()
        
        if paths is None:
            self.warning("Attempted to create mirror. but paths failed\n" + self._pathsInfoStr())
        else:
            newMirrorName = self.backupName.get_text().strip()
            if(not newMirrorName):
                self.request("Please supply a mirror name")
            else:
                dateStr, timeStr = self._currentTimeAsString()
                success = _rdiffBackupCreateSavePoint(paths[0], paths[1])

                #success = True
                if(success):
                    # ensure index as zero
                    self._savePointCount = 0
                
                    # mirrorname into now operative group title
                    # tmp, empty the list, until sorted out
                    self.backups.remove_all()
                    idStr = str(0)
                    self.backups.append(idStr, newMirrorName)
                    self.backups.set_active_id(idStr)
                    
                    # refresh display
                    self.savePoints.clear()
                        
                    # backup gsettings
                    self._settingsFromPopulation()
                    
                    # Move to savepoints
                    self.showNewSavepointButton()
                    
                    self.message('New mirror: {0}'.format(newMirrorName))
                else:
                    self.error('rdiff-backup failed?')
    
    
    def _newSavepoint(self, widget):
        paths = self._getPaths()
        
        if paths is None:
            self.warning("Attempted to create savepoint. but paths failed\n" + self._pathsInfoStr())
        else:
            # do we need to?
            isCurrent = _rdiffBackupIsCurrent(paths[SOURCE_PATH], paths[BACKUP_PATH])
    
            if isCurrent:
                self.message("Backups up to date")
            else:
                backupName = self.backupName.get_text().strip()
                if(not backupName):
                    self.request("Please supply a name")
                else:
                    dateStr, timeStr = self._currentTimeAsString()
                    #timeStr = self._timeToString(datetime.now())
    
                    success = _rdiffBackupCreateSavePoint(paths[SOURCE_PATH], paths[BACKUP_PATH])
                    #success = True
                    if(success):
                        # reset GUI
                        self.hideResetToMirrorButton()
    

                    
                        # refresh display
                        # (index, date, time, pointName, restoreFrom)
                        self.savePoints.append([
                            self._savePointCount,
                            dateStr,
                            timeStr,
                            backupName,
                            str(self._savePointLoaded)
                            ])
                            
                        # INC the count
                        self._savePointCount = self._savePointCount + 1
                        
                        # backup gsettings
                        self._settingsFromPopulation()
                        self.message('done')
                    else:
                        self.error('rdiff-backup failed?')

            
    def _deleteUntilSavepoint(self, widget):
        self.clearStatus()
        backupRoute = self.backupPath.get_text()

        it = self._selectedIter()
        if (not it):
            self.request("Please select a savepoint")
        else:
            # (don't bother with lastkey? Increment not an issue?)
            # refresh display
            #self.savePoints.remove(it)
            idx = self._index(it)
            print ("idx:" + str(idx))
            idxToEnd = self._indexToEndOf(it)
            print ("idxToEnd:" + str(idxToEnd))
            w3Date = self._toW3Date(it, False)
            print ("date:" + w3Date)

            success = _rdiffBackupDeleteUntil(w3Date, backupRoute)
            success = True
            if(success):
                # Remove previous rows
                # This appears to be the way to do that?
                i = idx
                itr = self.savePoints.get_iter_first()
                while i > 0:
                    self.savePoints.remove(itr)
                    i -= 1
                    
                # reset the index points
                i = 0
                while (itr):
                    self.savePoints[itr][0] = i
                    itr = self.savePoints.iter_next(itr)
                    i += 1
                    
                self._savePointCount = i
 
                # backup gsettings
                self._settingsFromPopulation()
                self.message('done')
            else:
                self.error('rdiff-backup failed?')


    def _deleteAllSavepoints(self, widget):
        self.clearStatus()
        backupRoute = self.backupPath.get_text()

        listLen = self._savepointLength()

        # (don't bother with lastkey? Could be updated to 0 here?)
        # refresh display
        it = self.iterLast()
        w3Date = self._toW3Date(it, False)
        success = _rdiffBackupDeleteUntil(w3Date, backupRoute)

        if(success):
            # Remove rows
            self.savePoints.clear()
            
            # reset lastkey
            self._savePointCount = 0

            # backup gsettings
            self._settingsFromPopulation()
            self.message('savepoints deleted')
        else:
            self.error('rdiff-backup failed?')
    
    
    def _resetToMirror(self, widget):
        self.clearStatus()

        if (self._savePointLoaded == NO_SAVEPOINT_LOADED):
            self.message("No loaded savepoint to reset")
        else:
            paths = self._getPaths()
        
            if paths is None:
                self.warning("Attempted to load mirror. but paths failed\n" + self._pathsInfoStr())
            else:
                success = _rdiffResetToMirror(paths[BACKUP_PATH], paths[SOURCE_PATH])

                #success = True
                if(success):
                    self._savePointLoaded = NO_SAVEPOINT_LOADED
                    self.hideResetToMirrorButton()
                    self.message('reset to mirror')
                else:
                    self.error('rdiff-backup failed?')
                    
                    
    def _loadSavepoint(self, widget):
        self.clearStatus()

        it = self._selectedIter()
        if (not it):
            self.request("Please select a savepoint")
        else:
            # ony one selection
            # get the date string
            #treeRef = Gtk.TreeRowReference.new(self.savePoints, self.savePoints.get_path(it))
            selectedDateStr = self.savePoints.get_value(it, 1)
            #print('selected: ' + str(selectedDateStr))

            paths = self._getPaths()
            if paths is None:
                self.warning("Attempted to load savepoint. but paths failed\n" + self._pathsInfoStr())
            else:
                idxToEnd = self._indexToEndOf(it)
                print ("idxToEnd:" + str(idxToEnd))
                success = _rdiffLoadSavepoint(idxToEnd, paths[BACKUP_PATH], paths[SOURCE_PATH])

                if(success):
                    self._savePointLoaded = idxToEnd
                    self.showResetToMirrorButton()
                    self.message('savepoint loaded num: {0}'.format(self._savePointLoaded))
                else:
                    self.error('rdiff-backup failed?')
    
    
    #def _doRollback(self, widget):
        #self.clearStatus()
        #select = self.listView.get_selection()
        ## (selData is tuple (model, iter))
        #selData = select.get_selected()
        #it = selData[1]
        #if (not it):
            #self.message("No selection made?")
        #else:
            ## (don't bother with lastkey? Increment not an issue?)

            ## ony one selection
            ## get the date string
            ##treeRef = Gtk.TreeRowReference.new(self.savePoints, self.savePoints.get_path(it))
            #selectedDateStr = self.savePoints.get_value(it, 1)
            ##print('selected: ' + str(selectedDateStr))

            ##path = self.savePoints.get_path(it)
            #sourceRoute = self.sourcePath.get_text()
            #backupRoute = self.backupPath.get_text()
            #idxToEnd = self._indexToEndOf(it)
            #print ("idxToEnd:" + str(idxToEnd))
            #success = _rdiffBackupRollback(idxToEnd, backupRoute, sourceRoute)
            ##success = True
            #if(success):
                ## Remove next rows
                ## This appears to be the way to do that?
                #i = self.savePoints.iter_next(it)
                #while (self.savePoints.iter_is_valid(i)):
                    #self.savePoints.remove(i)
                    
                ## backup gsettings
                #self._settingsFromPopulation()
                #self.message('done')
            #else:
                #self.message('rdiff-backup failed?')
    
    
                
    ## Combination widgets
    def _selectMirrorFolder(self, widget):
            dialog = Gtk.FileChooserDialog("Please choose a folder", self,
                Gtk.FileChooserAction.SELECT_FOLDER,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                 "Select", Gtk.ResponseType.OK))
            dialog.set_default_size(800, 400)
                # contrary to GTK3 advice
            dialog.set_current_folder(self.backupPath.get_text())
            
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                path = dialog.get_filename()
                self.backupPath.set_text(path)
                self._guiClear()
                self.message('New mirror folder')
            elif response == Gtk.ResponseType.CANCEL:
                self.message('Selection cancelled')
    
            dialog.destroy()


    def actionPage(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_homogeneous(False)

        # Model
        # (index, date, time, pointName, restoreFrom)
        self.savePoints = Gtk.ListStore(int, str, str, str, str)

        # View
        # (ignores the index col in model)
        self.listView = Gtk.TreeView(self.savePoints)
        box.pack_start(self.listView, True, True, 0)


        #r = Gtk.CellRendererToggle()
        
        # (index, date, time, pointName, restoreFrom)
        # For debug only
        #self.dateColumn = Gtk.TreeViewColumn("Index", Gtk.CellRendererText(), text=0)
        #self.listView.append_column(self.dateColumn)
        
        # Date
        self.dateColumn = Gtk.TreeViewColumn("Date", Gtk.CellRendererText(), text=1)
        self.listView.append_column(self.dateColumn)
        # sort by index, not date text
        self.dateColumn.set_sort_column_id(0)
        
        # Time
        self.timeColumn = Gtk.TreeViewColumn("Time", Gtk.CellRendererText(), text=2)
        self.listView.append_column(self.timeColumn)
        # no sort
        
        # Name
        self.nameColumn = Gtk.TreeViewColumn("Name", Gtk.CellRendererText(), text=3)
        self.listView.append_column(self.nameColumn)
        self.nameColumn.set_sort_column_id(3)

        # Restore mark
        self.restoreColumn = Gtk.TreeViewColumn("restoredFrom", Gtk.CellRendererText(), text=4)
        self.listView.append_column(self.restoreColumn)
        self.restoreColumn.set_sort_column_id(4)
        
        self.button1 = Gtk.Button(label="Load selected savepoint")
        #self.button1.connect("clicked", self._doRollback)
        self.button1.connect("clicked", self._loadSavepoint)
        box.pack_start(self.button1, False, True, 0)
        
        self.button6 = Gtk.Button(label="Reset to mirror")
        self.button6.connect("clicked", self._resetToMirror)
        box.pack_start(self.button6, False, True, 0)
        
        self.button3 = Gtk.Button(label="Delete until selected savepoint")
        self.button3.connect("clicked", self._deleteUntilSavepoint)
        box.pack_start(self.button3, False, True, 0)
        
        self.button4 = Gtk.Button(label="Delete all savepoints")
        self.button4.connect("clicked", self._deleteAllSavepoints)
        box.pack_start(self.button4, False, True, 0)
        
        # Widgets here double for mirror/savepoints
        self.backupNameLabel = Gtk.Label("Backup name:")
        box.pack_start(self.backupNameLabel, False, True, 0)

        self.backupName = Gtk.Entry()
        box.pack_start(self.backupName, False, True, 0)
        
        self.button2 = Gtk.Button(label="New Savepoint")
        self.button2.connect("clicked", self._newSavepoint)
        box.pack_start(self.button2, False, True, 0)
        
        self.button5 = Gtk.Button(label="New Mirror")
        self.button5.connect("clicked", self._newMirror)
        box.pack_start(self.button5, False, True, 0)
        
        return box
        
    def settingsPage(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_homogeneous(False)
        
        label = Gtk.Label()
        label.set_markup ("<b>Source path</b>")
        label.set_halign(Gtk.Align.START)  
        box.pack_start(label, False, True, 0)

        self.sourcePath = Gtk.Entry()
        self.sourcePath.set_margin_bottom(8)
        box.pack_start(self.sourcePath, False, True, 0)
        
        
        label = Gtk.Label()
        label.set_markup ("<b>Backup folder path</b>")
        label.set_halign(Gtk.Align.START)

        box.pack_start(label, False, True, 0)
        selectMirrorbutton = Gtk.Button(label="Select backup folder")
        selectMirrorbutton.connect("clicked", self._selectMirrorFolder)
        box.pack_start(selectMirrorbutton, False, True, 0)


        self.backupPath = Gtk.Entry()
        self.backupPath.set_editable(False)
        self.backupPath.set_margin_bottom(8)
        box.pack_start(self.backupPath, False, True, 0)

        return box
        
    
    def __init__(self):
        Gtk.Window.__init__(self, title="Backuper")
        self.set_border_width(10)

        # Setup lastkey. Start = 0
        self._savePointCount = 0
        
        # setup savepoint loaded
        self._savePointLoaded = NO_SAVEPOINT_LOADED

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(box)

        label = Gtk.Label("Mirror:")
        box.pack_start(label, False, True, 0)
        
        self.backups = Gtk.ComboBoxText.new()
        box.pack_start(self.backups, False, True, 0)

        self.notebook = Gtk.Notebook()
        box.pack_start(self.notebook, True, True, 0)

        page1 =  self.actionPage()
        page1.set_border_width(10)
        self.notebook.append_page(page1, Gtk.Label('Backups'))
        
        page2 =  self.settingsPage()
        page2.set_border_width(10)
        self.notebook.append_page(page2, Gtk.Label('Settings'))
        
        #self.statusbar = Gtk.Statusbar()
        #self.statusbarContext = self.statusbar.get_context_id("backuper")
        #box.pack_start(self.statusbar, False, True, 0)

        self.notebook.connect("switch-page", self._notebookSwitched)

        
        separator = Gtk.Separator()
        box.pack_start(separator, False, True, 4)
        
        statusbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        statusbox.set_homogeneous(False)
        
        
        self.statusbar = Gtk.Label()
        self.statusbar.set_margin_left(4)
        self.statusbar.set_margin_bottom(4)
        
        statusbox.pack_start(self.statusbar, False, True, 0)
        
        box.pack_start(statusbox, False, True, 0)






def end(widget, event):
    widget._settingsFromPopulation()
    Gtk.main_quit()
    
    
# settings for last used files
gsettings = Gio.Settings.new(GSCHEMA)
#        setting.bind("show-desktop-icons", switch, "active", Gio.SettingsBindFlags.DEFAULT)
win = MyWindow()
win.connect("delete-event", end)
win.show_all()

# Populate
win._populateFromSettings()
Gtk.main()
