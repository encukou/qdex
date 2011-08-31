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
        QtGui.QTreeView.__init__(self, *args)
        self.setUniformRowHeights(True)
        self.setAnimated(True)
        self.setIndentation(0)
        self.setRootIsDecorated(False)
        self.setSortingEnabled(True)

        self.header().setContextMenuPolicy(Qt.CustomContextMenu)
        self.header().customContextMenuRequested.connect(
                self.showHeaderContextMenu)

        # Enlarge (hopefully) the minimum column width to the size of
        # a pokémon icon (with a tad of extra padding).
        self.header().setMinimumSectionSize(max(
                QtGui.QApplication.globalStrut().width(),
                34,
            ))

    def setModel(self, model):
        if self.model():
            self.model().disconnect(self)

        # Qt remembers which column the view is sorted by, and tries to restore
        # the sort. We don't want that, and neither do we want to un-sort the
        # previous model, so set model to None and un-sort the view.
        super(QueryView, self).setModel(None)
        self.sortByColumn(-1, Qt.AscendingOrder)

        self.g = model.g
        super(QueryView, self).setModel(model)
        model.columnsInserted.connect(self.columnsChanged)
        model.columnsRemoved.connect(self.columnsChanged)
        model.columnsMoved.connect(self.columnsChanged)
        model.modelReset.connect(self.columnsChanged)
        self.columnsChanged()
        for i in range(self.model().columnCount()):
            self.autoResizeColumn(i)

    def autoResizeColumn(self, columnIndex):
        """Resize the column with the given index to some reasonable size

        The point is to not read all the data in the column
        """
        # XXX: Better initial size of columns?
        model = self.model()
        lastRow = self.model().rowCount() - 1
        options = self.viewOptions()
        index = model.index(0, columnIndex)
        delegate = self.itemDelegate(index)
        width = max(
                delegate.sizeHint(options, idx).width()
                for idx in (index, model.index(lastRow, columnIndex))
            ) * 3 / 2
        self.setColumnWidth(columnIndex, width)

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
            if columnIndex != 0:
                name = column.headerData(Qt.DisplayRole, self.model())
                action = menu.addAction(_(u'Remove column {0}').format(name))
                remove = lambda: model.removeColumn(columnIndex)
                action.triggered.connect(remove)
                menu.addSeparator()
        # XXX: Move the table's column groups to the model
        group = defaultColumnGroups.get(model.tableName)
        if group:
            def insertColumn(columnGroup):
                """Insert the column from the given columnGroup"""
                model.insertQueryColumn(
                        columnIndex + 1,
                        columnGroup.getColumn(model=model),
                    )
                if columnIndex == self.model().columnCount() - 2:
                    # We added a column after the last (stretchable) one.
                    # Let's be helpful and stretch the ex-last column to some
                    # reasonable size.
                    self.autoResizeColumn(columnIndex)
            buildColumnMenu(self.g, menu, group, _(u'Add {0} Column'),
                    lambda columnGroup: lambda: insertColumn(columnGroup))
        menu.exec_(self.header().mapToGlobal(pos))

