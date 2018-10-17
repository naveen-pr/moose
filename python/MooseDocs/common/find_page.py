import logging
import anytree
import MooseDocs
from exceptions import MooseDocsException
from check_type import check_type

#: Global cache of searches to increase speed, the anytree iterators can be slow
PAGE_CACHE=dict()

def find_page(root, name):
    """
    Find method for locating a single page, that errors if more than one are located.

    Inputs:
        see find_pages below.
    """
    nodes = find_pages(root, name)
    if len(nodes) == 0:
        msg = "Unable to locate a page that endswith the name '{}'.".format(name)
        raise MooseDocsException(msg)

    elif len(nodes) > 1:
        msg = "Multipe pages with a name that endswith '{}' were found:".format(name)
        for node in nodes:
            msg += '\n  {} (source: {})'.format(node.local, node.source)
        raise MooseDocsException(msg)

    return nodes[0]

def find_pages(root, name):
    """
    Return all pages that end with the name provided, starting at the root node.

    Inputs:
        root[pages.Page]: The node from where to begin the search.
        name[str]: The name of the node to located.
        lock[threading.Lock]: An optional thread lock for when the cache is updated.
    """
    if MooseDocs.LOG_LEVEL == logging.DEBUG:
        from MooseDocs.tree import pages
        check_type('root', root, pages.Page)
        check_type('name', name, (str, unicode))

    try:
        return list(PAGE_CACHE[name])

    except KeyError:

        nodes = anytree.search.findall(root, filter_=lambda n: n.fullpath.endswith(name))
        PAGE_CACHE[name] = set(nodes)
        return nodes
