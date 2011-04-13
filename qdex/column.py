#!/usr/bin/env python
# Encoding: UTF-8

"""Part of qdex: a Pokédex using PySide and veekun's pokedex library.

A query models for pokémon
"""

from PySide import QtGui, QtCore
Qt = QtCore.Qt

from sqlalchemy.sql.expression import and_

from pokedex.db import tables, media

from qdex.delegate import PokemonDelegate
from qdex.loadableclass import LoadableMetaclass

from qdex.sortclause import (SimpleSortClause, GameStringSortClause,
        LocalStringSortClause, ForeignKeySortClause, AssociationListSortClause)

from qdex.pokedexhelpers import getTranslationClass

class ModelColumn(object):
    """A column in a query model
    """
    __metaclass__ = LoadableMetaclass

    def __init__(self, name, model, identifier=None, mappedClass=None):
        self.name = name
        self.model = model
        if mappedClass is None:
            self.mappedClass = self.model.mappedClass
        else:
            self.mappedClass = mappedClass

    def headerData(self, role, model):
        """Data used for the column header"""
        if role == Qt.DisplayRole:
            return model.g.translator(self.name)

    def data(self, item, role):
        """Data for `item`"""
        return NotImplementedError

    def delegate(self, view):
        """Return a delegate for this column, using the given view"""
        return QtGui.QStyledItemDelegate()

    def collapsedData(self, forms, role):
        """Return a summary of data from all `forms`. Used for pokémon columns.
        """
        allData = [self.data(form, role) for form in forms]
        if all(data == allData[0] for data in allData[1:]):
            return allData[0]
        else:
            if role == Qt.DisplayRole:
                return '...'

    def save(self):
        """Return __init__ kwargs needed to reconstruct self"""
        return dict(name=self.name)

    def getSortClause(self, descending=True, **kwargs):
        """Get a SortClause that corresponds to this column & given args
        """
        raise NotImplementedError

    def orderColumns(self, builder):
        """Return key(s) that are used to order this column.
        Order clauses referencing the same keys are redundant.

        May return an iterable.

        Usually (for SimpleSortClause), these are ORM column properties.
        """
        raise NotImplementedError

