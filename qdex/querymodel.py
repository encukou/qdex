#!/usr/bin/env python
# Encoding: UTF-8

"""Part of qdex: a Pokédex using PySide and veekun's pokedex library.

Query models
"""

from PySide import QtCore, QtGui
Qt = QtCore.Qt
from sqlalchemy.orm import contains_eager, lazyload
from pokedex.db import tables
import traceback

from qdex.column import ModelColumn
from qdex.loadableclass import LoadableMetaclass
from qdex.sortclause import DefaultPokemonSortClause

class ModelMetaclass(LoadableMetaclass, type(QtCore.QAbstractItemModel)):
    """Merged metaclass"""
    pass

class BaseQueryModel(QtCore.QAbstractItemModel):
    """A model that displays an ORM query, with a set of custom columns.

    Can be queried the Python way, (with []).
    """
    collapsingPossible = False
    _pagesize = 100
    __metaclass__ = ModelMetaclass

    def __init__(self, g, mappedClass, query, columns, defaultSortClause=None):
        super(BaseQueryModel, self).__init__()
        self.g = g
        self.mappedClass = mappedClass
        self.g.registerRetranslate(self.allDataChanged)
        self.baseQuery = query
        self.columns = []
        for column in columns:
            try:
                self.columns.append(ModelColumn.load(column, model=self))
            except Exception:
                traceback.print_exc()
                print 'Failed to load column:', column
        if defaultSortClause is None:
            self.defaultSortClause = self.columns[0].getSortClause()
        else:
            self.defaultSortClause = defaultSortClause
        self.sortClauses = [self.defaultSortClause]
        self.filters = []
        self._setQuery()

    def _setQuery(self):
        """Called every time the query changes"""
        self._query = self.baseQuery
        for clause in reversed(self.sortClauses):
            self._query = clause.sortedQuery(self._query)
        self._rows = int(self._query.count())
        self.pages = [None] * (self._rows // self._pagesize + 1)

    def allDataChanged(self):
        """Called when all of the data is changed, e.g. retranslated"""
        self._setQuery()
        self.dataChanged.emit(
                self.index(0, 0),
                self.index(self.rowCount() - 1, self.columnCount() - 1),
            )
        self.headerDataChanged.emit(Qt.Horizontal, 0, self.columnCount() - 1)

    def __getitem__(self, i):
        pageno, offset = divmod(i, self._pagesize)
        page = self.pages[pageno]
        if not page:
            start = pageno * self._pagesize
            end = (pageno + 1) * self._pagesize
            print start, end
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
            return self.columns[section].headerData(role, self)

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

    def save(self):
        """Can't save a query directly"""
        raise AssertionError("Can't save a BaseQueryModel")

    def removeColumns(self, column, count, parent=QtCore.QModelIndex()):
        if not parent.isValid():
            last = column + count - 1
            if column == 0:
                # Can't remove the first column
                column += 1
                last -= 1
                if column == last:
                    return False
            self.beginRemoveColumns(QtCore.QModelIndex(), column, last)
            del self.columns[column:last + 1]
            self.endRemoveColumns()
            return True

    def insertQueryColumn(self, position, column):
        """Insert a ModelColumn at the specified position

        Qt's normal column-inserting API doesn't work: it doesn't specify
        the column to be inserted.
        """
        self.beginInsertColumns(QtCore.QModelIndex(), position, position)
        self.columns.insert(position, column)
        self.endInsertColumns()

    def sort(self, columnIndex, order=Qt.AscendingOrder):
        newClauses = []
        if columnIndex == -1:
            pass
        else:
            column = self.columns[columnIndex]
            descending = (order == Qt.DescendingOrder)
            sortClause = column.getSortClause(descending=descending)
            for clause in self.sortClauses:
                if not sortClause.overrides(clause):
                    newClauses.append(clause)
            newClauses.append(sortClause)
        if newClauses != self.sortClauses:
            QtGui.QApplication.setOverrideCursor(QtGui.QCursor(Qt.WaitCursor))
            try:
                self.layoutAboutToBeChanged.emit()
                self.sortClauses = newClauses
                self._setQuery()
                self.layoutChanged.emit()
            finally:
                QtGui.QApplication.restoreOverrideCursor()

class TableModel(BaseQueryModel):
    """Model that displays a DB table"""
    def __init__(self, g, table, columns):
        if isinstance(table, basestring):
            tableName = table
            for cls in tables.mapped_classes:
                if cls.__name__ == table:
                    break
            else:
                raise AssertionError('%s is not a valid table name' % tableName)
        else:
            tableName = table.__name__
            cls = table
        self.tableName = tableName
        query = g.session.query(cls)
        super(TableModel, self).__init__(g, cls, query, columns)

    def save(self):
        return dict(
                table=self.tableName,
                columns=[column.save() for column in self.columns],
            )

class PokemonModel(BaseQueryModel):
    """Pokémon query model

    Argh, forms >:/

    We want to:
    - if there are no filters/orders that could affect different forms
        differently, collapse *all* forms. (2)
        These would be pokédex IDs, name, species, flavor, etc.
    - otherwise if there aren't filters/orders that only affect
        functionally-different forms, collapse the æsthetic forms. (1)
        These exclude color, and Pokéathlon stats...
    - otherwise, don't collapse anything at all. (0)
    Picture/form name can always be collapsed.
    """
    _pagesize = 100
    def __init__(self, g, columns):
        mappedClass = tables.PokemonForm
        query = g.session.query(mappedClass)
        query = query.join(
                (tables.Pokemon, tables.PokemonForm.form_base_pokemon)
            )
        query = query.options(contains_eager('form_base_pokemon'))
        query = query.options(lazyload('form_base_pokemon.names'))
        BaseQueryModel.__init__(self, g, mappedClass, query, columns,
                defaultSortClause=DefaultPokemonSortClause())
        self.tableName = 'Pokemon'
        self._hack_small_icons = False

    def _setQuery(self):
        super(PokemonModel, self)._setQuery()
        self.collapsing = 2  # XXX: Depend on sort/order
        if self.collapsing == 2:
            countquery = self._query.from_self(tables.Pokemon.identifier)
            self._rows = int(countquery.distinct().count())
            self.collapseKey = lambda pf: pf.pokemon.identifier
        elif self.collapsing == 1:
            countquery = self._query.from_self(tables.Pokemon.id)
            self._rows = int(countquery.distinct().count())
            self.collapseKey = lambda pf: pf.pokemon.id
        else:
            # self._rows set by superclass
            self.collapseKey = lambda pf: pf.pokemon.id
        self.items = []
        self.nextindex = 0
        self.collapsed = {}

    def __getitem__(self, i):
        if not self.collapsing:
            return super(PokemonModel, self).__getitem__(i)
        while len(self.items) <= i + 1:
            try:
                nextitem = super(PokemonModel, self).__getitem__(self.nextindex)
            except IndexError:
                break
            else:
                self.nextindex += 1
                key = self.collapseKey(nextitem)
                if key in self.collapsed:
                    self.collapsed[key].append(nextitem)
                else:
                    self.items.append(nextitem)
                    self.collapsed[key] = []
        return self.items[i]

    def index(self, row, column, parent=QtCore.QModelIndex()):
        if 0 <= column < self.columnCount():
            if not parent.isValid():
                if 0 <= row < self.rowCount():
                    return self.createIndex(row, column, -1)
            else:
                if -1 <= row < self.rowCount(parent):
                    return self.createIndex(row, column, parent.row())
        return QtCore.QModelIndex()

    def rowCount(self, parent=QtCore.QModelIndex()):
        if not parent.isValid():
            return self._rows
        elif parent.internalId() == -1:
            key = self.collapseKey(self[parent.row()])
            return len(self.collapsed[key])
        else:
            return 0

    def data(self, index, role):
        if index.row() >= 0:
            return super(PokemonModel, self).data(index, role)
        else:
            item = self[index.internalId()]
            items = [item] + self.collapsed[self.collapseKey(item)]
            column = self.columns[index.column()]
            return column.collapsedData(items, index, role)

    def parent(self, index):
        iid = index.internalId()
        if iid == -1:
            return QtCore.QModelIndex()
        else:
            return self.createIndex(int(iid), 0, -1)

    def itemForIndex(self, index):
        if index.isValid():
            iid = index.internalId()
            if iid == -1:
                return self[index.row()]
            else:
                key = self.collapseKey(self.items[iid])
                return self.collapsed[key][index.row()]

    def save(self):
        return dict(
                columns=[column.save() for column in self.columns],
            )
