#!/usr/bin/env python
# Encoding: UTF-8

"""Part of qdex: a Pokédex using PySide and veekun's pokedex library.

A query models for pokémon
"""

from PySide import QtGui, QtCore
Qt = QtCore.Qt

from pokedex.db import media

from qdex.delegate import PokemonDelegate, PokemonNameDelegate

availableColumns = {}

class ModelColumnMetaclass(type):
    """Metaclass to automatically register columns in availableColumns by name
    """
    def __init__(cls, *args):
        super(ModelColumnMetaclass, cls).__init__(*args)
        assert cls.classname not in availableColumns, (
                'Column name %s is already taken' % cls.classname
            )
        availableColumns[cls.classname] = cls

    @property
    def classname(cls):
        """Return this column's class name, a key for availableColumns
        """
        return cls.__name__

class ModelColumn(object):
    """A column in a query model
    """
    __metaclass__ = ModelColumnMetaclass
    _is_qdex_column = True

    def __init__(self, name):
        self.name = name

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
        """Return a "safe-YAML-able" representation of this column

        See SimpleModelColumn for an example of how to extend this.
        """
        return {
                'class': self.classname,
                'name': self.name,
            }

    @staticmethod
    def load(representation):
        """Load a column from a representation

        The representation can either be something returned from save(),
        or an existing column object (in which case it's just returned).
        """
        try:
            # Copy the dict, since we'll be modifying it
            representation = dict(representation)
        except TypeError:
            # Oops, not a dict. Must be a column object then
            assert representation._is_qdex_column
            return representation
        else:
            try:
                cls = availableColumns[representation.pop('class')]
            except KeyError:
                # Make it easier to embed literal column descriptions
                cls = availableColumns[representation.pop('class_')]
            return cls(**representation)

class SimpleModelColumn(ModelColumn):
    """A pretty dumb column that just gets an attribute and displays it
    """
    def __init__(self, attr, name=None, **kwargs):
        if name is None:
            name = attr
        super(SimpleModelColumn, self).__init__(name=name, **kwargs)
        self.attr = attr

    def data(self, item, index, role):
        if role == Qt.DisplayRole:
            return getattr(item, self.attr)

    def save(self):
        representation = super(SimpleModelColumn, self).save()
        representation['attr'] = self.attr
        return representation

class PokemonNameColumn(ModelColumn):
    """Display the pokémon name & icon"""
    delegate = PokemonDelegate

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

class PokemonTypeColumn(ModelColumn):
    """Display the pokémon type/s"""
    delegate = PokemonNameDelegate

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
