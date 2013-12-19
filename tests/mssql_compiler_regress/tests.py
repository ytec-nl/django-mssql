from django.test import TestCase

from sqlserver_ado.compiler import _re_data_type_terminator

class CompilerRegexTestCase(TestCase):
    def test_data_type_terminator(self):
        """
        Make sure the regex to split a data type string works as expected.
        """
        pairs = [
            # data type string, left of split
            ('int', 'int'),
            ('int identity', 'int'),
            ('int IDENTITY (1, 1)', 'int'),
            ('int identity (1, 1)', 'int'),
            ('int default 0', 'int'),
            ('nvarchar(23)', 'nvarchar(23)'),
            ('nvarchar (max)', 'nvarchar (max)'),
            ('smallint CHECK ([name] >= 0)', 'smallint'),
            ('int null', 'int'),
            ('int not null', 'int'),
            ('decimal (2, 3)', 'decimal (2, 3)'),
        ]

        for val, expected in pairs:
            self.assertEqual(expected, _re_data_type_terminator.split(val)[0])
