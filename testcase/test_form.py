import sys
import unittest

sys.path.append('../yeast')

import tpl
from form import Form, check_and_warn


class FS(object):
    def __init__(self, dd):
        self.data_dict = dd

    def __iter__(self):
        return iter(self.data_dict.keys())

    def getfirst(self, name, dft=None):
        return self.data_dict.get(name, dft)


class MF1(Form):
    @check_and_warn('username', 'em#username')
    def username_is_ok(self, value, node):
        return "username is BAD"

    @check_and_warn('password', 'em#password')
    def password_is_ok(self, value, node):
        return "password is BAD"


class MF2(Form):
    @check_and_warn('username', 'em#username')
    def username_is_ok(self, value, node):
        return ""

    @check_and_warn('password', 'em#password')
    def password_is_ok(self, value, node):
        return "BAD PASS"


class MF3(Form):
    @check_and_warn('username', 'em#username')
    def username_is_ok(self, value, node):
        return "username is <bad>"


class TestForm(unittest.TestCase):
    def setup(self):
        self.mp = tpl.MyHtmlParser()
        self.mp.feed("""
            <html><body><form>
            <input type='text' name='username' /><em id='username' />
            <input type='password' name='password' /><em id='password' />
            </form></body></html>
        """)
        self.form_node = self.mp.root_node("form")[0]

    def test_form1(self):
        self.setup()
        fm = MF1(self.form_node)
        ret = fm.validate_and_update(FS({"username": "1", "password": "2"}))
        self.assertEqual(len(ret), 2)
        self.assertEqual(str(ret[0].children[0]), "username is BAD")
        self.assertEqual(str(ret[1].children[0]), "password is BAD")
        #self.assertEqual(ret[0], "username is BAD")
        #self.assertEqual(ret[1], "password is BAD")
        #print self.form_node
        data = str(self.form_node)
        self.mp = tpl.MyHtmlParser()
        self.mp.feed(data)
        self.assertEqual(str(self.mp.root_node("em#username")[0].children[0]),
                         "username is BAD")
        un = self.mp.root_node("input[name=username]")[0]
        self.assertEqual(un['value'], '1')
        self.assertEqual(str(self.mp.root_node("em#password")[0].children[0]),
                         "password is BAD")
        pn = self.mp.root_node("input[name=password]")[0]
        self.assertEqual(pn['value'], '2')

    def test_form2(self):
        self.setup()
        fm = MF2(self.form_node)
        ret = fm.validate_and_update(FS({"username": "3", "password": "4"}))
        self.assertEqual(len(ret), 1)
        self.assertEqual(str(ret[0].children[0]), "BAD PASS")
        #self.assertEqual(ret[0], "BAD PASS")
        #print self.form_node
        data = str(self.form_node)
        self.mp = tpl.MyHtmlParser()
        self.mp.feed(data)
        self.assertEqual(self.mp.root_node("em#username")[0].children, [])
        un = self.mp.root_node("input[name=username]")[0]
        self.assertEqual(un['value'], '3')
        self.assertEqual(str(self.mp.root_node("em#password")[0].children[0]),
                         "BAD PASS")
        pn = self.mp.root_node("input[name=password]")[0]
        self.assertEqual(pn['value'], '4')

    def test_form3(self):
        self.setup()
        fm = MF3(self.form_node)
        #print fm
        ret = fm.validate_and_update(FS({"username": "u<se>r"}))
        self.assertEqual(len(ret), 1)
        self.assertEqual(str(ret[0].children[0]), "username is &lt;bad&gt;")
        #self.assertEqual(ret[0], "username is <bad>")
        #print self.form_node
        data = str(self.form_node)
        self.mp = tpl.MyHtmlParser()
        self.mp.feed(data)
        #print self.mp.root_node
        self.assertEqual(len(self.mp.root_node("em#username")[0].children), 1)
        un = self.mp.root_node("input[name=username]")[0]
        #print un
        self.assertEqual(str(un),
            '<input type="text" name="username" value="u&lt;se&gt;r"></input>')
        self.assertEqual(un['value'], 'u<se>r')


if __name__ == '__main__':
    #unittest.main()
    unittest.main(defaultTest="TestForm.test_form3")
