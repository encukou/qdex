#!/usr/bin/env python
# Encoding: UTF-8

"""Part of qdex: a Pokédex using PySide and veekun's pokedex library.

A sort model view
"""

from PySide import QtCore, QtGui
Qt = QtCore.Qt

from pkg_resources import resource_filename

from qdex.columngroup import defaultColumnGroups, buildColumnMenu

class SortView(QtGui.QToolBar):
    def __init__(self, *args):
        QtGui.QToolBar.__init__(self, *args)
        self.model = None
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.setIconSize(QtCore.QSize(16, 16))

    def setModel(self, model):
        if self.model:
            self.model.disconnect(self)
        self.model = model
        self.model.rowsInserted.connect(self.rowsInserted)
        self.model.rowsRemoved.connect(self.rowsRemoved)
        self.model.dataChanged.connect(self.dataChanged)
        self.clear()

        _ = self.model.g.translator
        action = self.addAction(_('Sorting'))
        @action.triggered.connect
        def showMenu():
            menu = QtGui.QMenu()

            group = defaultColumnGroups.get(self.model.queryModel.tableName)
            if group:
                buildColumnMenu(self.model.g, menu, group, _(u'Sort by {0} Column'),
                        lambda columnGroup: lambda: self.model.append(
                            columnGroup.getColumn(model=self.model.queryModel).getSortClause()))

            action = menu.addAction(_('Clear sort'))
            action.setIcon(QtGui.QIcon(resource_filename('qdex', 'icons/cross.png')))
            action.triggered.connect(lambda: self.model.clear())

            menu.exec_(QtGui.QCursor.pos())

        if len(self.model):
            for i in range(0, len(self.model)):
                self.rowsInserted(None, i, i)

    def rowsInserted(self, parent, start, end):
        assert start == end, (
                'assuming the sort model only inserts rows one at a time')
        clause = self.model[start]
        descending_icon = QtGui.QIcon(resource_filename('qdex', 'icons/sort-alphabet-descending.png'))
        ascending_icon = QtGui.QIcon(resource_filename('qdex', 'icons/sort-alphabet.png'))
        if clause.descending:
            icon = descending_icon
            other_icon = ascending_icon
        else:
            icon = ascending_icon
            other_icon = descending_icon
        text = self.model.data(self.model.index(start, 0))
        action = change_sorting_action = QtGui.QAction(text, self)
        action.setIcon(icon)
        @action.triggered.connect
        def showMenu():
            menu = QtGui.QMenu()
            _ = self.model.g.translator

            action = menu.addAction(_('Switch to ascending sort') if clause.descending else _('Switch to descending sort'))
            action.setIcon(other_icon)
            menu.setDefaultAction(action)
            action.triggered.connect(lambda: self.model.replace(clause, clause.other_direction()))

            action = menu.addAction(_('Remove this sort').format(text))
            action.setIcon(QtGui.QIcon(resource_filename('qdex', 'icons/cross.png')))
            action.triggered.connect(lambda: self.model.remove(clause))

            priority_submenu = menu.addMenu(_('Sorting priority'))
            if len(self.model) == 1:
                priority_submenu.setEnabled(False)

            action = priority_submenu.addAction(_('Re-sort by {0}').format(text))
            action.setIcon(QtGui.QIcon(resource_filename('qdex', 'icons/control-stop-180.png')))
            action.triggered.connect(lambda: self.model.append(clause))
            if clause == self.model[-1]:
                action.setEnabled(False)

            action = priority_submenu.addAction(_('Increase priority of {0}').format(text))
            action.setIcon(QtGui.QIcon(resource_filename('qdex', 'icons/control-180.png')))
            action.triggered.connect(lambda: self.model.increase_priority(clause))
            if clause == self.model[-1]:
                action.setEnabled(False)

            action = priority_submenu.addAction(_('Decrease priority of {0}').format(text))
            action.setIcon(QtGui.QIcon(resource_filename('qdex', 'icons/control.png')))
            action.triggered.connect(lambda: self.model.decrease_priority(clause))
            if clause == self.model[0]:
                action.setEnabled(False)

            menu.addSeparator()

            menu.exec_(QtGui.QCursor.pos())

        if start == 0:
            self.addAction(action)
        else:
            self.insertAction(self.actions()[-start], action)

    def rowsRemoved(self, parent, start, end):
        assert start == end, (
                'assuming the sort model only removes rows one at a time')
        self.removeAction(self.actions()[-start - 1])

    def dataChanged(self, topleft, bottomright):
        start = topleft.row()
        if start == 0:
            # Redo the whole thing
            self.setModel(self.model)
        else:
            assert start == bottomright.row(), (
                    'assuming the sort model only changes rows one at a time')
            self.rowsRemoved(None, start, start)
            self.rowsInserted(None, start, start)
