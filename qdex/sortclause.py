#!/usr/bin/env python
# Encoding: UTF-8

"""Part of qdex: a Pokédex using PySide and veekun's pokedex library.

A sort clause for query models
"""

from sqlalchemy.sql.expression import and_, case
from sqlalchemy.orm import aliased
from pokedex.db import tables
from pokedex.db.multilang import default_language_param

from qdex.loadableclass import LoadableMetaclass

class SortClause(object):
    """A sort clause to be attached to a view
    """
    __metaclass__ = LoadableMetaclass

    def __init__(self, column, descending=False):
        self.column = column
        self.descending = descending

    def save(self):
        """Get this clause's representation as a simple dict
        """
        representation = dict(column=self.column.save())
        if self.descending:
            representation['descending'] = True
        return representation

    def sortedQuery(self, query):
        """Return `query` ordered by this clause
        """
        raise NotImplementedError

    def orderColumns(self):
        """Return DB the columns used by this clause
        """
        return self.column.orderColumns()

    def overrides(self, other):
        """Return True if this clause overrides the other one.
        """
        selfOrderColumns = set(self.orderColumns())
        otherOrderColumns = set(other.orderColumns())
        return selfOrderColumns >= otherOrderColumns

class SimpleSortClause(SortClause):
    """Simply sorts by the associated column's orderColumns
    """
    def __init__(self, column, descending=False):
        SortClause.__init__(self, column, descending)

    def sortedQuery(self, query):
        for column in self.orderColumns():
            if self.descending:
                query = query.order_by(column.desc())
            else:
                query = query.order_by(column.asc())
        return query

class DefaultPokemonSortClause(SimpleSortClause):
    """Default sort clause for Pokemon: pokemon.order and form.id
    """
    def __init__(self, descending=False):
        SimpleSortClause.__init__(self, None, descending)

    def sortedQuery(self, query):
        """Return `query` ordered by this clause
        """
        return query.order_by(tables.Pokemon.order, tables.PokemonForm.id)

    def orderColumns(self):
        """Return DB the columns used by this clause
        """
        return [tables.Pokemon.order, tables.PokemonForm.id]

class GameStringSortClause(SortClause):
    """Translated-message sort clause for strings in the "game language"
    """
    def sortedQuery(self, query):
        mappedClass = self.column.mappedClass
        translationClass = self.column.translationClass
        dbcolumn = getattr(translationClass, self.column.attr)
        query = query.join((translationClass, and_(
                translationClass.foreign_id == mappedClass.id,
                translationClass.local_language_id == default_language_param,
            )))
        if self.descending:
            query = query.order_by(dbcolumn.desc())
        else:
            query = query.order_by(dbcolumn.asc())
        return query

class LocalStringSortClause(SortClause):
    """Translated-message sort clause for strings in the "UI language(s)"
    """
    def sortedQuery(self, query):
        column = self.column
        mappedClass = column.mappedClass
        translationClass = column.translationClass
        attr = column.attr
        whens = []
        for language in column.languages:
            aliasedTable = aliased(translationClass, name='user_alias')
            query = query.outerjoin((aliasedTable, and_(
                    aliasedTable.foreign_id == mappedClass.id,
                    aliasedTable.local_language == language,
                )))
            aliasedColumn = getattr(aliasedTable, attr)
            whens.append((aliasedColumn != None, aliasedColumn))
        if attr == 'name':
            default = mappedClass.identifier
        else:
            default = None
        if self.descending:
            return query.order_by(case(whens, else_=default).desc())
        else:
            return query.order_by(case(whens, else_=default).asc())

class ForeignKeySortClause(SortClause):
    """Proxy sort clause, for use with a ForeignKeyColumn
    """
    def __init__(self, column, descending=False, **kwargs):
        SortClause.__init__(self, column, descending)
        self.foreignClause = self.column.foreignColumn.getSortClause(
                descending=self.descending, **kwargs)

    def sortedQuery(self, query):
        query = query.join(getattr(self.column.mappedClass, self.column.attr))
        return self.foreignClause.sortedQuery(query)


