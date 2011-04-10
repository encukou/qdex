#!/usr/bin/env python
# Encoding: UTF-8

"""Part of qdex: a Pokédex using PySide and veekun's pokedex library.

Helpers for dealing with the Pokédex library.

There should be a better way to do what they are used for... or they should be
put in pokedex :)
"""

from sqlalchemy.sql.expression import bindparam
from sqlalchemy.types import Integer

def getTranslationClass(mappedClass, attrName):
    """Get the translation class associated with the given translated attibute
    """
    for translationClass in mappedClass.translation_classes:
        columns = translationClass.__table__.c
        if any(col.name == attrName for col in columns):
            return translationClass
    else:
        raise ValueError("Translated column %s not found" % attrName)

default_language_param = bindparam('_default_language_id', value='dummy',
        type_=Integer, required=True)
