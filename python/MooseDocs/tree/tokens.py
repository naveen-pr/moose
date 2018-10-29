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

import MooseDocs
from MooseDocs import common
from MooseDocs.common import exceptions
from MooseDocs.tree.base import NodeBase

LOG = logging.getLogger(__name__)

class Property(object):
    # TODO: delete this, it is here just to transition to new Token generator
    def __init__(self, *args, **kwargs):
        pass

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
    def __init__(self, name=None, parent=None, **kwargs):
        kwargs.setdefault('recursive', True)
        kwargs.setdefault('string', None)
        super(Token, self).__init__(name, parent, **kwargs)

        # Storage for Lexer Information object
        self._info = None

        # Create string on demand
        string = self.attributes.pop('string', None)
        if string is not None:
            String(self, content=string) #pylint: disable=no-member

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

# TODO: MOVE TO CORE
Section = newToken(u'Section')
String = newToken(u'String', content=u'')
Word = newToken(u'Word', content=u'')
Space = newToken(u'Space', count=1)
Break = newToken(u'Break', count=1)
Punctuation = newToken(u'Punctuation', content=u'')
Number = newToken(u'Number', content=u'')
Code = newToken(u'Code', content=u'', language=u'text', escape=True)
Heading = newToken(u'Heading', level=1)
Paragraph = newToken(u'Paragraph')
OrderedList = newToken(u'OrderedList', start=1)
UnorderedList = newToken(u'UnorderedList')
ListItem = newToken(u'ListItem')
Link = newToken(u'Link', url=u'', tooltip=True)
Shortcut = newToken(u'Shortcut', key=u'', link=u'')
ShortcutLink = newToken(u'ShortcutLink', key=u'')
Monospace = newToken(u'Monospace', content=u'')
Strong = newToken(u'Strong')
Emphasis = newToken(u'Emphasis')
Underline = newToken(u'UnderLine')
Strikethrough = newToken(u'Strikethrough')
Quote = newToken(u'Quote')
Superscript = newToken(u'Superscript')
Subscript = newToken(u'Subscript')
Label = newToken(u'Label', text=u'')
ErrorToken = newToken(u'ErrorToken', message=u'', traceback=None)
DisabledToken = newToken(u'DisabledToken')
