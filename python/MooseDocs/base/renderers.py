"""Defines Renderer objects that convert AST (from Reader) into an output format."""
import os
import logging
import traceback
import uuid
import subprocess
import codecs
import shutil

import anytree

import mooseutils

import MooseDocs
from MooseDocs import common
from MooseDocs.common import exceptions, mixins
from MooseDocs.tree import html, latex, base, pages, tokens

LOG = logging.getLogger(__name__)

def create_directory(location):
    """Helper for creating a directory."""
    with MooseDocs.base.Translator.LOCK:
        dirname = os.path.dirname(location)
        if dirname and not os.path.isdir(dirname):
            LOG.debug('CREATE DIR %s', dirname)
            os.makedirs(dirname)

class Renderer(mixins.ConfigObject, mixins.ComponentObject):
    """
    Base renderer for converting AST to an output format.
    """

    #:[str] The name of the method to call on RendererComponent objects.
    METHOD = None

    def __init__(self, **kwargs):
        mixins.ConfigObject.__init__(self, **kwargs)
        mixins.ComponentObject.__init__(self)
        self.__functions = dict()  # functions on the RenderComponent to call

    def add(self, token, component):
        """
        Associate a RenderComponent object with a token type.

        Inputs:
            token[type]: The token type (not instance) to associate with the supplied component.
            compoment[RenderComponent]: The component to execute with the associated token type.
        """
        common.check_type("token", token, type)
        common.check_type("component", component, MooseDocs.base.components.RenderComponent)
        component.init(self)
        self.addComponent(component)
        self.__functions[token] = self._method(component)

    def getRoot(self):
        """
        Return the rendered content root node.

        Called by the Translator prior to beginning rendering.
        """
        raise NotImplementedError()

    def render(self, parent, token, page):
        """
        Convert the AST defined in the token input into a output node of parent.

        Inputs:
            ast[tree.token]: The AST to convert.
            parent[tree.base.NodeBase]: A tree object that the AST shall be converted to.
        """
        try:
            func = self.__getFunction(token)
            el = func(parent, token, page) if func else parent

        except Exception as e: #pylint: disable=broad-except
            el = None

            title = u'ERROR:{}'.format(e.message)
            if False:#self.translator.current:
                filename = mooseutils.colorText('{}:{}\n'.format(self.translator.current.source,
                                                                 token.info.line), 'RESET')
            else:
                filename = ''

            box = mooseutils.colorText(MooseDocs.common.box(token.info[0],
                                                            line=token.info.line,
                                                            width=100), 'LIGHT_CYAN')
            if True:#MooseDocs.LOG_LEVEL == logging.DEBUG:
                trace = mooseutils.colorText(traceback.format_exc(), 'GREY')
            else:
                trace = ''
            msg = u'\n{}\n{}{}\n{}\n'.format(title, filename, box, trace)
            LOG.error(msg)

        if el is not None:
            for child in token.children:
                self.render(el, child, page)

    def preExecute(self, root):
        """
        Called by Translator prior to beginning conversion, after reading.
        """
        pass

    def postExecute(self, root):
        """
        Called by Translator after all conversion is complete, prior to writing.
        """
        pass

    def preRender(self, result, page):
        """
        Called by Translator prior to rendereing.

        Inputs:
            result[tree.base.NodeBase]: The root node of the result tree.
        """
        pass

    def postRender(self, result, page):
        """
        Called by Translator after rendereing.

        Inputs:
            result[tree.base.NodeBase]: The root node of the result tree.
        """
        pass

    def write(self, page, result=None):
        """
        Write the supplied results using to the destination defined by the page.
        """
        if isinstance(page, pages.SourceNode):
            create_directory(page.destination)
            LOG.debug('WRITE %s -> %s', page.source, page.destination)
            with codecs.open(page.destination, 'w', encoding='utf-8') as fid:
                fid.write(result.write())

        elif isinstance(page, pages.FileNode):
            create_directory(page.destination)
            LOG.debug('COPY: %s-->%s', page.source, page.destination)
            shutil.copyfile(page.source, page.destination)

        elif isinstance(page, pages.DirectoryNode):
            create_directory(page.destination)

        else:
            LOG.error('Unknown Node type: %s', type(node))

    def _method(self, component):
        """
        Return the desired method to call on the RenderComponent object.

        Inputs:
            component[RenderComponent]: Object to use for locating desired method for renderering.
        """
        if self.METHOD is None:
            msg = "The Reader class of type {} must define the METHOD class member."
            raise exceptions.MooseDocsException(msg, type(self))
        elif not hasattr(component, self.METHOD):
            msg = "The component object {} does not have a {} method."
            raise exceptions.MooseDocsException(msg, type(component), self.METHOD)
        return getattr(component, self.METHOD)

    def __getFunction(self, token):
        """
        Return the desired function for the supplied token object.

        Inputs:
            token[tree.token]: token for which the associated RenderComponent function is desired.
        """
        return self.__functions.get(type(token), None)

