import inspect

from mogo.model import Model


class PolyModel(Model):
    """ A base class for inherited models """

    _child_models = None

    def __new__(cls, **kwargs):
        """ Creates a model of the appropriate type """
        # use the base model by default
        create_class = cls
        key_field = getattr(cls, cls.get_child_key(), None)
        key = kwargs.get(cls.get_child_key())
        if not key and key_field:
            key = key_field.default
        if key in cls._child_models:
            create_class = cls._child_models[key]
        return super(PolyModel, cls).__new__(create_class, **kwargs)

    @classmethod
    def register(cls, name):
        """ Decorator for registering a submodel """
        def wrap(child_class):
            """ Wrap the child class and return it """
            # Better way to do this?
            child_class._get_name = classmethod(lambda x: cls._get_name())
            child_class._polyinfo = {
                "parent": cls,
                "name": name
            }
            cls._child_models[name] = child_class
            return child_class
        if inspect.isclass(name) and issubclass(name, cls):
            # Decorator without arguments
            child_cls = name
            name = child_cls.__name__.lower()
            return wrap(child_cls)
        return wrap

    @classmethod
    def _update_search_spec(cls, spec):
        """ Update the search specification on child polymodels. """
        if hasattr(cls, "_polyinfo"):
            name = cls._polyinfo["name"]
            polyclass = cls._polyinfo["parent"]
            spec = spec or {}
            spec.setdefault(polyclass.get_child_key(), name)
        return spec

    @classmethod
    def find(cls, spec=None, *args, **kwargs):
        """ Add key to search params """
        spec = cls._update_search_spec(spec)
        return super(PolyModel, cls).find(spec, *args, **kwargs)

    @classmethod
    def find_one(cls, spec=None, *args, **kwargs):
        """ Add key to search params for single result """
        spec = cls._update_search_spec(spec)
        return super(PolyModel, cls).find_one(spec, *args, **kwargs)
