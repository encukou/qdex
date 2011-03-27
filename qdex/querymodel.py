#!/usr/bin/env python
# Encoding: UTF-8

"""Part of qdex: a Pokédex using PySide and veekun's pokedex library.

Query models
"""

from PySide import QtCore, QtGui
Qt = QtCore.Qt

class ModelColumn(object):
    """A column in a query model
    """
    def __init__(self, name):
        self.name = name

    def headerData(self, role):
        """Data used for the column header"""
        if role == Qt.DisplayRole:
            return self.name

    def data(self, item, index, role):
        """Data for `item`"""

    @staticmethod
    def delegate(view):
        """Return a delegate for this column, using the given view"""
        return QtGui.QStyledItemDelegate()

class SimpleModelColumn(ModelColumn):
    """A pretty dumb column that just gets an attribute and displays it
    """
    def __init__(self, attr, name=None, **kwargs):
        if name is None:
            name = attr
        super(SimpleModelColumn, self).__init__(name=name, **kwargs)
        self.attr = attr

    def data(self, item, index, role):
        if role == Qt.DisplayRole:
            return getattr(item, self.attr)

class QueryModel(QtCore.QAbstractItemModel):
    """A model that displays an ORM query, with a set of custom columns.

    Can be queried the Python way, (with []).
    """
    collapsingPossible = False
    _pagesize = 100

    def __init__(self, query, columns):
        super(QueryModel, self).__init__()
        self.baseQuery = query
        self.columns = columns
        self.filters = []
        self._setQuery()

    def _setQuery(self):
        """Called every time the query changes"""
        self._query = self.baseQuery
        self._rows = int(self._query.count())
        self.pages = [None] * (self._rows / self._pagesize + 1)

    def __getitem__(self, i):
        pageno, offset = divmod(i, self._pagesize)
        page = self.pages[pageno]
        if not page:
            start = pageno * self._pagesize
            end = (pageno + 1) * self._pagesize
            page = self.pages[pageno] = self._query[start:end]
        return page[offset]

    def columnCount(self, parent=QtCore.QModelIndex()):
        return len(self.columns)

    def data(self, index, role):
        item = self.itemForIndex(index)
        if item:
            return self.columns[index.column()].data(item, index, role)

    def itemForIndex(self, index):
        """Returns the item that corresponds to the given index"""
        if index.isValid() and not index.parent().isValid():
            return self[index.row()]

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal:
            return self.columns[section].headerData(role)

    def index(self, row, column, parent=QtCore.QModelIndex()):
        if not parent.isValid():
            if 0 <= row < self.rowCount() and 0 <= column < self.columnCount():
                return self.createIndex(row, column)

    def rowCount(self, parent=QtCore.QModelIndex()):
        if not parent.isValid():
            return self._rows
        else:
            return 0

    def parent(self, index):
        return QtCore.QModelIndex()