class HTMLRenderer(Renderer):
    """
    Converts AST into HTML.
    """
    METHOD = 'createHTML'
    EXTENSION = '.html'

    def createRoot(self, config):
        return html.Tag(None, 'body', class_='moose-content')

class MaterializeRenderer(HTMLRenderer):
    """
    Convert AST into HTML using the materialize javascript library (http://materializecss.com).
    """
    METHOD = 'createMaterialize'

    @staticmethod
    def defaultConfig():
        """
        Return the default configuration.
        """
        config = HTMLRenderer.defaultConfig()
        config['breadcrumbs'] = (True, "Toggle for the breadcrumb links at the top of page.")
        config['sections'] = (True, "Group heading content into <section> tags.")
        config['collapsible-sections'] = ([None, None, None, None, None, None],
                                          "Collapsible setting for the six heading level " \
                                          "sections, possible values include None, 'open', and " \
                                          "'close'. Each indicates if the associated section " \
                                          "should be collapsible, if so should it be open or " \
                                          "closed initially. The 'sections' setting must be " \
                                          "True for this to operate.")
        config['navigation'] = (None, "Top bar website navigation items.")
        config['repo'] = (None, "The source code repository.")
        config['name'] = (None, "The name of the website (e.g., MOOSE)")
        config['home'] = ('/', "The homepage for the website.")
        config['scrollspy'] = (True, "Enable/disable the scrolling table of contents.")
        config['search'] = (True, "Enable/disable the search bar.")
        config['google_analytics'] = (False, "Enable Google Analytics.")
        return config

    def __init__(self, *args, **kwargs):
        HTMLRenderer.__init__(self, *args, **kwargs)
        self.__navigation = None # Cache for navigation pages
        self.__index = False # page index created

    def update(self, **kwargs):
        """
        Update the default configuration with the supplied values. This is an override of the
        ConfigObject method and is simply modified here to the check the type of a configuration
        item.
        """
        HTMLRenderer.update(self, **kwargs)

        #collapsible = self['collapsible-sections']
        #if not isinstance(collapsible, list) or len(collapsible) != 6:
        #    msg = "The config option 'collapsible-sections' input must be a list of six entries, " \
        #          "the item supplied is a {} of length {}: {}"
        #    raise ValueError(msg.format(type(collapsible), len(collapsible), repr(collapsible)))

    def getRoot(self):
        return html.Tag(None, '!DOCTYPE html', close=False)

    def _method(self, component):
        """
        Fallback to the HTMLRenderer method if the MaterializeRenderer method is not located.

        Inputs:
            component[RenderComponent]: Object to use for locating desired method for renderering.
        """
        if hasattr(component, self.METHOD):
            return getattr(component, self.METHOD)
        elif hasattr(component, HTMLRenderer.METHOD):
            return getattr(component, HTMLRenderer.METHOD)
        else:
            msg = "The component object {} does not have a {} method."
            raise exceptions.MooseDocsException(msg, type(component), self.METHOD)

    def postRender(self, root, page):
        """
        Insert materialize specific items into the rendered html tree.
        """
        children = []
        for child in root.children:
            children.append(child)
            child.parent = None

        html_root = html.Tag(root, 'html')
        head = html.Tag(html_root, 'head')
        body = html.Tag(html_root, 'body')
        wrap = html.Tag(body, 'div', class_='page-wrap')

        header = html.Tag(wrap, 'header')
        nav = html.Tag(html.Tag(header, 'nav'), 'div', class_='nav-wrapper container')

        main = html.Tag(wrap, 'main', class_='main')

        container = html.Tag(main, 'div', class_="container")

        # <head> content
        self._addHead(head, page)
        self._addRepo(nav, page)
        self._addName(nav, page)
        self._addNavigation(nav, page)
        self._addBreadcrumbs(container, page)
        self._addSearch(nav, page)

        row = html.Tag(container, 'div', class_="row")
        col = html.Tag(row, 'div', class_="moose-content")
        col.children = children

        # Title <head><title>...
        self._addTitle(head, col, page)

        # Sections
        self._addSections(col, page)
        if self.get('scrollspy'):
            col.addClass('col', 's12', 'm12', 'l10')
            toc = html.Tag(row, 'div', class_="col hide-on-med-and-down l2")
            self._addContents(toc, col, page)
        else:
            col.addClass('col', 's12', 'm12', 'l12')

    def _addTitle(self, head, root, page): #pylint: disable=unused-argument
        """
        Add content to <title> tag.

        Inputs:
            head[html.Tag]: The <head> tag for the page being generated.
            ast[tokens.Token]: The root node for the AST.
            page[page.PageNodeBase]: The current page being converted.
        """

        # Locate h1 heading, if it is found extract the rendered text
        name = page.name if page else None # default
        for node in anytree.PreOrderIter(root):
            if node.name == 'h1':
                name = node.text()
                break

        # Add <title> tag
        if name is not None:
            html.Tag(head, 'title', string=u'{}|{}'.format(name, self.get('name')))

    def _addHead(self, head, page): #pylint: disable=unused-argument,no-self-use
        """
        Add content to <head> element with the required CSS/JS for materialize.

        Inputs:
            head[html.Tag]: The <head> tag for the page being generated.
            page[page.PageNodeBase]: The current page being converted.
        """

        def rel(path):
            """Helper to create relative paths for js/css dependencies."""
            if page:
                return os.path.relpath(path, os.path.dirname(page.local))
            return '/' + path

        html.Tag(head, 'meta', close=False, charset="UTF-8")
        html.Tag(head, 'link', href=rel("contrib/materialize/materialize.min.css"), type="text/css",
                 rel="stylesheet", media="screen,projection")
        html.Tag(head, 'link', href=rel("contrib/katex/katex.min.css"), type="text/css",
                 rel="stylesheet")
        html.Tag(head, 'link', href=rel("contrib/prism/prism.min.css"), type="text/css",
                 rel="stylesheet")
        html.Tag(head, 'link', href=rel("css/moose.css"), type="text/css", rel="stylesheet")
        html.Tag(head, 'script', type="text/javascript", src=rel("contrib/jquery/jquery.min.js"))
        html.Tag(head, 'script', type="text/javascript",
                 src=rel("contrib/materialize/materialize.min.js"))

        html.Tag(head, 'script', type="text/javascript",
                 src=rel("contrib/clipboard/clipboard.min.js"))
        html.Tag(head, 'script', type="text/javascript", src=rel("contrib/prism/prism.min.js"))
        html.Tag(head, 'script', type="text/javascript", src=rel("contrib/katex/katex.min.js"))

        if self.get('search', False):
            html.Tag(head, 'script', type="text/javascript", src=rel("contrib/fuse/fuse.min.js"))
            html.Tag(head, 'script', type="text/javascript", src=rel("js/search_index.js"))

        html.Tag(head, 'script', type="text/javascript", src=rel("js/init.js"))

        # Google Analytics (see https://support.google.com/analytics/answer/1008080)
        if self.get('google_analytics', False):
            html.Tag(head, 'script', type="text/javascript",
                     src=rel('js/google_analytics.js'))

    def _addContents(self, toc, content, page): #pylint: disable=unused-argument,no-self-use
        """
        Add the table of contents right-side bar that used scrollspy.

        Inputs:
            toc[html.Tag]: Table-of-contents <div> tag.
            content[html.Tag]: The complete html content that the TOC is going to reference.
            page[page.PageNodeBase]: The current page being converted.
        """

        div = html.Tag(toc, 'div', class_='toc-wrapper pin-top')
        ul = html.Tag(div, 'ul', class_='section table-of-contents')
        for node in anytree.PreOrderIter(content):
            if node.get('data-section-level', None) == 2:
                node.addClass('scrollspy')
                li = html.Tag(ul, 'li')
                a = html.Tag(li, 'a',
                             href='#{}'.format(node['id']),
                             string=node.get('data-section-text', 'Unknown...'),
                             class_='tooltipped')
                a['data-delay'] = '1000'
                a['data-position'] = 'left'
                a['data-tooltip'] = node['data-section-text']

    def _addRepo(self, nav, page): #pylint: disable=no-self-use
        """
        Add the repository link to the navigation bar.

        Inputs:
            nav[html.Tag]: The <div> containing the navigation for the page being generated.
            page[page.PageNodeBase]: The current page being converted.
        """

        repo = self.get('repo', None)
        if (repo is None):
            return

        a = html.Tag(nav, 'a', href=repo, class_='right')

        if 'github' in repo:
            img0 = common.find_page(page.root, 'github-logo.png')
            img1 = common.find_page(page.root, 'github-mark.png')

            html.Tag(a, 'img', src=img0.relativeDestination(page), class_='github-mark')
            html.Tag(a, 'img', src=img1.relativeDestination(page), class_='github-logo')

        elif 'gitlab' in repo:
            img = common.find_page(page.root, 'gitlab-logo.png')
            html.Tag(a, 'img', src=img.relativeDestination(page), class_='gitlab-logo')

    def _addNavigation(self, nav, page):
        """
        Add the repository navigation links.

        Inputs:
            nav[html.Tag]: The <div> containing the navigation for the page being generated.
            page[page.PageNodeBase]: The current page being converted.
        """

        def add_to_nav(key, value, nav):
            """Helper for building navigation page links."""
            if value.startswith('http'):
                nav[key] = value
            else:
                try:
                    node = common.find_page(page.root, value)
                except exceptions.MooseDocsException as e:
                    LOG.errog(e.message)
                    raise e
                nav[key] = node

        # Do nothing if navigation is not provided
        navigation = self.get('navigation', None)
        if (navigation is None):
            return

        # Locate the navigation pages
        if self.__navigation is None:
            self.__navigation = navigation
            for key1, value1 in navigation.iteritems():
                if isinstance(value1, dict):
                    for key2, value2 in value1.iteritems():
                        add_to_nav(key2, value2, self.__navigation[key1])
                else:
                    add_to_nav(key1, value1, self.__navigation)

        # Hamburger icon
        hamburger = html.Tag(nav, 'a', href=u"#", class_="button-collapse")
        hamburger['data-activates'] = "moose-mobile-menu"
        html.Tag(hamburger, 'i', class_="material-icons", string=u'menu')

        # Build menu
        top_ul = html.Tag(nav, 'ul', id="nav-mobile", class_="right hide-on-med-and-down")
        side_ul = html.Tag(nav, 'ul', id="moose-mobile-menu", class_="side-nav")
        def menu_helper(ul): #pylint: disable=invalid-name
            """Add menu items to the supplied ul tag."""

            for key1, value1 in self.__navigation.iteritems():
                if isinstance(value1, str):
                    top_li = html.Tag(ul, 'li')
                    a = html.Tag(top_li, 'a', href=value1, string=unicode(key1))

                elif not isinstance(value1, dict):
                    href = value1.relativeDestination(page)
                    top_li = html.Tag(ul, 'li')
                    a = html.Tag(top_li, 'a', href=href, string=unicode(key1))

                else:
                    id_ = uuid.uuid4()
                    top_li = html.Tag(ul, 'li')
                    a = html.Tag(top_li, 'a', class_="dropdown-button", href="#!",
                                 string=unicode(key1))
                    a['data-activates'] = id_
                    a['data-constrainWidth'] = "false"
                    html.Tag(a, "i", class_='material-icons right', string=u'arrow_drop_down')

                    bot_ul = html.Tag(nav, 'ul', id_=id_, class_='dropdown-content')
                    for key2, node in value1.iteritems():
                        bot_li = html.Tag(bot_ul, 'li')
                        if isinstance(node, str):
                            a = html.Tag(bot_li, 'a', href=node, string=unicode(key2))
                        else:
                            href = node.relativeDestination(page)
                            a = html.Tag(bot_li, 'a', href=href, string=unicode(key2))

        menu_helper(top_ul)
        menu_helper(side_ul)

    def _addSearch(self, nav, page): #pylint: disable=no-self-use
        """
        Add search bar to the navigation bar.

        Inputs:
            nav[html.Tag]: The <div> containing the navigation for the page being generated.
            page[page.PageNodeBase]: The current page being converted.

        TODO:  The content of this method and most of the other methods in this class should be
               moved to extensions. The extension should create a SearchToken at the top level
               of the AST (i.e., in preTokenize). The render method should inject the search in to
               the navigation bar (which could be another but require extension). Doing this
               would make this class much simpler and keep the overall design almost exclusively
               plugin based. The MaterializeRender should be as close to as empty as possible.
        """

        # Do nothing if navigation is not provided
        search = self.get('search', True)
        if (not search):
            return

        # Search button
        btn = html.Tag(nav, 'a', class_="modal-trigger", href="#moose-search")
        html.Tag(btn, 'i', string=u'search', class_="material-icons")

        # Search modal
        div = html.Tag(anytree.search.find_by_attr(nav.root, 'header'), 'div', id_="moose-search",
                       class_="modal modal-fixed-footer moose-search-modal")
        container = html.Tag(div, 'div',
                             class_="modal-content container moose-search-modal-content")
        row = html.Tag(container, 'div', class_="row")
        col = html.Tag(row, 'div', class_="col l12")
        box_div = html.Tag(col, 'div', class_="input-field")
        box = html.Tag(box_div, 'input', type_='text', id_="moose-search-box",
                       onkeyup="mooseSearch()", autocomplete="off")
        html.Tag(box, 'label', for_="search", string=unicode(self.get('home')))
        result_wrapper = html.Tag(row, 'div')
        html.Tag(result_wrapper, 'div', id_="moose-search-results", class_="col s12")
        footer = html.Tag(div, 'div', class_="modal-footer")
        html.Tag(footer, 'a', href='#!', class_="modal-action modal-close btn-flat",
                 string=u'Close')

    def _addName(self, nav, page): #pylint: disable=unused-argument
        """
        Add the page name to the left-hand side of the top bar.

        Inputs:
            nav[html.Tag]: The <div> containing the navigation for the page being generated.
            page[page.PageNodeBase]: The current page being converted.
        """
        name = self.get('name', None)
        if name is not None:
            html.Tag(nav, 'a', class_='left moose-logo hide-on-med-and-down',
                     href=unicode(self.get('home', '#!')),
                     string=unicode(name))

    def _addBreadcrumbs(self, container, page): #pylint: disable=no-self-use
        """
        Inserts breadcrumb links at the top of the page.

        Inputs:
            root[tree.html.Tag]: The tag to which the breadcrumbs should be inserted.

        TODO: This is relying on hard-coded .md/.html extensions, that should not be the case.
        """

        if not self.get('breadcrumbs', None):
            return

        row = html.Tag(container, 'div', class_="row")
        col = html.Tag(row, 'div', class_="col hide-on-med-and-down l12")
        nav = html.Tag(col, 'nav', class_="breadcrumb-nav")
        div = html.Tag(nav, 'div', class_="nav-wrapper")

        node = page
        for n in node.path:
            if not n.local:
                continue
            elif isinstance(n, pages.DirectoryNode):
                idx = anytree.search.find_by_attr(n, 'index.md', maxlevel=1)
                if idx:
                    url = os.path.relpath(n.local,
                                          os.path.dirname(node.local)).replace('.md', '.html')
                    a = html.Tag(div, 'a', href=url, class_="breadcrumb", string=unicode(n.name))
                else:
                    span = html.Tag(div, 'span', class_="breadcrumb")
                    html.String(span, content=unicode(n.name))

            elif isinstance(n, pages.FileNode) and n.name != 'index.md':
                url = os.path.relpath(n.local,
                                      os.path.dirname(node.local)).replace('.md', '.html')
                a = html.Tag(div, 'a', href=url, class_="breadcrumb")
                html.String(a, content=unicode(os.path.splitext(n.name)[0]))

    def _addSections(self, container, page): #pylint: disable=unused-argument
        """
        Group content into <section> tags based on the heading tag.

        Inputs:
            root[tree.html.Tag]: The root tree.html node tree to add sections.read
            collapsible[list]: A list with six entries indicating the sections to create as
                               collapsible.
        """
        if not self.get('sections', False):
            return

        collapsible = self.get('collapsible-sections')
        if isinstance(collapsible, unicode):
            collapsible = eval(collapsible)

        section = container
        for child in section.children:
            if child.name in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
                level = int(child.name[-1])
                current = section.get("data-section-level", 0) # get the current section level

                if level == current:
                    section = html.Tag(section.parent, 'section')
                elif level > current:
                    section = html.Tag(section, 'section')
                elif level < current:
                    section = html.Tag(section.parent.parent, 'section')

                section['data-section-level'] = level
                section['data-section-text'] = child.text()
                section['id'] = uuid.uuid4()
                if 'data-details-open' in child:
                    section['data-details-open'] = child['data-details-open']

            child.parent = section

        for node in anytree.PreOrderIter(container, filter_=lambda n: n.name == 'section'):

            if 'data-details-open' in node:
                status = node['data-details-open']
            else:
                status = collapsible[node['data-section-level']-1]

            if status:
                summary = html.Tag(None, 'summary')
                node(0).parent = summary

                details = html.Tag(None, 'details', class_="moose-section-content")
                if status.lower() == 'open':
                    details['open'] = 'open'
                details.children = node.children
                summary.parent = details
                details.parent = node

                icon = html.Tag(None, 'span', class_='moose-section-icon')
                summary(0).children = [icon] + list(summary(0).children)

