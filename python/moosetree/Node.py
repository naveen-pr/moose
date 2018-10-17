import collections
import inspect
from mooseutils import MooseException

class Property(object):
    """
    A descriptor object for creating properties for the NodeBase class defined below.

    A system using this object and the NodeBase class was created to allow for dynamic property
    creation on nodes that allows defaults, types, and a required status to be defined for the
    properties.

    When developing the tokens it was desirable to create properties (via @property) etc. to access
    token data, but it became a bit tedious so an automatic method was created, see the
    documentation on the NodeBase class for information on using the automatic system.

    This property class can also be inherited from to allow for arbitrary checks to be performed,
    for example that a number is positive or a list is the correct length.
    """
    def __init__(self, name, default=None, ptype=None, required=False):
        self.__name = name
        self.__type = ptype
        self.__required = required
        self.__default = default

        if (ptype is not None) and (not isinstance(ptype, type)):
            msg = "The supplied property type (ptype) must be of type 'type', but '{}' provided."
            raise MooseException(msg, type(ptype).__name__)

        if (ptype is not None) and (default is not None) and (not isinstance(default, ptype)):
            msg = "The default for property must be of type '{}', but '{}' was provided."
            raise MooseException(msg, ptype.__name__, type(default).__name__)

    @property
    def name(self):
        """Return the name of the property."""
        return self.__name

    @property
    def default(self):
        """Return the default for this property."""
        return self.__default

    @property
    def type(self):
        """The required property type."""
        return self.__type

    @property
    def required(self):
        """Return the required status for the property."""
        return self.__required

    def __set__(self, instance, value):
        """Set the property value."""
        if (self.__type is not None) and (not isinstance(value, self.__type)):
            msg = "The supplied property '{}' must be of type '{}', but '{}' was provided."
            raise MooseException(msg, self.name, self.type.__name__, type(value).__name__)
        instance._Node__properties[self.name] = value

    def __get__(self, instance, key):
        """Get the property value."""
        return instance._Node__properties.get(self.name, self.default)

def addProperty(*args, **kwargs):
    """Decorator for adding properties."""
    def create(cls):
        prop = Property(*args, **kwargs)

        properties = set()
        for sub_cls in inspect.getmro(cls):
            properties.update(cls.__DESCRIPTORS__[sub_cls])
        properties.add(prop)
        cls.__DESCRIPTORS__[cls].update(properties)

        setattr(cls, prop.name, prop)
        return cls

    return create

class Node(object):
    """
    Base class for tree nodes that accepts defined properties and arbitrary attributes.

    Properties, in the python sense, may be created using the class PROPERTIES variable.
    For example,

        @addProperty('foo', required=True)
        class ExampleNode(NodeBase):
            ...
        node = ExampleNode(foo=42)
        node.foo = 43

    The properties from all parent classes are automatically retrieved.

    Additionally, arbitrary attributes can be stored on creation or by using the dict() style
    set/get methods. By convention any leading or trailing underscores used in defining the
    attribute in the constructor are removed for storage.

        node = ExampleNode(foo=42, class_='fancy')
        node['class'] = 'not fancy'

    Inputs:
        parent[NodeBase]: (Optional) Set the parent node of the node being created, if not
                          supplied the resulting node will be the root node.
        kwargs: (Optional) Any key, value pairs supplied are stored as properties or attributes.
    """

    #: Storage for Property object descriptors, this should not be messed with.
    __DESCRIPTORS__ = collections.defaultdict(set)

    #: mooseutils.colorText color for printing the tree
    COLOR = 'RESET'

    def __init__(self, parent=None, name=None, **kwargs):

        # Class members
        self.__parent = None
        self.__name = name if (name is not None) else self.__class__.__name__
        self.__properties = dict() # storage for property values
        self.__attributes = dict() # storage for attributes (i.e., unknown key, values)
        self.__children = list()

        # Setup tree connections
        if parent is not None:
            self.parent = parent

        # Create properties and set defaults
        descriptors = self.__DESCRIPTORS__[self.__class__]
        for prop in descriptors:
            setattr(self.__class__, prop.name, prop)
            self.__properties[prop.name] = prop.default

        # Update the properties from the key value pairs
        for key, value in kwargs.iteritems():
            key = key.strip('_')
            if value is None:
                continue
            if key in self.__properties:
                setattr(self, key, value)
            else:
                self.__attributes[key] = value

        # Check required
        for prop in descriptors:
            if prop.required and (self.__properties[prop.name] is None):
                raise MooseException("The property '{}' is required.", prop.name)

    def __str__(self):
        #TODO: Make this better with console and color, properties (non default???), attributes
        out = u'{}{}\n'.format(u' '*2*self.depth, self.name)
        n = len(self.children)
        for i, child in enumerate(self.children):
            out += unicode(child)
        return out

    def append(self, *args):
        """Append the supplied nodes to the end of the list of children."""
        for node in args:
            node.parent = self

    def insert(self, index, *args):
        """Insert the supplied nodes after the supplied index."""

        # Remove parent from nodes and set this node as the parent
        for node in args:
            if node._Node__parent is not None:
                node._Node__children.remove(node)
            node._Node__parent = self

        # Add the nodes as children, in the correct location
        self._Node__children[index:index] = args

    @property
    def parent(self):
        """Return the parent node."""
        return self.__parent

    @parent.setter
    def parent(self, value):
        """Set the parent node."""
        if self.__parent is not None:
            self.__parent._Node__children.remove(self)

        self.__parent = value

        #TODO: This is killing performance when constructing objects
        self.__parent._Node__children.append(self)

    @property
    def name(self):
        """Return the node name."""
        return self.__name

    @property
    def children(self):
        """Return the list of children."""
        return self.__children

    @property
    def depth(self):
        """Return the tree depth for this node."""
        d = -1
        node = self
        while node is not None:
            node = node.parent
            d += 1
        return d

    @property
    def path(self):
        """Return the nodes back to the root."""
        out = []
        node = self
        while node is not None:
            out.append(node)
            node = node.parent
        return out

    @property
    def root(self):
        """Return the root node."""
        return self.path[-1]

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
        return len(self.__children)

    def dict(self):

        kwargs = self.__attributes

        descriptors = self.__DESCRIPTORS__[self.__class__]
        for prop in descriptors:
            value = self.__properties[prop.name]
            if value != prop.default:
                kwargs[prop.name] = value

        children = []
        for child in self.children:
            children.append(child.dict())
        return (self.__class__.__name__, kwargs, children)


    """
    def __getstate__(self):
        return self.dict()

    def __setstate__(self, state):

        def load(state_in):
            node = eval(state_in[0], **state_in[1])
            children = []
            for child in state_in[2]:
                children.append(load(child))
            #node.append(*children)
            return node

        return load(state)
    """
