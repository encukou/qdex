#!/usr/bin/env python
# Encoding: UTF-8

"""Part of qdex: a Pokédex using PySide and veekun's pokedex library.

A query models for pokémon
"""

import copy

from PySide import QtGui, QtCore
Qt = QtCore.Qt

from sqlalchemy.sql.expression import and_

from pokedex.db import tables
from pokedex.util import media

from qdex.delegate import PokemonNameDelegate
from qdex.loadableclass import LoadableMetaclass
from qdex import media_root
from qdex.sortclause import (SimpleSortClause, GameStringSortClause,
        LocalStringSortClause, ForeignKeySortClause, AssociationListSortClause,
        PokemonNameSortClause)

from qdex.pokedexhelpers import getTranslationClass

class ModelColumn(object):
    """A column in a query model
    """
    __metaclass__ = LoadableMetaclass

    def __init__(self, name, model, identifier=None, mappedClass=None, baseName=None):
        self.name = name or ''
        if baseName is None:
            self.baseName = name
        else:
            self.baseName = baseName
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
        return self.model.defaultDelegateClass(view)

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
        return dict(name=self.name, baseName=self.baseName)

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

    def getSubcolumns(self, parent):
        return ()

    def replaceSubcolumn(self, orig_column, replacement):
        return self

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
            if item is not None:
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
        if item is None:
            return None
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
    def __init__(self, foreignColumn, foreignMappedClass=None, idAttr=None, **kwargs):
        SimpleModelColumn.__init__(self, **kwargs)
        attr = self.attr
        idAttr = idAttr or attr + '_id'
        if foreignMappedClass is None:
            for column in self.mappedClass.__table__.c:
                if column.name == idAttr:
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
                raise ValueError("Column %s not found" % idAttr)
        self.foreignColumn = ModelColumn.load(foreignColumn,
                mappedClass=foreignMappedClass, model=self.model)

    def data(self, item, role=Qt.DisplayRole):
        return self.foreignColumn.data(getattr(item, self.attr), role)

    def collapsedData(self, items, role=Qt.DisplayRole):
        subitems = [getattr(item, self.attr) for item in items]
        return self.foreignColumn.collapsedData(subitems, role)

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

    def getSubcolumns(self, parent):
        yield self, self.foreignColumn
        for column in self.foreignColumn.getSubcolumns(self):
            yield column

    def replaceSubcolumn(self, orig_column, replacement):
        if self.foreignColumn != orig_column:
            # Not replacing exactly our child column, but the target might be
            # further down the hierarchy
            replacement = self.foreignColumn.replaceSubcolumn(orig_column, replacement)
            if replacement == self.foreignColumn:
                # If no replacement took place, return self unchanged
                return self
        # We need to replace our foreignColumn
        new = copy.copy(self)
        new.foreignColumn = replacement
        _ = self.model.g.translator
        if self.baseName:
            new.name = _(self.baseName) + '.' + _(replacement.name)
        else:
            new.name = replacement.name
        return new

class PokemonColumn(ForeignKeyColumn):
    """A proxy column that gives information about a pokémon from its form.
    """
    def __init__(self, **kwargs):
        foreignMappedClass = kwargs.pop('foreignMappedClass', tables.Pokemon)
        kwargs.setdefault('baseName', '')
        ForeignKeyColumn.__init__(self, foreignMappedClass=foreignMappedClass,
                attr='pokemon', **kwargs)

    def getSortClause(self, descending=True, **kwargs):
        clause = ForeignKeySortClause(self, descending, **kwargs)
        clause.collapsing = 1
        return clause

    def getSubcolumns(self, parent):
        yield parent, self.foreignColumn
        for column in self.foreignColumn.getSubcolumns(parent):
            yield column

class SpeciesColumn(PokemonColumn):
    """A proxy column that gives information about a pokémon species from its form.
    """
    def __init__(self, **kwargs):
        kwargs['foreignColumn'] = {
                'foreignColumn': kwargs['foreignColumn'],
                'class': 'ForeignKeyColumn',
                'attr': 'species',
            }
        PokemonColumn.__init__(self, **kwargs)

    def getSortClause(self, descending=True, **kwargs):
        clause = ForeignKeySortClause(self, descending, **kwargs)
        clause.collapsing = 2
        return clause

