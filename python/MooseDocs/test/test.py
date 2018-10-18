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

PROCESS_FINISHED = -1


def build(reader, renderer, nodes, data, lock):
    pid = multiprocessing.current_process()

    lock.acquire()
    print pid.name, [n._id for n in nodes]
    lock.release()

    for node in nodes:
        root = reader.getRoot()
        reader.tokenize(root, reader.read(node), node)
        data[node._id] = root

    lock.acquire()
    lock.release()

    for node in nodes:
        root = renderer.getRoot()
        renderer.render(root, data[node._id], node)


if __name__ == '__main__':
    config = 'materialize.yml'
    #config = os.path.join(os.getenv('MOOSE_DIR'), 'modules', 'doc', 'config.yml')
    translator, _ = common.load_config(config)
    translator.init()

    num_threads = 2
    nodes = [n for n in anytree.PreOrderIter(translator._Translator__root)]
    source_nodes = [n for n in nodes if isinstance(n, pages.SourceNode)]
    num_nodes = len(source_nodes)

    manager = multiprocessing.Manager()
    lock = manager.Lock()
    translator.__page_syntax_trees = manager.list([None]*num_nodes)

    start = time.time()
    jobs = []
    for i, n in enumerate(source_nodes):
        n._id = i

    for chunk in mooseutils.make_chunks(source_nodes, num_threads):
        p = multiprocessing.Process(target=build,
                                    args=(translator.reader, translator.renderer, chunk, translator.__page_syntax_trees, lock))
        p.start()
        jobs.append(p)

    for job in jobs:
        job.join()

    t = time.time() - start
