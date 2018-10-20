"""
Module that defines Translator objects for converted AST from Reader to Rendered output from
Renderer objects. The Translator objects exist as a place to import extensions and bridge
between the reading and rendering content.
"""
import os
import logging
import time
import json
import random
import multiprocessing
import anytree

import mooseutils

import MooseDocs
from MooseDocs import common
from MooseDocs.common import mixins, exceptions
from MooseDocs.tree import pages, tokens
from components import Extension
from readers import Reader
from renderers import Renderer, MaterializeRenderer

LOG = logging.getLogger('MooseDocs.Translator')

class Meta(object):
    """
    Meta data object for data on the pages.Page objects.

    The primary purpose for this object is to enable the ability to modify configurations of the
    reader, renderer, and extension objects from within an extension (i.e., the config extension).

    However, it is possible to store arbitrary data in the 'user' key. All data for this object
    is set in the Extension::updateMeta method. This method is called by the Translator the
    configuration keys are automatically applied to the correct objects during tokenization and
    rendering.
    """
    def __init__(self, extensions):
        self.__config = dict(user=dict(), reader=dict(), renderer=dict())
        for ext in extensions:
            self.__config[ext.__class__.__name__] = dict()

    def updateConfig(self, key, **kwargs):
        self.__config[key].update(kwargs)

    def getConfig(self, key):
        return self.__config[key]