class LatexRenderer(Renderer):
    """
    Renderer for converting AST to LaTeX.
    """
    METHOD = 'createLatex'
    EXTENSION = '.tex'

    def __init__(self, *args, **kwargs):
        self._packages = set()
        Renderer.__init__(self, *args, **kwargs)

    def getRoot(self):
        """
        Return LaTeX root node.
        """
        return base.NodeBase()

    def postExecute(self):
        """
        Combines all the LaTeX files into a single file.

        Organizing the files is still a work in progress.
        """
        def sort_node(node):
            """Helper to organize nodes files then directories."""
            files = []
            dirs = []
            for child in node.children:
                child.parent = None
                if isinstance(child, page.DirectoryNode):
                    dirs.append(child)
                else:
                    files.append(child)
                sort_node(child)

            for child in files:
                child.parent = node
            for child in dirs:
                child.parent = node

        root = self.translator.root
        sort_node(root)

        main = self._processPages(root)
        loc = self.translator['destination']
        with open(os.path.join(loc, 'main.tex'), 'w+') as fid:
            fid.write(main.write())

        main_tex = os.path.join(loc, 'main.tex')
        LOG.info("Building complete LaTeX document: %s", main_tex)
        cmd = ['pdflatex', '-halt-on-error', main_tex]
        try:
            subprocess.check_output(cmd, cwd=loc, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            msg = 'Failed to run command: {}'
            raise exceptions.MooseDocsException(msg, ' '.join(cmd), error=e.output)

    def addPackage(self, *args):
        """
        Add a LaTeX package to the list of packages for rendering.
        """
        self._packages.update(args)

    def _processPages(self, root):
        """
        Build a main latex file that includes the others.
        """

        main = base.NodeBase()
        latex.Command(main, 'documentclass', string=u'report', end='')
        for package in self._packages:
            latex.Command(main, 'usepackage', string=package, start='\n', end='')

        func = lambda n: isinstance(n, pages.SourceNode)
        nodes = [n for n in anytree.PreOrderIter(root, filter_=func)]
        for node in nodes:

            # If the parallel implementation was better this would not be needed.
            node.tokenize()
            node.render(node.ast)

            if node.depth == 1:
                title = latex.Command(main, 'title', start='\n')
                for child in node.result.children[0]:#[0].children:
                    child.parent = title
                node.result.children[0].parent = None

        doc = latex.Environment(main, 'document', end='\n')
        latex.Command(doc, 'maketitle')
        for node in nodes:
            node.write()
            cmd = latex.Command(doc, 'input', start='\n')
            latex.String(cmd, content=unicode(node.destination), escape=False)

        return main

class JSONRenderer(Renderer):
    """
    Render the AST as a JSON file.
    """
    METHOD = 'dummy' # The AST can write JSON directly.
    EXTENSION = '.json'

    def createRoot(self, config): #pylint: disable=unused-argument
        """
        Return LaTeX root node.
        """
        return tokens.Token()

    def _method(self, component):
        """
        Do not call any methods on the component, just create a new tree for writing JSON.
        """
        return self.__function

    @staticmethod
    def __function(token, parent):
        """Replacement for Component function (see _method)."""
        token.parent = parent
        return token
