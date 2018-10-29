import anytree
import MooseDocs

HEADING_CACHE = dict()
def find_heading(page, ast, bookmark=None):
    """
    Locate the first Heading token for the supplied page.

    Inputs:
        page[pages.SourceNode]: The page that will be searched.
        ast[tokens.Token]: The AST from the given page to search.
        bookmark[unicode]: The "id" for the heading.
    """
    if bookmark is not None:
        func = lambda n: (n.name == 'Heading') and (n['id'] == bookmark)
    else:
        func = lambda n: n.name == 'Heading'

    for node in anytree.PreOrderIter(ast, filter_=func):
        return node.copy()


"""
    try:
        return copy.copy(HEADING_CACHE[(page.fullpath, bookmark)])
    except KeyError:
        if bookmark is not None:
            func = lambda n: (n.name == 'Heading') and (n['id'] == bookmark)
        else:
            func = lambda n: n.name == 'Heading'
        for node in anytree.PreOrderIter(ast, filter_=func):
            HEADING_CACHE[(page.fullpath, bookmark)] = node
            return copy.copy(node)
"""
