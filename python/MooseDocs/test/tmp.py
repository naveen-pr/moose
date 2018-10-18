import timeit
import anytree


def newToken(name, **kwargs):
    for key in kwargs.keys():
        if key.endswith('_'):
            kwargs[key[:-1]] = kwargs.pop(key)
    return lambda parent: anytree.Node(name, parent, **kwargs)


""" tree.newToken... """

Word = newToken('Word', string=None, class_=list())

w = Word(None)

print w, w.name




"""
class A(object):
    pass

x = int(1)


print timeit.timeit('1 == 42', number=1000000)
print timeit.timeit('"foo" == "bar"', number=1000000)
print timeit.timeit('isinstance("bar", int)', number=1000000)
"""
