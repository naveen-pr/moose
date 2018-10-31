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
import mooseutils
import MooseDocs
from MooseDocs.common import exceptions, mixins, check_type
from MooseDocs.tree import base, tokens

LOG = logging.getLogger(__name__)

@mooseutils.addProperty('base', ptype=str)   # set by Translator::init
@mooseutils.addProperty('source', ptype=str, required=True) # supplied source file/directory
class Page(mooseutils.AutoPropertyMixin):
    """
    Base class for input content that defines the methods called by the translator.

    This classes uses properties to minimize modifications after construction.
    """
    def __init__(self, fullname, **kwargs):
        super(Page, self).__init__(**kwargs)

        self._fullname = fullname            # local path of the node
        self._name = fullname.split('/')[-1] # file/folder name
        self._dependencies = set()           # page names that depend on this page
        self.__unique_id = None              # internal id that should not be used

    def buildIndex(self, home):
        """Return the index for this page."""
        return None

    @property
    def name(self):
        """Return the name of the page (i.e., the directory or filename)."""
        return self._name

    @property
    def dependencies(self):
        """A set of Page object that depend on this page."""
        return self._dependencies

    @property
    def local(self):
        """Returns the local directory/filename."""
        return self._fullname

    @property
    def destination(self):
        """Returns the translator destination location."""
        return os.path.join(self.base, self.local)

    def addDependency(self, other):
        """Add a Page object as a dependency to this page."""
        if MooseDocs.LOG_LEVEL == logging.DEBUG:
            check_type('other', other, str)
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

    def __str__(self):
        """Define the anytree screen output."""
        return '{}: {}, {}'.format(mooseutils.colorText(self.__class__.__name__, self.COLOR),
                                   self.local, self.source)

class Directory(Page):
    """
    Directory nodes.
    """
    COLOR = 'CYAN'

class File(Page):
    """
    File nodes.

    General files that need to be copied to the output directory.
    """
    COLOR = 'MAGENTA'

class Source(File):
    """
    Node for content that is being converted (e.g., Markdown files).
    """
    COLOR = 'YELLOW'
    def __init__(self, *args, **kwargs):
        self._output_extension = kwargs.pop('output_extension', None)
        super(File, self).__init__(*args, **kwargs)

    @property
    def destination(self):
        """The content destination (override)."""
        _, ext = os.path.splitext(self.source)
        return super(Source, self).destination.replace(ext, self._output_extension)

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
            location = urlparse.urlsplit(self.destination.replace(self._base, home)) \
                       ._replace(scheme=None, netloc=None, fragment=str(section['id'])).geturl()
            index.append(dict(name=name, text=text, location=location))

        return index
