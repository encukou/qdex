#!/usr/bin/env python
# Encoding: UTF-8

"""Part of qdex: a Pokédex using PySide and veekun's pokedex library.

A query models for pokémon
"""

from PySide import QtGui, QtCore
Qt = QtCore.Qt

class PokemonDelegate(QtGui.QStyledItemDelegate):
    """Delegate for a Pokémon

    Shows summary information when the group of forms is collapsed.
    """
    def __init__(self, view):
        super(PokemonDelegate, self).__init__()
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
        super(PokemonDelegate, self).paint(painter, option, index)

    def sizeHint(self, option, index):
        hint = super(PokemonDelegate, self).sizeHint
        summaryHint = hint(option, self.indexToShow(index, True))
        return hint(option, index).expandedTo(summaryHint)

class PokemonNameDelegate(PokemonDelegate):
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

