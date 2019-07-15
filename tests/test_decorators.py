import unittest
from mogo.decorators import notinstancemethod


class MogoTestModel(unittest.TestCase):

    def test_notinstancemethod_raises_when_wrapping_nonmethod(self) -> None:
        with self.assertRaises(ValueError):
            notinstancemethod(5)  # type: ignore

    def test_notinstancemethod_raises_when_wrapping_instance_method(
            self) -> None:

        with self.assertRaises(ValueError):
            class Foo(object):

                @notinstancemethod
                def foo(self) -> int:
                    return 4

    def test_notinstancemethod_rejects_instance_call(self) -> None:

        class Foo(object):

            @notinstancemethod
            @classmethod
            def foo(cls) -> int:
                return 4

        foo = Foo()

        with self.assertRaises(TypeError):
            foo.foo()
