#!/usr/bin/env python
# Encoding: UTF-8

"""Part of qdex: a Pokédex using PySide and veekun's pokedex library.

A sort clause model
"""

from PySide import QtCore, QtGui
Qt = QtCore.Qt

from qdex.querybuilder import QueryBuilder

class ColumnIndices(object):
    name = 0
    order = 1

    _count = 2

class SortModel(QtCore.QAbstractItemModel):
    """A model that keeps track of sort criteria
    """
    collapsingPossible = False
    _pagesize = 1000

    def __init__(self, queryModel, clauses):
        super(SortModel, self).__init__()
        self.clauses = clauses
        self.queryModel = queryModel
        self.g = queryModel.g
        self.g.registerRetranslate(self.allDataChanged)

    def allDataChanged(self):
        """Called when all of the data is changed, e.g. retranslated"""
        self.dataChanged.emit(
                self.index(0, 0),
                self.index(self.rowCount() - 1, self.columnCount() - 1),
            )
        self.headerDataChanged.emit(Qt.Horizontal, 0, self.columnCount() - 1)

    def columnCount(self, parent=QtCore.QModelIndex()):
        if parent.isValid():
            return 0
        else:
            return ColumnIndices._count

    def data(self, index, role=Qt.DisplayRole):
        clause = self.clauses[index.row()]
        if role == Qt.UserRole:
            return clause
        if index.column() == ColumnIndices.name:
            column = clause.column
            if column:
                return column.headerData(role, self.queryModel)
            else:
                if role == Qt.DisplayRole:
                    return clause.name
        elif index.column() == ColumnIndices.order:
            if role == Qt.DisplayRole:
                if clause.descending:
                    return u'↑'
                else:
                    return u'↓'

    def index(self, row, column=0, parent=QtCore.QModelIndex()):
        if isinstance(row, int):
            if not parent.isValid():
                if 0 <= row < self.rowCount() and 0 <= column < self.columnCount():
                    return self.createIndex(row, column)
        else:
            return self.clauses.index(row)

    def rowCount(self, parent=QtCore.QModelIndex()):
        if parent.isValid():
            return 0
        else:
            return len(self.clauses)

    def parent(self, index):
        return QtCore.QModelIndex()

    def clear(self):
        while self.clauses:
            del self[len(self) - 1]

    # List-like methods

    def __iter__(self): return iter(self.clauses)
    def __getitem__(self, i): return self.clauses[i]
    def __len__(self): return len(self.clauses)

    def append(self, clause):
        builder = QueryBuilder(self.queryModel.baseQuery,
                self.queryModel.mappedClass)
        # Remove overridden clauses
        while True:
            # To prevent problems with list index reordering, we remove one
            # clause at a time.
            for i, existingClause in enumerate(self.clauses):
                if existingClause.overrides(clause, builder):
                    del self[i]
                    break
            else:
                # All overridden clauses removed; add the new one
                self.beginInsertRows(QtCore.QModelIndex(),
                        len(self.clauses), len(self.clauses))
                self.clauses.append(clause)
                self.endInsertRows()
                return

    def __setitem__(self, index, clause):
        self.clauses[index] = clause
        self.dataChanged.emit(self.index(index, 0),
                self.index(index, self.columnCount() - 1))

    def __delitem__(self, index):
        self.beginRemoveRows(QtCore.QModelIndex(), index, index)
        del self.clauses[index]
        self.endRemoveRows()

    def replace(self, old, new):
        self[self.clauses.index(old)] = new

    def remove(self, clause):
        del self[self.clauses.index(clause)]

    def increase_priority(self, clause, amount=1):
        index = self.clauses.index(clause)
        del self[index]
        index += amount
        if index < 0: index = 0
        if index >= len(self): index = len(self)
        self.beginInsertRows(QtCore.QModelIndex(), index, index)
        self.clauses.insert(index, clause)
        self.endInsertRows()

    def decrease_priority(self, clause, amount=1):
        self.increase_priority(clause, -amount)
