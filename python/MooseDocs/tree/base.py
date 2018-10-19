#pylint: disable=missing-docstring
#* This file is part of the MOOSE framework
#* https://www.mooseframework.org
#*
#* All rights reserved, see COPYRIGHT for full restrictions
#* https://github.com/idaholab/moose/blob/master/COPYRIGHT
#*
#* Licensed under LGPL 2.1, please see LICENSE for details
#* https://www.gnu.org/licenses/lgpl-2.1.html
#pylint: enable=missing-docstring
import inspect
import importlib
import logging
import collections
import json
import anytree
import mooseutils
from MooseDocs.common import exceptions

LOG = logging.getLogger(__name__)

class Property(object):
    """DUMMY CLASS FOR UPDATING"""
    def __init__(self, *args, **kwargs):
        pass

class NodeBase(anytree.NodeMixin):
    """
    Base class for tree nodes that accepts arbitrary attributes.

    The class behaves as a dict(), with respect to accessing the attributes.

    Inputs:
        parent[NodeBase]: The parent Node (use None for the root)
        name[str]: The name of the node.
        **kwargs: Arbitrary key, value pairs that are added to the __dict__ by the anytree.Node
                  class. These are accessible

    IMPORTANT: In a previous version of MOOSEDocs there was a property system that did automatic
               setters and getters with type checking and slew of other clever things. Well the
               cleverness was too slow. The constructor of these objects is called a lot, so the
               checking was hurting performance.
    """

    #The color to print (see mooseutils.colorText).
    COLOR = 'RESET'

    def __init__(self, parent=None, name=None, **kwargs):
        anytree.NodeMixin.__init__(self, name, parent, **kwargs)
        self.__attributes = kwargs

    def console(self):
        """
        String returned from this function is for screen output. This allows coloring to be
        handled automatically.
        """
        return '{}: Properties: {}, Attributes: {}'. \
            format(self.name, repr(self.__properties), repr(self.__attributes))

    def __repr__(self):
        """
        Prints the name of the token, this works in union with __str__ to print
        the tree structure of any given node.
        """
        return mooseutils.colorText(self.console(), self.COLOR)

    def __str__(self):
        """
        Print the complete tree beginning at this node.
        """
        return str(anytree.RenderTree(self))

    def __call__(self, index):
        """
        Return a child given the numeric index.

        Inputs:
            index[int]: The numeric index of the child object to return, this is the same
                        as doing self.children[index].
        """
        if len(self.children) <= index:
            LOG.error('A child node with index %d does not exist, there are %d children.',
                      index, len(self.children))
            return None
        return self.children[index]

    def __iter__(self):
        """
        Allows for iterator access over the child nodes.
        """
        for child in self.children:
            yield child

    def __getitem__(self, key):
        """
        Return an attribute.
        """
        return self.__attributes[key]

    def __setitem__(self, key, value):
        """
        Create/set an attribute.
        """
        self.__attributes[key] = value

    def __contains__(self, key):
        """
        Allow for "in" operator to check for attributes.
        """
        return key in self.__attributes

    def __len__(self):
        """Return the number of children."""
        return len(self.children)

    def __nonzero__(self):
        """
        When __len__ is defined it is used for bool operations.

        If this class exists then it should evaluate to True. This is actually a requirement for
        the node to continue to work with anytree itself. Therefore, this method is defined
        to make sure that it always returns True when queried as a boolean.
        """
        return True

    def get(self, key, default=None):
        """
        Get an attribute with a possible default.
        """
        value = self.__attributes.get(key, default)
        if value is None:
            value = default
        return value

    @property
    def attributes(self):
        """
        Return the attributes for the object.
        """
        return self.__attributes

    def write(self):
        """
        Method for outputting content of node to a string.
        """
        out = ''
        for child in self.children:
            out += child.write()
        return out

def to_dict(root):
    """Convert tree into a dict()."""

    item = collections.OrderedDict()
    item['type'] = root.__class__#.__name__
    item['name'] = root.name
    item['children'] = list()

    properties = dict()
    for key, value in root._NodeBase__properties.iteritems():
        properties[key] = value
    item['properties'] = properties

    attributes = dict()
    for key, value in root._NodeBase__attributes.iteritems():
        attributes[key] = value
    item['attributes'] = attributes

    for child in root.children:
        item['children'].append(to_dict(child))

    return item

def to_json(root):
    """
    Return a dict() appropriate for JSON output.

    Inputs:
        _raw[bool]: An internal flag for skipping json conversion while building containers
    """
    return json.dumps(to_dict(root), indent=2, sort_keys=True)


#def from_dict(data):
#    return None

"""
def to_string(root, _raw=False):

    data = dict()
    for key, value in root._NodeBase__properties.iteritems():
        data[key] = value

    for key, value in root._NodeBase__attributes.iteritems():
        data[key] = value

    out = ','.join([str(root.depth),
                    root.__module__,
                    root.__class__.__name__,
                    root.name,
                    repr(data)])
    for child in root.children:
        out += '\n' + to_string(child)

    return out

def __load_line(line):
    from MooseDocs.tree import tokens
    data = line.split(',', 4)
    depth = int(data[0])

    try:
        kwargs = eval(data[4])
    except SyntaxError as e:
        print line
        import sys; sys.exit(1)

    mod = importlib.import_module(data[1])
    cls = getattr(mod, data[2])
    try:
        return depth, cls(None, data[3], **kwargs)
    except:
        print line


def from_string(data):
    #import importlib

    lines = data.splitlines()
    _, root = __load_line(lines[0])

    parent = root
    for line in lines[1:]:
        depth, node = __load_line(line)
        parent = root
        for i in range(depth-1):
            parent = parent.children[-1]
        node.parent = parent

    return root
"""


#def from_json(data):
#    return None
