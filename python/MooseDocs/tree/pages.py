#pylint: disable=missing-docstring,no-member
#* This file is part of the MOOSE framework
#* https://www.mooseframework.org
#*
#* All rights reserved, see COPYRIGHT for full restrictions
#* https://github.com/idaholab/moose/blob/master/COPYRIGHT
#*
#* Licensed under LGPL 2.1, please see LICENSE for details
#* https://www.gnu.org/licenses/lgpl-2.1.html
#pylint: enable=missing-docstring
import os
import shutil
import logging
import codecs
import types
import urlparse

import anytree

import MooseDocs
from MooseDocs import common
from MooseDocs.common import exceptions, mixins
from MooseDocs.tree import base, tokens

LOG = logging.getLogger(__name__)

class Page(base.NodeBase):
    """
    Base class for input content that defines the methods called by the translator.

    This classes uses properties to minimize modifications after construction.
    """
    COLOR = None
    PROPERTIES = [base.Property('source', ptype=str),
                  base.Property('base', ptype=str, default='')]

    def __init__(self, *args, **kwargs):
        base.NodeBase.__init__(self, *args, **kwargs)

        # Anytree property
        self.name = os.path.basename(self.source)

        # Complete path of the node
        self._fullpath = os.path.join(self.parent.fullpath, self.name) if self.parent else self.name

        # The following are set by the Translator object.
        #self._content = None
        #self._meta = None
        #self._ast = None
        #self._index = None
        #self._result = None
        self._dependencies = set()

        # A unique ID used by the translator during parallel computations for data communication,
        # this should not be used, it is changed by the translator prior to each parallel run.
        #self.__unique_id = None

        # File/directory modification time
        #self._modified = 0
        #if self.source and os.path.exists(self.source):
        #    self._modified = os.path.getmtime(self.source)

    # TODO: Move read() to reader: read(page)
    # TODO: Move write() to renderer: write(page, result)

    #def read(self):
    #    """Return content for the page."""
    #    return None

    def buildIndex(self, home):
        """Return the index for this page."""
        return None

    #def write(self): #TODO: This should take the result
    #    """
    #    Write the to the destination.
    #    """
    #    pass

    @property
    def fullpath(self):
        return self._fullpath

    #@property
    #def content(self):
    #    """Return the read content for the page (this can be None)."""
    #    return self._content

    #@property
    #def meta(self):
    #    """Return the meta data for this page."""
    #    return self._meta

    #@property
    #def ast(self):
    #    """Return the AST for the page (this can be None)."""
    #    return self._ast

    #@property
    #def index(self):
    #    """Return the index."""
    #    return self._index

    #@property
    #def result(self):
    #    """Return the rendered result for this page (this can be None)."""
    #    return self._result

    @property
    def dependencies(self):
        """A set of Page object that depend on this page."""
        return self._dependencies

    @property
    def local(self):
        """Returns the local directory/filename."""
        return self.fullpath

    @property
    def destination(self):
        """Returns the translator destination location."""
        return os.path.join(self.base, self.local)

    def addDependency(self, other):
        """Add a Page object as a dependency to this page."""
        if MooseDocs.LOG_LEVEL == logging.DEBUG:
            common.check_type('other', other, str)
        self._dependencies.add(other)

    def modified(self):
        """
        Returns True if the content has been modified from the last call.
        """
        if self.source and os.path.exists(self.source):
            return os.path.getmtime(self.source) > self._modified
        return True

    def relativeSource(self, other):
        """ Location of this page related to the other page."""
        return os.path.relpath(self.local, os.path.dirname(other.local))

    def relativeDestination(self, other):
        """
        Location of this page related to the other page.

        Inputs:
            other[LocationNodeBase]: The page that this page is relative too.
        """
        return os.path.relpath(self.destination, os.path.dirname(other.destination))

    def console(self):
        """Define the anytree screen output."""
        return '{} ({}): fullpath={}, {}'.format(self.name, self.__class__.__name__, self.fullpath, self.source)

class DirectoryNode(Page):
    """
    Directory nodes.
    """
    COLOR = 'CYAN'
    def write(self):
        """
        Write the to the destination.
        """
        create_directory(self.destination)

class FileNode(Page):
    """
    File nodes.

    General files that need to be copied to the output directory.
    """
    COLOR = 'MAGENTA'

class SourceNode(FileNode):
    """
    Node for content that is being converted (e.g., Markdown files).
    """
    COLOR = 'YELLOW'
    PROPERTIES = [base.Property('output_extension', ptype=str, required=True)]

    @property
    def destination(self):
        """The content destination (override)."""
        _, ext = os.path.splitext(self.source)
        return super(SourceNode, self).destination.replace(ext, self.output_extension)

    def buildIndex(self, home):
        """
        Build the search index.

        TODO: This only works with materialize output, is it possible to make this work with other
              formats. There also needs to be a check on the output type.

        This should just go away an be put in the postRender method of an Extension, the
        method could check the renderer type to do what it needs.

        This might need to be a method on Renderer because it requires data communication or could
        the Meta object be used for this, if it doesn't go away?
        """
        if self._result is None:
            return []

        index = []
        for section in anytree.search.findall_by_attr(self._result, 'section'):
            name = self.name.replace('_', ' ')
            if name.endswith('.md'):
                name = name[:-3]
            text = section['data-section-text']
            location = urlparse.urlsplit(self.destination.replace(self.base, home)) \
                       ._replace(scheme=None, netloc=None, fragment=str(section['id'])).geturl()
            index.append(dict(name=name, text=text, location=location))

        return index
