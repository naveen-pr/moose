#!/usr/bin/env python2
import unittest
import cPickle as pickle
from mooseutils import MooseException
import moosetree

class TestNode(unittest.TestCase):
    """Test moosetree.Node class."""

    def testSingleNode(self):
        node = moosetree.Node()
        self.assertEqual(node.name, 'Node')
        self.assertIsNone(node.parent)
        self.assertIs(node.root, node)
        self.assertEqual(node.depth, 0)
        self.assertEqual(node.children, [])
        self.assertEqual(node.path, [node])

    def testName(self):
        node = moosetree.Node(None, 'arg')
        self.assertEqual(node.name, 'arg')
        node = moosetree.Node(name='kwarg')
        self.assertEqual(node.name, 'kwarg')

    def testParent(self):
        n0 = moosetree.Node()
        n1 = moosetree.Node(n0)
        self.assertIsNone(n0.parent)
        self.assertIs(n1.parent, n0)

        n0 = moosetree.Node()
        n1 = moosetree.Node(parent=n0)
        self.assertIsNone(n0.parent)
        self.assertIs(n1.parent, n0)

    def testTree(self):
        n0 = moosetree.Node(name='n0')
        n1 = moosetree.Node(n0, 'n1')
        n2 = moosetree.Node(n0, 'n2')
        n11 = moosetree.Node(n1, 'n11')
        n12 = moosetree.Node(n1, 'n12')
        n21 = moosetree.Node(n2, 'n21')
        n22 = moosetree.Node(n2, 'n22')

        # parent
        self.assertIs(n1.parent, n0)
        self.assertIs(n2.parent, n0)
        self.assertIs(n11.parent, n1)
        self.assertIs(n12.parent, n1)
        self.assertIs(n21.parent, n2)
        self.assertIs(n22.parent, n2)

        # children
        self.assertEqual(n0.children, [n1, n2])
        self.assertEqual(len(n0), 2)
        self.assertEqual(n1.children, [n11, n12])
        self.assertEqual(len(n1), 2)
        self.assertEqual(n2.children, [n21, n22])
        self.assertEqual(len(n1), 2)

        self.assertEqual(n11.children, [])
        self.assertEqual(n12.children, [])
        self.assertEqual(n21.children, [])
        self.assertEqual(n22.children, [])

        # depth
        self.assertEqual(n0.depth, 0)
        self.assertEqual(n1.depth, 1)
        self.assertEqual(n2.depth, 1)
        self.assertEqual(n11.depth, 2)
        self.assertEqual(n12.depth, 2)
        self.assertEqual(n21.depth, 2)
        self.assertEqual(n22.depth, 2)

        # path
        self.assertEqual(n0.path, [n0])
        self.assertEqual(n1.path, [n1, n0])
        self.assertEqual(n2.path, [n2, n0])
        self.assertEqual(n11.path, [n11, n1, n0])
        self.assertEqual(n12.path, [n12, n1, n0])
        self.assertEqual(n21.path, [n21, n2, n0])
        self.assertEqual(n22.path, [n22, n2, n0])

        # root
        self.assertIs(n1.root, n0)
        self.assertIs(n2.root, n0)
        self.assertIs(n11.root, n0)
        self.assertIs(n12.root, n0)
        self.assertIs(n21.root, n0)
        self.assertIs(n21.root, n0)

    def testReParent(self):
        n0 = moosetree.Node()
        n1 = moosetree.Node(n0)
        n2 = moosetree.Node(n0)

        self.assertIsNone(n0.parent)
        self.assertEqual(n0.children, [n1, n2])
        self.assertIs(n1.parent, n0)
        self.assertEqual(n1.children, [])
        self.assertIs(n2.parent, n0)
        self.assertEqual(n2.children, [])
        self.assertEqual(n2.children, [])

        n2.parent = n1
        self.assertIsNone(n0.parent)
        self.assertEqual(n0.children, [n1])
        self.assertIs(n1.parent, n0)
        self.assertEqual(n1.children, [n2])
        self.assertIs(n2.parent, n1)

    def testAppend(self):
        n0 = moosetree.Node()
        n1 = moosetree.Node()
        n2 = moosetree.Node()

        self.assertIsNone(n0.parent)
        self.assertEqual(n0.children, [])
        self.assertIsNone(n1.parent)
        self.assertEqual(n1.children, [])
        self.assertIsNone(n2.parent)
        self.assertEqual(n2.children, [])
        self.assertEqual(len(n0), 0)

        n0.append(n1, n2)
        self.assertIsNone(n0.parent)
        self.assertEqual(n0.children, [n1, n2])
        self.assertEqual(len(n0), 2)
        self.assertIs(n1.parent, n0)
        self.assertEqual(n1.children, [])
        self.assertIs(n2.parent, n0)
        self.assertEqual(n2.children, [])

        n1.append(n2)
        self.assertIsNone(n0.parent)
        self.assertEqual(n0.children, [n1])
        self.assertEqual(len(n0), 1)
        self.assertIs(n1.parent, n0)
        self.assertEqual(n1.children, [n2])
        self.assertIs(n2.parent, n1)

    def testInsert(self):
        n0 = moosetree.Node()
        n1 = moosetree.Node(n0)
        n2 = moosetree.Node()
        n3 = moosetree.Node(n0)

        self.assertIsNone(n0.parent)
        self.assertEqual(n0.children, [n1, n3])
        self.assertIs(n1.parent, n0)
        self.assertEqual(n1.children, [])
        self.assertIsNone(n2.parent)
        self.assertEqual(n2.children, [])
        self.assertIs(n3.parent, n0)
        self.assertEqual(n3.children, [])

        n0.insert(1, n2)
        self.assertIsNone(n0.parent)
        self.assertEqual(n0.children, [n1, n2, n3])
        self.assertIs(n1.parent, n0)
        self.assertEqual(n1.children, [])
        self.assertIs(n2.parent, n0)
        self.assertEqual(n2.children, [])
        self.assertIs(n3.parent, n0)
        self.assertEqual(n3.children, [])

    def testProperty(self):

        @moosetree.addProperty('prop')
        class MyNode(moosetree.Node):
            pass

        node = MyNode()
        self.assertTrue(hasattr(node, 'prop'))
        self.assertIsNone(node.prop)
        node.prop = 1
        self.assertEqual(node.prop, 1)
        node.prop = 'foo'
        self.assertEqual(node.prop, 'foo')

        node = MyNode(prop=1)
        self.assertEqual(node.prop, 1)

    def testPropertyRequired(self):

        @moosetree.addProperty('prop', required=True)
        class MyNode(moosetree.Node):
            pass

        with self.assertRaises(MooseException) as e:
            node = MyNode()
        self.assertIn("The property 'prop' is required.", e.exception.message)

        node = MyNode(prop=1)
        self.assertEqual(node.prop, 1)

    def testPropertyDefault(self):
        @moosetree.addProperty('prop', default=12345)
        class MyNode(moosetree.Node):
            pass
        node = MyNode()
        self.assertEqual(node.prop, 12345)
        node.prop = 'combo'
        self.assertEqual(node.prop, 'combo')

        node = MyNode(prop=34567)
        self.assertEqual(node.prop, 34567)

    def testPropertyType(self):
        @moosetree.addProperty('prop', ptype=int)
        class MyNode(moosetree.Node):
            pass

        node = MyNode()
        self.assertIsNone(node.prop)
        with self.assertRaises(MooseException) as e:
            node.prop = 'foo'
        self.assertIn("The supplied property 'prop' must be of type 'int', but 'str' was provided.",
                      e.exception.message)

        node.prop = 12345
        self.assertEqual(node.prop, 12345)

    def testPropertyInheritance(self):

        @moosetree.addProperty('prop0')
        class N0(moosetree.Node):
            pass

        @moosetree.addProperty('prop1')
        class N1(N0):
            pass

        n0 = N0(prop0=1)
        self.assertTrue(hasattr(n0, 'prop0'))
        self.assertFalse(hasattr(n0, 'prop1'))
        self.assertEqual(n0.prop0, 1)

        n1 = N1(prop0=2, prop1=3)
        self.assertTrue(hasattr(n1, 'prop0'))
        self.assertTrue(hasattr(n1, 'prop1'))
        self.assertEqual(n1.prop0, 2)
        self.assertEqual(n1.prop1, 3)

    def testMixedTreeWithProperties(self):
        @moosetree.addProperty('prop0')
        class N0(moosetree.Node):
            pass

        @moosetree.addProperty('prop1')
        class N1(moosetree.Node):
            pass

        root = moosetree.Node()
        c0 = N0(root, prop0=0)
        c1 = N1(root, prop1=1)

        self.assertEqual(root.children, [c0, c1])
        self.assertIs(c0.parent, root)
        self.assertIs(c1.parent, root)
        self.assertIsInstance(root.children[0], N0)
        self.assertIsInstance(root.children[1], N1)

        self.assertEqual(c0.prop0, 0)
        self.assertEqual(c1.prop1, 1)

    def testAttributes(self):

        @moosetree.addProperty('bar')
        class N(moosetree.Node):
            pass

        n = N(foo=1)
        self.assertFalse(hasattr(n, 'foo'))
        self.assertIn('foo', n)
        self.assertNotIn('bar', n)
        self.assertEqual(n['foo'], 1)

        n['foo'] = 2
        self.assertEqual(n['foo'], 2)


    def testDict(self):

        n0 = moosetree.Node()
        n1 = moosetree.Node(n0)

        print n0.dict()

    def testPickle(self):

        n0 = moosetree.Node()
        n1 = moosetree.Node(n0)
        n2 = moosetree.Node(n0)
        n11 = moosetree.Node(n1)
        n12 = moosetree.Node(n1)
        n21 = moosetree.Node(n2)
        n22 = moosetree.Node(n2)

        filename = 'tmpNodeData.pk1'
        with open(filename, 'w+') as fid:
            pickle.dump(n0, fid, -1)
        with open(filename, 'r') as fid:
            m0 = pickle.load(fid)xf

        print m0


if __name__ == '__main__':
    unittest.main(module=__name__, verbosity=2)
