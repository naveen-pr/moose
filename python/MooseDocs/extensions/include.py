#pylint: disable=missing-docstring
import re
from MooseDocs import base, common
from MooseDocs.common import exceptions
from MooseDocs.extensions import command

def make_extension(**kwargs):
    return IncludeExtension(**kwargs)

class IncludeExtension(command.CommandExtension):
    """Enables the !include command for including files in other files."""

    def extend(self, reader, renderer):
        self.requires(command)
        self.addCommand(reader, IncludeCommand())

class IncludeCommand(command.CommandComponent):
    COMMAND = 'include'
    SUBCOMMAND = 'md' #TODO: get this from the reader inside the __init__ method.

    @staticmethod
    def defaultSettings():
        settings = command.CommandComponent.defaultSettings()
        settings.update(common.extractContentSettings())
        return settings

    def createToken(self, parent, info, page):
        """
        Tokenize the included content and create dependency between pages.
        """
        include_page = common.find_page(page.root, info['subcommand'])
        include_page.addDependency(page.fullpath)

        content, line = common.extractContent(include_page.read(), self.settings)
        self.reader.tokenize(parent, content, include_page, line=line)
        return parent