class Translator(mixins.ConfigObject):
    """
    Object responsible for converting reader content into an AST and rendering with the
    supplied renderer.

    Inputs:
        content[page.Page]: A tree of input "pages".
        reader[Reader]: A Reader instance.
        renderer[Renderer]: A Renderer instance.
        extensions[list]: A list of extensions objects to use.
        kwargs[dict]: Key, value pairs applied to the configuration options.

    This class is the workhorse of MOOSEDocs, it is the hub for all data in and out.  It is not
    designed to be customized and extensions have no access to this the class.
    """
    #: A multiprocessing lock. This is used in various locations, mainly prior to caching items
    #  as well as during directory creation.
    LOCK = multiprocessing.Lock()

    #: A code for indicating that parallel work is done, see __runProcess
    PROCESS_FINISHED = -1

    @staticmethod
    def defaultConfig():
        config = mixins.ConfigObject.defaultConfig()
        config['destination'] = (os.path.join(os.getenv('HOME'), '.local', 'share', 'moose',
                                              'site'),
                                 "The output directory.")
        config['incremental_build'] = (False,
                                       "Do a complete build (default) or incremental build.")
        return config

    def __init__(self, content, reader, renderer, extensions, **kwargs):
        mixins.ConfigObject.__init__(self, **kwargs)

        if MooseDocs.LOG_LEVEL == logging.DEBUG:
            common.check_type('content', content, pages.Page)
            common.check_type('reader', reader, Reader)
            common.check_type('renderer', renderer, Renderer)
            common.check_type('extensions', extensions, list)
            for ext in extensions:
                common.check_type('extensions', ext, Extension)

        self.__initialized = False
        self.__root = content
        self.__extensions = extensions
        self.__reader = reader
        self.__renderer = renderer
        self.__destination = None # assigned during init()

        # Members used during conversion, see execute (only used with incremental build)
        self.__page_syntax_trees = None
        self.__page_meta_data = None
        self.__page_dependencies = None

    @property
    def extensions(self):
       """Return list of loaded Extension objects."""
       return self.__extensions

    @property
    def reader(self):
       """Return the Reader object."""
       return self.__reader

    @property
    def renderer(self):
       """Return the Renderer object."""
       return self.__renderer

    @property
    def root(self):
       """Return the root page of the documents being translated."""
       return self.__root

    def update(self, **kwargs):
        """Update configuration and handle destination."""
        dest = kwargs.get('destination', None)
        if dest is not None:
            kwargs['destination'] = mooseutils.eval_path(dest)
        mixins.ConfigObject.update(self, **kwargs)

    def getSyntaxTree(self, page):
        """
        Return the AST for the supplied page, this is used by the RenderComponent.

        see Translator::execute and RenderComponent::setTranslator/getSyntaxTree
        """
        ast = self.__page_syntax_trees[page._Page__unique_id]
        if ast is None:
            content = self.reader.read(page)
            ast = self.reader.getRoot()
            self.reader.tokenize(ast, content, page)
            self.__page_syntax_trees[page._Page__unique_id] = ast
        return ast

    def init(self):
        """
        Initialize the translator with the output destination for the converted content.

        This method also initializes all the various items within the translator for performing
        the conversion. It is required to allow the build command to modify configuration items
        (i.e., the 'destination' option) prior to setting up the extensions.

        Inputs:
            destination[str]: The path to the output directory.
        """
        if self.__initialized:
            msg = "The {} object has already been initialized, this method should not " \
                  "be called twice."
            raise MooseDocs.common.exceptions.MooseDocsException(msg, type(self))

        # Initialize the extension and call the extend method, then set the extension object
        # on each of the extensions.
        destination = self.get("destination")
        for ext in self.__extensions:
            common.check_type('extensions', ext, MooseDocs.base.components.Extension)
            ext.extend(self.__reader, self.__renderer)
            for comp in self.__reader.components:
                if comp.extension is None:
                    comp.extension = ext
            for comp in self.__renderer.components:
                comp.setTranslator(self) # see Translator::execute and RenderComponent::setTranslator
                if comp.extension is None:
                    comp.extension = ext

        # Check that the extension requirements are met
        for ext in self.__extensions:
            self.__checkRequires(ext)

        for node in anytree.PreOrderIter(self.__root):
            node.set('base', destination)

        self.__initialized = True

    def execute(self, num_threads=1, nodes=None):
        """
        Perform parallel build for all pages.

        Inputs:
            num_threads[int]: The number of threads to use (default: 1).
            nodes[list]: A list of Page object to build, if not provided all pages will be created.

        NOTE: There is still additional work that need to be done to improve the performance of this,


        The translator execute method is responsible for converting all pages.Page objects
        contained within the self.__root member variable, these shall be rewhiferred to as "pages"
        herein. The conversion process is as follows.

        1. Read all content from the pages, in parallel.
        2. Call Reader::preExecute, Renderer::preExecute, and Extension::preExecute.
        3. Tokenize the content from pages, in parallel, and on each page:
           a. Create the root node for the AST by calling Reader::getRoot()
           b. Prepare the AST by calling Reader::preTokenize and Extension::preTokenize.
           c. Create the AST by calling Reader::tokenize.
           d. Complete the AST by calling Reser::postTokenize and Extension::postTokenize.
        4. Create an index base on the AST, in parallel.
        5. Render the AST from pages, in parallel, and on each page:
           a. Create the root node for the results by calling Renderer::getRoot()
           b. Prepare the results by calling Render::preRender and Extension::preRender.
           c. Create the results by calling Render::render.
           d. Complete the results by calling Render::postRender and Extension::postRender.
        6. Call Reader::postExecute, Renderer::postExecute, and Extension::postExecute.
        7. Write the contents of the converted data.

        When the term "in parallel" is used above it refers to the use of the multiprocessing
        package. This package allows for concurrent execution of operations on each of the pages,
        but it requires some effort to maintain data on each of the page objects.

        Due to how the python interpreter operates direct shared memory is nearly impossible, so
        data must be passed via pickling. Most of this is handled automatically by the
        multiprocessing package, but certain container is required for it to work correctly. This
        is a multiprocessing.Manager().list() container for the problem at hand.

        In general, the following is preformed for each of the parallel operations listed above.

        1. The supplied pages are separated into chunks based on the number of threads.
        2. A multiprocessing.Process is created with a function that accepts a chunk as
           well as a shared list (see multiprocessing.Manager.list).
        3. The function loops through each page in the chunk and computes some data (e.g., a
           file is read and the content of this file is the data).
        4. The generated data is pushed into the shared list.
        5. The multiprocsssing.Process is completed.
        6. The data from the shared list is then assigned to the pages on the main process, this
           makes it available for the next step in the conversion process.

           This passing and updating is required because the Processes do not operate on the actual
           page objects created, they operate on proxies. Therefore, it is necessary to update the
           actual objects on the main process with the data computed by the proxies.

        TODO: Transferring the AST and rendered results tree is still a major performance bottleneck.
              It might be possible to improve performance by implementing a custom __getstate__
              method that only packages the attributes and properties.


        NOTES: Page object must limit stored data, because they all contain each other.

        """
        common.check_type('num_threads', num_threads, int)
        self.__assertInitialize()

        # Extract the SourceNodes for translation
        nodes = nodes or [n for n in anytree.PreOrderIter(self.__root)]
        source_nodes = [n for n in nodes if isinstance(n, pages.SourceNode)]
        other_nodes = [n for n in nodes if not isinstance(n, pages.SourceNode)]

        random.shuffle(source_nodes)

        # Assign an ID to each node for data transfer
        num_nodes = len(source_nodes)
        for i, n in enumerate(source_nodes):
            n._Page__unique_id = i

        start = time.time()
        LOG.info('Translating using %s threads...', num_threads)

        LOG.info('  Executing preExecute methods...')
        t = self.__executeExtensionFunction('preExecute', self.root)
        LOG.info('  Finished preExecute methods [%s sec]', t)

        if not self.get('incremental_build'):
        #if False:
            self.__page_syntax_trees = [None]*num_nodes # cache for getSyntaxTree
            LOG.info('  Building pages...')
            t = self.__build(source_nodes, num_threads)
            #self.__build_target(source_nodes)
            #t = None; mooseutils.run_profile(self.__build_target, source_nodes)
            LOG.info('  Building complete [%s sec.]', t)

        else:
            # Tokenization
            # These must be sized up front to work correctly with multiprocessing.Connection
            # object recv() method.
            self.__page_syntax_trees = [None]*num_nodes
            self.__page_meta_data = [None]*num_nodes
            self.__page_dependencies = [None]*num_nodes

            LOG.info('  Creating ASTs...')
            t = self.__tokenize(source_nodes, num_threads)
            LOG.info('  ASTs Finished [%s sec.]', t)

            # Rendering/writing
            LOG.info('  Rendering ASTs...')
            t = self.__render(source_nodes, num_threads)
            LOG.info('  Rendering Finished [%s sec.]', t)

        # Indexing/copying
        LOG.info('  Finalizing content...')
        t = self.__finalize(other_nodes, num_threads)
        LOG.info('  Finalizing Finished [%s sec.]', t)

        LOG.info('  Executing postExecute methods...')
        t =self.__executeExtensionFunction('postExecute', self.root)
        LOG.info('  Finished postExecute methods [%s sec]', t)

        LOG.info('Translating complete [%s sec.]', time.time() - start)

    def __build(self, source_nodes, num_threads):
        """Perform a complete build."""
        start = time.time()

        jobs = []
        for chunk in mooseutils.make_chunks(source_nodes, num_threads):
            p = multiprocessing.Process(target=self.__build_target, args=(chunk,))
            p.start()
            jobs.append(p)

        for job in jobs:
            job.join()

        return time.time() - start

    def __tokenize(self, source_nodes, num_threads):
        """Perform tokenization (see comments in execute method."""
        start = time.time()
        jobs = []
        for chunk in mooseutils.make_chunks(source_nodes, num_threads):
            conn1, conn2 = multiprocessing.Pipe()
            p = multiprocessing.Process(target=self._tokenize_target,
                                        args=(self, chunk, conn2))
            p.daemon = True
            p.start()
            jobs.append((p, conn1, conn2))

        while any(job[0].is_alive() for job in jobs):
            for job, conn1, conn2 in jobs:
                if conn1.poll():
                    uid = conn1.recv()
                    if uid == Translator.PROCESS_FINISHED:
                        conn1.close()
                        job.join()
                        continue

                    self.__page_syntax_trees[uid] = conn1.recv()
                    self.__page_dependencies[uid] = conn1.recv()
                    self.__page_meta_data[uid] = conn1.recv()

        return time.time() - start

    def __render(self, source_nodes, num_threads):
        """
        Perform renderering (see comments in execute method).
        """
        start = time.time()
        jobs = []
        for chunk in mooseutils.make_chunks(source_nodes, num_threads):
            p = multiprocessing.Process(target=self._render_target, args=(self, chunk))
            p.daemon = True
            p.start()
            jobs.append(p)

        for job in jobs:
            job.join()

        return time.time() - start

    def __finalize(self, other_nodes, num_threads):
        """
        Complete copying of non-source (e.g., images) files as well as perform indexing.
        """
        start = time.time()
        for node in other_nodes:
            self.renderer.write(node)
        return time.time() - start

    def __build_target(self, nodes):
        """multiprocessing target for translating pages."""
        for node in nodes:
            self.__build_page(node)

    def __build_page(self, node):
        """Build a single page."""
        content = self.reader.read(node)
        meta = Meta(self.__extensions)
        self.__executeExtensionFunction('updateMetaData', meta, content, node)

        ast = self.reader.getRoot()
        self.__updateConfigurations(meta)
        self.__executeExtensionFunction('preTokenize', ast, node)
        self.reader.tokenize(ast, content, node)
        self.__executeExtensionFunction('postTokenize', ast, node)

        result = self.renderer.getRoot()
        self.__executeExtensionFunction('preRender', result, node)
        self.renderer.render(result, ast, node)
        self.__executeExtensionFunction('postRender', result, node)
        self.__renderer.write(node, result)

        self.__resetConfigurations()

    @staticmethod
    def _tokenize_target(translator, nodes, conn):
        """multiprocessing target for the tokenize() method."""
        for node in nodes:
            try:
                content = translator.__reader.read(node)
                if content is not None:
                    meta = Meta(translator.__extensions)
                    translator.__executeExtensionFunction('updateMetaData', meta, content, node)
                    ast = translator.__reader.getRoot()
                    translator.__updateConfigurations(meta)
                    translator.__executeExtensionFunction('preTokenize', ast, node)
                    translator.__reader.tokenize(ast, content, node)
                    translator.__executeExtensionFunction('postTokenize', ast, node)
                    translator.__resetConfigurations()
                    conn.send(node._Page__unique_id)
                    conn.send(ast)
                    conn.send(node.dependencies)
                    conn.send(meta)

                elif isinstance(node, pages.SourceNode):
                    msg = "The source file, %s, does not contain any content."
                    LOG.warning(msg, node.source)

            except Exception as e:
                with Translator.LOCK:
                    msg = common.report_exception("Failed to tokenize: {}", node.source)
                    LOG.critical(msg)

        conn.send(Translator.PROCESS_FINISHED)

    @staticmethod
    def _render_target(translator, nodes):
        """multiprocessing target for the render() method."""
        for node in nodes:
            try:
                ast = translator.__page_syntax_trees[node._Page__unique_id]
                meta = translator.__page_meta_data[node._Page__unique_id]
                if ast is not None:
                    result = translator.__renderer.getRoot()
                    translator.__updateConfigurations(meta)
                    translator.__executeExtensionFunction('preRender', result, node)
                    translator.__renderer.render(result, ast, node)
                    translator.__executeExtensionFunction('postRender', result, node)
                    translator.__renderer.write(node, result)
                    translator.__resetConfigurations()

            except Exception as e:
                with Translator.LOCK:
                    msg = common.report_exception("Failed to render: {}", node.source)
                    LOG.critical(msg)

    def __executeExtensionFunction(self, name, *args, **kwargs):
        """Execute pre/post functions for extensions, reader, and renderer."""

        start = time.time()
        if MooseDocs.LOG_LEVEL == logging.DEBUG:
            common.check_type('name', name, str)

        if hasattr(self.__reader, name):
            getattr(self.__reader, name)(*args, **kwargs)

        if hasattr(self.__renderer, name):
            getattr(self.__renderer, name)(*args, **kwargs)

        for ext in self.__extensions:
            if ext.active:
                func = getattr(ext, name)
                func(*args, **kwargs)

        return time.time() - start

    def __updateConfigurations(self, meta):
        """Update configuration from meta data."""
        self.__reader.update(**meta.getConfig('reader'))
        self.__renderer.update(**meta.getConfig('renderer'))
        for ext in self.__extensions:
            ext.update(**meta.getConfig(ext.__class__.__name__))

    def __resetConfigurations(self):
        """Reset configuration to original state."""
        self.__reader.resetConfig()
        self.__renderer.resetConfig()
        for ext in self.__extensions:
            ext.resetConfig()

    def __assertInitialize(self):
        """Helper for asserting initialize status."""
        if not self.__initialized:
            msg = "The Translator.init() method must be called prior to executing this method."
            raise exceptions.MooseDocsException(msg)

    def __checkRequires(self, extension):
        """Helper to check the loaded extensions."""
        available = [e.__module__ for e in self.__extensions]
        messages = []
        for ext in extension._Extension__requires:
            if ext.__name__ not in available:
                msg = "The {} extension is required but not included.".format(ext.__name__)
                messages.append(msg)

        if messages:
            raise exceptions.MooseDocsException('\n'.join(messages))
