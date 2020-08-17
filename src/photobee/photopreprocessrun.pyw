    # -*- coding: utf-8 -*-
"""
Created on Tue Oct 18 09:24:39 2016

@author: Neil.Griffin
"""

import sys
from PyQt5 import QtWidgets
#import imp
#photopreprocess = imp.load_source('photopreprocess v0.3', 'photopreprocess v0.3.py')
import photogui
from ng import machine

#imfolder=r"P:\ST\Aykroyd NG1 C61187\Measurement\photos intray"

if __name__ == '__main__':
    paths = sys.argv[1:]
    paths = sys.argv[1]
    app = QtWidgets.QApplication(sys.argv)
    screensize = app.desktop().screenGeometry().size()
    canvassize = (screensize.width() - 470, screensize.height() - 200)
    ui = photogui.PhotoUI(paths, canvassize=canvassize)   # -ve processes means threads
    app.exec_()
#    sys.exit(app.exec_())
    