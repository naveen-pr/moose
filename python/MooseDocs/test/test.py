#!/usr/bin/env python
import os
import time
import anytree
import livereload
import copy
import uuid
import ctypes
import random
import collections
import mooseutils
import MooseDocs
from MooseDocs import common
from MooseDocs.base.translators import Meta
from MooseDocs.tree import pages, tokens, to_dict

import logging
logging.basicConfig()

import multiprocessing

"""
Parallel Complete build (no heading)
  j2: 268
  j12: 129
  j24: 87

Read only (j24):
  Parallel: 0.44
    Serial: 0.84

  Read + AST via Translator (j24):
  Parallel: 55.7
    Serial:

"""

if __name__ == '__main__':

    """
     TIMING: MOOSE_TEST, j24, read, ast only
     Parallel, Serial
     9.8, 56.6 (all on)
     3.3, 17.9

     MODULES/DOC
       8.0, 43.8 (5.5) - all off, read, ast
       16.9, 108.2 (6.4) - all off, read, ast, render, write

    """

    def build(translator, node):
        content = translator.reader.read(node)
        meta = Meta(translator.extensions)
        translator._Translator__executeExtensionFunction('updateMetaData', meta, content, node)

        ast = translator.reader.getRoot()
        translator._Translator__updateConfigurations(meta)
        translator._Translator__executeExtensionFunction('preTokenize', ast, node)
        translator.reader.tokenize(ast, content, node)
        translator._Translator__executeExtensionFunction('postTokenize', ast, node)

        result = translator.renderer.getRoot()
        translator._Translator__executeExtensionFunction('preRender', result, node)
        translator.renderer.render(result, ast, node)
        translator._Translator__executeExtensionFunction('postRender', result, node)
        translator._Translator__renderer.write(node, result)

        translator._Translator__resetConfigurations()

    def target(translator, nodes):
        for node in nodes:
            build(translator, node)


    #config = 'materialize.yml'
    config = os.path.join(os.getenv('MOOSE_DIR'), 'modules', 'doc', 'config.yml')
   #config = os.path.join(os.getenv('MOOSE_DIR'), 'test', 'doc', 'config.yml')
    translator, _ = common.load_config(config)
    translator.init()

    num_threads = 24
    nodes = [n for n in anytree.PreOrderIter(translator._Translator__root)]
    source_nodes = [n for n in nodes if isinstance(n, pages.SourceNode)]
    num_nodes = len(source_nodes)

    if True:
        start = time.time()
        translator._Translator__executeExtensionFunction('preExecute', translator.root)

        jobs = []
        for chunk in mooseutils.make_chunks(source_nodes, num_threads):
            p = multiprocessing.Process(target=target, args=(translator, chunk))
            p.start()
            jobs.append(p)

        for job in jobs:
            job.join()

        translator._Translator__executeExtensionFunction('postExecute', translator.root)
        print 'Parallel', time.time() - start

        #mooseutils.run_profile(run)

    # Serial build
    if True:
        start = time.time()
        translator._Translator__executeExtensionFunction('preExecute', translator.root)
        for node in source_nodes:
            build(translator, node)
        translator._Translator__executeExtensionFunction('postExecute', translator.root)
        print 'Serial', time.time() - start

    if False:
        server = livereload.Server()
        server.serve(root=translator['destination'])
