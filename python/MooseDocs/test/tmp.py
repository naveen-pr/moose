import time
import anytree
import logging
import collections
import MooseDocs
from MooseDocs.tree import base

Prop = collections.namedtuple('Property', 'default ptype')

class Property(object):
    def __init__(self, name, default=None, ptype=None):
        self.name = name
        self.default = default
        self.ptype = ptype

def checkProperty(*props):
    def create(cls, *args, **kwargs):
        if MooseDocs.LOG_LEVEL == logging.DEBUG:
            pass
        return cls(*args, **kwargs)
    return create

#def newToken(name, **defaults):
"""
TOO SLOW...
def newToken(name, *props):
    defaults = dict()
    for prop in props:
        defaults[prop.name.rstrip('_')] = prop.default

    def tokenGenerator(parent, **kwargs):
        if MooseDocs.LOG_LEVEL == logging.DEBUG:
            # TODO: perform type checking here
            pass
        kwargs = {key.rstrip('_'): value for key, value in kwargs.iteritems()}
        defaults.update(**kwargs)
        return anytree.Node(name, parent, **defaults)

    return tokenGenerator
"""

class Node(anytree.NodeMixin):
    def __init__(self, name, parent=None, **kwargs):
        self.name = name
        self.parent = parent
        self.__attributes = kwargs

def newToken(name, **defaults):
    if MooseDocs.LOG_LEVEL == logging.DEBUG:
        pass
    #defaults = {key: value[0] for key, value in defaults.iteritems()}
    defaults = {key:value[0] for key, value in defaults.iteritems()}

    #for key in defaults.keys():
    #    if key.endswith('_'):
    #        defaults[key[:-1]] = defaults[key]
    #defaults = {key.rstrip('_'): value for key, value in defaults.iteritems()}

    # NOTE: stripping _ is too slow
    # TODO: make a debug version with type checking


    def tokenGenerator(parent, **kwargs):
        if MooseDocs.LOG_LEVEL == logging.DEBUG:
            pass

        defaults.update(**kwargs)

        #return Node(name, parent, **defaults)
        return anytree.Node(name, parent, **defaults)

    return tokenGenerator

""" tree.newToken... """


#Word = newToken('Word', foo=None, bar=list())
#Word = newToken('Word', foo=(None, int, True), bar=([], list))
Word = newToken('Word',
                #Property('foo', None, int),
                #Property('bar', 42, float))
                foo=(None, int),
                bar=([], list))


#DEBUG could build Properties that perform type checking
#Word = newToken('Word', Property('foo', int, None), Property('bar', float, 42))

N = 1000000
def run(func, *args, **kwargs):
    start = time.time()
    for i in xrange(N):
        func(*args, **kwargs)
    return time.time() - start

#print 'NodeBase:', run(A, foo=2, bar='bar')
print 'Node', run(anytree.Node, 'name', None, foo=2, bar='bar')
print 'Word', run(Word, None, foo=2, bar='bar')



"""
class A(object):
    pass

x = int(1)


print timeit.timeit('1 == 42', number=1000000)
print timeit.timeit('"foo" == "bar"', number=1000000)
print timeit.timeit('isinstance("bar", int)', number=1000000)
"""
