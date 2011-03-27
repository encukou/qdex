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
from qdex.queryview import QueryView

session = connect(engine_args=dict(echo=True))

def main():
    """Open the main window and run the event loop"""
    pokemodel = PokemonModel(session, [
            PokemonNameColumn(),
            PokemonTypeColumn(),
        ])

    app = QtGui.QApplication(sys.argv)

    hello = QueryView()
    hello.setModel(pokemodel)
    hello.resize(800, 600)

    hello.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
