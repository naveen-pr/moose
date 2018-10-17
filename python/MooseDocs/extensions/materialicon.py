#pylint: disable=missing-docstring,attribute-defined-outside-init
from MooseDocs.base import components
from MooseDocs.tree import html, tokens
from MooseDocs.extensions import command

def make_extension(**kwargs):
    return MaterialIconExtension(**kwargs)

class IconBlockToken(tokens.Token):
    pass

class IconToken(tokens.Token):
    PROPERTIES = [tokens.Property('icon', ptype=unicode, required=True)]

class MaterialIconExtension(command.CommandExtension):
    "Adds ability to include material icons."""

    @staticmethod
    def defaultConfig():
        config = components.Extension.defaultConfig()
        return config

    def extend(self, reader, renderer):
        self.requires(command)
        self.addCommand(reader, IconCommand())
        renderer.add(IconToken, RenderIconToken())
        renderer.add(IconBlockToken, RenderIconBlockToken())

class IconCommand(command.CommandComponent):
    COMMAND = 'icon'
    SUBCOMMAND = '*'

    def createToken(self, parent, info, page):
        return IconToken(parent, icon=info['subcommand'])

class RenderIconToken(components.RenderComponent):
    def createHTML(self, parent, token, page):
        pass

    def createMaterialize(self, parent, token, page): #pylint: disable=no-self-use,unused-argument
        i = html.Tag(parent, 'i', class_='material-icons', **token.attributes)
        html.String(i, content=token.icon, hide=True)

    def createLatex(self, parent, token, page):
        pass

class RenderIconBlockToken(components.RenderComponent):
    def createHTML(self, parent, token, page):
        pass

    def createMaterialize(self, parent, token, page): #pylint: disable=no-self-use,unused-argument
        div = html.Tag(parent, 'div', class_='icon-block')
        return div

    def createLatex(self, parent, token, page):
        pass
