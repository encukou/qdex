#!/usr/bin/env python
# Encoding: UTF-8

"""Part of qdex: a Pokédex using PySide and veekun's pokedex library.

Decorator for Models, Columns and other objects loadable from a dict
representation.
"""

class LoadableMetaclass(type):
    """Calls loadable() on the root of the hierarchy, and registers classes.

    Gives classNameForLoad as the class name.
    """
    def __init__(self, name, bases, dct):
        super(LoadableMetaclass, self).__init__(name, bases, dct)
        if 'classNameForLoad' not in dct:
            self.classNameForLoad = name
        try:
            register = self.registerForLoad
        except AttributeError:
            loadable(self)
            register = self.registerForLoad
        register(self)

def loadable(cls):
    """Decorator for loadable classes.

    Decorate a class with this. Then, provide a save method that returs __init__
    args needed to load the class, in a dict.
    If not all needed arguments are saved by save(), it's possible to give the
    remaining ones to load().

    Register derived classes with registerForLoad, or use the LoadablaMetaclass
    to do that automatically.
    Make sure the derived classes have unique in the classNameForLoad
    class atrribute.

    Abstract, unsavable classes can set classNameForLoad to None.

    The save method will be auto-decorated so the dict includes a 'class'
    entry.
    """
    availableClasses = {}

    def registerForLoad(registeredClass):
        """Register the given class for load()"""
        classname = registeredClass.classNameForLoad
        assert classname is not None
        assert classname not in availableClasses, (
                'Class name %s is already taken.'
            ) % classname
        availableClasses[classname] = registeredClass
    cls.registerForLoad = staticmethod(registerForLoad)

    try:
        oldSave = cls.save
    except AttributeError:
        oldSave = lambda: {}

    def save(self):
        """Return __init__ kwargs needed to reconstruct self"""
        representation = oldSave(self)
        classname = self.classNameForLoad
        assert classname is not None, "%s can't be saved." % self
        representation['class'] = self.classname
        return representation
    cls.save = save

    def load(representation, **extraKwargs):
        """Load an object from a representation

        The representation can either be something returned from save(),
        in which case it's actually loaded, or an existing loadable object,
        which is just returned.

        Extra keyword arguments can be added, in case save() didn't quite save
        everything we need.
        """
        try:
            # Copy the dict, since we'll be modifying it
            representation = dict(representation)
        except TypeError:
            # Oops, not a dict. Must be a loadable object already
            assert representation.classNameForLoad
            return representation
        else:
            try:
                subclass = availableClasses[representation.pop('class')]
            except KeyError:
                try:
                    subclass = cls.defaultClassForLoad
                except AttributeError:
                    print 'Error loading:', representation
                    raise
            extraKwargs.update(representation)
            try:
                return subclass(**extraKwargs)
            except:
                print 'Error loading:', representation
                print 'Class:', subclass
                raise
    cls.load = staticmethod(load)

    return cls
