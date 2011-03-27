#!/usr/bin/env python
# Encoding: UTF-8

"""Part of qdex: a Pokédex using PySide and veekun's pokedex library.

A query models for pokémon
"""

from sqlalchemy.orm import contains_eager, lazyload

from PySide import QtCore, QtGui
Qt = QtCore.Qt

from pokedex.db import tables, media

from qdex.querymodel import QueryModel, ModelColumn

class PokemonColumn(ModelColumn):
    """Column for the Pokemon model

    The main thing about these is that they have to worry about collapsing.
    """
    collapsing = 0

class PokemonNameColumn(PokemonColumn):
    """Display the pokémon name & icon"""
    collapsing = 2
    def __init__(self, **kwargs):
        super(PokemonNameColumn, self).__init__(name='Name', **kwargs)

    def data(self, form, role):
        if role == Qt.DisplayRole:
            return form.pokemon_name
        elif role == Qt.DecorationRole:
            try:
                return QtGui.QPixmap(form.media.icon().path)
            except ValueError:
                return QtGui.QPixmap(media.PokemonMediaById(0).icon().path)
        elif role == Qt.SizeHintRole:
            return QtCore.QSize(32, 32)  # XXX: Do 24x24, with a cool Delegate

class PokemonTypeColumn(PokemonColumn):
    """Display the pokémon type/s"""
    collapsing = 2
    def __init__(self, **kwargs):
        super(PokemonTypeColumn, self).__init__(name='Type', **kwargs)

    def data(self, form, role):
        if role == Qt.DisplayRole:
            return '/'.join(t.name for t in form.pokemon.types)

class PokemonModel(QueryModel):
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
    def __init__(self, session, columns):
        query = session.query(tables.PokemonForm)
        query = query.join(
                (tables.Pokemon, tables.PokemonForm.form_base_pokemon)
            )
        query = query.options(contains_eager('form_base_pokemon'))
        query = query.options(lazyload('form_base_pokemon.texts'))
        query = query.order_by(tables.Pokemon.order, tables.PokemonForm.id)
        super(PokemonModel, self).__init__(query, columns)

    def _setQuery(self):
        self._query = self.baseQuery
        count = int(self._query.count())
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
            self._rows = int(count)
            self.collapseKey = lambda pf: pf.pokemon.id
        self.pages = [None] * (count / self._pagesize + 1)
        self.items = []
        self.nextindex = 0
        self.collapsed = {}

    def __getitem__(self, i):
        if not self.collapsing:
            return super(PokemonModel, self).__getitem__(i)
        while len(self.items) <= i:
            print i
            nextitem = super(PokemonModel, self).__getitem__(self.nextindex)
            self.nextindex += 1
            key = self.collapseKey(nextitem)
            if key in self.collapsed:
                self.collapsed[key].append(nextitem)
            else:
                self.items.append(nextitem)
                self.collapsed[key] = []
        return self.items[i]

    def index(self, row, column, parent=QtCore.QModelIndex()):
        if not parent.isValid():
            return self.createIndex(row, column, -1)
        else:
            return self.createIndex(row, column, parent.row())

    def rowCount(self, parent=QtCore.QModelIndex()):
        if not parent.isValid():
            return self._rows
        elif parent.internalId() == -1:
            key = self.collapseKey(self.items[parent.row()])
            return len(self.collapsed[key])
        else:
            return 0

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
