#pylint: disable=missing-docstring, no-member
#* This file is part of the MOOSE framework
#* https://www.mooseframework.org
#*
#* All rights reserved, see COPYRIGHT for full restrictions
#* https://github.com/idaholab/moose/blob/master/COPYRIGHT
#*
#* Licensed under LGPL 2.1, please see LICENSE for details
#* https://www.gnu.org/licenses/lgpl-2.1.html
import collections
import logging
import json
import mooseutils

from MooseDocs import common
from MooseDocs.common import exceptions
from MooseDocs.tree.base import NodeBase

LOG = logging.getLogger(__name__)

def newToken(name, **defaults):
    """
    Function for creating Token objects with unique names and default attributes.

    TODO: Add a default system that has type checking and required checking (only in DEBUG)
    """
    if MooseDocs.LOG_LEVEL == logging.DEBUG:
        pass # Future consistency checking

    def tokenGenerator(parent, **kwargs):
        if MooseDocs.LOG_LEVEL == logging.DEBUG:
            pass # Future consistency checking
        defaults.update(**kwargs)
        return Token(name, parent, **defaults)

    return tokenGenerator

class Token(NodeBase):
    """
    Base class for AST tokens. All tokens are of this type, but should be generate with the
    newToken function to assign default attributes.

    Input:
        *args, **kwarg: (Optional) All arguments and key, value pairs supplied are stored in the
                        settings property and may be retrieved via the various access methods.
    """
    PROPERTIES = [Property('recursive', default=True, ptype=bool),
                  Property('string', ptype=unicode)]

    def __init__(self, parent=None, name=None, **kwargs):
        kwargs.setdefault('recursive', True)
        kwargs.setdefault('string', None)
        super(Token, self).__init__(parent, name, **kwargs)
        if self.string is not None: #pylint: disable=no-member
            String(self, content=self.string) #pylint: disable=no-member

    @property
    def info(self):
        """Retrieve the Information object from a parent node."""
        node = self
        while node._info is None: # use _info to prevent infinite loop
            if node.parent is None:
                break
            node = node.parent
        return node._info

    @info.setter
    def info(self, value):
        self._info = value

    def text(self):
        """
        Convert String objects into a single string.
        """
        strings = []
        for node in anytree.PreOrderIter(self):
            if node.name == 'String':
                strings.append(node.content)
        return u' '.join(strings)

    def write(self, _raw=False): #pylint: disable=arguments-differ
        """
        Return a dict() appropriate for JSON output.

        Inputs:
            _raw[bool]: An internal flag for skipping json conversion while building containers
        """
        return self.to_json(self)

Section = newToken('Section')
String = newToken('String', content=u'')
Word = newToken('Word', content=u'')
Space = newToken('Space', count=1)
Break = newToken('Break', count=1)
Punctuation = newToken('Punctuation', content=u'')
Number = newToken('Number', content=u'')
Code = newToken('Code', content=u'', language=u'text', escape=True)
Heading = newToken('Heading', level=1)
Paragraph = newToken('Paragraph')
OrderedList = newToken('OrderedList')
UnorderedList = newToken('UnorderedList')
ListItem = newToken('ListItem')
Link = newToken('Link', url=u'', tooltip=True)
Shortcut = newToken('Shortcut', key=u'', link=u'')
ShortcutLink = newToken('ShortcutLink', key=u'')
Monospace = newToken('Monospace')
Strong = newToken('Strong')
Emphasis = newToken('Emphasis')
Underline = newToken('UnderLine')
Strikethrough = newToken('Strikethrough')
Quote = newToken('Quote')
Superscript = newToken('Superscript')
Subscript = newToken('Subscript')
Label = newToken('Label', text=u'')
ErrorToken = newToken('ExeceptionToken', message=u'', page=None, traceback=None)
DisabledToken = newToken('DisabledToken')
