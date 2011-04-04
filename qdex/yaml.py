#!/usr/bin/env python
# Encoding: UTF-8

"""Part of qdex: a Pokédex using PySide and veekun's pokedex library.

Tools handling custom YAML tags
"""

# Not to be confused with the PyYaml library
from __future__ import absolute_import

import yaml
from forrin.translator import TranslatableString

translatableStringTag = u'tag:encukou.cz,2011:forrin/_'

try:
    BaseDumper = yaml.CSafeDumper
    BaseLoader = yaml.CSafeLoader
except AttributeError:
    BaseDumper = yaml.SafeDumper
    BaseLoader = yaml.SafeLoader

class Dumper(BaseDumper):
    """Custom YAML dumper"""
    pass

def representTranslatableString(dumper, data):
    """Represent a forrin TranslatableString"""
    representation = {}
    if data.context:
        representation['context'] = data.context
    if data.comment:
        representation['comment'] = data.comment
    if data.plural:
        representation['plural'] = data.plural
    if representation:
        representation['message'] = data.message
        return dumper.represent_mapping(translatableStringTag, representation)
    else:
        return dumper.represent_scalar(translatableStringTag, data.message)

Dumper.add_representer(TranslatableString, representTranslatableString)

def dump(data, stream=None):
    """As in yaml.load, but use our own dialect"""
    return yaml.dump(data, stream, Dumper, encoding='utf-8', indent=4)


class Loader(BaseLoader):
    """Custom YAML loader"""
    pass

def constructTranslatableString(loader, node):
    """Construct a TranslatableString from a YAML node"""
    try:
        message = loader.construct_scalar(node)
    except yaml.constructor.ConstructorError:
        return TranslatableString(**loader.construct_mapping(node))
    else:
        return TranslatableString(message)

Loader.add_constructor(translatableStringTag, constructTranslatableString)

def load(stream):
    """As in yaml.load, but resolve forrin _ tags"""
    return yaml.load(stream, Loader)


def extractMessages(fileobj, keywords, commentTags, options):
    """Extract Babel messages out of a YAML file"""
    currentArgs = None
    currentKey = None
    for event in yaml.parse(fileobj):
        if isinstance(event, yaml.events.MappingStartEvent):
            if event.tag == translatableStringTag:
                currentArgs = {}
        elif isinstance(event, yaml.events.MappingEndEvent) and currentArgs:
            try:
                message = currentArgs['context'] + '|' + currentArgs['message']
            except KeyError:
                message = currentArgs['message']
            try:
                comments = [currentArgs['comment']]
            except KeyError:
                comments = []
            yield event.start_mark.line, '_', message, comments
            currentArgs = None
        elif isinstance(event, yaml.events.ScalarEvent):
            if currentArgs is not None:
                if currentKey is None:
                    currentKey = event.value
                else:
                    currentArgs[currentKey] = event.value
                    currentKey = None
            elif event.tag == translatableStringTag:
                yield event.start_mark.line, '_', event.value, []
