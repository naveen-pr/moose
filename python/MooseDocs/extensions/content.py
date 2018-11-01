#pylint: disable=missing-docstring
import os
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
AtoZToken = tokens.newToken('AtoZToken', location=u'', level=None, buttons=bool)

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
        #renderer.add('ContentToken', RenderContent())
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

        location = self.settings['location']

        tree = dict()
        tree[()] = ContentToken(parent)
        func = lambda p: p.local.startswith(location) and isinstance(p, pages.Source)
        for node in self.findPages(func):
            key = tuple(node.local.replace(location, '').strip('/').split('/'))

            for i in range(1, len(key)):
                dir_key = key[:i]
                if dir_key not in tree:
                    ul = tokens.UnorderedList(tree[key[:i-1]])
                    tokens.String(ul, content=unicode(dir_key[-1]), class_='moose-source-directory')
                    tree[dir_key] = ul

            li = tokens.ListItem(tree[key[:-1]])
            loc = node.relativeDestination(page)
            tokens.Link(li,
                        url=loc,
                        string=unicode(key[-1]),
                        class_='moose-source-file')

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

        """
        nodes = self.findPages(lambda p: p.local.startswith(token['location']))

        ul = html.Tag(parent, 'ul')
        for node in nodes:

            #if isinstance(
            #folders = nod.local.split(os.sep)



            li = html.Tag(ul, 'li')

            # Directory
            if isinstance(node, pages.Directory):
                continue

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
        """

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
