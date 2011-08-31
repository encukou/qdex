#!/usr/bin/env python
# Encoding: UTF-8

"""Part of qdex: a Pokédex using PySide and veekun's pokedex library.

Runner module.
"""

import sys
import os.path
from PySide import QtCore, QtGui
Qt = QtCore.Qt

import pkg_resources

media_root = os.path.join(pkg_resources.resource_filename('pokedex', '.'),
        '..', '..', 'pokedex-media')

def resource_filename(package, *path):
    if package == 'pokedex-media':
        return os.path.join(media_root, *path)
    else:
        return pkg_resources.resource_filename(package, *path)

from qdex.mainwindow import MainWindow

def main():
    app = QtGui.QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
