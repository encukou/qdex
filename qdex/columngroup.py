#!/usr/bin/env python
# Encoding: UTF-8

"""Part of qdex: a Pokédex using PySide and veekun's pokedex library.

Column groups: Columns, grouped together. Yeah.
"""

# XXX: Better name for ColumnGroup: should take the leaf objects into account

from PySide import QtGui, QtCore
Qt = QtCore.Qt
from pkg_resources import resource_filename

from qdex.loadableclass import LoadableMetaclass
from qdex.column import ModelColumn, SimpleModelColumn
from qdex import yaml

class ColumnGroupVisitor(object):
    """Visitor for column groups"""
    def visit(self, columnGroup):
        """Visit a ColumnGroup"""
        raise NotImplementedError

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

class ColumnMenuBuilder(ColumnGroupVisitor):
    """Column group visitor that builds up a menu, with an Action for each leaf

    Usually invoked through buildColumnMenu, see its doc.
    """
    def __init__(self, g, menu, rootString, slotFactory):
        super(ColumnMenuBuilder, self).__init__()
        self.g = g
        self.state = [(menu, None)]
        self.actionStack = []
        self.rootString = rootString
        self.inRoot = True
        self.slotFactory = slotFactory

    def build(self, columnGroup):
        """Build the menu"""
        for column in columnGroup.columns:
            column.accept(self)

    def visit(self, columnGroup):
        inRoot = len(self.state) == 1
        menu, parentAction = self.state[-1]
        addSpecialAction = columnGroup.addSpecialAction
        if addSpecialAction:
            action = addSpecialAction(menu)
        else:
            name = self.g.translator(columnGroup.name)
            if inRoot:
                name = self.g.translator(self.rootString).format(name)
            else:
                name = name
            action = menu.addAction(name)
        if columnGroup.columnClass:
            action.triggered.connect(self.slotFactory(columnGroup))
        action.setEnabled(columnGroup.enabled)
        self.lastAction = action
        return self

    def __enter__(self):
        menu = QtGui.QMenu()
        self.state.append((menu, self.lastAction))
        return self

    def __exit__(self, *args):
        menu, action = self.state.pop()
        if action:
            action.setMenu(menu)

def buildColumnMenu(g, menu, columnGroup, rootString, slotFactory):
    """Build a menu out of the contents of a column group

    g: Global object with a Translator
    menu: The menu to fill
    columnGroup: the root column group whose children will fill the menu
    rootString: The top-level menu entries will be named
            rootString.format(colgroup.name). Example: "Add {0} column"
    slotFactory: Function that takes a column class and returns the function to
            be called when that column is selected
    """
    builder = ColumnMenuBuilder(g, menu, rootString, slotFactory)
    return builder.build(columnGroup)

class BaseColumnGroup(object):
    """Base class for column-group-like objects

    Node in a tree whose leaves are possible column classes, and which lends
    itself to creating a menu for selecting the columns
    """
    enabled = True
    columnClass = None
    addSpecialAction = None

    def accept(self, visitor):
        """Accept a column group visitor"""
        visitor.visit(self)

class ColumnGroup(BaseColumnGroup):
    """A column group: non-leaf node"""
    __metaclass__ = LoadableMetaclass
    enabled = True

    def __init__(self, columns, name=None):
        super(ColumnGroup, self).__init__()
        self.columns = []
        self.name = name
        for column in columns:
            if column == '---':
                self.columns.append(Separator())
            else:
                self.columns.append(self.load(column))

    def accept(self, visitor):
        with visitor.visit(self) as inner:
            for column in self.columns:
                column.accept(inner)

    @property
    def enabled(self):
        """The group is enabled iff any of its kids is"""
        return any(column.enabled for column in self.columns)

    @classmethod
    def resolveClassName(cls, classname):
        """Load column classes as our wrappers. Grey out unavailable ones"""
        try:
            return cls.availableClassesForLoad[classname]
        except KeyError:
            try:
                cls = ModelColumn.availableClassesForLoad[classname]
                return columnFactory(cls)
            except KeyError:
                return DisabledColumn

def columnFactory(columnClass):
    """Return a wrapper class for a column class"""
    try:
        return columnFactory.memo[columnClass]
    except AttributeError:
        columnFactory.memo = {}
        return columnFactory(columnClass)
    except KeyError:
        outerColumnClass = columnClass
        class ColumnFactory(BaseColumnGroup):
            """Wrapper class for a column class"""
            classNameForLoad = None
            columnClass = outerColumnClass

            def __init__(self, name, **kwargs):
                super(ColumnFactory, self).__init__()
                self.name = name
                self.kwargs = kwargs

            def getColumn(self):
                """Get a new column from this factory"""
                return self.columnClass(name=self.name, **self.kwargs)

        columnFactory.memo[columnClass] = ColumnFactory
        return ColumnFactory
ColumnGroup.defaultClassForLoad = columnFactory(SimpleModelColumn)

class DisabledColumn(BaseColumnGroup):
    """A disabled (greyed-out, not selectable) node. For undefined classes."""
    enabled = False

    def __init__(self, name=None, **kwargs):
        super(DisabledColumn, self).__init__()
        self.name = name
        self.columns = None

class Separator(BaseColumnGroup):
    """A menu separator. Just a visual thing."""
    enabled = False

    def addSpecialAction(self, menu):
        """Add a separator to the menu"""
        return menu.addSeparator()

defaultColumnGroups = {}
fileobj = open(resource_filename('qdex', 'columns.yaml'))
for tableName, group in yaml.load(fileobj).items():
    defaultColumnGroups[tableName] = ColumnGroup(**group)


