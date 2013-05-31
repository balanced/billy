from unittest import TestCase


class TestDB(TestCase):

    def test_sqlachemy(self):
        import sqlalchemy
        ver = sqlalchemy.__version__
        ver_req = '0.8.1'
        self.assertEquals(ver, ver_req, "Sqlalchemy version is {}, requires {}".format(ver, ver_req))


