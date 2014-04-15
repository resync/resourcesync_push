import unittest


class ResourceSyncPuSHTest(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

testmodules = [
    'test_resourcesync_push',
    'test_subscriber',
    'test_publisher',
    'test_hub'
]

suite = unittest.TestSuite()

for t in testmodules:
    try:
        # If the module defines a suite() function, call it to get the suite.
        mod = __import__(t, globals(), locals(), ['suite'])
        suitefn = getattr(mod, 'suite')
        suite.addTest(suitefn())
    except (ImportError, AttributeError):
        # else, just load all the test cases from the module.
        suite.addTest(unittest.defaultTestLoader.loadTestsFromName(t))


if __name__ == '__main__':
    unittest.TextTestRunner().run(suite)
