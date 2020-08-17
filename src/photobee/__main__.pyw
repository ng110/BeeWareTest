# -*- coding: utf-8 -*-
"""
# Created on Dec 6 2016

@author: Neil.Griffin
"""

import sys
from PyQt5 import QtGui, QtCore
from photogui import PhotoUI
#from ng import getmachine

testpath = r'C:\Users\ng110\Pictures\Pictures\XX Gunton Dec15'

def main(paths=None):
    """The main routine."""
    if paths is None:
        if len(sys.argv) > 1:
#            paths = sys.argv[1:]
            paths = sys.argv[1]
        else:
            paths = testpath
    app = QtGui.QApplication(sys.argv)
    ui = PhotoUI(paths, processes=-20, imsize=(1200,900))   # -ve processes means threads
    app.exec_()


if __name__ == '__main__':
    main()

