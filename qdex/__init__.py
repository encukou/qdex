#!/usr/bin/env python
# Encoding: UTF-8

"""Part of qdex: a Pokédex using PySide and veekun's pokedex library.

Runner module.
"""

import sys
from PySide import QtCore, QtGui
Qt = QtCore.Qt

from pokedex.db import connect, tables, media

from qdex.pokemonmodel import PokemonModel, PokemonNameColumn, PokemonTypeColumn

session = connect(engine_args=dict(echo=True))

def main():
    """Open the main window and run the event loop"""
    pokemodel = PokemonModel(session, [
            PokemonNameColumn(),
            PokemonTypeColumn(),
        ])

    app = QtGui.QApplication(sys.argv)

    hello = QtGui.QTreeView()
    hello.setUniformRowHeights(True)
    hello.setModel(pokemodel)

    hello.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
