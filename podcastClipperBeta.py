import os
import sys
import csv
import urllib2
import feedparser
import subprocess
from xml.dom import minidom
from PyQt4 import QtGui, QtCore
from PyQt4.phonon import Phonon
import icons_rc

originalDir = os.getcwd() #Location of program
print originalDir

#Set the program to manipulate files in a user's documents folder
os.chdir(os.path.expanduser('~\Documents'))
curDir = os.getcwd()
print(curDir)

#Global lists to contain data from .csv files
subList = [] #Holds data from subscriptions.csv
episodeList = [] #Holds data from library.csv
clipList = [] #Holds data from clips.csv


#Custom class to store subscription data
class Subscription:
    def __init__(self, title, url, directory):
        self.title = title
        self.url = url
        self.directory = directory


#Custom class to store episode data
class Episode:
    def __init__(self, podcast, title, summary, directory, downloadFile, playbackFile):
        self.podcast = podcast
        self.episodeTitle = title
        self.episodeSummary = summary
        self.episodeDirectory = directory
        self.episodeFile = downloadFile
        self.episodePlaybackFile = playbackFile


#Custom class to store clip data
class Clip:
    def __init__(self, podcast, clipName, clipDescription, clipDirectory, mp3File, playbackFile):
        self.clipPodcast = podcast
        self.clipName = clipName
        self.clipDescription = clipDescription
        self.clipDirectory = clipDirectory
        self.clipMP3File = mp3File
        self.clipPlaybackFile = playbackFile


