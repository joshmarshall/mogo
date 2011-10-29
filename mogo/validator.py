""" The basic field attributes. """

import types

class Validator(object):
    """ Base class for building validators"""
    def __init__(self):
        pass

    def validate(self, value):
        """ Override this method to check your value """
        raise ValueError('Unimplemented')


class LengthValidator(Validator):
    def __init__(self, *args, **kwargs):
        self.min_length = kwargs.get('min_length')
        self.max_length = kwargs.get('max_length')
        super(Validator, self).__init__()

    def validate(self, value):
        if len(value)<self.min_length:
            raise ValueError('minimum length is %d' % (self.min_length))

        if self.max_length:
            if len(value)>self.max_length:
                raise ValueError('maximum length is %d' % (self.max_length))
        return True
IS_LENGTH = lambda min, max=0: LengthValidator(min_length=min, max_length=max)


class IntValidator(Validator):
    def __init__(self, *args, **kwargs):
        self.min_value = kwargs.get('min_value')
        self.max_value = kwargs.get('max_value')
        super(Validator, self).__init__()

    def validate(self, value):
        if value<self.min_value:
            raise ValueError('minimum value is %d' % (self.min_value))
        if self.max_value != 0:
            if value>self.max_value:
                raise ValueError('maximum value is %d' % (self.max_value))
        return True
IS_INT_IN_RANGE = lambda min, max=0: IntValidator(min_value=min, max_value=max)

