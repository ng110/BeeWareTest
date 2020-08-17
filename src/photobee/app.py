# -*- coding: utf-8 -*-
"""
Created on Mon Mar 23 22:36:40 2015
@author: Neil
Photo Workflow part 1:

set source directory (with jpg and raw)
set destination directory (jpg in root, subdirs for raw, pana, toedit)
set smugmug destination gallery
process photos with checkboxes to indicate: toedit (colour, crop, etc), pana, keepraw, to smugmug,
delete script copies files to destination and writes instructions for further processing

photopreviewier with checkboxes to presort into destination directory + workspace directory
 fphotopreprocess.py


v0.3: refactor having learned how to use QThreads properly.
v0.4: working with file moves, and cleaned up a bit

"""

import os
import sys
from glob import glob
import time
from PIL import Image, ImageQt, ImageEnhance
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from PySide2 import QtCore, QtGui, QtWidgets
import subprocess
import shutil
from math import cos, sin, radians
from collections import OrderedDict
import platform
from photobee.exif import Exif, readdatetaken, printalldates, exifinsert
from photobee.fisheye import fishwarppil
softwareName = 'photogui.py'

machinedict = {'DESKTOP-RH96J42': 'yoga',
               'Neils-T100': 't100',      # (1368, 768)
               'ST-2WD0GV1-NG': 'workold',   # (1680, 1050)/(1366, 768)
               'CL-24GQQQ2-NG': 'work',   # (1680, 1050)/(1280, 720)
               'ZEMAX01': 'zemax'}
machine = machinedict[platform.node()]

def editsavePhoto(job, outpath):
    original = Image.open(job['path'])
    width, height = original.size
    exif = Exif(job['path'])

    if job['rotangle'] == 90 or job['rotangle'] == -90:
        image = original.rotate(job['rotangle'], expand=True)
#        scale = (image.size[1]/original.size[0], job['rotangle'])
    else:
        image = original.rotate(job['rotangle'],)
#        scale = (image.size[0]/original.size[0], job['rotangle'])
    if job['brightcontrast']:
        bfactor = job['brightcontrast'][0]
        cfactor = job['brightcontrast'][1]
        brightnessadjuster = ImageEnhance.Brightness(image)
        image = brightnessadjuster.enhance(bfactor)
        contrastadjuster = ImageEnhance.Contrast(image)
        image = contrastadjuster.enhance(cfactor)
        exif.setcustomrendered()
    thetascale = 1.0
    if job['fish']:
        image = fishwarppil(image, level=job['fish'])
    if job['theta']:
        thetascale = job['thetascale']
        image = image.rotate(job['theta'], resample=Image.BICUBIC, expand=True)
    print('crop0', job['path'], job['crop'], flush=True)
    if job['crop']:
        print('crop1', job['path'], flush=True)
        rect = job['croprect']
        print('crop2', flush=True)
        sc = 1/(thetascale*job['scale'])
        print('crop3', flush=True)
        image = image.crop((round(sc*rect.x()), round(sc*rect.y()),
                           round(sc*(rect.width()+rect.x())),
                           round(sc*(rect.height()+rect.y()))))
        print('crop4', flush=True)

    image.save(outpath)
    exifinsert(outpath, job['path'], software=softwareName, orientation=1)
    # exif.width = image.size[0]
    # exif.height = image.size[1]
    # exif.orientation = 1
    # exif.removethumbnail()
    # exif.software = softwareName
    # exif.write(outpath)

# ex3['Exif'][piexif.ExifIFD.DateTimeOriginal]  - make sure present; if note set to DateTime value
# ex3['Exif'][piexif.ExifIFD.DateTimeDigitized]
# ex3['0th'][piexif.ImageIFD.DateTime]  - update (and exif.SubsecTime)
# ex3['0th'][piexif.ImageIFD.DateTime]  - update
# ex3['Exif'][piexif.ExifIFD.PixelXDimension]  - update
# ex3['Exif'][piexif.ExifIFD.PixelYDimension]  - update


def loadPhoto(path, previewsize, thumbsize):
    try:
        original = Image.open(path)
    except Exception as e:
        print('lp', path, e, flush=True)
        return
    width, height = original.size
