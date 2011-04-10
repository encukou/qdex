#!/usr/bin/env python
# Encoding: UTF-8

"""Part of qdex: a Pokédex using PySide and veekun's pokedex library.

A query models for pokémon
"""

from PySide import QtGui, QtCore
Qt = QtCore.Qt

from pokedex.db import tables, media

from qdex.delegate import PokemonDelegate, PokemonNameDelegate
from qdex.loadableclass import LoadableMetaclass

from qdex.sortclause import (SimpleSortClause, GameStringSortClause,
        LocalStringSortClause)

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

    def data(self, item, index, role):
        """Data for `item`"""

    @staticmethod
    def delegate(view):
        """Return a delegate for this column, using the given view"""
        return QtGui.QStyledItemDelegate()

    def collapsedData(self, forms, index, role):
        """Return a summary of data from all `forms`. Used for pokémon columns.
        """
        allData = [self.data(form, index, role) for form in forms]
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

    def orderColumns(self):
        """Return key(s) that are used to order this column.
        Order clauses referencing the same keys are redundant.

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

    def data(self, item, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return getattr(item, self.attr)

    def save(self):
        representation = super(SimpleModelColumn, self).save()
        representation['attr'] = self.attr
        return representation

    def getSortClause(self, descending=False):
        return SimpleSortClause(self, descending)

    def orderColumns(self):
        return [getattr(self.model.mappedClass, self.attr)]

ModelColumn.defaultClassForLoad = SimpleModelColumn

def getTranslationClass(mappedClass, attrName):
    for translationClass in mappedClass.translation_classes:
        columns = translationClass.__table__.c
        if any(col.name == attrName for col in columns):
            return translationClass
    else:
        raise ValueError("Translated column %s not found" % attrName)

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

    def data(self, item, index, role=Qt.DisplayRole):
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

    def orderColumns(self):
        return [getattr(self.model.mappedClass, self.mapAttr)]

class PokemonNameColumn(GameStringColumn):
    """Display the pokémon name & icon"""
    delegate = PokemonDelegate

    def __init__(self, **kwargs):
        GameStringColumn.__init__(self,
                attr='name', mappedClass=tables.Pokemon, **kwargs)

    def data(self, form, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            g = self.model.g
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
                    pixmap.load(media.PokemonFormMedia(form).icon().path)
                    transform = QtGui.QTransform.fromScale(-1, 1)
                    pixmap = pixmap.transformed(transform)
                    QtGui.QPixmapCache.insert(key, pixmap)
                return pixmap
            except ValueError:
                return QtGui.QPixmap(media.UnknownPokemonMedia(0).icon().path)

    def collapsedData(self, forms, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return "{name} ({forms})".format(
                    name=forms[0].pokemon.name,
                    forms=len(forms),
                )
        else:
            return self.data(forms[0], index, role)

    def orderColumns(self):
        return [tables.Pokemon.name]

class PokemonTypeColumn(ModelColumn):
    """Display the pokémon type/s"""
    delegate = PokemonNameDelegate

    def data(self, form, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            g = self.model.g
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
