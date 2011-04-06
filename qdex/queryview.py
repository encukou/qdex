#!/usr/bin/env python
# Encoding: UTF-8

"""Part of qdex: a Pokédex using PySide and veekun's pokedex library.

Views for displaying the query models
"""

from PySide import QtCore, QtGui
Qt = QtCore.Qt

from qdex.columngroup import defaultColumnGroups, buildColumnMenu

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

        self.header().setContextMenuPolicy(Qt.CustomContextMenu)
        self.header().customContextMenuRequested.connect(
                self.showHeaderContextMenu)

    def setModel(self, model):
        if self.model():
            self.model().disconnect(self)
        self.g = model.g
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

    def showHeaderContextMenu(self, pos):
        """Show a context menu when the header is right-clicked"""
        _ = self.g.translator
        model = self.model()
        menu = QtGui.QMenu()
        columnIndex = self.columnAt(pos.x())
        try:
            column = model.columns[columnIndex]
        except IndexError:
            pass
        else:
            name = column.headerData(Qt.DisplayRole, self.model())
            action = menu.addAction(_(u'Remove column {0}').format(name))
            action.triggered.connect(lambda: model.removeColumn(columnIndex))
            menu.addSeparator()
        # XXX: Move the table's column groups to the model
        group = defaultColumnGroups.get(model.tableName)
        if group:
            buildColumnMenu(self.g, menu, group, _(u'Add {0} Column'),
                lambda column: lambda: model.insertColumn(columnIndex, column))
        menu.exec_(self.header().mapToGlobal(pos))