class SimpleModelColumn(ModelColumn):
    """A pretty dumb column that just gets an attribute and displays it
    """
    def __init__(self, attr, name=None, **kwargs):
        if name is None:
            name = attr
        ModelColumn.__init__(self, name=name, **kwargs)
        self.attr = attr

    def data(self, item, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return getattr(item, self.attr)

    def save(self):
        representation = super(SimpleModelColumn, self).save()
        representation['attr'] = self.attr
        return representation

    def getSortClause(self, descending=False):
        return SimpleSortClause(self, descending)

    def orderColumns(self, builder):
        return [getattr(builder.mappedClass, self.attr)]

ModelColumn.defaultClassForLoad = SimpleModelColumn

class GameStringColumn(SimpleModelColumn):
    """A column to display data translated to the game language
    """
    def __init__(self, attr, model, translationClass=None, **kwargs):
        SimpleModelColumn.__init__(self, model=model, attr=attr, **kwargs)
        self.translationClass = getTranslationClass(self.mappedClass, attr)

    def getSortClause(self, descending=False):
        return GameStringSortClause(self, descending)

class LocalStringColumn(ModelColumn):
    """A column to display data translated to the UI language
    """
    def __init__(self, attr, name=None, **kwargs):
        if name is None:
            name = attr
        ModelColumn.__init__(self, name=name, **kwargs)
        self.attr = attr
        self.mapAttr = attr + '_map'
        self.translationClass = getTranslationClass(self.mappedClass, attr)

    def data(self, item, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            translations = getattr(item, self.mapAttr)
            for language in self.languages:
                try:
                    translation = translations[language]
                except KeyError:
                    continue
                else:
                    if translation:
                        return translation
            if self.mapAttr == 'name_map':
                # For maps, fall back to identifiers
                return '[%s]' % item.identifier
            else:
                return '[???]'

    @property
    def languages(self):
        """The UI languages, by order of precedence
        """
        return self.model.g.languages

    def save(self):
        representation = super(LocalStringColumn, self).save()
        representation['attr'] = self.attr
        return representation

    def getSortClause(self, descending=False):
        return LocalStringSortClause(self, descending)

    def orderColumns(self, builder):
        return [getattr(builder.mappedClass, self.mapAttr)]

class ForeignKeyColumn(SimpleModelColumn):
    """A proxy column that gives information about a foreign key column.

    `foreignColumn` is a column for the referenced table
    """
    def __init__(self, foreignColumn, foreignMappedClass=None, **kwargs):
        SimpleModelColumn.__init__(self, **kwargs)
        attr = self.attr
        if foreignMappedClass is None:
            for column in self.mappedClass.__table__.c:
                if column.name == attr + '_id':
                    (foreignKey, ) = column.foreign_keys
                    table = foreignKey.column.table
                    for cls in tables.mapped_classes:
                        if cls.__table__ == table:
                            foreignMappedClass = cls
                            break
                    else:
                        raise AssertionError('Table %s not found' % table.name)
                    break
            else:
                raise ValueError("Column %s_id not found" % attr)
        self.foreignColumn = ModelColumn.load(foreignColumn,
                mappedClass=foreignMappedClass, model=self.model)

    def data(self, item, role=Qt.DisplayRole):
        return self.foreignColumn.data(getattr(item, self.attr), role)

    def delegate(self, view):
        return self.foreignColumn.delegate(view)

    def save(self):
        representation = super(ForeignKeyColumn, self).save()
        representation['foreignColumn'] = self.foreignColumn.save()
        return representation

    def getSortClause(self, descending=True, **kwargs):
        return ForeignKeySortClause(self, descending, **kwargs)

    def orderColumns(self, builder):
        subbuilder = builder.subbuilder(
                getattr(builder.mappedClass, self.attr),
                self.foreignColumn.mappedClass,
            )
        return self.foreignColumn.orderColumns(subbuilder)

class PokemonColumn(ForeignKeyColumn):
    """A proxy column that gives information about a pokémon through its form.
    """
    def __init__(self, **kwargs):
        ForeignKeyColumn.__init__(self, foreignMappedClass=tables.Pokemon,
                attr='form_base_pokemon', **kwargs)

class AssociationListColumn(SimpleModelColumn):
    """A proxy column that gives information about an AssociationProxy.

    `foreignColumn` is a column for the referenced table

    `orderAttr` is an attribute on the linking class by which the values are
    ordered.
    `orderValues` are the values of orderAttr that the column gets sorted by.
    """
    def __init__(self, orderAttr, orderValues, separator, foreignColumn,
            foreignMappedClass=None, **kwargs):
        SimpleModelColumn.__init__(self, **kwargs)
        self.orderAttr = orderAttr
        self.orderValues = orderValues
        self.separator = separator
        # XXX: A better way to get stuff from the relation?
        relation = getattr(self.mappedClass, self.attr)
        self.secondaryTable = relation.property.secondary
        foreignMappedClass = relation.property.mapper.class_
        # Find the proper columns... this ain't that nice :(
        for column in relation.property.secondary.c:
            if column.foreign_keys:
                (foreignKey,) = column.foreign_keys
                if foreignKey.column.table == self.mappedClass.__table__:
                    self.primaryColumnName = column.name
                elif foreignKey.column.table == foreignMappedClass.__table__:
                    self.secondaryColumnName = column.name
        # Check that we did get them
        assert all((self.primaryColumnName, self.secondaryColumnName))
        self.foreignColumn = ModelColumn.load(foreignColumn,
                mappedClass=foreignMappedClass, model=self.model)

    def data(self, item, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            subitems = getattr(item, self.attr)
            data = [self.foreignColumn.data(si, role) for si in subitems]
            return self.separator.join(str(d) for d in data)

    def orderColumns(self, builder):
        for subbuilder in self.getOrderSubbuilders(builder):
            for column in self.foreignColumn.orderColumns(subbuilder):
                yield column

    def getOrderSubbuilders(self, builder):
        """Get a sub-builder for each item in the list we're ordering by
        """
        for i, value in enumerate(self.orderValues):
            subbuilder = builder.subbuilderOn(
                    (self, i),
                    lambda aliasedClass, aliasedSecondary: and_(
                            aliasedSecondary.c[self.secondaryColumnName] ==
                                    aliasedClass.id,
                        ),
                    self.foreignColumn.mappedClass,
                    secondary = self.secondaryTable,
                    secondaryOnFactory = lambda aliasedClass,
                        aliasedSecondary: and_(
                            aliasedSecondary.c[self.primaryColumnName] ==
                                    builder.mappedClass.id,
                            aliasedSecondary.c[self.orderAttr] == value,
                        ),
                )
            yield subbuilder

    def getSortClause(self, descending=True, **kwargs):
        return AssociationListSortClause(self, descending, **kwargs)

class PokemonNameColumn(SimpleModelColumn):
    """Display the pokémon name & icon"""
    delegate = PokemonDelegate

    def __init__(self, **kwargs):
        SimpleModelColumn.__init__(self,
                attr='name', mappedClass=tables.Pokemon, **kwargs)

    def data(self, form, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            g = self.model.g
            formName = g.name(form)
            if formName:
                return u'{0} {1}'.format(formName, form.form_base_pokemon.name)
            else:
                return form.form_base_pokemon.name
        elif role == Qt.DecorationRole:
            if self.model._hack_small_icons:
                # XXX: A hack to make the delegate think the icon is smaller
                # than it really is
                return QtGui.QPixmap(32, 24)
            try:
                key = "flipped pokemon icon/%s" % form.id
                pixmap = QtGui.QPixmap()
                if not QtGui.QPixmapCache.find(key, pixmap):
                    pixmap.load(media.PokemonFormMedia(form).icon().path)
                    transform = QtGui.QTransform.fromScale(-1, 1)
                    pixmap = pixmap.transformed(transform)
                    QtGui.QPixmapCache.insert(key, pixmap)
                return pixmap
            except ValueError:
                return QtGui.QPixmap(media.UnknownPokemonMedia().icon().path)

    def collapsedData(self, forms, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return "{name} ({forms})".format(
                    name=forms[0].pokemon.name,
                    forms=len(forms),
                )
        else:
            return self.data(forms[0], role)

    def orderColumns(self, builder):
        subbuilder = builder.subbuilder(
                builder.mappedClass.form_base_pokemon,
                tables.Pokemon,
            )
        names = builder.join(
                subbuilder.mappedClass.names_local,
                tables.Pokemon.names_table,
            )
        return [names.name]
