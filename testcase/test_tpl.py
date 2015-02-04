import sys
import unittest

sys.path.append('../yeast')
import tpl


class TestParser(unittest.TestCase):
    def setup(self, data=None):
        self.mp = tpl.MyHtmlParser()
        if data:
            self.mp.feed(data)

    def test_data1(self):
        self.setup()
        self.mp.feed("abc")
        self.assertTrue(isinstance(self.mp.root_node.children[0],
                                   tpl.DataNode))
        self.assertEqual("abc", str(self.mp.root_node))

    def test_data2(self):
        self.setup()
        self.mp.feed("abc")
        self.assertTrue(isinstance(self.mp.root_node.children[0],
                                   tpl.DataNode))
        self.assertEqual("abc", str(self.mp.root_node))
        self.mp.feed("def")
        self.assertTrue(isinstance(self.mp.root_node.children[-1],
                                   tpl.DataNode))
        self.assertEqual(1, len(self.mp.root_node.children))
        self.assertEqual("abcdef", str(self.mp.root_node))

    def test_comment1(self):
        self.setup()
        h = "<!--thisiscomment-->"
        self.mp.feed(h)
        self.assertTrue(isinstance(self.mp.root_node.children[0],
                                   tpl.CommNode))
        self.assertEqual(h, str(self.mp.root_node))

    def test_comment2(self):
        self.setup()
        h = "<!--thisis><a> hehe </a> <comment-->"
        self.mp.feed(h)
        self.assertTrue(isinstance(self.mp.root_node.children[0],
                                   tpl.CommNode))
        self.assertEqual(h, str(self.mp.root_node))

    def test_pi(self):
        self.setup()
        h = "<?--thisispi-->"
        self.mp.feed(h)
        self.assertTrue(isinstance(self.mp.root_node.children[0], tpl.PiNode))
        self.assertEqual(h, str(self.mp.root_node))

    def test_decl(self):
        self.setup()
        #h = "<![thisispi]>"
        #self.mp.feed(h)
        #print self.mp.root_node.children
        #self.assertEqual(h, str(self.mp.root_node))

    def test_tag1(self):
        self.setup()
        h = "<div a='1' b='2'>  </div>"
        self.mp.feed(h)
        self.assertEqual(1, len(self.mp.root_node.children))
        t = self.mp.root_node.children[0]
        self.assertTrue(isinstance(t, tpl.TagNode))
        self.assertEqual(t['a'], '1')
        self.assertEqual(t['b'], '2')
        self.assertEqual(t.tag, 'div')
        self.assertEqual([('a', '1'), ('b', '2')],
                         sorted((k, v) for k, v in t))
        self.assertEqual(h, str(t))

    def test_tag2(self):
        self.setup()
        data = """<a /> <b p='1' d="2" /><c e='12'></c><d f="34"> </d>"""
        #data = """<c e='12'></c>"""
        self.mp.feed(data)
        #print self.mp.root_node("c")[0].children
        self.assertEqual(data, str(self.mp.root_node))

    def test_tag3(self):
        data = """<a b="c&lt;d&gt;e" />"""
        self.setup(data)
        an = self.mp.root_node('a')[0]
        self.assertEqual(data, str(an))
        self.assertEqual(an['b'], "c<d>e")
        an['c'] = "123"
        del an['c']
        self.assertEqual(str(an), """<a b="c&lt;d&gt;e"></a>""")


