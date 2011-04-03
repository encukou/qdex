#!/usr/bin/env python
# Encoding: UTF-8

"""Part of qdex: a Pokédex using PySide and veekun's pokedex library.

A query models for pokémon
"""

from sqlalchemy.orm import contains_eager, lazyload

from PySide import QtCore, QtGui
Qt = QtCore.Qt
from forrin.translator import _

from pokedex.db import tables, media

from qdex.querymodel import QueryModel, ModelColumn

class PokemonItemDelegate(QtGui.QStyledItemDelegate):
    """Delegate for a Pokémon

    Shows summary information when the group of forms is collapsed.
    """
    def __init__(self, view):
        super(PokemonItemDelegate, self).__init__()
        self.view = view

    def indexToShow(self, index, summary=None):
        """Get the index to show instead of this one

        summary can be True to show the all-forms summary information (if
            the row is expandable at all), False to show the notmal data,
            or None to choose based on the state of the view

        It's not too easy to hijack the QItemDelegate pipeling with custom
        data, so we hack around this by storing the summary in a child with
        row -1 (which isn't accessible from normal views), and switching to
        that when necessary.
        """
        if summary is False:
            return index
        parent = index.sibling(index.row(), 0)
        hasChildren = index.model().hasChildren(parent)
        if summary is None:
            summary = hasChildren and not self.view.isExpanded(parent)
        if summary and hasChildren:
            return parent.child(-1, index.column())
        else:
            return index

    def paint(self, painter, option, index):
        index = self.indexToShow(index)
        super(PokemonItemDelegate, self).paint(painter, option, index)

    def sizeHint(self, option, index):
        hint = super(PokemonItemDelegate, self).sizeHint
        summaryHint = hint(option, self.indexToShow(index, True))
        return hint(option, index).expandedTo(summaryHint)

class PokemonColumn(ModelColumn):
    """Column for the Pokemon model

    The main thing about these is that they have to worry about collapsing.
    """
    collapsing = 0
    delegate = PokemonItemDelegate

    def collapsedData(self, forms, index, role):
        """Return a summary of data from all `forms`
        """
        return self.data(forms[0], index, role)

class PokemonNameDelegate(PokemonItemDelegate):
    """Delegate for the Pokémon icon/name column"""
    def sizeHint(self, option, index):
        option.decorationSize = QtCore.QSize(0, 0)
        self.view.model()._hack_small_icons = True
        hint = super(PokemonNameDelegate, self).sizeHint(option, index)
        self.view.model()._hack_small_icons = False
        return hint

    def paint(self, painter, option, index):
        option.decorationAlignment = Qt.AlignBottom | Qt.AlignHCenter
        super(PokemonNameDelegate, self).paint(painter, option, index)

class PokemonNameColumn(PokemonColumn):
    """Display the pokémon name & icon"""
    collapsing = 2
    delegate = PokemonNameDelegate

    def __init__(self, **kwargs):
        super(PokemonNameColumn, self).__init__(name=_('Name'), **kwargs)

    def data(self, form, index, role):
        if role == Qt.DisplayRole:
            g = index.model().g
            formName = g.name(form)
            if formName:
                return u'{0} {1}'.format(formName, form.form_base_pokemon.name)
            else:
                return form.form_base_pokemon.name
        elif role == Qt.DecorationRole:
            if index.model()._hack_small_icons:
                # XXX: A hack to make the delegate think the icon is smaller
                # than it really is
                return QtGui.QPixmap(32, 24)
            try:
                key = "flipped pokemon icon/%s" % form.id
                pixmap = QtGui.QPixmap()
                if not QtGui.QPixmapCache.find(key, pixmap):
                    pixmap.load(form.media.icon().path)
                    transform = QtGui.QTransform.fromScale(-1, 1)
                    pixmap = pixmap.transformed(transform)
                    QtGui.QPixmapCache.insert(key, pixmap)
                return pixmap
            except ValueError:
                return QtGui.QPixmap(media.PokemonMediaById(0).icon().path)

    def collapsedData(self, forms, index, role):
        if role == Qt.DisplayRole:
            return "{name} ({forms})".format(
                    name=forms[0].pokemon.name,
                    forms=len(forms),
                )
        else:
            return self.data(forms[0], index, role)

class PokemonTypeColumn(PokemonColumn):
    """Display the pokémon type/s"""
    collapsing = 2
    def __init__(self, **kwargs):
        super(PokemonTypeColumn, self).__init__(name=_('Type'), **kwargs)

    def data(self, form, index, role):
        if role == Qt.DisplayRole:
            g = index.model().g
            return '/'.join(g.name(t) for t in form.pokemon.types)
        elif role == Qt.UserRole:
            return form.pokemon.types

    def collapsedData(self, forms, index, role=Qt.UserRole):
        if role == Qt.UserRole:
            typesFirst = forms[0].pokemon.types
            typesFirstSet = set(typesFirst)
            typesOther = [f.pokemon.types for f in forms[1:]]
            commonTypes = typesFirstSet.intersection(*typesOther)
            allTypes = typesFirstSet.union(*typesOther)
            extraTypes = allTypes - commonTypes
            commonTypes = sorted(commonTypes, key=typesFirst.index)
            if extraTypes:
                commonTypes.append(None)
            return commonTypes
        elif role == Qt.DisplayRole:
            g = index.model().g
            types = self.collapsedData(forms, index)
            return '/'.join(g.name(t) if t else '...' for t in types)
        else:
            return self.data(forms[0], index, role)

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
    def __init__(self, g, columns):
        query = g.session.query(tables.PokemonForm)
        query = query.join(
                (tables.Pokemon, tables.PokemonForm.form_base_pokemon)
            )
        query = query.options(contains_eager('form_base_pokemon'))
        query = query.options(lazyload('form_base_pokemon.names'))
        query = query.order_by(tables.Pokemon.order, tables.PokemonForm.id)
        super(PokemonModel, self).__init__(g, query, columns)
        self._hack_small_icons = False

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
