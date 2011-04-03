#!/usr/bin/env python
# Encoding: UTF-8

"""Part of qdex: a Pokédex using PySide and veekun's pokedex library.

The main pokédex window
"""

import os

from pkg_resources import resource_filename
from PySide import QtCore, QtGui
Qt = QtCore.Qt

from forrin.translator import BaseTranslator
from pokedex.db import connect, tables

from qdex.queryview import QueryView
from qdex.metamodel import MetaModel, MetaModelView

class Translator(BaseTranslator):
    """Our very own translator"""
    package = 'qdex'

class Global(object):
    """Global options for everything relating to the entire app"""
    def __init__(self,
            session=None,
            langs=None,
            mainwindow=None,
        ):
        self.session = session or connect()
        self.mainwindow = mainwindow
        self.langs = langs or [u'en']

    @property
    def langs(self):
        """UI language identifiers, by priority (highest first)"""
        return self._langs

    @langs.setter
    def langs(self, langs):
        """UI language identifiers, by priority (highest first)"""
        self._langs = langs
        self.languages = [(self.session.query(tables.Language)
                .filter_by(identifier=lang)
                .one()
            ) for lang in langs]
        self.translator = Translator(langs)
        if self.mainwindow:
            self.mainwindow.retranslate.emit()

    def name(self, dbObject):
        """Get an object's name"""
        for language in self.languages:
            try:
                return dbObject.name_map[language]
            except KeyError:
                pass
        return dbObject.identifier

    def tr(self, stringMap, fallbackLanguage=None):
        """Get an appropriate string from string_map.

        Falls back to fallback_language, or the game language by default,
        but uglifies the string if it does.
        """
        for language in self.languages:
            try:
                return stringMap[language]
            except KeyError:
                pass
        if fallbackLanguage == None:
            fallbackLanguage = self.session.defaultLanguage
        try:
            return '[%s: %s]' % (
                    fallbackLanguage.identifier,
                    stringMap[fallbackLanguage],
                )
        except KeyError:
            _ = self.translator
            return _('[translation not available]')

    def registerRetranslate(self, slot):
        """Connect slot to the mainwindow's retranslate signal"""
        if self.mainwindow:
            self.mainwindow.retranslate.connect(slot)

