#!/usr/bin/env python
# Encoding: UTF-8

"""Part of qdex: a Pokédex using PySide and veekun's pokedex library.

Query builder
"""

from sqlalchemy.orm import aliased

class QueryBuilder(object):
    """Helps build a query while avoiding duplicate tables.

    Attributes (and __init__ args):
    `query`: he query being built, can be modified directly
    'mappedClass`: the mapped class that's being selected from the query
    """
    def __init__(self, query, mappedClass, _relations=None, _query=None):
        self.mappedClass = mappedClass
        # _relations is a dict that maps relationship keys to (mapped class,
        # sub-_relations) tuples
        if _relations is None:
            self._relations = {}
        else:
            self._relations = _relations
        # Sub-builders need to be able to modify the query, so store it
        # in a shared one-element list.
        self._query = _query or [query]

    @property
    def query(self):
        """Get the query"""
        return self._query[0]

    @query.setter
    def query(self, newQuery):
        """Set the query"""
        self._query[0] = newQuery

    def join(self, relation, foreignClass):
        """Join the relation to an alias of targetClass, return the alias

        Modifies the query.
        If this relation was joined in already, return the existing alias.
        """
        return self.joinOn(relation, lambda *a: relation, foreignClass)

    def joinOn(self, key, onFactory, foreignClass,
            secondary=None, secondaryOnFactory=None,
        ):
        """Join an alias of foreignClass, return the alias

        Modifies the query.
        `key`: a unique key identifying the particular join. If the key was
            already used, the pre-existing alias is returned.
        `onFactory`: a function that takes the aliased table and returns a
            relation or where-clause to join on
        `secondary`, secondaryJoinFactory: Can be used for a intermediary
            table. If present, each onFactory will receive two arguments:
            the aliased foreignClass and the intermediary alias.
        """
        try:
            return self._relations[key][0]
        except KeyError:
            aliasedClass = aliased(foreignClass)
            self._relations[key] = aliasedClass, {}
            if secondary is not None:
                aliasedSecondary = secondary.alias()
                self.query = self.query.outerjoin((
                        aliasedSecondary,
                        secondaryOnFactory(aliasedClass, aliasedSecondary),
                    ))
                self.query = self.query.outerjoin((
                        aliasedClass,
                        onFactory(aliasedClass, aliasedSecondary),
                    ))
            else:
                self.query = self.query.outerjoin((
                        aliasedClass,
                        onFactory(aliasedClass),
                    ))
            return aliasedClass

    def subbuilder(self, relation, foreignClass, **kwargs):
        """Make a new builder that operates on a joined class
        """
        aliasedClass = self.join(relation, foreignClass, **kwargs)
        return QueryBuilder(None, aliasedClass,
                _relations=self._relations[relation][1], _query=self._query)

    def subbuilderOn(self, key, onFactory, foreignClass, **kwargs):
        """As subbuilder, but joins using joinOn
        """
        aliasedClass = self.joinOn(key, onFactory, foreignClass, **kwargs)
        return QueryBuilder(None, aliasedClass,
                _relations=self._relations[key][1], _query=self._query)

    def setIncluded(self, key, foreignClass):
        """Mark foreignClass as already included in the builder, under key.

        Useful for SQLA's joined-loaded properties
        """
        self._relations[key] = foreignClass, {}
