#!/usr/bin/env python2
import time
import cProfile as profile
import cPickle as pickle
import StringIO
import pstats
import anytree

import moosetree

def run_profile(func, *args):
    pr = profile.Profile()
    start = time.time()
    pr.runcall(func, *args)
    print 'Total Time:', time.time() - start
    s = StringIO.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('tottime')
    ps.print_stats()
    print s.getvalue()

def run_pickle(root):
    start = time.time()
    filename = 'tmp.pickle'
    with open(filename, 'w+') as fid:
        pickle.dump(root, fid, -1)
    with open(filename, 'r') as fid:
        out = pickle.load(fid)
    print 'Total Time:', time.time() - start
    return out

def build_tree(cls, count):
    root = cls(None)
    for i in range(count):
        n0 = cls(root)
        for j in range(count):
            n1 = cls(n0)
    stop = time.time()
    return root

if __name__ == '__main__':
    N = 1000

    """
    print 'ANYTREE--------------------------'
    run_profile(build_tree, anytree.Node, N)
    print 'MOOSETREE------------------------'
    run_profile(build_tree, moosetree.Node, N)
    """


    print 'ANYTREE--------------------------'
    run_pickle(build_tree(anytree.Node, N))
    print 'MOOSETREE------------------------'
    run_pickle(build_tree(moosetree.Node, N))
