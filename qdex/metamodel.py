#!/usr/bin/env python
# Encoding: UTF-8

"""Part of qdex: a Pokédex using PySide and veekun's pokedex library.

Metamodel: Contains other models
"""

from pkg_resources import resource_filename

from PySide import QtCore, QtGui
Qt = QtCore.Qt
from forrin.translator import _

from qdex.querymodel import QueryModel, PokemonModel
from qdex.column import SimpleModelColumn, PokemonNameColumn, PokemonTypeColumn

from pokedex.db import tables

# XXX: Move the default contents somewhere else

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
    model = None

    def __init__(self, name, icon=None, children=None, g=None, **kwargs):
        self.parent = None
        self.icon = icon
        self.name = name
        self.g = g
        self.children = children or []
        self.kwargs = kwargs
        for child in self.children:
            child.parent = self

    def data(self, model, role):
        """Return the data to display for this item

        For Qt.UserRole return self
        """
        if role == Qt.DisplayRole:
            return self.g.translator(self.name)
        elif role == Qt.DecorationRole:
            return self.icon
        elif role == Qt.UserRole:
            return self

class PokemonItem(MetamodelItem):
    """Item for the pokémon list
    """
    @property
    def model(self):
        try:
            return self._model
        except AttributeError:
            self._model = PokemonModel(self.g, [
                    dict(class_='PokemonNameColumn', name=_(u'Pokémon', context='pokemon column name')), dict(class_='PokemonTypeColumn', name=_(u'Type', context='pokemon column name')),
                ])
        return self._model

class QueryItem(MetamodelItem):
    """Item for a query list
    """
    @property
    def model(self):
        try:
            return self._model
        except AttributeError:
            self._model = QueryModel(self.g, self.g.session.query(self.kwargs['table']), [
                    dict(class_='SimpleModelColumn', attr='id'), dict(class_='SimpleModelColumn', attr='name'),
                ])
        return self._model

class MetaModel(QtCore.QAbstractItemModel):
    """A model containing shortcuts to models the pokédex can display
    """
    def __init__(self, g):
        super(MetaModel, self).__init__()
        self.g = g
        # XXX: Need better icons!!!
        folder_icon = QtGui.QIcon(resource_filename('qdex',
                'icons/folder-horizontal.png'))
        pokemon_icon = QtGui.QIcon(resource_filename('pokedex',
                u'data/media/items/poké-ball.png'))
        move_icon = QtGui.QIcon(resource_filename('pokedex',
                u'data/media/items/tm-normal.png'))
        type_icon = QtGui.QIcon(resource_filename('qdex',
                u'icons/diamond.png'))
        ability_icon = QtGui.QIcon(resource_filename('qdex',
                u'icons/color.png'))
        item_icon = QtGui.QIcon(resource_filename('pokedex',
                u'data/media/items/rare-candy.png'))
        nature_icon = QtGui.QIcon(resource_filename('qdex',
                u'icons/smiley-cool.png'))
        self.root = MetamodelItem('_root', children=[
                MetamodelItem(_(u'Standard lists'), icon=folder_icon, children=[
                        PokemonItem(_(u'Pokémon'), icon=pokemon_icon, g=g),
                        QueryItem(_(u'Moves'), icon=move_icon, g=g, table=tables.Move),
                        QueryItem(_(u'Types'), icon=type_icon, g=g, table=tables.Type),
                        QueryItem(_(u'Abilities'), icon=ability_icon, g=g, table=tables.Ability),
                        QueryItem(_(u'Items'), icon=item_icon, g=g, table=tables.Item),
                        QueryItem(_(u'Natures'), icon=nature_icon, g=g, table=tables.Nature),
                    ]),
            ])
        # XXX: Only have one category of lists now; show a flat list
        # (update defaultIndex when this changes)
        self.root = self.root.children[0]

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
