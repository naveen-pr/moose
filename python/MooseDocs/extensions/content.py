#pylint: disable=missing-docstring
import collections
import uuid
import anytree
import mooseutils
from MooseDocs import common
from MooseDocs.base import components
from MooseDocs.common import exceptions
from MooseDocs.tree import pages, tokens, html
from MooseDocs.extensions import command

def make_extension(**kwargs):
    return ContentExtension(**kwargs)

class ContentToken(tokens.Token):
    """
    Token for source code tree for the supplied page node object.
    """
    PROPERTIES = [tokens.Property('node', ptype=str, required=True)]

class AtoZToken(tokens.Token):
    PROPERTIES = [tokens.Property('level', ptype=int, required=True),
                  tokens.Property('buttons', ptype=bool, default=True)]

class ContentExtension(command.CommandExtension):
    """
    Allows for the creation of markdown contents lists.
    """
    @staticmethod
    def defaultConfig():
        config = command.CommandExtension.defaultConfig()
        return config

    def extend(self, reader, renderer):
        self.requires(command)
        self.addCommand(reader, ContentCommand())
        self.addCommand(reader, AtoZCommand())
        renderer.add(ContentToken, RenderContent())
        renderer.add(AtoZToken, RenderAtoZ())

class ContentCommand(command.CommandComponent):
    COMMAND = 'contents' #TODO: Change this to content after format is working
    SUBCOMMAND = None

    @staticmethod
    def defaultSettings():
        settings = command.CommandComponent.defaultSettings()
        settings['location'] = (None, "The markdown content directory to build contents.")
        return settings

    def createToken(self, parent, info, page):

        location = self.settings['location']
        if location is None:
            node = self.translator.root
        else:
            func = lambda n: n.name == location and isinstance(n, pages.DirectoryNode)
            node = anytree.search.find(page.root, filter_=func)
            if not node:
                raise exceptions.TokenizeException("Unable to locate the directory '{}'.", location)

        ContentToken(parent, node=node.fullpath)
        return parent

class AtoZCommand(command.CommandComponent):
    COMMAND = 'contents'
    SUBCOMMAND = 'a-to-z'

    @staticmethod
    def defaultSettings():
        settings = command.CommandComponent.defaultSettings()
        settings['level'] = (2, 'Heading level for A, B,... headings.')
        settings['buttons'] = (True, 'Display buttons linking to the A, B,... headings.')
        return settings

    def createToken(self, parent, info, page):
        return parent
        #return AtoZToken(parent, level=self.settings['level'], buttons=self.settings['buttons'])

class RenderContent(components.RenderComponent):
    def createHTML(self, parent, token, page):
        node = common.find_page(page.root, token.node)
        self._dump(parent, node, page)

    def _dump(self, parent, node, page, level=2):

        ul = html.Tag(parent, 'ul')
        items = [] # storage for non-directories to allow for directories to list first
        for child in node.children:
            li = html.Tag(None, 'li')

            # ignores source/index.md
            if child is page:
                continue

            # Directory
            elif isinstance(child, pages.DirectoryNode):
                text = html.Tag(None, 'span',
                                string=unicode(child.name),
                                class_='moose-source-directory')

            # File
            else:
                loc = child.relativeDestination(page)
                text = html.Tag(None, 'a',
                                string=unicode(child.name.replace('.md', '')),
                                href=loc,
                                class_='moose-source-file')

            # Enable scrollspy for top-level, see renderers.py for how this works
            if level == 2:
                li['data-section-level'] = level
                li['data-section-text'] = child.name
                li['data-section-text'] = text.text()
                li['id'] = text.text().lower().replace(' ', '-')
                text['class'] = 'moose-source-directory'

            # Create nested, collapsible list of children
            if child.children:
                details = html.Tag(ul, 'details', open='open')
                summary = html.Tag(details, 'summary')
                html.Tag(summary, 'span', class_='moose-section-icon')
                text.parent = summary

                li.parent = details
                self._dump(li, child, page, level + 1)

            else:
                text.parent = li
                items.append(li)

        # Add file items to the list
        for li in items:
            li.parent = ul

class RenderAtoZ(components.RenderComponent):
    def createHTML(self, parent, token, page):
        pass

    def createMaterialize(self, parent, token, page):

        # Initalized alphabtized storage
        headings = dict()
        for letter in 'ABCDEFGHIJKLNMOPQRSTUVWXYZ':
            headings[letter] = dict()

        # Extract headings, default to filename if a heading is not found
        filter_=lambda n: isinstance(n, pages.SourceNode)
        for node in anytree.PreOrderIter(page.root, filter_=filter_):
            h_node = common.find_heading(node)
            if h_node is not None:
                r = html.Tag(None, 'span')
                self.renderer.render(r, h_node, page)
                key = r.text()
            else:
                r = None
                key = node.name

            letter = key[0].upper()
            headings[letter][key] = node.relativeDestination(page)

        # Buttons
        buttons = html.Tag(parent, 'div', class_='moose-a-to-z-buttons')
        if not token.buttons:
            buttons.parent = None

        # Build lists
        for letter, items in headings.iteritems():
            id_ = uuid.uuid4()
            btn = html.Tag(buttons, 'a',
                           string=unicode(letter),
                           class_='btn moose-a-to-z-button',
                           href='#{}'.format(id_))

            if not items:
                btn.addClass('disabled')
                continue

            h = html.Tag(parent, 'h{}'.format(token.level),
                         class_='moose-a-to-z',
                         id_=unicode(id_),
                         string=unicode(letter))

            row = html.Tag(parent, 'div', class_='row')

            links = [(text, href) for text, href in items.iteritems()]
            for chunk in mooseutils.make_chunks(links, 3):
                col = html.Tag(row, 'div', class_='col s12 m6 l4')
                ul = html.Tag(col, 'ul', class_='moose-a-to-z')
                for text, href in chunk:
                    li = html.Tag(ul, 'li')
                    html.Tag(li, 'a', href=href, string=unicode(text))