#Class to create main GUI window
class Player(QtGui.QMainWindow):
    def __init__(self):
        os.chdir(os.path.expanduser('~\Documents\podcastClipper'))

        super(Player, self).__init__()
        self.setGeometry(50,50,960,473)  #Window size
        self.setWindowTitle("Podcast Clipper") #Window name

        #Create options in file menu
        #Option to subscribe to podcast by entering RSS feed
        newSubscriptionAction = QtGui.QAction("New Subscription", self)
        newSubscriptionAction.triggered.connect(self.newSubscription)

        #Option to import podcast subscriptions with an XML or OPML file
        importSubscriptionAction = QtGui.QAction("Import Subscription", self)
        importSubscriptionAction.triggered.connect(self.importSubscriptions)

        #Option to exit the program
        exitAction = QtGui.QAction("Exit", self)
        exitAction.setShortcut("Ctrl+Q")

        mainMenu = self.menuBar()
        fileMenu = mainMenu.addMenu('&File') #Adds file button
        fileMenu.addAction(newSubscriptionAction)  #Add option to file drop down
        fileMenu.addAction(importSubscriptionAction) #Add option to file drop down
        fileMenu.addAction(exitAction) #Add option to file drop down

        #Box on left-hand side of program that allows user to view library and subscriptions
        self.libraryBox = QtGui.QTreeWidget(self) #View library and subs in a tree format
        self.libraryBox.setGeometry(0,20,250,200) #Box size and location
        self.libraryBox.header().setVisible(False) #Removes header

        self.item_0 = QtGui.QTreeWidgetItem(self.libraryBox) #Top of tree for Library
        self.item_1 = QtGui.QTreeWidgetItem(self.item_0)  #Episodes child
        self.item_1 = QtGui.QTreeWidgetItem(self.item_0)  #Clips child

        self.item_00 = QtGui.QTreeWidgetItem(self.libraryBox) #Top of tree for Subscriptions
        self.addSubcriptionChild() #Function to add children based on data from subscriptions.csv

        #Set the text for parents and children of tree widget
        self.libraryBox.topLevelItem(0).setText(0, "Library")
        self.libraryBox.topLevelItem(0).child(0).setText(0,"Episodes")
        self.libraryBox.topLevelItem(0).child(1).setText(0,"Clips")

        self.libraryBox.topLevelItem(1).setText(0, "Subscriptions")
        #Subscription children are named in addSubscriptionChild() function


        #Handles a user clicking on an item in the tree
        self.libraryBox.itemClicked.connect(self.libraryBoxClick)

        #Box that displays artwork from the podcast episode being played
        self.artworkBox = QtGui.QLabel(self)
        self.artworkBox.setGeometry(0,220,250,250)  #Set dimensions for artowrk 250px x 250px
        #Set the background-color of box as black when a file has not been chosen
        self.artworkBox.setStyleSheet("QLabel {background-color: black}")

        #Box in center of program that shows a list of episodes and clips
        self.episodeBox = QtGui.QTreeWidget(self)
        self.episodeBox.setGeometry(250,20,455,380)

        #Box has two header items that change names depending on what is being viewed
        self.episodeBox.headerItem().setText(0,"Title")
        self.episodeBox.headerItem().setText(1,"Date")

        #Box on right-hand side of program that generates preview artwork
        self.podcastInfoBox = QtGui.QLabel(self)
        self.podcastInfoBox.setGeometry(705,20,255,200) #Set dimensions for artwork
        self.podcastInfoBox.setStyleSheet("QLabel {background-color: black}") #Black if no episode selected

        #Box on right-hand side of program to display the description of an episode
        self.descriptionBox = QtGui.QTextBrowser(self)
        self.descriptionBox.setGeometry(705,200,255,200)

        #Button that displays a play/pause icon
        self.btnPlay = QtGui.QPushButton(self)
        self.btnPlay.setIcon(QtGui.QIcon(':icons/play.png'))
        self.btnPlay.setIconSize(QtCore.QSize(24,24))
        self.btnPlay.setGeometry(260,430,24,24)
        self.btnPlay.clicked.connect(self.handleButton)

        #Button to launch dialog to create a clip from an episode being played
        btnClip = QtGui.QPushButton("clip", self)
        btnClip.move(360,430)
        btnClip.clicked.connect(self.handleClipDialog)

        #Initiate PyQt4's Phonon module which handles audio playback
        self.mediaObject = Phonon.MediaObject(self)
        self.audioOutput = Phonon.AudioOutput(Phonon.MusicCategory, self)
        self.metaInformationResolver = Phonon.MediaObject(self)
        Phonon.createPath(self.mediaObject, self.audioOutput)

        self.mediaObject.setTickInterval(100)
        self.mediaObject.tick.connect(self.tick)  #Increments seek slider
        self.mediaObject.totalTimeChanged.connect(self.tock) #Displays current time

        #Initiate seek slider which allows user to control audio position
        slider = Phonon.SeekSlider(self)
        slider.setMediaObject(self.mediaObject)
        slider.setGeometry(300,410,380,20)

        #Display title of episode near bottom of window
        self.titleLabel = QtGui.QLabel(self)
        self.titleLabel.setGeometry(480,435,400,20)
        self.titleLabel.setText("Playing None")

        #Display the current time next to the seek slider
        self.currentTimeLabel = QtGui.QLabel(self)
        self.currentTimeLabel.setGeometry(690, 410, 45, 20)
        self.currentTimeLabel.setText("00:00:00")

        #Display the total time of a file
        self.lengthLabel = QtGui.QLabel(self)
        self.lengthLabel.setGeometry(735,410,55,20)
        self.lengthLabel.setText("/ 00:00:00")

        #Slider that allows user to control volume
        volumeSlider = Phonon.VolumeSlider(self)
        volumeSlider.setGeometry(810,410,110,20)
        volumeSlider.setAudioOutput(self.audioOutput)

        self.show() #PyQt4 function to display window

    #Function to handle adding a new podcast subscription with url
    def newSubscription(self):
        print "preparing to add new subscription" #For debug
        #Displays a field asking for a url
        podcastSource, ok = QtGui.QInputDialog.getText(self, 'Podcast Clipper', 'Enter RSS feed: ')

        if ok: #If user clicks ok
            podcastRSS = str(podcastSource) #Save url input
            addSub(podcastRSS) #Call function to save subscription
            QtGui.QTreeWidgetItem.takeChildren(self.item_00) #Refresh subscription tree
            self.addSubcriptionChild() #Function that re-generates an updated subscription list

    #Funtion to handle adding subscriptions with a XML/OPML file
    def importSubscriptions(self):
        print "importing subscriptions" #For debug
        #Displays file browser to choose file to import subscriptions
        xmlImport, ok = QtGui.QFileDialog.getOpenFileNameAndFilter(self, "Open File", "C:\\Desktop", "(*.opml *.xml)")

        if ok: #If user clicks ok
            print xmlImport
            print str(xmlImport)
            #print xmlImport.fileSelected()
            #xmlImportFile = xmlImport[0]
            xmlImportFile = str(xmlImport) #Get name of file selected


            xmlFile = minidom.parse(xmlImportFile) #Initiate parsing of file
            #Search file for <outline> elements.  These contain the attribute which has the feed url
            podcastList = xmlFile.getElementsByTagName('outline')

            for pod in podcastList: #Search all <outline> tags
                print(pod.attributes['xmlUrl'].value)
                addSub(pod.attributes['xmlUrl'].value) #Add subscription with url
                QtGui.QTreeWidgetItem.takeChildren(self.item_00) #Refresh subscription tree
                self.addSubcriptionChild() #Function that re-generates an updated subscription list
        else:
            print "cancel"

    #Function to handle clicking on an item in library/subscription trees
    def libraryBoxClick(self):

        itemClicked = self.libraryBox.currentItem() #Item clicked by user

        #If statements to determine which child a user has clicked
        if itemClicked.text(0) == "Episodes":
            print "episodes clicked"
            self.episodeBox.clear() #Needs to be cleared or else data will be appended
            self.episodeBox.headerItem().setText(0,"Podcast") #Change header of first column
            self.episodeBox.headerItem().setText(1,"Episode") #Change header of second column
            self.episodeBox.setColumnWidth(0,155) #Set width of first column

            #Sort episodeList array by podcast name for organization
            self.sortedEpisodeList = sorted(episodeList, key=lambda epi: epi.podcast)
            for i in range(0, len(self.sortedEpisodeList)):
                #print i, sortedEpisodeList[i].podcast, sortedEpisodeList[i].episodeTitle
                self.item_0 = QtGui.QTreeWidgetItem(self.episodeBox)
                self.episodeBox.topLevelItem(i).setText(0,"%s" % self.sortedEpisodeList[i].podcast)
                self.episodeBox.topLevelItem(i).setText(1,"%s" % self.sortedEpisodeList[i].episodeTitle)

            self.episodeBox.itemClicked.connect(self.episodeClick)
            self.episodeBox.itemDoubleClicked.connect(self.episodeDoubleClick)

        elif itemClicked.text(0) == "Clips":
            print "clips clicked"
            #Same logic as episodes clicked
            self.episodeBox.clear()
            self.episodeBox.headerItem().setText(0,"Podcast")
            self.episodeBox.headerItem().setText(1,"Clip")
            self.episodeBox.setColumnWidth(0,155)

            self.sortedClipList = sorted(clipList, key=lambda clip: clip.clipPodcast)
            for i in range(0, len(self.sortedClipList)):
                self.item_0 = QtGui.QTreeWidgetItem(self.episodeBox)
                self.episodeBox.topLevelItem(i).setText(0,"%s" % self.sortedClipList[i].clipPodcast)
                self.episodeBox.topLevelItem(i).setText(1,"%s" % self.sortedClipList[i].clipName)

            self.episodeBox.itemClicked.connect(self.clipClick)
            self.episodeBox.itemDoubleClicked.connect(self.clipDoubleClick)

        else:
            print "subscription clicked"
            #Same logic as episodes clicked
            self.episodeBox.clear()
            self.episodeBox.headerItem().setText(0,"Episode Title")
            self.episodeBox.headerItem().setText(1,"Date")
            self.episodeBox.setColumnWidth(0,300)

            self.sortedSubList = sorted(subList, key=lambda sub: sub.title)
            self.podcastURL = ""
            for i in range(0, len(self.sortedSubList)):
                if itemClicked.text(0) == self.sortedSubList[i].title:
                    self.podcastURL = self.sortedSubList[i].url
                    self.podcastDirectory = self.sortedSubList[i].directory
                    print self.podcastURL

            self.fetchFeedWorkerThread = FetchFeedThread(self.podcastURL, self.episodeBox)
            self.fetchFeedWorkerThread.start()

            self.episodeBox.itemDoubleClicked.connect(self.subscriptionEpisodeClick)

        print itemClicked.text(0)

    #Function that runs when program is done loading a feed
    def fetchThreadDone(self):
        print "fetch thread complete"

    #Function to handle clicking on a clip
    def clipClick(self):
        print "clip clicked"
        itemClicked = self.episodeBox.currentItem()
        clipSingleClick = False

        #Match clicked item with clip
        for i in range(0, len(self.sortedClipList)):
            if itemClicked.text(1) == self.sortedClipList[i].clipName:
                clipSingleClick = True
                clipDirectory = self.sortedClipList[i].clipDirectory
                os.chdir(os.path.expanduser('~\Documents\podcastClipper\%s' % clipDirectory))
                clipPodcast = self.sortedClipList[i].clipPodcast
                clipDescription = self.sortedClipList[i].clipDescription

        if clipSingleClick:

            #Statements to set preview artwork
            self.descriptionBox.setText(clipDescription)
            if os.path.isfile('folder.jpg'):
                clickedArtwork = QtGui.QPixmap(os.getcwd() + "/folder.jpg")
            elif os.path.isfile('folder.png'):
                clickedArtwork = QtGui.QPixmap(os.getcwd() + "/folder.png")

            scaledClickedArtwork = clickedArtwork.scaled(400,400,QtCore.Qt.KeepAspectRatio,QtCore.Qt.SmoothTransformation)

            paint = QtGui.QPainter()
            brush = QtGui.QBrush(QtGui.QColor(0,0,0,128))
            paint.begin(scaledClickedArtwork)
            paint.setBrush(brush)
            paint.drawRect(0,0,400,400)
            paint.end()

            self.podcastInfoBox.setPixmap(scaledClickedArtwork)
            print "Clip Click Complete"

    #Function to initiate clip playback
    def clipDoubleClick(self):
        print "episode double clicked"
        itemDoubleClicked = self.episodeBox.currentItem()
        clipDoubleClick = False

        #Match clicked item with clip
        for i in range(0, len(self.sortedClipList)):
            if itemDoubleClicked.text(1) == self.sortedClipList[i].clipName:
                clipDoubleClick = True
                self.episodeDirectory = self.sortedClipList[i].clipDirectory
                os.chdir(os.path.expanduser('~\Documents\podcastClipper\%s' % self.episodeDirectory))
                self.episodeLocation = self.sortedClipList[i].clipPlaybackFile
                self.episodeTitle = self.sortedClipList[i].clipName
                self.episodePodcast = self.sortedClipList[i].clipPodcast
                self.episodeSummary = self.sortedClipList[i].clipDescription

        if clipDoubleClick:
            #Play file
            self.mediaObject.setCurrentSource(Phonon.MediaSource('%s' % str(self.episodeLocation)))
            self.mediaObject.play()

            #Change play icon to paused icon
            self.btnPlay.setIcon(QtGui.QIcon(':icons/pause.png'))

            #Display episode summary
            self.descriptionBox.setText(self.episodeSummary)

            #Statements to display artwork
            if os.path.isfile('folder.jpg'):
                self.artwork = QtGui.QPixmap(os.getcwd() + "/folder.jpg")
            elif os.path.isfile('folder.png'):
                self.artwork = QtGui.QPixmap(os.getcwd() + "/folder.png")

            self.scaledArtwork = self.artwork.scaled(250,250, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            self.artworkBox.setPixmap(self.scaledArtwork)
            self.scaledPodcastBox = self.artwork.scaled(400,400, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)

            self.paint = QtGui.QPainter()
            self.brush = QtGui.QBrush(QtGui.QColor(0,0,0,128))
            self.paint.begin(self.scaledPodcastBox)
            self.paint.setBrush(self.brush)
            self.paint.drawRect(0,0,400,400)
            self.paint.end()

            self.podcastInfoBox.setPixmap(self.scaledPodcastBox)

            #Display name of episode that is playing
            self.titleLabel.setText("Playing " + self.episodeTitle)

    #Function to handle clicking on a single episode
    def episodeClick(self):
        print "episode clicked"
        itemClicked = self.episodeBox.currentItem()
        episodeSingleClick = False

        for i in range(0,len(self.sortedEpisodeList)):
            if itemClicked.text(1) == self.sortedEpisodeList[i].episodeTitle:
                episodeSingleClick = True
                episodeDirectory = self.sortedEpisodeList[i].episodeDirectory
                os.chdir(os.path.expanduser('~\Documents\podcastClipper\%s' % episodeDirectory))
                episodePodcast = self.sortedEpisodeList[i].podcast
                episodeDescription = self.sortedEpisodeList[i].episodeSummary

        if episodeSingleClick:
            #Display epsidoe description
            self.descriptionBox.setText(episodeDescription)

            #Statements to display preview artwork
            if os.path.isfile('folder.jpg'):
                clickedArtwork = QtGui.QPixmap(os.getcwd() + "/folder.jpg")
            elif os.path.isfile('folder.png'):
                clickedArtwork = QtGui.QPixmap(os.getcwd() + "/folder.png")

            scaledClickedArtwork = clickedArtwork.scaled(400,400,QtCore.Qt.KeepAspectRatio,QtCore.Qt.SmoothTransformation)

            paint = QtGui.QPainter()
            brush = QtGui.QBrush(QtGui.QColor(0,0,0,128))
            paint.begin(scaledClickedArtwork)
            paint.setBrush(brush)
            paint.drawRect(0,0,400,400)
            paint.end()

            self.podcastInfoBox.setPixmap(scaledClickedArtwork)
            print "Episode Click Completed"

    #Function to handle episode playback
    def episodeDoubleClick(self):
        print "episode double clicked"
        itemDoubleClicked = self.episodeBox.currentItem()
        episodeLibraryClick = False

        for i in range(0, len(self.sortedEpisodeList)):
            if itemDoubleClicked.text(1) == self.sortedEpisodeList[i].episodeTitle:
                episodeLibraryClick = True
                self.episodeDirectory = self.sortedEpisodeList[i].episodeDirectory
                os.chdir(os.path.expanduser('~\Documents\podcastClipper\%s' % self.episodeDirectory))
                self.episodeLocation = self.sortedEpisodeList[i].episodePlaybackFile
                self.episodeTitle = self.sortedEpisodeList[i].episodeTitle
                self.episodePodcast = self.sortedEpisodeList[i].podcast
                self.episodeSummary = self.sortedEpisodeList[i].episodeSummary

        if episodeLibraryClick:
            #Play file
            self.mediaObject.setCurrentSource(Phonon.MediaSource('%s' % str(self.episodeLocation)))
            self.mediaObject.play()

            #Change play icon to pause icon
            self.btnPlay.setIcon(QtGui.QIcon(':icons/pause.png'))

            #Display description
            self.descriptionBox.setText(self.episodeSummary)

            #Statements to display artowrk
            if os.path.isfile('folder.jpg'):
                self.artwork = QtGui.QPixmap(os.getcwd() + "/folder.jpg")
            elif os.path.isfile('folder.png'):
                self.artwork = QtGui.QPixmap(os.getcwd() + "/folder.png")

            self.scaledArtwork = self.artwork.scaled(250,250, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            self.artworkBox.setPixmap(self.scaledArtwork)
            self.scaledPodcastBox = self.artwork.scaled(400,400, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)


            self.paint = QtGui.QPainter()
            self.brush = QtGui.QBrush(QtGui.QColor(0,0,0,128))
            self.paint.begin(self.scaledPodcastBox)
            self.paint.setBrush(self.brush)
            self.paint.drawRect(0,0,400,400)
            self.paint.end()

            self.podcastInfoBox.setPixmap(self.scaledPodcastBox)

            self.titleLabel.setText("Playing " + self.episodeTitle)

    #Function to initiate episode download
    def subscriptionEpisodeClick(self):
        print "subscription episode double clicked"
        itemDoubleClicked = self.episodeBox.currentItem()
        subEpisodeClick = False
        uniqueDownload = True
        self.clickedPodcast = feedparser.parse(self.podcastURL)
        for i in range(0, len(self.clickedPodcast.entries)):
            if itemDoubleClicked.text(0) == self.clickedPodcast.entries[i].title:
                subEpisodeClick = True
                print "Episode location: ", self.clickedPodcast.entries[i].enclosures[0].href

                episodeNo = i
                episodeLocation = self.clickedPodcast.entries[i].enclosures[0].href
                episodeFileName = episodeLocation.split('/')[-1]
                episodeSummary = self.clickedPodcast.entries[episodeNo].summary
                feedTitle = self.clickedPodcast.feed.title
                episodeTitle = self.clickedPodcast.entries[episodeNo].title

                os.chdir(os.path.expanduser('~\Documents\podcastClipper\%s' % self.podcastDirectory))

        if len(episodeList) == 0:
            uniqueDownload = True

        if subEpisodeClick:
            for i in range(0, len(episodeList)):
                if episodeFileName == episodeList[i].episodeFile:
                    print("Episode has already been downloaded")
                    uniqueDownload = False
                #else:
                    #uniqueDownload = True

            if uniqueDownload:
                dialog = DownloadDialog(episodeLocation, episodeFileName, feedTitle, episodeTitle, episodeSummary, self.podcastDirectory)
                dialog.exec_()
            else:
                print "Redundant"
                pass

    #Function to display a list of subscriptions
    def addSubcriptionChild(self):

        #Alphabetically lists subscriptions
        sortedSubList = sorted(subList, key=lambda sub: sub.title)
        sortedEpisodeList = sorted(episodeList, key=lambda epi: epi.podcast)
        for i in range(0, len(sortedSubList)):
            self.item_1 = QtGui.QTreeWidgetItem(self.item_00)
            self.libraryBox.topLevelItem(1).child(i).setText(0,"%s" % sortedSubList[i].title)

    #Function to handle a user clicking on the clip button
    def handleClipDialog(self):

        launch = ClipDialog()
        if launch.exec_():
            clipName = launch.getClipName()
            clipLength = launch.getClipLength()
            clipDescription = launch.getClipDescription()

            currentTime = self.mediaObject.currentTime()
            print currentTime

            self.clipCreateThread = ClipCreateThread(currentTime, clipName, clipLength, clipDescription, self.episodePodcast, self.episodeDirectory, self.episodeLocation)
            self.clipCreateThread.start()

    #Function updates current playback time
    def tick(self, position):
        position = position/1000
        h = position/3600
        m = (position-3600*h)/60
        s = (position-3600*h-m*60)
        self.currentTimeLabel.setText('%02d:%02d:%02d '%(h,m,s))

    #Function displays the total length of a file
    def tock(self):
        totalTime = self.mediaObject.totalTime()
        totalTime = totalTime/1000
        h = totalTime/3600
        m = (totalTime-3600*h)/60
        s = (totalTime-3600*h-m*60)
        self.lengthLabel.setText('/ %02d:%02d:%02d'%(h,m,s))

    #Function to handle playing/pausing audio
    def handleButton(self):
        if self.mediaObject.state() == Phonon.PlayingState:
            self.mediaObject.pause()
            self.btnPlay.setIcon(QtGui.QIcon(':icons/play.png'))
        else:
            self.mediaObject.play()
            self.btnPlay.setIcon(QtGui.QIcon(':icons/pause.png'))

    def handleStateChanged(self):
        print("state")


#Class that creates window to give user options when creating clips
class ClipDialog(QtGui.QDialog):
    def __init__(self):
        super(ClipDialog, self).__init__()
        self.resize(400,300)
        self.setWindowTitle("Create Clip")

        self.OkCancelButtons = QtGui.QDialogButtonBox(self)
        self.OkCancelButtons.setGeometry(QtCore.QRect(30,240,341,32))
        self.OkCancelButtons.setOrientation(QtCore.Qt.Horizontal)
        self.OkCancelButtons.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)

        self.clipNameLineEdit = QtGui.QLineEdit(self)
        self.clipNameLineEdit.setGeometry(QtCore.QRect(110,20,113,20))

        self.clipName = QtGui.QLabel(self)
        self.clipName.setGeometry(QtCore.QRect(20,20,111,16))
        self.clipName.setText("Enter clip name: ")

        self.clipLengthSpinBox = QtGui.QDoubleSpinBox(self)
        self.clipLengthSpinBox.setGeometry(QtCore.QRect(190,60,62,22))

        self.clipLength = QtGui.QLabel(self)
        self.clipLength.setGeometry(QtCore.QRect(20,60,141,16))
        self.clipLength.setText("Select clip length: ")

        self.clipDescriptionPlainText = QtGui.QPlainTextEdit(self)
        self.clipDescriptionPlainText.setGeometry(QtCore.QRect(20,140,261,71))

        self.clipDescription = QtGui.QLabel(self)
        self.clipDescription.setGeometry(QtCore.QRect(20,110,161,16))
        self.clipDescription.setText("Enter description: ")

        QtCore.QObject.connect(self.OkCancelButtons, QtCore.SIGNAL("accepted()"), self.accept)
        QtCore.QObject.connect(self.OkCancelButtons, QtCore.SIGNAL("rejected()"), self.reject)
        QtCore.QMetaObject.connectSlotsByName(self)

    def getClipName(self):
        clipName = self.clipNameLineEdit.text()
        return clipName

    def getClipLength(self):
        clipLength = self.clipLengthSpinBox.value()
        return clipLength

    def getClipDescription(self):
        clipDescription = self.clipDescriptionPlainText.toPlainText()
        return clipDescription

    def getClipData(self):
        clipName = self.clipNameLineEdit.text()
        clipLength = self.clipLengthSpinBox.value()
        clipDescription = self.clipDescriptionPlainText.toPlainText()

        return clipName, clipLength, clipDescription


#Class that creates window to aleart user that a file is downloading
class DownloadDialog(QtGui.QDialog):
    def __init__(self, episodeLocation, episodeFileName, feedTitle, episodeTitle, episodeSummary, podcastDirectory, parent = None):
        super(DownloadDialog, self).__init__()
        self.resize(200,80)
        self.setWindowTitle("Download")

        self.downloadMessage = QtGui.QLabel(self)
        self.downloadMessage.setGeometry(QtCore.QRect(50,10,121,16))
        self.downloadMessage.setText("Downloading ")

        self.okButton = QtGui.QPushButton("OK",self)
        self.okButton.setGeometry(70,40,75,23)
        self.okButton.hide()

        self.episodeLocation = episodeLocation
        self.episodeFileName = episodeFileName
        self.feedTitle = feedTitle
        self.episodeTitle = episodeTitle
        self.episodeSummary = episodeSummary
        self.podcastDirectory = podcastDirectory

        self.filedownloadthread = FileDownloadThread(episodeLocation, episodeFileName, feedTitle, episodeTitle, episodeSummary, podcastDirectory)
        self.connect(self.filedownloadthread, QtCore.SIGNAL('signal'), self.update)
        self.filedownloadthread.start()

    def update(self):

        self.downloadMessage.setText("Episode downloaded")
        self.okButton.show()

        QtCore.QObject.connect(self.okButton, QtCore.SIGNAL("clicked()"), self.ok)
        QtCore.QMetaObject.connectSlotsByName(self)

    def ok(self):
        self.close()


#Inities download
class FileDownloadThread(QtCore.QThread):
    def __init__(self, episodeLocation, episodeFileName, feedTitle, episodeTitle, episodeSummary, podcastDirectory):
        super(FileDownloadThread, self).__init__()
        self.episodeLocation = episodeLocation
        self.episodeFileName = episodeFileName
        self.feedTitle = feedTitle
        self.episodeTitle = episodeTitle
        self.episodeSummary = episodeSummary
        self.podcastDirectory = podcastDirectory
        self.progressBar = QtGui.QProgressBar()

    def run(self):
        try:
            downloadIncomplete = True
            notAdded = True

            if downloadIncomplete:
                #Download file
                downloader = urllib2.urlopen(self.episodeLocation)
                epfile = open(self.episodeFileName, 'wb')
                print "Downloading"
                epfile.write(downloader.read())
                epfile.close()

                #Save episode description
                episodeDescription = removeNonAsciiCharacters(self.episodeSummary)
                #Convert MP3 to OGG to ensure playback works
                episodeFileConvert = self.episodeFileName[:-4]+".ogg"
                convert(self.episodeFileName, episodeFileConvert, self.podcastDirectory)

                os.chdir(os.path.expanduser('~\Documents\podcastClipper'))
                self.sortedEpisodeList = sorted(episodeList, key=lambda epi: epi.podcast)
                for i in range(0,len(self.sortedEpisodeList)):
                    if self.sortedEpisodeList[i].episodeTitle == self.episodeTitle:
                        notAdded = False

                if notAdded:
                    #Save data to librar.csv
                    episodeList.append(Episode(self.feedTitle, self.episodeTitle, episodeDescription, self.podcastDirectory, self.episodeFileName, episodeFileConvert))
                    with open('library.csv', 'ab') as libfile:
                        libwriter = csv.writer(libfile, quoting=csv.QUOTE_ALL)
                        libwriter.writerow([self.feedTitle, self.episodeTitle, episodeDescription, self.podcastDirectory, self.episodeFileName, episodeFileConvert])
                    print("Added")

            self.emit(QtCore.SIGNAL('signal'))

        except urllib2.HTTPError, e:
            print e


#Thread to load a podcast feed to avoid the program from hanging
class FetchFeedThread(QtCore.QThread):

    def __init__(self, podcastURL, episodeBox, parent=None):
        super(FetchFeedThread, self).__init__()
        #self.itemClicked = itemClicked
        self.podcastURL = podcastURL
        self.episodeBox = episodeBox

    def run(self):

        #Display episodes in feed
        self.clickedPodcast = feedparser.parse(self.podcastURL)
        for i in range(0, len(self.clickedPodcast.entries)):
            self.item_0 = QtGui.QTreeWidgetItem(self.episodeBox)
            self.episodeBox.topLevelItem(i).setText(0,"%s" % self.clickedPodcast.entries[i].title)
            self.episodeBox.topLevelItem(i).setText(1,"%s" % self.clickedPodcast.entries[i].published)
        self.emit(QtCore.SIGNAL("fetchThreadDone()"))


#Thread to create clips
class ClipCreateThread(QtCore.QThread):
    def __init__(self, currentTime, clipName, clipLength, clipDescription, episodePodcast, episodeDirectory, episodeLocation, parent=None):
        super(ClipCreateThread, self).__init__()
        self.currentTime = currentTime
        self.clipName = clipName
        self.clipLength = clipLength
        self.clipDescription = clipDescription
        self.episodePodcast = episodePodcast
        self.episodeDirectory = episodeDirectory
        self.episodeLocation = episodeLocation
        print currentTime

    def run(self):

        clipLengthToSeconds = self.clipLength*60
        clipNameMP3 = self.clipName+'.mp3'
        clipNameConvert = self.clipName+'.ogg'

        clipEnd = self.currentTime/1000
        clipStart = clipEnd - clipLengthToSeconds
        print str(clipStart)

        ffmpeg = originalDir + '\\ffmpeg\\bin\\ffmpeg.exe'
        subprocess.call(['%s' % ffmpeg, '-ss', '%s' % str(clipStart), '-t', '%s' % clipLengthToSeconds, '-i', '%s' % str(self.episodeLocation), '%s' % clipNameMP3])
        convert(clipNameMP3, clipNameConvert, self.episodeDirectory)

        os.chdir(os.path.expanduser('~\Documents\podcastClipper'))
        clipList.append(Clip(self.episodePodcast, self.clipName, self.clipDescription, self.episodeDirectory, clipNameMP3, clipNameConvert))
        with open('clips.csv', 'ab') as clipfile:
            clipwriter = csv.writer(clipfile, quoting=csv.QUOTE_ALL)
            clipwriter.writerow([self.episodePodcast, self.clipName, self.clipDescription, self.episodeDirectory, clipNameMP3, clipNameConvert])

        self.emit(QtCore.SIGNAL("clipThreadDone()"))


#Function to check to see if podcastClipper folder exists
def checkDir():
    if os.path.isdir('podcastClipper'):
        print("Podcast directory detected")
        os.chdir(os.path.expanduser('~\Documents\podcastClipper'))
        print(os.getcwd())
    else:
        print("Podcast directory not detected")
        os.mkdir('podcastClipper')
        print("Podcast directory created")
        os.chdir(os.path.expanduser('~\Documents\podcastClipper'))
        print(os.getcwd())


#Function to load data from csv files
def checkSub():
    if os.path.isfile('subscriptions.csv'):
        print("Subscription file detected")
        print("Importing subscriptions")

        with open('subscriptions.csv', 'rb') as subfile:
            subreader = csv.reader(subfile)
            for row in subreader:
                subList.append(Subscription(row[0], row[1], row[2]))

        with open('library.csv', 'rb') as libfile:
            libreader = csv.reader(libfile)
            for row in libreader:
                episodeList.append(Episode(row[0], row[1], row[2], row[3], row[4], row[5]))

        with open('clips.csv', 'rb') as clipfile:
            clipreader = csv.reader(clipfile)
            for row in clipreader:
                clipList.append(Clip(row[0], row[1], row[2], row[3], row[4], row[5]))

        #viewSub()
    else:
        print("Subscription file NOT detected")
        subFile = open("subscriptions.csv", "wb")
        subFile.close()
        libFile = open("library.csv", "wb")
        libFile.close()
        clipFile = open("clips.csv", "wb")
        clipFile.close()
        print("Subscription file created")


#Function to view subscriptions for debugging purposes
def viewSub():
    print("-----------------------Subscriptions---------------------")
    sortedSubList = sorted(subList, key=lambda sub: sub.title)
    for i in range(0, len(sortedSubList)):
        print i, sortedSubList[i].title, sortedSubList[i].url


#Function to add a subscription with
def addSub(feedLocation):
    podcast = feedparser.parse(feedLocation)
    podcastTitle = str(podcast.feed.title)
    podcastURL = str(feedLocation)

    #print "the length of subList is ", len(subList)

    uniqueSub = True

    for i in range(0, len(subList)):

        if podcastTitle == subList[i].title:
            print("Already subscribed to this podcast")
            uniqueSub = False

    os.chdir(os.path.expanduser('~\Documents\podcastClipper'))

    if uniqueSub:
        print("Adding subscription")

        directoryName = podcast.feed.title

        #Remove unallowed characters in a directory if podcast title contains one
        if directoryName.find('\\'):
            directoryName = directoryName.replace('\\', '_')
        if directoryName.find('/'):
            directoryName = directoryName.replace('/', '_')
        if directoryName.find(':'):
            directoryName = directoryName.replace(':', '_')
        if directoryName.find('*'):
            directoryName = directoryName.replace('*', '_')
        if directoryName.find('?'):
            directoryName = directoryName.replace('?', '_')
        if directoryName.find('"'):
            directoryName = directoryName.replace('"', '_')
        if directoryName.find('<'):
            directoryName = directoryName.replace('<', '_')
        if directoryName.find('>'):
            directoryName = directoryName.replace('>', '_')
        if directoryName.find('|'):
            directoryName = directoryName.replace('|', '_')

        os.mkdir('%s' % directoryName)

        subList.append(Subscription(podcastTitle, podcastURL, directoryName))
        with open('subscriptions.csv', 'ab') as csvfile:
            subwriter = csv.writer(csvfile, quoting=csv.QUOTE_ALL)
            subwriter.writerow([podcastTitle, podcastURL, directoryName])

        os.chdir(os.path.expanduser('~\Documents\podcastClipper\%s' % directoryName))

        artworkFileName = podcast.feed.image.href.split('/')[-1]
        artworkFileExtension = artworkFileName[-4:]
        artworkDownload = "folder"+artworkFileExtension

        try:
            #Download artwork
            print "Downloading artwork"
            downloader = urllib2.urlopen(podcast.feed.image.href)
            artworkFile = open(artworkDownload, 'wb')
            artworkFile.write(downloader.read())
            artworkFile.close()
            print "Artwork downloaded"
        except urllib2.HTTPError, e:
            print e

        os.chdir(os.path.expanduser('~\Documents\podcastClipper'))

        print("Subscription added")


#Removes special characters from descriptions
def removeNonAsciiCharacters(description):
    return ''.join(i for i in description if ord(i) < 128)


#Function to convert MP3 file to OGG
def convert(episodeFileName, episodeFileConvert, folder):
    print("Preparing file for playback")
    os.chdir(os.path.expanduser('~\Documents\podcastClipper\%s' % folder))
    ffmpeg = originalDir + '\\ffmpeg\\bin\\ffmpeg.exe'
    subprocess.call(['%s' % ffmpeg, '-y', '-i', '%s' % episodeFileName, '-vn', '-f', 'ogg', '%s' % episodeFileConvert])
    print("File ready for playback")


def main():
    app = QtGui.QApplication(sys.argv)
    GUI = Player()
    app.exec_()

checkDir()
checkSub()
main()