#    exifdict = get_exif_data(original)
    exif = Exif(path)
    orientation = exif.orientation
    rotangle = 0
    if orientation == 6:
        rotangle = -90
    if orientation == 8:
        rotangle = 90
    if orientation == 3:
        rotangle = 180
    if orientation == 6 or orientation == 8:  # if rotating by +-90deg
        preview = original.resize( (previewsize[1],previewsize[1]*height//width),
                                      resample=Image.ANTIALIAS).rotate(rotangle,expand=True)
        thumb = original.resize( (thumbsize[1],thumbsize[1]*height//width),
                                  resample=Image.ANTIALIAS).rotate(rotangle,expand=True)
        scale = (preview.size[0]/original.size[1], rotangle)
    else:
        if (width / height > previewsize[0]/previewsize[1]):  # if wider than normal
            preview = original.resize( (previewsize[0],previewsize[0]*height//width),
                                      resample=Image.ANTIALIAS).rotate(rotangle)
        else:
###            print('lp2', height, width, path, flush=True)
            preview = original.resize( (previewsize[1]*width//height,previewsize[1]),
                                      resample=Image.ANTIALIAS).rotate(rotangle)
        thumb = original.resize( (thumbsize[1]*width//height,thumbsize[1]),
                                  resample=Image.ANTIALIAS).rotate(rotangle)
        scale = (preview.size[0]/original.size[0], rotangle)
    return(path, preview, thumb, exif, scale)


class Photo(QtCore.QObject):
    loadimage = QtCore.Signal(str, tuple, tuple)  # send text to status bar
    newlabeltext = QtCore.Signal(str)  # named Photo has new label text

    def __init__(self, worker, path, imsize, thumbsize):
        super().__init__()
        self.worker = worker
        self.imsize = imsize
        self.thumbsize = thumbsize
        self.path = path
        self.filename = self.path.split('\\')[-1]
        self.keep = True
#        self.keep = False
        self.keepraw = False
        self.smugmug = True
        self.smugmug = False
        self.pano = False
        self.postedit = False
        self.crop = False
        self.croprect = None
        self.brightcontrast = False
        self.fish = False
        self.theta = False
        self.categorised = False
        self.category = 0
        self.thetascale = 1.0
        self.setlabeltext()
        self.loadimage.connect(self.worker.loadimages)
        self.loadimage.emit(self.path, self.imsize, self.thumbsize)

    def setlabeltext(self):
        self.labeltext = '<font color="green">+</font>' if self.keep else '-'
        self.labeltext += '<font color="blue">R</font>' if self.keepraw else '-'
        self.labeltext += '<font color="red">S</font>' if self.smugmug else '-'
        self.labeltext += '<font color="purple">E</font>' if self.postedit else '-'
        self.labeltext += '<font color="brown">P</font>' if self.pano else '-'
        self.labeltext += '<font color="darkorange">C</font>' if self.crop else '-'
        self.labeltext += '<font color="gray">B</font>' if self.brightcontrast else '-'
        self.labeltext += '<font color="goldenrod">&theta;</font>' if self.theta else '-'
        self.labeltext += '<font color="deeppink">F</font>' if self.fish else '-'
        self.labeltext += '<font color="teal">{:X}</font>'.format(self.category) if self.categorised else '-'
        self.labeltext += ' {}'.format(self.filename)
        self.newlabeltext.emit(self.path)

    def makethumb(self, thumb):
        self.qimage = ImageQt.ImageQt(thumb)
        self.qpixmap = QtGui.QPixmap.fromImage(self.qimage)
        self.thumb = QtGui.QIcon(self.qpixmap)

    def makepreview(self, preview):
        self.preview = preview  # Keep as PIL Image to allow later editing
        self.previewwidth = preview.size[0]
        self.previewheight = preview.size[1]

    def readexif(self, exif):
        self.exif = exif    # not used outside this method: only use date, model orientation
        self.time = exif.time
        self.model = exif.camera
        self.orientation = exif.orientation

    def findrawpath(self, path):
        paths = [path, path+'\\raw', path+'\\RAW', path+'\\Raw']
        ext = ['RW2', 'RAW', 'raw', 'Raw']
        self.rawpath = None
        for p in paths:
            for e in ext:
                trialpath = p + '\\' + self.filename.split('.')[0] + '.' + e
                if os.path.isfile(trialpath):
                    self.rawpath = trialpath
####                    print(self.rawpath, flush=True)
                    return

    def setscale(self, scale):
        self.scale = scale[0]
        self.rotangle = scale[1]

    def setcroprect(self, croprect):
        self.croprect = croprect
        if self.croprect.x() < 0:
            self.croprect.setX(0)
        if self.croprect.y() < 0:
            self.croprect.setY(0)
        if self.croprect.x() + self.croprect.width() >= self.previewwidth:
            self.croprect.setRight(self.previewwidth-1)
        if self.croprect.y() + self.croprect.height() >= self.previewheight:
            self.croprect.setBottom(self.previewheight-1)
#        print(croprect.x(), croprect.y(), croprect.x()+croprect.width(), croprect.y()+croprect.height(), flush=True)
#        print(croprect, self.previewwidth, self.previewheight, flush=True)

    def convertimage(self):  # crop, transform etc before saving
        self.outimage = Image.open(self.path)
#        self.outimage = self.outimage.xxxx

    def togglekeep(self):
        self.keep = not self.keep
        self.setlabeltext()

    def togglekeepraw(self):
        if self.rawpath:
            self.keepraw = not self.keepraw
            self.setlabeltext()

    def togglesmugmug(self):
        self.smugmug = not self.smugmug
        self.setlabeltext()

    def toggleedit(self):
        self.postedit = not self.postedit
        self.setlabeltext()

    def togglepano(self):
        self.pano = not self.pano
        self.setlabeltext()

    def setbrightcontrast(self, dbr, dcon):
        if self.brightcontrast:
            self.brightcontrast[0] *= dbr
            self.brightcontrast[1] *= dcon
            print(self.brightcontrast, flush=True)
        else:
            self.brightcontrast = [dbr, dcon]
#            print('a',self.brightcontrast, flush=True)
        self.setlabeltext()

    def resetbrightcontrast(self):
        self.brightcontrast = False
        self.setlabeltext()

    def dtheta(self, dtheta):
        if self.theta:
            self.theta += dtheta
            print(self.theta, flush=True)
        else:
            self.theta = dtheta
            print('a', self.theta, flush=True)
        wsc = (abs(self.previewwidth * cos(radians(self.theta))) +
               abs(self.previewheight * sin(radians(self.theta)))) / self.previewwidth
        hsc = (abs(self.previewwidth * sin(radians(self.theta))) +
               abs(self.previewheight * cos(radians(self.theta)))) / self.previewheight
        self.thetascale = 1/max(wsc, hsc)
        self.setlabeltext()

    def resettheta(self):
        self.theta = False
        self.thetascale = 1.0
        self.setlabeltext()

    def dfish(self, dfish):
        if self.fish:
            self.fish += dfish
            print('f', self.fish, flush=True)
        else:
            self.fish = dfish
            print('ff', self.fish, flush=True)
        self.setlabeltext()

    def resetfish(self):
        self.fish = False
        self.setlabeltext()

    def setcategory(self, cat):
        print(cat, flush=True)
        if cat == 0:
            self.categorised = False
            self.category = 0
        elif type(cat) is int and cat > 0 and cat <= 11:
            self.categorised = True
            self.category = cat
        else:
            raise TypeError
        self.setlabeltext()





class Canvas(QtWidgets.QLabel):
    cropboxactivated = QtCore.Signal()  # send text to status bar

    def __init__(self):
        super().__init__()
        self.rubberBand = QtWidgets.QRubberBand(QtWidgets.QRubberBand.Rectangle, self)
        self.setAlignment(QtCore.Qt.AlignTop)

    def redraw(self):
        self.rubberBand.setGeometry(self.rect)
        self.rubberBand.show()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.origin = QtCore.QPoint(event.pos())
            self.rubberBand.setGeometry(QtCore.QRect(self.origin, QtCore.QSize()))
            self.rubberBand.show()

    def mouseMoveEvent(self, event):
        if not self.origin.isNull():
            self.rubberBand.setGeometry(QtCore.QRect(self.origin, event.pos()).normalized())

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.rect = self.rubberBand.frameGeometry()
            self.cropboxactivated.emit()


class Worker(QtCore.QObject):
    imagesready = QtCore.Signal(str, object, object, object, tuple, int)
    sendstatus = QtCore.Signal(str)

    def __init__(self, indir, outdir, processes, ui):
        super().__init__()
        self.ready = False
        self.futures = []
        self.indir = indir
        self.outdir = outdir
        self.ui = ui
        self.fullreslist = []
        if processes > 0:
            self.pool = ProcessPoolExecutor(processes)
        elif processes < 0:
            self.pool = ThreadPoolExecutor(-processes)

    def run(self):
        self.ready = True

    @QtCore.Slot(str, tuple, tuple)
    def loadimages(self, path, previewsize, thumbsize):
        f = self.pool.submit(loadPhoto, path, previewsize, thumbsize)
        self.futures.append(f)
        f.add_done_callback(self.photocallback)

    def photocallback(self, future):
        try:
            if future.cancelled():
                return
            path, preview, thumb, exif, scale = future.result()
            self.futures.remove(future)
            self.imagesready.emit(path, preview, thumb, exif, scale, len(self.futures))
        except Exception as e:
            print('Callbackfail:', e, path, flush=True)
            return

    @QtCore.Slot(str)
    def maintainfullreslist(self, path):
        if path not in self.fullreslist:
            self.fullreslist.append(path)

    @QtCore.Slot(dict)
    def movefiles(self, job):
        # reject
        if job['reject']:
            shutil.copy2(job['path'], self.outdir + '\\reject')
            print('Rejected file moved:', job['path'], flush=True)
            self.sendstatus.emit('Rejected file moved:' + job['path'])
            return

        # keepraw:
        if job['keepraw']:
            shutil.copy2(job['rawpath'], self.outdir + '\\raw')
            self.sendstatus.emit('Saving raw file' + job['rawpath'])
        # set outpath:
        if job['pano']:
            outdir = self.outdir + '\\pano'
        elif job['postedit']:
            outdir = self.outdir + '\\postedit'
        else:
            outdir = self.outdir
        outpath = outdir + '\\' + os.path.basename(job['path'])
        # save file:
        if job['brightcontrast'] or job['theta']:
            editsavePhoto(job, outpath)
        elif job['crop']:
            rect = job['croprect']
            sc = 1.0 / job['scale']
            jpegtran = os.path.dirname(os.path.dirname(__file__)) + r'\\bin\\jpegtran.exe'
            if job['rotangle'] == -90:
                command = '{} -rotate 90 -crop {}x{}+{}+{} -copy all "{}" "{}"'.format(jpegtran, round(sc*rect.width()),
                            round(sc*rect.height()), round(sc*rect.x()), round(sc*rect.y()), job['path'], outpath)
            elif job['rotangle'] == 90:
                command = '{} -rotate 270 -crop {}x{}+{}+{} -copy all "{}" "{}"'.format(jpegtran, round(sc*rect.width()),
                            round(sc*rect.height()), round(sc*rect.x()), round(sc*rect.y()), job['path'], outpath)
            elif job['rotangle'] == 180:
                command = '{} -rotate 180 -crop {}x{}+{}+{} -copy all "{}" "{}"'.format(jpegtran, round(sc*rect.width()),
                            round(sc*rect.height()), round(sc*rect.x()), round(sc*rect.y()), job['path'], outpath)
            else:
                command = '{} -crop {}x{}+{}+{} -copy all "{}" "{}"'.format(jpegtran, round(sc*rect.width()),
                            round(sc*rect.height()), round(sc*rect.x()), round(sc*rect.y()), job['path'], outpath)
            print(command, job['rotangle'], flush=True)
            subprocess.run(command, creationflags=0x08000000)
            time.sleep(1)
            exif = Exif(job['path'])
            exif.orientation = 1
            exif.removethumbnail()
            exif.software = softwareName
            exif.write(outpath)
            # set 0th.orientation, 1st.orientation to 1 and remove thumbnail.  Plus other exif changes.
        else:
            shutil.copy2(job['path'], outdir)
        if job['smugmug']:
            shutil.copy2(outpath, self.outdir + '\\smugmug')
        if job['cat'] > 0:
            shutil.move(outpath, self.outdir + '\\{:X}'.format(job['cat']))
        print('File moved:', job['path'], flush=True)
        self.sendstatus.emit('File moved:' + job['path'])
#        time.sleep(10)

    def close(self):
        for f in self.futures:
            try:
                f.cancel()
            except:
                pass


class PhotoUI(QtWidgets.QMainWindow):
    ''' Create photo sorting app window.\n
    Parameters:\n
    indir: directory where source image photos are stored\n
    outdir: path of output directory.  Defaults to <indir>/out \n
    inraw: path of source raw files.  Defaults to same as indir. \n
    outraw: path of output directory.  Defaults to <indir>/out/raw \n
    outdir, inraw and outraw are relative to indir unless they are a
    full path starting with a drive specification
    '''

    requestfullres = QtCore.Signal(str)  # request loading of full-res version of current photo
    submitfilemove = QtCore.Signal(dict)  # enqueue a file move/copy job

    def __init__(self, indir, outdir=None, 
                 canvassize=(900, 600), thumbsize=(128, 96), listwidth=300):
        super().__init__()
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setAttribute(QtCore.Qt.WA_QuitOnClose)

        if machine == 'yoga':
            print('Running on YOGA.  Folder =', indir, flush=True)
            processes = -4   # -ve processes means threads
        elif machine == 't100':
            print('Running on T100.  Folder =', indir, flush=True)
            processes = 2
        elif machine == 'work' or machine == 'workold':
            print('Running on Work PC.  Folder =', indir, flush=True)
            processes = 4
        elif machine == 'zemax':
            print('Running on Zemax Machine.  Folder =', indir, flush=True)
            processes = 4
        else:
            print('Cannot identify machine.  Folder =', indir, flush=True)
            processes = 6
        self.canvassize = canvassize
        self.thumbsize = thumbsize
        self.listwidth = listwidth
        self.timer = QtCore.QTimer()
        self.recentselections = []
        self.buildui()
        self.fullrespath = None
        self.fullres = None
        self.refreshing = False
        self.refreshwaiting = False
        self.remaining = True

        self.indir = indir
        if not outdir:
            self.outdir = indir+r'\ppout'
        else:
            if ':' in outdir:
                self.outdir = outdir
            else:
                self.outdir = indir+outdir

        # setup manager thread
        self.workerthread = QtCore.QThread()
        self.worker = Worker(self.indir, self.outdir, processes, self)
        self.worker.moveToThread(self.workerthread)
        self.workerthread.started.connect(self.worker.run)
        self.workerthread.start()

        # connect other slots
        self.worker.imagesready.connect(self.catchphoto)
        self.worker.sendstatus.connect(self.statusmessage)
        self.canvas.cropboxactivated.connect(self.cropactivated)
        self.listwidget.currentItemChanged.connect(self.on_item_changed)
        self.submitfilemove.connect(self.worker.movefiles)
        self.requestfullres.connect(self.worker.maintainfullreslist)

        self.show()
        self.loadphotos()

    def buildui(self):
        self.setMinimumSize(self.canvassize[0]+self.listwidth, self.canvassize[1]+50)
        self.setWindowTitle('PhotoUI')
        self.setWindowIcon(QtGui.QIcon('buttercup.png'))
        self.statusmessage('Initialising...')

        menubar = self.menuBar()
        # File Menu
        exitAction = QtWidgets.QAction(QtGui.QIcon('exit.bmp'), 'E&xit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.triggered.connect(self.close)
        filemoveAction = QtWidgets.QAction(QtGui.QIcon('exit.bmp'), '&Move files', self)
        filemoveAction.setShortcut('Ctrl+M')
        filemoveAction.triggered.connect(self.filemove)
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(exitAction)
        fileMenu.addAction(filemoveAction)
        # Photo menu
        togglekeepAction = QtWidgets.QAction('Toggle &Keep Photo', self)
        togglekeepAction.setShortcut(' ')
        togglekeepAction.triggered.connect(self.togglekeep)
        toggleallkeepAction = QtWidgets.QAction('Toggle All Keep Photo', self)
        toggleallkeepAction.setShortcut('Ctrl+ ')
        toggleallkeepAction.triggered.connect(self.toggleallkeep)
        togglekeeprawAction = QtWidgets.QAction('Toggle Keep &Raw', self)
        togglekeeprawAction.setShortcut('R')
        togglekeeprawAction.triggered.connect(self.togglekeepraw)
        togglesmugmugAction = QtWidgets.QAction('Toggle &Smugmug', self)
        togglesmugmugAction.setShortcut('S')
        togglesmugmugAction.triggered.connect(self.togglesmugmug)
        toggleallsmugmugAction = QtWidgets.QAction('Toggle All Smugmug', self)
        toggleallsmugmugAction.setShortcut('Ctrl+S')
        toggleallsmugmugAction.triggered.connect(self.toggleallsmugmug)
        toggleeditAction = QtWidgets.QAction('Toggle Post-&Edit', self)
        toggleeditAction.setShortcut('E')
        toggleeditAction.triggered.connect(self.toggleedit)
        togglepanoAction = QtWidgets.QAction('Toggle &Panorama', self)
        togglepanoAction.setShortcut('P')
        togglepanoAction.triggered.connect(self.togglepano)
        brightupAction = QtWidgets.QAction('Increase Brightness (+,=)', self)
        brightupAction.setShortcut('+')
        brightupAction.setShortcut('=')
        brightupAction.triggered.connect(self.brightup)
        brightdownAction = QtWidgets.QAction('Reduce Brightness (-)', self)
        brightdownAction.setShortcut('-')
        brightdownAction.triggered.connect(self.brightdown)
        contrastupAction = QtWidgets.QAction('Increase Contrast (Ctrl++,Ctrl+=)', self)
        contrastupAction.setShortcut('Ctrl++')
        contrastupAction.setShortcut('Ctrl+=')
        contrastupAction.triggered.connect(self.contrastup)
        contrastdownAction = QtWidgets.QAction('Reduce Contrast (Ctrl+-)', self)
        contrastdownAction.setShortcut('Ctrl+-')
        contrastdownAction.triggered.connect(self.contrastdown)
        brightcontrastoffAction = QtWidgets.QAction('Reset Brightness+Contrast (0)', self)
        brightcontrastoffAction.setShortcut('0')
        brightcontrastoffAction.triggered.connect(self.brightcontrastoff)
        dclockwiseAction = QtWidgets.QAction('Small Clockwise (,)', self)
        dclockwiseAction.setShortcut(',')
        dclockwiseAction.triggered.connect(self.dthetac)
        dcclockwiseAction = QtWidgets.QAction('Small Anti-Clockwise (.)', self)
        dcclockwiseAction.setShortcut('.')
        dcclockwiseAction.triggered.connect(self.dthetacc)
        stepclockwiseAction = QtWidgets.QAction('Small Clockwise (Ctrl+,)', self)
        stepclockwiseAction.setShortcut('Ctrl+,')
        stepclockwiseAction.triggered.connect(self.thetac)
        stepcclockwiseAction = QtWidgets.QAction('Small Anti-Clockwise (Ctrl+.)', self)
        stepcclockwiseAction.setShortcut('Ctrl+.')
        stepcclockwiseAction.triggered.connect(self.thetacc)
        thetaoffAction = QtWidgets.QAction('Reset Rotation (/)', self)
        thetaoffAction.setShortcut('/')
        thetaoffAction.triggered.connect(self.thetaoff)
        fishupAction = QtWidgets.QAction('Increase &Fisheye correction (F)', self)
        fishupAction.setShortcut('F')
        fishupAction.triggered.connect(self.fishup)
        fishdownAction = QtWidgets.QAction('Reduce Fisheye correction (G)', self)
        fishdownAction.setShortcut('G')
        fishdownAction.triggered.connect(self.fishdown)
        fishoffAction = QtWidgets.QAction('Reset Fisheye correction (H)', self)
        fishoffAction.setShortcut('H')
        fishoffAction.triggered.connect(self.fishoff)
        photoMenu = menubar.addMenu('&Photo')
        photoMenu.addAction(togglekeepAction)
        photoMenu.addAction(toggleallkeepAction)
        photoMenu.addAction(togglekeeprawAction)
        photoMenu.addAction(togglesmugmugAction)
        photoMenu.addAction(toggleallsmugmugAction)
        photoMenu.addAction(toggleeditAction)
        photoMenu.addAction(togglepanoAction)
        photoMenu.addAction(brightupAction)
        photoMenu.addAction(brightdownAction)
        photoMenu.addAction(contrastupAction)
        photoMenu.addAction(contrastdownAction)
        photoMenu.addAction(brightcontrastoffAction)
        photoMenu.addAction(dclockwiseAction)
        photoMenu.addAction(dcclockwiseAction)
        photoMenu.addAction(stepclockwiseAction)
        photoMenu.addAction(stepcclockwiseAction)
        photoMenu.addAction(thetaoffAction)
        photoMenu.addAction(fishupAction)
        photoMenu.addAction(fishdownAction)
        photoMenu.addAction(fishoffAction)


        # Set All menu
        allkeepAction = QtWidgets.QAction('Keep all', self)
        allkeepAction.triggered.connect(self.allkeep)
        nonekeepAction = QtWidgets.QAction('Keep none', self)
        nonekeepAction.triggered.connect(self.nonekeep)
        allsmugmugAction = QtWidgets.QAction('Smugmug all', self)
        allsmugmugAction.triggered.connect(self.allsmugmug)
        nonesmugmugAction = QtWidgets.QAction('Smugmug none', self)
        nonesmugmugAction.triggered.connect(self.nonesmugmug)
        allrawAction = QtWidgets.QAction('Keep all raw', self)
        allrawAction.triggered.connect(self.allraw)
        nonerawAction = QtWidgets.QAction('Keep none raw', self)
        nonerawAction.triggered.connect(self.noneraw)
        allcat1Action = QtWidgets.QAction('All category 1', self)
        allcat1Action.triggered.connect(self.allcat1)
        nonecatAction = QtWidgets.QAction('All uncategorised', self)
        nonecatAction.triggered.connect(self.nonecat)

        setallMenu = menubar.addMenu('Set &All')
        setallMenu.addAction(allkeepAction)
        setallMenu.addAction(nonekeepAction)
        setallMenu.addAction(allsmugmugAction)
        setallMenu.addAction(nonesmugmugAction)
        setallMenu.addAction(allrawAction)
        setallMenu.addAction(nonerawAction)
        setallMenu.addAction(allcat1Action)
        setallMenu.addAction(nonecatAction)

        # image canvas
        self.canvas = Canvas()
        self.canvas.setFixedSize(*self.canvassize)
        self.canvasbackgroundimage = QtGui.QPixmap()
        # file list
        self.listwidget = QtWidgets.QListWidget()
        self.listwidget.resize(self.listwidth, self.canvassize[1])
        self.listwidget.setIconSize(QtCore.QSize(50, 50))
        # define layout
        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.canvas)
        hbox.addStretch(1)
        hbox.addWidget(self.listwidget)
        self.central = QtWidgets.QLabel()
        self.setCentralWidget(self.central)
        self.central.setLayout(hbox)

    def loadphotos(self):
        filelist = []
        for extension in ['jpg', 'jpeg', 'tif', 'tiff', 'png', 'PNG']:
            pattern = os.path.join(self.indir, '*.{}'.format(extension))
            for file in [f for f in glob(pattern) if f not in filelist]:
                filelist.append(file)
        if len(filelist) == 0:
            print("No images found in {}.\nExiting...".format(self.indir), flush=True)
            self.close()
            return()
        filelist.sort(key=readdatetaken)
        self.statusmessage('Sorting complete.')

        self.photos = OrderedDict()
        self.items = OrderedDict()
        for file in filelist:
#            printalldates(file)   #### uncomment to print the various exif date information
            photo = Photo(self.worker, file, self.canvassize, self.thumbsize)
            self.photos[file] = photo

        self.statusmessage('Photo objects generated.')
        for file in filelist:
            item = QtWidgets.QListWidgetItem(self.listwidget)
            self.items[file] = item
            item.path = file
            item.setText(self.photos[file].filename)
            font = self.font()
            font.setItalic(True)
            item.setFont(font)
            item.label = QtWidgets.QLabel()
        self.listwidget.setCurrentItem(self.items[filelist[0]])

    @QtCore.Slot(str)
    def statusmessage(self, message, timeout=30000):
        self.statusBar().showMessage(message, timeout)

    @QtCore.Slot(str, object, object, object, tuple, int)
    def catchphoto(self, path, preview, thumb, exif, scale, remaining):
        self.remaining = remaining
        self.photos[path].readexif(exif)
        self.photos[path].makethumb(thumb)
        self.photos[path].makepreview(preview)
        self.photos[path].findrawpath(self.indir)
        self.photos[path].setscale(scale)
        self.items[path].setText('')
        self.items[path].label.setText(self.photos[path].labeltext)
        self.listwidget.setItemWidget(self.items[path], self.items[path].label)
        self.items[path].setIcon(self.photos[path].thumb)
        self.statusmessage("{} loaded. {} remaining.".format(self.photos[path].filename, remaining))
        if self.items[path] == self.listwidget.currentItem():
            self.refreshcanvas()

    @QtCore.Slot()
    def cropactivated(self):
        self.photos[self.listwidget.currentItem().path].crop = True
        self.photos[self.listwidget.currentItem().path].setlabeltext()
        self.items[self.listwidget.currentItem().path].label.setText(
                   self.photos[self.listwidget.currentItem().path].labeltext)
#        self.photos[self.listwidget.currentItem().path].croprect = self.canvas.rect
        self.photos[self.listwidget.currentItem().path].setcroprect(self.canvas.rect)

    @QtCore.Slot()
    def togglesmugmug(self):
        self.photos[self.listwidget.currentItem().path].togglesmugmug()
        self.items[self.listwidget.currentItem().path].label.setText(
                   self.photos[self.listwidget.currentItem().path].labeltext)
    @QtCore.Slot()
    def toggleallsmugmug(self):
        for path in self.items:
            self.photos[path].togglesmugmug()
            self.items[path].label.setText(self.photos[path].labeltext)

    @QtCore.Slot()
    def togglekeepraw(self):
        self.photos[self.listwidget.currentItem().path].togglekeepraw()
        self.items[self.listwidget.currentItem().path].label.setText(
                   self.photos[self.listwidget.currentItem().path].labeltext)

    @QtCore.Slot()
    def togglekeep(self):
        self.photos[self.listwidget.currentItem().path].togglekeep()
        self.items[self.listwidget.currentItem().path].label.setText(
                   self.photos[self.listwidget.currentItem().path].labeltext)
        self.refreshcanvas()

    @QtCore.Slot()
    def toggleallkeep(self):
        for path in self.items:
            self.photos[path].togglekeep()
            self.items[path].label.setText(self.photos[path].labeltext)
        self.refreshcanvas()

    @QtCore.Slot()
    def toggleedit(self):
        self.photos[self.listwidget.currentItem().path].toggleedit()
        self.items[self.listwidget.currentItem().path].label.setText(
                   self.photos[self.listwidget.currentItem().path].labeltext)

    @QtCore.Slot()
    def togglepano(self):
        self.photos[self.listwidget.currentItem().path].togglepano()
        self.items[self.listwidget.currentItem().path].label.setText(
                   self.photos[self.listwidget.currentItem().path].labeltext)

    @QtCore.Slot()
    def brightup(self):
        self.photos[self.listwidget.currentItem().path].setbrightcontrast(1.02,1)
        self.items[self.listwidget.currentItem().path].label.setText(
                   self.photos[self.listwidget.currentItem().path].labeltext)
        self.refreshcanvas()
    @QtCore.Slot()
    def brightdown(self):
        self.photos[self.listwidget.currentItem().path].setbrightcontrast(.98,1)
        self.items[self.listwidget.currentItem().path].label.setText(
                   self.photos[self.listwidget.currentItem().path].labeltext)
        self.refreshcanvas()
    @QtCore.Slot()
    def contrastup(self):
        self.photos[self.listwidget.currentItem().path].setbrightcontrast(1,1.04)
        self.items[self.listwidget.currentItem().path].label.setText(
                   self.photos[self.listwidget.currentItem().path].labeltext)
        self.refreshcanvas()
    @QtCore.Slot()
    def contrastdown(self):
        self.photos[self.listwidget.currentItem().path].setbrightcontrast(1,.96)
        self.items[self.listwidget.currentItem().path].label.setText(
                   self.photos[self.listwidget.currentItem().path].labeltext)
        self.refreshcanvas()
    @QtCore.Slot()
    def brightcontrastoff(self):
        self.photos[self.listwidget.currentItem().path].resetbrightcontrast()
        self.items[self.listwidget.currentItem().path].label.setText(
                   self.photos[self.listwidget.currentItem().path].labeltext)
        self.refreshcanvas()

    @QtCore.Slot()
    def dthetacc(self):
        self.photos[self.listwidget.currentItem().path].dtheta(-0.5)
        self.items[self.listwidget.currentItem().path].label.setText(
                   self.photos[self.listwidget.currentItem().path].labeltext)
        self.refreshcanvas()
    def dthetac(self):
        self.photos[self.listwidget.currentItem().path].dtheta(0.5)
        self.items[self.listwidget.currentItem().path].label.setText(
                   self.photos[self.listwidget.currentItem().path].labeltext)
        self.refreshcanvas()
    def thetacc(self):
        self.photos[self.listwidget.currentItem().path].dtheta(-5)
        self.items[self.listwidget.currentItem().path].label.setText(
                   self.photos[self.listwidget.currentItem().path].labeltext)
        self.refreshcanvas()
    def thetac(self):
        self.photos[self.listwidget.currentItem().path].dtheta(5)
        self.items[self.listwidget.currentItem().path].label.setText(
                   self.photos[self.listwidget.currentItem().path].labeltext)
        self.refreshcanvas()
    @QtCore.Slot()
    def thetaoff(self):
        self.photos[self.listwidget.currentItem().path].resettheta()
        self.items[self.listwidget.currentItem().path].label.setText(
                   self.photos[self.listwidget.currentItem().path].labeltext)
        self.refreshcanvas()
    @QtCore.Slot()
    def fishup(self):
        self.photos[self.listwidget.currentItem().path].dfish(1)
        self.items[self.listwidget.currentItem().path].label.setText(
                   self.photos[self.listwidget.currentItem().path].labeltext)
        self.refreshcanvas()
    @QtCore.Slot()
    def fishdown(self):
        self.photos[self.listwidget.currentItem().path].dfish(-1)
        self.items[self.listwidget.currentItem().path].label.setText(
                   self.photos[self.listwidget.currentItem().path].labeltext)
        self.refreshcanvas()
    @QtCore.Slot()
    def fishoff(self):
        self.photos[self.listwidget.currentItem().path].resetfish()
        self.items[self.listwidget.currentItem().path].label.setText(
                   self.photos[self.listwidget.currentItem().path].labeltext)
        self.refreshcanvas()

    @QtCore.Slot()
    def allkeep(self):
        for path in self.items:
            self.photos[path].keep = True
            self.photos[path].setlabeltext()
            self.items[path].label.setText(self.photos[path].labeltext)
        self.refreshcanvas()

    @QtCore.Slot()
    def nonekeep(self):
        for path in self.items:
            self.photos[path].keep = False
            self.photos[path].setlabeltext()
            self.items[path].label.setText(self.photos[path].labeltext)
        self.refreshcanvas()

    @QtCore.Slot()
    def allsmugmug(self):
        for path in self.items:
            self.photos[path].smugmug = True
            self.photos[path].setlabeltext()
            self.items[path].label.setText(self.photos[path].labeltext)
        self.refreshcanvas()

    @QtCore.Slot()
    def nonesmugmug(self):
        for path in self.items:
            self.photos[path].smugmug = False
            self.photos[path].setlabeltext()
            self.items[path].label.setText(self.photos[path].labeltext)
        self.refreshcanvas()

    @QtCore.Slot()
    def allraw(self):
        for path in self.items:
            if self.photos[path].rawpath:
                self.photos[path].keepraw = True
                self.photos[path].setlabeltext()
                self.items[path].label.setText(self.photos[path].labeltext)
        self.refreshcanvas()

    @QtCore.Slot()
    def noneraw(self):
        for path in self.items:
            self.photos[path].keepraw = False
            self.photos[path].setlabeltext()
            self.items[path].label.setText(self.photos[path].labeltext)
        self.refreshcanvas()

    @QtCore.Slot()
    def allcat1(self):
        for path in self.items:
            self.photos[path].categorised = True
            self.photos[path].category = 1
            self.photos[path].setlabeltext()
            self.items[path].label.setText(self.photos[path].labeltext)
        self.refreshcanvas()

    @QtCore.Slot()
    def nonecat(self):
        for path in self.items:
            self.photos[path].categorised = False
            self.photos[path].category = 0
            self.photos[path].setlabeltext()
            self.items[path].label.setText(self.photos[path].labeltext)
        self.refreshcanvas()

    def keyPressEvent(self, event):
        currpath = self.listwidget.currentItem().path
        keyval = event.key()
        if keyval == QtCore.Qt.Key_Escape:
            self.canvas.rubberBand.hide()
            self.photos[currpath].crop = False
            self.photos[currpath].setlabeltext()
            self.items[currpath].label.setText(self.photos[currpath].labeltext)
        if keyval >= QtCore.Qt.Key_F1 and keyval <= QtCore.Qt.Key_F12:
            self.photos[currpath].setcategory((1 + keyval - QtCore.Qt.Key_F1)%12)
            self.photos[currpath].setlabeltext()
            self.items[currpath].label.setText(self.photos[currpath].labeltext)

    def refreshcanvas(self):
        if self.refreshing:
            self.refreshwaiting = True
        else:
            self.dorefreshcanvas()

    def dorefreshcanvas(self):
        self.refreshwaiting = False
        self.refreshing = True
        try:
            path = self.listwidget.currentItem().path
            self.image = self.photos[path].preview.copy()
            if not self.photos[path].keep:
#                self.image = self.image.convert(mode="L")
                contrastadjuster = ImageEnhance.Contrast(self.image)
                self.image = contrastadjuster.enhance(0.2)
            elif self.photos[self.listwidget.currentItem().path].brightcontrast:
                bfactor = self.photos[path].brightcontrast[0]
                cfactor = self.photos[path].brightcontrast[1]
                brightnessadjuster = ImageEnhance.Brightness(self.image)
                self.image = brightnessadjuster.enhance(bfactor)
                contrastadjuster = ImageEnhance.Contrast(self.image)
                self.image = contrastadjuster.enhance(cfactor)
            if self.photos[path].fish:
                self.image = fishwarppil(self.image, level=self.photos[path].fish)
            if self.photos[path].theta:
                scaledsize = (round(self.photos[path].thetascale*self.photos[path].previewwidth),
                              round(self.photos[path].thetascale*self.photos[path].previewheight))
                self.image = self.image.resize(scaledsize, resample=Image.BICUBIC).rotate(
                                      self.photos[path].theta, resample=Image.BICUBIC, expand=True)
            self.qimage = ImageQt.ImageQt(self.image)
            self.pixmap = QtGui.QPixmap.fromImage(self.qimage)
            self.canvas.setPixmap(self.pixmap)
            self.canvas.rubberBand.hide()
            if self.photos[self.listwidget.currentItem().path].crop:
                self.canvas.rect = self.photos[self.listwidget.currentItem().path].croprect
                self.canvas.redraw()
#         if self.photos[self.listwidget.currentItem().path].rotate:   # future: rotated preview

#        if self.dorefreshcanvas():
#            self.dorefreshcanvas()

        except AttributeError:
            print('Refreshcanvas attribute error', flush=True)
            self.canvas.setPixmap(self.canvasbackgroundimage)
            self.canvas.rubberBand.hide()
        finally:
            self.refreshing = False


    @QtCore.Slot(QtWidgets.QListWidgetItem, QtWidgets.QListWidgetItem)
    def on_item_changed(self, curr, prev):
        photo = self.photos[curr.path]
        try:
            self.refreshcanvas()
            timestring = photo.time.strftime("%Y-%m-%d %H:%M:%S") if photo.time else '<no date>'
            self.statusmessage('{} taken {} using {}'.format(
                               photo.filename, timestring,
                               photo.model if photo.model else '<no camera>'))
            # exif = Exif(curr.path)
            # x = exif.time
            # print(type(exif.datetime),type(exif.digtime),type(exif.origtime),readdatetaken(curr.path    ))
            # timestring = "dt{},digt{},ot{}".format(
            #     exif.datetime.strftime("%Y-%m-%d %H:%M:%S") if exif.datetime else '-',
            #     exif.digtime.strftime("%Y-%m-%d %H:%M:%S") if exif.digtime else '-',
            #     exif.origtime.strftime("%Y-%m-%d %H:%M:%S") if exif.origtime else '-'
            # )
            self.statusmessage('{} taken {} using {}'.format(
                               photo.filename, timestring,
                               photo.model if photo.model else '<no camera>'))
        except Exception as e:
            print('ee', photo.filename, e, flush=True)
#         self.requestfullres.emit(curr.path)
#         if curr.path != self.fullrespath:
#             self.fullres = None

    @QtCore.Slot(str, object)
    def receivefullres(self, path, fullresphoto):
        if path == self.listwidget.currentItem().path:
            self.fullrespath = path
            self.fullres = fullresphoto

    @QtCore.Slot()
    def filemove(self):
        if self.remaining:
            self.statusmessage("Wait until load completed....")
            return
        if not os.path.exists(self.outdir):
            os.mkdir(self.outdir)
        if not os.path.exists(self.outdir + '\\raw'):
            os.mkdir(self.outdir + '\\raw')
        if not os.path.exists(self.outdir + '\\postedit'):
            os.mkdir(self.outdir + '\\postedit')
        if not os.path.exists(self.outdir + '\\pano'):
            os.mkdir(self.outdir + '\\pano')
        if not os.path.exists(self.outdir + '\\smugmug'):
            os.mkdir(self.outdir + '\\smugmug')
        if not os.path.exists(self.outdir + '\\reject'):
            os.mkdir(self.outdir + '\\reject')
        self.statusmessage("Queuing jobs")
        for path, photo in self.photos.items():
            if photo.categorised and not os.path.exists(self.outdir + '\\{:X}'.format(photo.category)):
                os.mkdir(self.outdir + '\\{:X}'.format(photo.category))
            if photo.keep:
                job = {'path':path, 'rawpath':photo.rawpath, 'theta':photo.theta, 'thetascale':photo.thetascale,
                       'keepraw':photo.keepraw, 'crop':photo.crop, 'croprect':photo.croprect, 'scale':photo.scale,
                       'rotangle':photo.rotangle, 'postedit':photo.postedit, 'pano':photo.pano, 'cat':photo.category,
                       'smugmug':photo.smugmug, 'brightcontrast':photo.brightcontrast, 'fish':photo.fish, 'reject':False}
                self.submitfilemove.emit(job)
                time.sleep(.1)
            else:
                job = {'path':path, 'reject':True}
                self.submitfilemove.emit(job)
                time.sleep(.1)

    def closeEvent(self, event):  # reimplementation of parent method (which just closes window)
        self.worker.close()
        self.workerthread.terminate()
        print('Done.', flush=True)
        event.accept()


def main(imfolder):
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    screensize = app.desktop().screenGeometry().size()
    canvassize = (screensize.width() - 470, screensize.height() - 200)
    main_window = PhotoUI(imfolder, canvassize=canvassize)   # -ve processes means threads
    sys.exit(app.exec_())


# class PhotoBee(QtWidgets.QMainWindow):
#     def __init__(self):
#         super().__init__()
#         self.init_ui()

#     def init_ui(self):
#         self.setWindowTitle('photobee')
#         self.show()

