#! /usr/bin/python

import sys
import unittest


def testall():
    #init_test_env()
    import test_tpl
    import test_form
    import test_acore
    import test_ahttp
    import test_adbs

    load = unittest.TestLoader().loadTestsFromTestCase
    suite = unittest.TestSuite([
                                load(test_tpl.TestParser),
                                load(test_tpl.TestSelect),
                                load(test_tpl.TestCall),
                                load(test_form.TestForm),
                                load(test_acore.TestARW),
                                load(test_ahttp.TestAhttp),
                                load(test_adbs.TestWhere),
                                load(test_adbs.TestTable),
                                load(test_adbs.TestColumn),
                                load(test_adbs.TestSQL),
                               ])

    res = unittest.TextTestRunner(verbosity=2).run(suite)
    # notice caller
    if not res.wasSuccessful():
        sys.exit(1)


if __name__ == "__main__":
    testall()