class MainWindow(QtGui.QMainWindow):
    """The main pokédex window"""
    retranslate = QtCore.Signal()

    def __init__(self, **globalArgs):
        super(MainWindow, self).__init__()
        self.g = Global(mainwindow=self, **globalArgs)
        self.g.registerRetranslate(self.retranslateUi)
        icon = resource_filename('pokedex', u'data/media/items/poké-ball.png')
        self.setWindowIcon(QtGui.QIcon(icon))

        splitter = QtGui.QSplitter(self)
        self.setCentralWidget(splitter)

        metaview = MetaModelView(self)
        metaview.setModel(MetaModel(self.g))
        splitter.addWidget(metaview)

        self.mainlistview = QueryView()
        splitter.addWidget(self.mainlistview)

        metaview.selectionModel().currentChanged.connect(lambda index:
                metaview.model().setModelOnView(index, self.mainlistview)
            )
        metaview.selectionModel().select(
                metaview.model().defaultIndex(),
                QtGui.QItemSelectionModel.ClearAndSelect,
            )

        self.resize(800, 600)

        # XXX: The min-size resizing should be done with default data shown,
        # and custom collapsed
        metaview.resizeColumnToContents(0)
        metaview.setMinimumWidth(metaview.columnWidth(0))
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setCollapsible(1, False)
        splitter.setSizes([1, 1])
        splitter.setCollapsible(0, True)

        self.retranslateUi()

    def retranslateUi(self):
        """Called when the UI or game language changes
        """
        self.populateMenu()

    def populateMenu(self):
        """Populate the app's main menu"""
        _ = self.g.translator
        self.setWindowTitle(_(u'Pokédex'))
        self.menuBar().clear()
        fileMenu = self.menuBar().addMenu(_(u"&Pokédex"))
        icon = QtGui.QIcon(resource_filename('qdex', 'icons/star.png'))
        self.addMenuItem(fileMenu, _(u'&About…'), self.about, icon=icon)
        fileMenu.addSeparator()
        icon = QtGui.QIcon(resource_filename('qdex', 'icons/cross-button.png'))
        self.addMenuItem(fileMenu, _('&Exit'), QtGui.QApplication.exit,
                icon=icon)
        self.settingsMenu = self.menuBar().addMenu(_(u"Settings"))
        self.uilangMenu = self.settingsMenu.addMenu(_(u"Program &Language"))
        self.uilangMenu.aboutToShow.connect(self.fillUilangMenu)
        self.gamelangMenu = self.settingsMenu.addMenu(_(u"Game &Language"))
        self.gamelangMenu.aboutToShow.connect(self.fillGamelangMenu)

    def addMenuItem(self, menu, name, action, **kwargs):
        """Convenience method to add a menu item to a menu"""
        qaction = QtGui.QAction(name, self, **kwargs)
        qaction.triggered.connect(action)
        menu.addAction(qaction)

    def fillGamelangMenu(self):
        """Fill up the game language menu"""
        self.gamelangMenu.clear()
        query = self.g.session.query(tables.Language)
        query = query.filter_by(official=True)
        query = query.order_by(tables.Language.order)
        for language in query:
            def _scope(language):
                def _retranslate():
                    self.g.session.default_language = language
                    self.retranslate.emit()
                name = self.g.name(language)
                icon = os.path.join('flags', language.iso3166 + '.png')
                icon = QtGui.QIcon(resource_filename('qdex', icon))
                self.addMenuItem(self.gamelangMenu, name, _retranslate,
                        icon=icon,
                        checkable=True,
                        checked=self.g.session.default_language == language,
                    )
            _scope(language)

    def fillUilangMenu(self):
        """Fill up the UI language menu"""
        self.uilangMenu.clear()
        query = self.g.session.query(tables.Language)
        for lang in self.g.translator.available_languages():
            def _scope(lang):
                language = query.filter_by(identifier=lang).one()
                icon = os.path.join('flags', language.iso3166 + '.png')
                icon = QtGui.QIcon(resource_filename('qdex', icon))
                try:
                    name = language.name_map[language]
                except KeyError:
                    name = self.g.name(language)
                def _retranslate():
                    self.g.langs = [lang]
                self.addMenuItem(self.uilangMenu, name, _retranslate,
                        icon=icon,
                        checkable=True,
                        checked=self.g.langs[0] == language.identifier,
                    )
            _scope(lang)

    def about(self):
        """Create and show the About box
        """
        _ = self.g.translator
        about = QtGui.QDialog(self)
        about.setWindowTitle(_(u"About Pokédex"))
        layout = QtGui.QGridLayout(about)

        labels = []
        expanding = QtGui.QSizePolicy(
                QtGui.QSizePolicy.MinimumExpanding,
                QtGui.QSizePolicy.MinimumExpanding,
            )
        iconArgs = []
        for i, thing in enumerate((
                ('pokedex', u'data/media/items/poké-ball.png'),
                _(u'''<strong>Pokédex 0.1</strong>
                    <br>
                    by Petr “En-Cu-Kou” Viktorin &lt;<a
                    href="encukou@gmail.com">encukou@gmail.com</a>&gt;
                    <br>
                    Provided under the open-source MIT license'''),
                ('pokedex', u'data/media/icons/133.png'),
                _(u'''Data from the veekun database: see <a
                    href="http://veekun.com">http://veekun.com</a>
                    <br>
                    Thanks to Eevee, Zhorken, magical and everyone else who
                    contributed'''),
                ('qdex', u'icons/palette.png'),
                _(u'''Fugue icon set by Yusuke Kamiyamane &lt;<a
                    href="http://p.yusukekamiyamane.com"
                    >http://p.yusukekamiyamane.com</a>&gt;
                    <br>
                    Used under the <a
                    href="http://creativecommons.org/licenses/by/3.0"
                    >Creative Commons Attribution 3.0 license</a>'''),
                ('qdex', u'icons/globe.png'),
                _(u'''Flag icons from <a
                    href="http://www.famfamfam.com/lab/icons/flags/"
                    >famfamfam.com</a> by Mark James'''),
                ('qdex', u'icons/auction-hammer--exclamation.png'),
                _(u'''Pokémon and everything related to them is intellectual
                    property of Nintendo, Creatures, inc., and GAME FREAK, inc.
                    and is protected by various copyrights and trademarks.
                    The author believes that the use of this intellectual
                    property for a fan reference is covered by fair use and
                    that the software is significantly impaired without said
                    property included. Any use of this copyrighted property
                    is at your own legal risk.'''),
            )):
            try:
                package, path = thing
            except (ValueError, TypeError):
                label = QtGui.QLabel(
                        ' '.join(thing.split()),
                        textInteractionFlags=Qt.LinksAccessibleByMouse
                                |Qt.TextSelectableByMouse,
                        sizePolicy=expanding,
                        wordWrap=len(thing) > 300,
                    )
                layout.addWidget(label, i, 1)
                labels.append(label)
                iconArgs[-1][3] += 1
            else:
                if i:
                    layout.setRowStretch(i, 1)
                filename = resource_filename(package, path)
                iconArgs.append([
                        QtGui.QLabel(
                                pixmap=QtGui.QPixmap(filename),
                                alignment=Qt.AlignVCenter|Qt.AlignHCenter,
                            ),
                        i + 1, 0, 0, 1
                    ])
        for args in iconArgs:
            layout.addWidget(*args)

        layout.setRowStretch(i + 1, 1)
        buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok)
        buttonBox.accepted.connect(about.accept)
        layout.addWidget(buttonBox, i + 2, 0, 1, 2)

        about.exec_()