class AssociationListColumn(ForeignKeyColumn):
    """A proxy column that gives information about an AssociationProxy.

    `foreignColumn` is a column for the referenced table

    `orderAttr` is an attribute on the linking class by which the values are
    ordered.
    `orderValues` are the values of orderAttr that the column gets sorted by.
    """
    def __init__(self, orderAttr, orderValues, separator, foreignColumn,
            foreignMappedClass=None, **kwargs):
        # XXX: NB: skipping ForeignKeyColumn initialization
        SimpleModelColumn.__init__(self, **kwargs)
        self.orderAttr = orderAttr
        self.orderValues = orderValues
        self.separator = unicode(separator)
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
            return self.separator.join(unicode(d) for d in data)

    def collapsedData(self, items, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and items:
            subdata = []
            for item in items:
                subitems = getattr(item, self.attr)
                subdata.append([self.foreignColumn.data(si, role)
                        for si in subitems])
            firstData = set(subdata[0])
            commonData = set(firstData)
            allData = set(firstData)
            for data in subdata[1:]:
                commonData.intersection_update(data)
                allData.update(data)
            sortedData = sorted(commonData, key=subdata[0].index)
            if allData != commonData:
                sortedData.append('...')
            return self.separator.join(unicode(d) for d in sortedData)

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

    def save(self):
        representation = super(AssociationListColumn, self).save()
        representation['orderAttr'] = self.orderAttr
        representation['orderValues'] = self.orderValues
        representation['separator'] = self.separator
        return representation

class PokemonNameColumn(SimpleModelColumn):
    """Display the pokémon name & icon"""

    def __init__(self, **kwargs):
        mappedClass = kwargs.pop('mappedClass', tables.Pokemon)
        SimpleModelColumn.__init__(self,
                attr='name', mappedClass=mappedClass, **kwargs)

    def data(self, form, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            g = self.model.g
            formName = form.name
            if formName:
                return formName
            else:
                return form.pokemon.name
        elif role == Qt.DecorationRole:
            if self.model._hack_small_icons:
                # XXX: A hack to make the delegate think the icon is smaller
                # than it really is
                return QtGui.QPixmap(32, 24)
            try:
                key = "flipped pokemon icon/%s" % form.id
                pixmap = QtGui.QPixmap()
                if not QtGui.QPixmapCache.find(key, pixmap):
                    pixmap.load(media.PokemonFormMedia(media_root, form).icon().path)
                    transform = QtGui.QTransform.fromScale(-1, 1)
                    pixmap = pixmap.transformed(transform)
                    QtGui.QPixmapCache.insert(key, pixmap)
                return pixmap
            except ValueError:
                return QtGui.QPixmap(media.UnknownPokemonMedia().icon().path)

    def collapsedData(self, forms, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return u"{name} ({forms})".format(
                    name=forms[0].species.name,
                    forms=len(forms),
                )
        else:
            return self.data(forms[0], role)

    def delegate(self, view):
        """Return a delegate for this column, using the given view"""
        return PokemonNameDelegate(view)

    def getSortClause(self, descending=False):
        return PokemonNameSortClause(self, descending)

    def orderColumns(self, builder):
        pokemon_builder = builder.subbuilder(builder.mappedClass.pokemon,
                tables.Pokemon)
        species_builder = pokemon_builder.subbuilder(pokemon_builder.mappedClass.species,
                tables.PokemonSpecies)
        name_builder = species_builder.subbuilder(species_builder.mappedClass.names_local,
                tables.PokemonSpecies.names_table)
        formname_builder = builder.subbuilder(builder.mappedClass.names_local,
                tables.PokemonForm.names_table)
        return [
                name_builder.mappedClass.name,
                formname_builder.mappedClass.form_name,
                builder.mappedClass.form_identifier,
            ]
