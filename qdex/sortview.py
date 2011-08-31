#!/usr/bin/env python
# Encoding: UTF-8

"""Part of qdex: a Pokédex using PySide and veekun's pokedex library.

A sort model view
"""

from PySide import QtCore, QtGui
Qt = QtCore.Qt

from pkg_resources import resource_filename

class SortView(QtGui.QToolBar):
    def __init__(self, *args):
        QtGui.QToolBar.__init__(self, *args)
        self.model = None
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

    def setModel(self, model):
        if self.model:
            self.model.disconnect(self)
        self.model = model
        self.model.rowsInserted.connect(self.rowsInserted)
        self.model.rowsRemoved.connect(self.rowsRemoved)
        self.model.dataChanged.connect(self.dataChanged)
        self.clear()
        if len(self.model):
            for i in range(0, len(self.model)):
                self.rowsInserted(None, i, i)

    def rowsInserted(self, parent, start, end):
        assert start == end, (
                'assuming the sort model only inserts rows one at a time')
        clause = self.model[start]
        if clause.descending:
            arrow = u'↑'
            icon = QtGui.QIcon(resource_filename('qdex', 'icons/sort-alphabet-descending.png'))
        else:
            arrow = u'↓'
            icon = QtGui.QIcon(resource_filename('qdex', 'icons/sort-alphabet.png'))
        text = self.model.data(self.model.index(start, 0))
        action = QtGui.QAction(text, self)
        action.setIcon(icon)
        @action.triggered.connect
        def changeSorting():
            self.model.replace(clause, clause.other_direction())
        if not len(self.actions()):
            self.addWidget(QtGui.QLabel('Sorting:'))
        if start == 0:
            self.addAction(action)
        else:
            self.insertAction(self.actions()[-start], action)

    def rowsRemoved(self, parent, start, end):
        assert start == end, (
                'assuming the sort model only removes rows one at a time')
        self.removeAction(self.actions()[-start - 1])

    def dataChanged(self, topleft, bottomright):
        start = topleft.row()
        assert start == bottomright.row(), (
                'assuming the sort model only changes rows one at a time')
        self.rowsRemoved(None, start, start)
        self.rowsInserted(None, start, start)

