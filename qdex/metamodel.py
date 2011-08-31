#!/usr/bin/env python
# Encoding: UTF-8

"""Part of qdex: a Pokédex using PySide and veekun's pokedex library.

Metamodel: Contains other models
"""

import os.path

from pkg_resources import resource_filename

from PySide import QtCore, QtGui
Qt = QtCore.Qt

from qdex.querymodel import TableModel
from qdex.loadableclass import LoadableMetaclass
from qdex import yaml
from qdex import media_root

def MetaModelView(parent=None):
    """A view for the meta model

    (just a factory function for now)
    """
    view = QtGui.QTreeView(parent)
    view.setHeaderHidden(True)
    view.setRootIsDecorated(False)
    return view

class MetamodelItem(object):
    """Item for the metamodel
    """
    __metaclass__ = LoadableMetaclass

    model = None

    def __init__(self, name, icon=None, children=(), g=None, model=None):
        self.parent = None
        self.icon = icon
        if isinstance(icon, basestring):
            self._icon = QtGui.QIcon(icon)
        elif isinstance(icon, list):
            if icon[0] == 'pokedex-media':
                self._icon = QtGui.QIcon(os.path.join(media_root, *icon[1:]))
            else:
                self._icon = QtGui.QIcon(resource_filename(*icon))
        else:
            #raise AssertionError("Can't set icon directly")
            self._icon = icon
        self.name = name
        self.g = g
        self.children = [MetamodelItem.load(child, g=g) for child in children]
        if model:
            self.model = TableModel.load(model, g=g)
        for child in self.children:
            child.parent = self

    def data(self, model, role):
        """Return the data to display for this item

        For Qt.UserRole return self
        """
        if role == Qt.DisplayRole:
            return self.g.translator(self.name)
        elif role == Qt.DecorationRole:
            return self._icon
        elif role == Qt.UserRole:
            return self

    def save(self):
        """Save to dict"""
        return dict(
                name=self.name,
                icon=self.icon,
                children=[child.save() for child in self.children],
                model=None if self.model is None else self.model.save(),
            )
MetamodelItem.defaultClassForLoad = MetamodelItem

class MetaModel(QtCore.QAbstractItemModel):
    """A model containing shortcuts to models the pokédex can display
    """
    def __init__(self, g, model=None):
        super(MetaModel, self).__init__()
        self.g = g
        self.g.registerRetranslate(self.retranslated)
        if model is None:
            defaultfile = open(resource_filename('qdex', 'metamodel.yaml'))
            model = yaml.load(defaultfile)
        self.root = MetamodelItem.load(model, g=g)
        # XXX: Only have one category of lists now; show a flat list
        self.root = self.root.children[0]

    def retranslated(self):
        """Called when the app is retranslated"""
        self.dataChanged.emit(
                self.index(0, 0),
                self.index(self.rowCount() - 1, self.columnCount() - 1),
            )

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 1

    def data(self, index, role):
        if index.isValid():
            return index.internalPointer().data(self, role)

    def index(self, row, column, parent=QtCore.QModelIndex()):
        if not parent.isValid():
            parent = self.root
        else:
            parent = parent.internalPointer()
        if 0 <= column < self.columnCount():
            return self.createIndex(row, column, parent.children[row])

    def rowCount(self, parent=QtCore.QModelIndex()):
        if not parent.isValid():
            parent = self.root
        else:
            parent = parent.internalPointer()
        return len(parent.children)

    def parent(self, index):
        if index.isValid():
            item = index.internalPointer()
            parent = item.parent
            if item.parent:
                grandparent = parent.parent
                if grandparent:
                    row = grandparent.children.index(parent)
                    return self.createIndex(row, 0, parent)
        return QtCore.QModelIndex()

    def defaultIndex(self):
        """Return the index of the default model

        This is the one shown at startup
        """
        return self.index(0, 0)

    def setModelOnView(self, index, view):
        """Set an index's model (if any) on a view
        """
        self.g.mainwindow.setCursor(QtGui.QCursor(Qt.WaitCursor))
        try:
            model = index.data(Qt.UserRole).model
            if model:
                view.setModel(model)
        finally:
            self.g.mainwindow.unsetCursor()
