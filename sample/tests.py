from django.db.utils import IntegrityError
from django.test import TestCase

from .models import Bar, Foo


class CompositeForeignKeyTestCase(TestCase):
    def test_composite_fk(self):
        """
        Make sure that foos can only be created with a baz of 10
        """
        bar = Bar.objects.create(baz=10)
        Foo.objects.create(bar=bar, baz=10)
        with self.assertRaises(IntegrityError):
            Foo.objects.create(bar=bar, baz=12)
