#!/usr/bin/env python
# Encoding: UTF-8

"""Part of qdex: a Pokédex using PySide and veekun's pokedex library.

A sort clause for query models
"""

import copy

from sqlalchemy.sql.expression import and_, case
from pokedex.db import tables

from qdex.loadableclass import LoadableMetaclass
from qdex.pokedexhelpers import default_language_param

class SortClause(object):
    """A sort clause to be attached to a view
    """
    __metaclass__ = LoadableMetaclass
    collapsing = 1

    def __init__(self, column, descending=False, collapsing=None):
        self.column = column
        self.descending = descending
        if collapsing:
            self.collapsing = collapsing

    @property
    def name(self):
        if self.column:
            return self.column.name
        else:
            return '?'

    def save(self):
        """Get this clause's representation as a simple dict
        """
        representation = dict(column=self.column.save())
        if self.descending:
            representation['descending'] = True
        return representation

    def sort(self, builder):
        """Sort the query in the given QueryBuilder
        """
        for column in tuple(self.orderColumns(builder)):
            if self.descending:
                order = column.desc().nullslast()
            else:
                order = column.asc().nullsfirst()
            builder.query = builder.query.order_by(order)

    def orderColumns(self, builder):
        """Return DB columns used by the clause based on the given Builder
        """
        return self.column.orderColumns(builder)

    def overrides(self, other, builder):
        """Return True if this clause overrides the other one.
        """
        selfOrderColumns = set(self.orderColumns(builder))
        otherOrderColumns = set(other.orderColumns(builder))
        return selfOrderColumns >= otherOrderColumns

    def other_direction(self):
        """Return a clause with the opposite sorting direction
        """
        new = copy.copy(self)
        new.descending = not new.descending
        return new

class SimpleSortClause(SortClause):
    """Simply sorts by the associated column's orderColumns
    """
    pass

class DefaultPokemonSortClause(SimpleSortClause):
    """Default sort clause for PokemonForm: pokemon.order and form.id
    """
    collapsing = 2

    def __init__(self, descending=False):
        SimpleSortClause.__init__(self, None, descending)

    def orderColumns(self, builder):
        """Return DB the columns used by this clause
        """
        pokemon = builder.join(builder.mappedClass.pokemon,
                tables.Pokemon)
        return [pokemon.order]

class PokemonNameSortClause(SortClause):
    collapsing = 2

    def sort(self, builder):
        """Sort the query in the given QueryBuilder
        """
        species_name, form_name, form_identifier = self.orderColumns(builder)
        if self.descending:
            builder.query = builder.query.order_by(species_name.desc())
            builder.query = builder.query.order_by(form_identifier != None)
            builder.query = builder.query.order_by(form_name.desc())
        else:
            builder.query = builder.query.order_by(species_name.asc())
            builder.query = builder.query.order_by(form_identifier == None)
            builder.query = builder.query.order_by(form_name.asc())

class GameStringSortClause(SortClause):
    """Translated-message sort clause for strings in the "game language"
    """
    def sort(self, builder):
        translationClass = self.column.translationClass
        onFactory = lambda translationClass: and_(
                translationClass.foreign_id == builder.mappedClass.id,
                translationClass.local_language_id == default_language_param,
            )
        translationClass = builder.joinOn('message', onFactory,
                translationClass)
        dbcolumn = getattr(translationClass, self.column.attr)
        if self.descending:
            builder.query = builder.query.order_by(dbcolumn.desc().nullslast())
        else:
            builder.query = builder.query.order_by(dbcolumn.asc().nullsfirst())

class LocalStringSortClause(SortClause):
    """Translated-message sort clause for strings in the "UI language(s)"
    """
    def sort(self, builder):
        column = self.column
        translationClass = column.translationClass
        attr = column.attr
        whens = []
        for language in column.languages:
            key = ('translation', translationClass, language)
            onFactory = lambda aliasedTable: and_(
                    aliasedTable.foreign_id == builder.mappedClass.id,
                    aliasedTable.local_language == language,
                )
            aliasedTable = builder.joinOn(key, onFactory, translationClass)
            aliasedColumn = getattr(aliasedTable, attr)
            whens.append((aliasedColumn != None, aliasedColumn))
        if attr == 'name':
            default = builder.mappedClass.identifier
        else:
            default = None
        query = builder.query
        if self.descending:
            order = case(whens, else_=default).desc().nullslast()
        else:
            order = case(whens, else_=default).asc().nullsfirst()
        query = query.order_by(order)
        builder.query = query

class BaseForeignSortClause(SortClause):
    def other_direction(self):
        other = super(BaseForeignSortClause, self).other_direction()
        other.foreignClause = other.foreignClause.other_direction()
        return other

class ForeignKeySortClause(BaseForeignSortClause):
    """Proxy sort clause, for use with a ForeignKeyColumn

    Set `join` to True to disable joining the proxied class
    """
    def __init__(self, column, descending=False, **kwargs):
        SortClause.__init__(self, column, descending)
        self.foreignClause = self.column.foreignColumn.getSortClause(
                descending=self.descending, **kwargs)

    def sort(self, builder):
        subbuilder = builder.subbuilder(
                getattr(builder.mappedClass, self.column.attr),
                self.column.foreignColumn.mappedClass,
            )
        self.foreignClause.sort(subbuilder)

class AssociationListSortClause(BaseForeignSortClause):
    """Proxy sort clause, for use with a ForeignKeyColumn

    Set `join` to True to disable joining the proxied class
    """
    def __init__(self, column, descending=False, **kwargs):
        SortClause.__init__(self, column, descending)
        self.foreignClause = self.column.foreignColumn.getSortClause(
                descending=self.descending, **kwargs)

    def sort(self, builder):
        for subbuilder in self.column.getOrderSubbuilders(builder):
            self.foreignClause.sort(subbuilder)