class TestSelect(unittest.TestCase):
    def setup(self):
        self.mp = tpl.MyHtmlParser()
        self.func = self.mp.root_node.get_descendants

    def _test_tag1(self, h):
        self.setup()
        #h = "<a> </a>"
        self.mp.feed(h)
        ret = tpl.select('a', self.func)
        self.assertEqual(len(ret), 1)
        self.assertTrue(isinstance(ret[0], tpl.TagNode))
        self.assertEqual(ret[0].tag, 'a')
        self.assertEqual(ret[0]['b'], '2')
        ret = tpl.select('b', self.func)
        self.assertEqual(ret, [])

    def test_tag1(self):
        self._test_tag1("<a b='2'> </a>")
        self._test_tag1("<html><a b='2'> </a></html>")
        self._test_tag1("<html><a b='2'> <div/> </ a></html>")

    def test_tag2(self):
        self.setup()
        h = "<html><a b='1'> </a><div/><a b='2'> <br/></a></html>"
        self.mp.feed(h)
        ret = tpl.select('a', self.func)
        self.assertEqual(len(ret), 2)
        self.assertTrue(isinstance(ret[0], tpl.TagNode))
        self.assertTrue(isinstance(ret[1], tpl.TagNode))
        self.assertEqual((ret[0].tag, ret[1].tag), ('a', 'a'))
        self.assertEqual((ret[0]['b'], ret[1]['b']), ('1', '2'))
        ret = tpl.select('b', self.func)
        self.assertEqual(ret, [])

    def _test_class1(self, h):
        self.setup()
        #h = "<a> </a>"
        self.mp.feed(h)
        ret = tpl.select('.a', self.func)
        self.assertEqual(len(ret), 1)
        self.assertTrue(isinstance(ret[0], tpl.TagNode))
        self.assertEqual(ret[0].tag, 'a')
        self.assertEqual(ret[0]['class'], 'a')
        ret = tpl.select('.b', self.func)
        self.assertEqual(ret, [])

    def test_class1(self):
        self._test_class1("<a class='a' b='2'> </a>")
        self._test_class1("<html><a class='a' b='2'> </a></html>")
        self._test_class1("<html><a class='a' b='2'> <div/> </a></html>")

    def test_class2(self):
        self.setup()
        h = """<html><a class='a' b='1'> </a><div/>
                     <c class='a' b='2'> <br/></c></html>"""
        self.mp.feed(h)
        ret = tpl.select('.a', self.func)
        self.assertEqual(len(ret), 2)
        self.assertTrue(isinstance(ret[0], tpl.TagNode))
        self.assertTrue(isinstance(ret[1], tpl.TagNode))
        self.assertEqual((ret[0].tag, ret[1].tag), ('a', 'c'))
        self.assertEqual((ret[0]['b'], ret[1]['b']), ('1', '2'))
        ret = tpl.select('.b', self.func)
        self.assertEqual(ret, [])

    def test_class3(self):
        self.setup()
        h = "<a class='cd a' b='2'> </a>"
        self.mp.feed(h)
        ret = tpl.select('.a', self.func)
        self.assertEqual(len(ret), 1)
        self.assertTrue(isinstance(ret[0], tpl.TagNode))
        self.assertEqual(ret[0].tag, 'a')
        self.assertEqual(ret[0]['class'], 'cd a')
        ret = tpl.select('.b', self.func)
        self.assertEqual(ret, [])

    def _test_id1(self, h):
        self.setup()
        self.mp.feed(h)
        ret = tpl.select('#a', self.func)
        self.assertEqual(len(ret), 1)
        self.assertTrue(isinstance(ret[0], tpl.TagNode))
        self.assertEqual(ret[0]['id'], 'a')
        ret = tpl.select('#b', self.func)
        self.assertEqual(ret, [])

    def test_id1(self):
        self._test_id1("<b id='a' b='2'> </b>")
        self._test_id1("<html><b class='c' b='2' id='a'> </b></html>")
        self._test_id1("<html><b class='c' b='2' id='a'> <div/> </b></html>")

    def test_id2(self):
        self.setup()
        self.mp.feed("<a id='b' b='2'> </a>")
        ret = tpl.select('#a', self.func)
        self.assertEqual(ret, [])

    def _test_direct_child1(self, h):
        self.setup()
        self.mp.feed(h)
        ret = tpl.select('a>b', self.func)
        #print ret, str(ret[0])
        self.assertEqual(len(ret), 1)
        self.assertTrue(isinstance(ret[0], tpl.TagNode))
        self.assertEqual(ret[0].tag, 'b')
        self.assertEqual(ret[0].parent.tag, 'a')

    def test_direct_child1(self):
        self._test_direct_child1("<a>a<b>b</b></a>")
        self._test_direct_child1("<a>a<c>c</c><b>b</b></a>")

    def test_direct_child2(self):
        self.setup()
        self.mp.feed("<a>a<c>c<b>b</b></c></a>")
        ret = tpl.select('a>b', self.func)
        self.assertEqual(len(ret), 0)

    def _test_indirect_child1(self, h):
        self.setup()
        self.mp.feed(h)
        ret = tpl.select('a b', self.func)
        self.assertEqual(len(ret), 1)
        self.assertTrue(isinstance(ret[0], tpl.TagNode))
        self.assertEqual(ret[0].tag, 'b')

    def test_indirect_child1(self):
        self._test_indirect_child1("<a>a<b>b</b></a>")
        self._test_indirect_child1("<a>a<c>c</c><b>b</b></a>")
        self._test_indirect_child1("<a>a<c>c<b>b</b></c></a>")

    def test_group1(self):
        self.setup()
        self.mp.feed("<a>a</a><b>b</b>")
        ret = tpl.select('b,a', self.func)
        self.assertEqual(len(ret), 2)
        self.assertEqual(ret[0].tag, 'b')
        self.assertEqual(ret[1].tag, 'a')
        ret = tpl.select('a,b', self.func)
        self.assertEqual(len(ret), 2)
        self.assertEqual(ret[1].tag, 'b')
        self.assertEqual(ret[0].tag, 'a')

    def test_group2(self):
        self.setup()
        self.mp.feed("<a>a</a><b>b</b>")
        ret = tpl.select('b , a', self.func)
        self.assertEqual(len(ret), 2)

    def test_first_child1(self):
        self.setup()
        self.mp.feed("<a>a</a><b>b</b>")
        ret = tpl.select(':first-child', self.func)
        self.assertEqual(len(ret), 3)
        self.assertTrue(isinstance(ret[0], tpl.TagNode))
        self.assertEqual(ret[0].tag, 'a')
        self.assertTrue(isinstance(ret[1], tpl.DataNode))
        self.assertEqual(str(ret[1]), 'a')
        self.assertTrue(isinstance(ret[2], tpl.DataNode))
        self.assertEqual(str(ret[2]), 'b')

    def test_first_child2(self):
        self.setup()
        self.mp.feed("<a><b id='b'>b</b>a<b id='c'></b></a>")
        ret = tpl.select('b:first-child', self.func)
        self.assertEqual(len(ret), 1)
        self.assertTrue(isinstance(ret[0], tpl.TagNode))
        self.assertEqual(ret[0].tag, 'b')
        self.assertEqual(ret[0]['id'], 'b')

    def test_first_child3(self):
        self.setup()
        self.mp.feed("<a>a<b id='b'>b</b>a<b id='c'></b></a>")
        ret = tpl.select('b:first-child', self.func)
        self.assertEqual(len(ret), 0)

    def test_checked1(self):
        self.setup()
        self.mp.feed("<a><input type='checkbox' checked name='who' />a</a>")
        ret = tpl.select(':checked', self.func)
        self.assertEqual(len(ret), 1)
        self.assertTrue(isinstance(ret[0], tpl.TagNode))
        self.assertEqual(ret[0]['name'], 'who')

    def test_checked2(self):
        self.setup()
        self.mp.feed("<a><input type='radio' checked name='who' />a</a>")
        ret = tpl.select(':checked', self.func)
        self.assertEqual(len(ret), 1)
        self.assertTrue(isinstance(ret[0], tpl.TagNode))
        self.assertEqual(ret[0]['name'], 'who')

    def test_checked3(self):
        self.setup()
        self.mp.feed("<a><input type='checkbox' check name='who' />a</a>")
        ret = tpl.select(':checked', self.func)
        self.assertEqual(len(ret), 0)

    def test_checked4(self):
        self.setup()
        self.mp.feed("<a><input checked name='who' />a</a>")
        ret = tpl.select(':checked', self.func)
        self.assertEqual(len(ret), 0)

    def test_disabled1(self):
        self.setup()
        self.mp.feed("<a><input disabled name='who' />a</a>")
        ret = tpl.select(':disabled', self.func)
        self.assertEqual(len(ret), 1)
        self.assertTrue(isinstance(ret[0], tpl.TagNode))
        self.assertEqual(ret[0]['name'], 'who')

    def test_disabled2(self):
        self.setup()
        self.mp.feed("<a><input name='who' />a</a>")
        ret = tpl.select(':disabled', self.func)
        self.assertEqual(len(ret), 0)
        ret = tpl.select(':enabled', self.func)
        self.assertEqual(len(ret), 1)
        self.assertTrue(isinstance(ret[0], tpl.TagNode))
        self.assertEqual(ret[0]['name'], 'who')

    def test_enabled1(self):
        self.setup()
        self.mp.feed("<a><input enabled name='who' />a</a>")
        ret = tpl.select(':enabled', self.func)
        self.assertEqual(len(ret), 1)
        self.assertTrue(isinstance(ret[0], tpl.TagNode))
        self.assertEqual(ret[0]['name'], 'who')

    def test_attribute1(self):
        self.setup()
        self.mp.feed("<a abcd='1'></a><b abcd></b>")
        ret = tpl.select('[abcd]', self.func)
        self.assertEqual(len(ret), 2)
        self.assertTrue(isinstance(ret[0], tpl.TagNode))
        self.assertEqual(ret[0]['abcd'], '1')
        self.assertEqual(ret[0].tag, 'a')
        self.assertTrue(isinstance(ret[1], tpl.TagNode))
        self.assertTrue(ret[1]['abcd'] is None)
        self.assertEqual(ret[1].tag, 'b')

    def test_attribute2(self):
        self.setup()
        self.mp.feed("<a abcd='1'></a><b abcd></b>")
        ret = tpl.select('a[abcd]', self.func)
        self.assertEqual(len(ret), 1)
        self.assertTrue(isinstance(ret[0], tpl.TagNode))
        self.assertEqual(ret[0]['abcd'], '1')
        self.assertEqual(ret[0].tag, 'a')

    def test_attribute_eq1(self):
        self.setup()
        self.mp.feed("<a abcd='1'></a><b abcd></b>")
        ret = tpl.select('[abcd=1]', self.func)
        self.assertEqual(len(ret), 1)
        self.assertTrue(isinstance(ret[0], tpl.TagNode))
        self.assertEqual(ret[0]['abcd'], '1')
        self.assertEqual(ret[0].tag, 'a')

    def test_attribute_eq2(self):
        self.setup()
        self.mp.feed("<a abcd='1'> </a><b abcd='2'> aa </b>")
        ret = tpl.select('b[abcd=2]', self.func)
        self.assertEqual(len(ret), 1)
        self.assertTrue(isinstance(ret[0], tpl.TagNode))
        self.assertEqual(ret[0]['abcd'], '2')
        self.assertEqual(ret[0].tag, 'b')

    def test_attribute_eq3(self):
        self.setup()
        self.mp.feed(" <a abcd='1'> </a> <b abcd='2'> abccc </b>")
        ret = tpl.select('[abcd=2]', self.func)
        self.assertEqual(len(ret), 1)
        self.assertTrue(isinstance(ret[0], tpl.TagNode))
        self.assertEqual(ret[0]['abcd'], '2')
        self.assertEqual(ret[0].tag, 'b')

    def test_attribute_eq4(self):
        self.setup()
        self.mp.feed(" <a abcd='1'> <b abcd='2'> abccc </b> </a>")
        ret = tpl.select('a  [abcd=2]', self.func)
        self.assertEqual(len(ret), 1)
        self.assertTrue(isinstance(ret[0], tpl.TagNode))
        self.assertEqual(ret[0]['abcd'], '2')
        self.assertEqual(ret[0].tag, 'b')

    def test_attribute_eq5(self):
        self.setup()
        self.mp.feed(" <a abcd='1'> <b abcd='2 3'> abccc </b> </a>")
        ret = tpl.select('a  [abcd="2 3"]', self.func)
        self.assertEqual(len(ret), 1)
        self.assertTrue(isinstance(ret[0], tpl.TagNode))
        self.assertEqual(ret[0]['abcd'], '2 3')
        self.assertEqual(ret[0].tag, 'b')

    def test_attribute_st1(self):
        self.setup()
        self.mp.feed("<a abcd='efgh'></a><b abcd></b>")
        ret = tpl.select('[abcd^=ef]', self.func)
        self.assertEqual(len(ret), 1)
        self.assertTrue(isinstance(ret[0], tpl.TagNode))
        self.assertEqual(ret[0]['abcd'], 'efgh')
        self.assertEqual(ret[0].tag, 'a')

    def test_attribute_st2(self):
        self.setup()
        self.mp.feed("<a abcd='efgh'></a><b abcd></b>")
        ret = tpl.select('[abcd^=fg]', self.func)
        self.assertEqual(len(ret), 0)

    def test_attribute_in1(self):
        self.setup()
        self.mp.feed("<a abcd='efgh'></a><b abcd></b>")
        ret = tpl.select('[abcd*=ef]', self.func)
        self.assertEqual(len(ret), 1)
        t = ret[0]
        self.assertTrue(isinstance(t, tpl.TagNode))
        self.assertEqual(t['abcd'], 'efgh')
        self.assertEqual(t.tag, 'a')

        ret = tpl.select('[abcd*=fg]', self.func)
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret[0], t)

        ret = tpl.select('[abcd*=gh]', self.func)
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret[0], t)

    def test_attribute_ed1(self):
        self.setup()
        self.mp.feed("<a abcd='efgh'></a><b abcd></b>")
        ret = tpl.select('[abcd$=gh]', self.func)
        self.assertEqual(len(ret), 1)
        self.assertTrue(isinstance(ret[0], tpl.TagNode))
        self.assertEqual(ret[0]['abcd'], 'efgh')
        self.assertEqual(ret[0].tag, 'a')

    def test_attribute_ed2(self):
        self.setup()
        self.mp.feed("<a abcd='efgh'></a><b abcd></b>")
        ret = tpl.select('[abcd^=fg]', self.func)
        self.assertEqual(len(ret), 0)


class TestCall(unittest.TestCase):
    def setup(self):
        self.mp = tpl.MyHtmlParser()

    def test_call(self):
        self.setup()
        self.mp.feed("<a><div id='mydiv' /></a>")
        ret = self.mp.root_node("div")
        self.assertEqual(len(ret), 1)
        self.assertTrue(isinstance(ret[0], tpl.TagNode))
        self.assertEqual(ret[0].tag, 'div')
        self.assertEqual(ret[0]['id'], 'mydiv')


if __name__ == '__main__':
    #unittest.main()
    #unittest.main(defaultTest="TestSelect.test_group2")
    unittest.main(defaultTest="TestParser.test_tag3")
