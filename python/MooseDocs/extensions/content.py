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

ContentToken = tokens.newToken('ContentToken', location=u'')
AtoZToken = tokens.newToken('AtoZToken', level=None, buttons=bool)

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
        renderer.add('ContentToken', RenderContent())
        renderer.add('AtoZToken', RenderAtoZ())

class ContentCommand(command.CommandComponent):
    COMMAND = 'contents' #TODO: Change this to content after format is working
    SUBCOMMAND = None

    @staticmethod
    def defaultSettings():
        settings = command.CommandComponent.defaultSettings()
        settings['location'] = (None, "The markdown content directory to build contents.")
        return settings

    def createToken(self, parent, info, page):
        ContentToken(parent, location=self.settings['location'])
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
        return AtoZToken(parent, level=self.settings['level'], buttons=self.settings['buttons'])

class RenderContent(components.RenderComponent):
    def createHTML(self, parent, token, page):
        nodes = self.findPages(lambda p: p.local.startswith(token.location))

        ul = html.Tag(parent, 'ul')
        for node in nodes:
            li = html.Tag(ul, 'li')

            # ignores the page with the command (i.e., source/index.md)
            if node is page:
                continue

            # Directory
            elif isinstance(node, pages.Directory):
                text = html.Tag(li, 'span',
                                string=unicode(node.name),
                                class_='moose-source-directory')

            # File
            else:
                loc = node.relativeDestination(page)
                text = html.Tag(li, 'a',
                                string=unicode(node.name.replace('.md', '')),
                                href=loc,
                                class_='moose-source-file')

            # Enable scrollspy for top-level, see renderers.py for how this works
            li['data-section-level'] = 2
            li['data-section-text'] = node.name
            li['data-section-text'] = text.text()
            li['id'] = text.text().lower().replace(' ', '-')
            text['class'] = 'moose-source-directory'


class RenderAtoZ(components.RenderComponent):
    def createHTML(self, parent, token, page):
        pass

    def createMaterialize(self, parent, token, page):

        # Initialized alphabetized storage
        headings = dict()
        for letter in 'ABCDEFGHIJKLNMOPQRSTUVWXYZ':
            headings[letter] = dict()

        # Extract headings, default to filename if a heading is not found
        func = lambda n: n.local.startswith(token['location']) and isinstance(n, pages.Source)
        for node in self.findPages(func):
            print 'NODE:', node
            ast = self.getSyntaxTree(node)
            h_node = common.find_heading(node, ast)
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
        if not token['buttons']:
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

            h = html.Tag(parent, 'h{}'.format(token['level']),
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
