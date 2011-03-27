#!/usr/bin/env python
# Encoding: UTF-8

"""Part of qdex: a Pokédex using PySide and veekun's pokedex library.

Views for displaying the query models
"""

from PySide import QtCore, QtGui
Qt = QtCore.Qt

class QueryView(QtGui.QTreeView):
    """A tree-view for displaying query models.

    The main difference from a vanilla QTreeView is that this sets
    column-specific delegates.
    """
    def __init__(self, *args):
        super(QueryView, self).__init__(*args)
        self.setUniformRowHeights(True)
        self.setAnimated(True)
        self.setIndentation(0)
        self.setRootIsDecorated(False)

    def setModel(self, model):
        if self.model():
            self.model().disconnect(self)
        super(QueryView, self).setModel(model)
        self.connect(QtCore.SIGNAL('columnsInserted'), self.columnsChanged)
        self.connect(QtCore.SIGNAL('columnsDeleted'), self.columnsChanged)
        self.connect(QtCore.SIGNAL('columnsMoved'), self.columnsChanged)
        self.connect(QtCore.SIGNAL('modelReset'), self.columnsChanged)
        self.columnsChanged()
        options = self.viewOptions()
        # XXX: Better initial size of columns?
        lastRow = self.model().rowCount() - 1
        for i in range(self.model().columnCount()):
            index = model.index(0, i)
            delegate = self.itemDelegate(index)
            width = max(
                    delegate.sizeHint(options, idx).width()
                    for idx in (index, model.index(lastRow, i))
                ) * 3 / 2
            self.setColumnWidth(i, width)

    def columnsChanged(self):
        """Called when the columns change; re-assigns delegates
        """
        self.delegates = [c.delegate(self) for c in self.model().columns]
        for i, delegate in enumerate(self.delegates):
            self.setItemDelegateForColumn(i, delegate)



