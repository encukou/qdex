#!/usr/bin/env python
# Encoding: UTF-8

"""Part of qdex: a Pokédex using PySide and veekun's pokedex library.

The main pokédex window
"""

import os

from pkg_resources import resource_filename
from PySide import QtCore, QtGui
Qt = QtCore.Qt

from forrin.translator import BaseTranslator
from pokedex.db import connect, tables

from qdex.queryview import QueryView
from qdex.metamodel import MetaModel, MetaModelView

class Translator(BaseTranslator):
    """Our very own translator"""
    pass

class Global(object):
    """Global options for stuff"""
    def __init__(self, session=None, translator=None, languages=None):
        self.session = session or connect()
        self.languages = languages or ['en']
        self.translator = translator or Translator(self.languages)

class MainWindow(QtGui.QMainWindow):
    """The main pokédex window"""
    def __init__(self, **globalArgs):
        super(MainWindow, self).__init__()
        self.g = Global(**globalArgs)
        self.populateMenu()
        self.setWindowTitle(u'Pokédex')
        icon = resource_filename('pokedex', u'data/media/items/poké-ball.png')
        self.setWindowIcon(QtGui.QIcon(icon))

        splitter = QtGui.QSplitter(self)
        self.setCentralWidget(splitter)

        metaview = MetaModelView(self)
        metaview.setModel(MetaModel(self.g))
        splitter.addWidget(metaview)

        self.mainlistview = QueryView()
        splitter.addWidget(self.mainlistview)

        metaview.selectionModel().currentChanged.connect(lambda index:
                metaview.model().setModelOnView(index, self.mainlistview)
            )
        metaview.selectionModel().select(
                metaview.model().defaultIndex(),
                QtGui.QItemSelectionModel.ClearAndSelect,
            )

        self.resize(800, 600)

        # XXX: The min-size resizing should be done with default data shown,
        # and custom collapsed
        metaview.resizeColumnToContents(0)
        metaview.setMinimumWidth(metaview.columnWidth(0))
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setCollapsible(1, False)
        splitter.setSizes([1, 1])
        splitter.setCollapsible(0, True)


    def populateMenu(self):
        """Populate the app's main menu"""
        _ = self.g.translator
        self.menuBar().clear()
        fileMenu = self.menuBar().addMenu(_(u"&Pokédex"))
        icon = QtGui.QIcon(resource_filename('qdex', 'icons/cross-button.png'))
        self.addMenuItem(fileMenu, '&Exit', QtGui.QApplication.exit, icon=icon)

    def addMenuItem(self, menu, name, action, icon=None):
        """Convenience method to add a menu item to a menu"""
        qaction = QtGui.QAction(name, self)
        qaction.triggered.connect(action)
        if icon:
            qaction.setIcon(icon)
        menu.addAction(qaction)
