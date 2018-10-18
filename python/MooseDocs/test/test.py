#!/usr/bin/env python
import os
import time
import anytree
import copy
import uuid
import ctypes
import random
import collections
import mooseutils
import MooseDocs
from MooseDocs import common
from MooseDocs.tree import pages, tokens, to_dict

import logging
logging.basicConfig()

import multiprocessing
from multiprocessing.queues import SimpleQueue

PROCESS_FINISHED = -1


def tokenize3(nodes, conn, translator):
    for node in nodes:
        root = translator._Translator__reader.getRoot()
        translator._Translator__reader.tokenize(root, node.read(), node)
        conn.send(node._Page__unique_id)
        conn.send(root)
        conn.send(node.dependencies)
    conn.send(PROCESS_FINISHED)

if __name__ == '__main__':
    config = 'materialize.yml'
    #config = os.path.join(os.getenv('MOOSE_DIR'), 'modules', 'doc', 'config.yml')
    translator, _ = common.load_config(config)
    translator.init()



    num_threads = 12
    nodes = [n for n in anytree.PreOrderIter(translator._Translator__root)]
    source_nodes = [n for n in nodes if isinstance(n, pages.SourceNode)]
    N = len(source_nodes)

    #translator._manager = multiprocessing.Manager()
    _ast = list([None]*N)# translator._manager.list([None]*N)
    translator._dep = list([None]*N)# translator._manager.list([None]*N)


    start = time.time()
    jobs = []
    for i, n in enumerate(source_nodes):
        n._Page__unique_id = i

    for chunk in mooseutils.make_chunks(source_nodes, num_threads):
        conn1, conn2 = multiprocessing.Pipe()
        p = multiprocessing.Process(target=tokenize3, args=(chunk, conn2, translator))
        p.daemon = True
        p.start()
        jobs.append((p, conn1, conn2))

    while any(job[0].is_alive() for job in jobs):
        for job, conn1, conn2 in jobs:
            if conn1.poll():
                uid = conn1.recv()
                if uid == PROCESS_FINISHED:
                    conn1.close()
                    job.join()
                    continue
                #local = list()
                for i in xrange(1):
                   _ast[uid] = conn1.recv()
                   translator._dep[uid] = conn1.recv()
                    #d = conn1.recv()
                    #print type(d), os.getpid()
                    #data.append(d)
                    #print conn1.recv()
                    #data.append(conn1.recv())
                #print local
                #data[uid] = local

    #for job, _, _ in jobs:
    #    job.join()

    t = time.time() - start

    print _ast[12] #source_nodes[12]._foo
