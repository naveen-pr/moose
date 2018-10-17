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

def tokenize(nodes, conn, translator):
    for node in nodes:
        root = tokens.Token(None)
        translator.reader.tokenize(root, node.content, node)
        conn.send(node._unique_id)
        conn.send(root)
    conn.send(PROCESS_FINISHED)

def tokenize2(nodes, q, translator):
    for node in nodes:
        root = tokens.Token(None)
        translator.reader.tokenize(root, node.content, node)
        q.put((node._unique_id, root))

def runProcess(target, translator, nodes, args=tuple(), attributes=0, num_threads=1):
    start = time.time()
    jobs = []
    for i, n in enumerate(nodes):
        n._Page__unique_id = i

    for chunk in mooseutils.make_chunks(nodes, num_threads):
        conn1, conn2 = multiprocessing.Pipe()
        p = multiprocessing.Process(target=target, args=(chunk, conn2, translator) + args)
        p.daemon = True
        p.start()
        jobs.append((p, conn1, conn2))

    data = dict()
    while any(job[0].is_alive() for job in jobs):
        for job, conn1, conn2 in jobs:
            if conn1.poll():
                uid = conn1.recv()
                if uid == PROCESS_FINISHED:
                    conn1.close()
                    job.join()
                    break
               #data[uid] = list()
                for i in xrange(attributes):
                    conn1.recv()
    return time.time() - start, data

def tokenize3(nodes, conn, translator):
    for node in nodes:
        root = translator.reader.getRoot()
        translator.reader.tokenize(root, node.read(), node)
        conn.send(node._Page__unique_id)
        conn.send(root)
    conn.send(PROCESS_FINISHED)

def render3(nodes, conn, translator):
    for node in nodes:
        root = translator.reader.getRoot()
        translator.reader.tokenize(root, node.read(), node)
        conn.send(node._Page__unique_id)
        conn.send(root)
    conn.send(PROCESS_FINISHED)




if __name__ == '__main__':
    #config = 'materialize.yml'
    config = os.path.join(os.getenv('MOOSE_DIR'), 'modules', 'doc', 'config.yml')
    translator, _ = common.load_config(config)
    translator.init()


    num_threads = 2

    nodes = [n for n in anytree.PreOrderIter(translator.root)]
    source_nodes = [n for n in nodes if isinstance(n, pages.SourceNode)]


    if True:
        t, ast = runProcess(tokenize3, translator, source_nodes, attributes=1, num_threads=num_threads)

        print t



    # CURRENT FUNCTIONS
    elif False:
        translator.read(nodes, 1)
        translator.executeExtensionFunction('preExecute', translator.root)
        start = time.time()
        translator.tokenize(source_nodes, num_threads)
        print 'CURRENT:', time.time() - start, [n.ast.height for n in source_nodes]

    # PIPE VERSION
    elif False:
        translator.read(nodes, 1)
        translator.executeExtensionFunction('preExecute', translator.root)

        for i, n in enumerate(source_nodes):
            n._unique_id = i
        t = runProcess(tokenize,
                       translator,
                       source_nodes,
                       num_threads=num_threads,
                       attributes=('_ast', ))

        """
        start = time.time()
        jobs = []
        for chunk in mooseutils.make_chunks(source_nodes, num_threads):
            conn1, conn2 = multiprocessing.Pipe()
            p = multiprocessing.Process(target=tokenize, args=(chunk, conn2, translator))
            p.daemon = True
            p.start()
            jobs.append((p, conn1, conn2))

        while any(job[0].is_alive() for job in jobs):
            for job, conn1, conn2 in jobs:
                if conn1.poll():
                    uid = conn1.recv()
                    if uid is None:
                        conn1.close()
                        job.join()
                        break
                    root = conn1.recv()
                    source_nodes[uid]._ast = root
        """

        print 'PIPE:', t, [n.ast.height for n in source_nodes]


    # Queue
    else:
        translator.read(nodes, 1)
        translator.executeExtensionFunction('preExecute', translator.root)

        for i, n in enumerate(source_nodes):
            n._unique_id = i

        start = time.time()
        manager = multiprocessing.Manager()
        queue = manager.Queue(len(source_nodes))
        jobs = []
        for chunk in mooseutils.make_chunks(source_nodes, num_threads):
            p = multiprocessing.Process(target=tokenize2, args=(chunk, queue, translator))
            p.daemon = True
            p.start()
            jobs.append(p)

        for job in jobs:
            job.join()

        while not queue.empty():
            uid, ast = queue.get()
            source_nodes[uid]._ast = ast


        print 'Queue:', time.time() - start, [n.ast.height for n in source_nodes]
