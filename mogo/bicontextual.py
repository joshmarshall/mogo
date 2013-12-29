class BiContextual(object):
    """ Probably a terrible, terrible idea. """

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, type=None):
        """ Return a properly named method. """
        if obj is None:
            return getattr(type, "_class_" + self.name)
        return getattr(obj, "_instance_" + self.name)
