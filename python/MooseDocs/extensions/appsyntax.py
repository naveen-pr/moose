#pylint: disable=missing-docstring,attribute-defined-outside-init
import os
import collections
import logging
import re
import time
import anytree

import mooseutils

import MooseDocs
from MooseDocs import common
from MooseDocs.base import components
from MooseDocs.common import exceptions
from MooseDocs.tree import html, tokens, syntax, app_syntax
from MooseDocs.extensions import floats, autolink, materialicon

from MooseDocs.extensions import command

LOG = logging.getLogger(__name__)

def make_extension(**kwargs):
    return AppSyntaxExtension(**kwargs)

class InputParametersToken(tokens.Token):
    PROPERTIES = [tokens.Property('parameters', ptype=dict, required=True),
                  tokens.Property('level', default=2, ptype=int),
                  tokens.Property('groups', ptype=list),
                  tokens.Property('hide', ptype=set),
                  tokens.Property('show', ptype=set),
                  tokens.Property('visible', ptype=set)]

    def __init__(self, *args, **kwargs):
        tokens.Token.__init__(self, *args, **kwargs)

        if self.show and self.hide:
            msg = "The 'show' and 'hide' properties cannot both be set."
            raise exceptions.TokenizeException(msg)

class AppSyntaxDisabledToken(tokens.Token):
    pass

class SyntaxList(tokens.Token):
    pass

class SyntaxListItem(tokens.Token):
    PROPERTIES = [tokens.Property('header', default=False, ptype=bool)]


class DatabaseListToken(tokens.Token):
    PROPERTIES = [tokens.Property('level', default=2, ptype=int)]

class AppSyntaxExtension(command.CommandExtension):

    @staticmethod
    def defaultConfig():
        config = command.CommandExtension.defaultConfig()
        config['executable'] = (None,
                                "The MOOSE application executable to use for generating syntax.")
        config['includes'] = ([],
                              "List of include directories to investigate for class information.")
        config['inputs'] = ([],
                            "List of directories to interrogate for input files using an object.")
        config['disable'] = (False,
                             "Disable running the MOOSE application executable and simply use " \
                             "place holder text.")
        config['hide'] = (None, "Dictionary of syntax to hide.")
        config['remove'] = (None, "List or Dictionary of lists of syntax to remove.")
        config['visible'] = (set(['required', 'optional']),
                             "Parameter groups to show as un-collapsed.")
        config['alias'] = (None, "List of Dictionary of lists of syntax aliases.")
        config['allow-test-objects'] = (False, "Enable the test objects.")
        return config

    def __init__(self, *args, **kwargs):
        command.CommandExtension.__init__(self, *args, **kwargs)

        self._app_type = None
        self._app_syntax = None
        self._database = None

        if not self['disable'] and self.get('executable') is None:
            msg = "No executable defined, the 'appsyntax' extension is being disabled."
            LOG.error(msg)
            self.update(disable=True)

        if not self['disable']:
            self.__initApplicationSyntax()
            self.__initClassDatabase()

        if self._app_syntax is None:
            self.update(disable=True)

    def __initApplicationSyntax(self):
        """Initialize the application syntax."""

        start = time.time()
        LOG.info("Reading MOOSE application syntax...")
        exe = mooseutils.eval_path(self['executable'])
        exe = mooseutils.find_moose_executable(exe, show_error=False)

        if exe is None:
            LOG.error("Failed to locate a valid executable in %s.", self['executable'])
        else:
            try:
                self._app_syntax = app_syntax(exe,
                                              alias=self['alias'],
                                              remove=self['remove'],
                                              hide=self['hide'],
                                              allow_test_objects=self['allow-test-objects'])

                out = mooseutils.runExe(exe, ['--type'])
                match = re.search(r'^MooseApp Type:\s+(?P<type>.*?)$', out, flags=re.MULTILINE)
                if match:
                    self._app_type = match.group("type")
                else:
                    msg = "Failed to determine application type by running the following:\n"
                    msg += "    {} --type".format(exe)
                    LOG.error(msg)

            except Exception as e: #pylint: disable=broad-except
                msg = "Failed to load application executable from '%s', " \
                      "application syntax is being disabled:\n%s"
                LOG.error(msg, self.get('executable'), e.message)
        LOG.info("MOOSE application syntax complete [%s sec.]", time.time() - start)

    def __initClassDatabase(self):
        """Initialize the class database for faster searching."""

        # Do nothing if the syntax failed to build
        if self._app_syntax is None:
            return

        start = time.time()
        LOG.info("Building MOOSE class database...")
        self._database = common.build_class_database(self['includes'], self['inputs'])

        # Cache the syntax entries, search the tree is very slow
        self._cache = dict()
        self._object_cache = dict()
        self._syntax_cache = dict()
        for node in anytree.PreOrderIter(self._app_syntax):
            if not node.removed:
                self._cache[node.fullpath] = node
                if node.alias:
                    self._cache[node.alias] = node
                if isinstance(node, syntax.ObjectNode):
                    self._object_cache[node.fullpath] = node
                    if node.alias:
                        self._object_cache[node.alias] = node
                elif isinstance(node, syntax.SyntaxNode):
                    self._syntax_cache[node.fullpath] = node
                    if node.alias:
                        self._syntax_cache[node.alias] = node
        LOG.info("MOOSE class database complete [%s sec]", time.time() - start)

    @property
    def syntax(self):
        return self._app_syntax

    @property
    def database(self):
        return self._database

    @property
    def apptype(self):
        return self._app_type

    def find(self, name, node_type=None, exc=exceptions.TokenizeException):
        try:
            if node_type == syntax.ObjectNode:
                return self._object_cache[name]
            elif node_type == syntax.SyntaxNode:
                return self._syntax_cache[name]
            return self._cache[name]
        except KeyError:
            msg = "'{}' syntax was not recognized."
            raise exc(msg, name)

    def extend(self, reader, renderer):
        self.requires(floats, autolink, materialicon)

        self.addCommand(reader, SyntaxDescriptionCommand())
        self.addCommand(reader, SyntaxParametersCommand())
        self.addCommand(reader, SyntaxChildrenCommand())
        self.addCommand(reader, SyntaxInputsCommand())
        #self.addCommand(reader, SyntaxListCommand())
        self.addCommand(reader, SyntaxCompleteCommand())
        self.addCommand(reader, SyntaxDisabledCommand())

        renderer.add(InputParametersToken, RenderInputParametersToken())
        renderer.add(SyntaxList, RenderSyntaxList())
        renderer.add(SyntaxListItem, RenderSyntaxListItem())
        renderer.add(AppSyntaxDisabledToken, RenderAppSyntaxDisabledToken())

class SyntaxDisabledCommand(command.CommandComponent):
    PARSE_SETTINGS = False
    COMMAND = 'syntax'
    SUBCOMMAND = '*'

    def createToken(self, parent, info, page):
        return AppSyntaxDisabledToken(parent, string=info[0])

class SyntaxCommandBase(command.CommandComponent):
    NODE_TYPE = None
    COMMAND = 'syntax'

    @staticmethod
    def defaultSettings():
        settings = command.CommandComponent.defaultSettings()
        settings['syntax'] = (None, "The name of the syntax to extract. If the name of the syntax "\
                                    "is the first item in the settings the 'syntax=' may be " \
                                    "omitted, e.g., `!syntax parameters /Kernels/Diffusion`.")
        return settings

    def createToken(self, parent, info, page):
        if self.extension.get('disable'):
            return AppSyntaxDisabledToken(parent, string=info[0])


        if self.settings['syntax'] is None:
            args = info['settings'].split()
            if args and ('=' not in args[0]):
                self.settings['syntax'] = args[0]

        if self.settings['syntax']:
            obj = self.extension.find(self.settings['syntax'], self.NODE_TYPE)
        else:
            obj = self.extension.syntax

        return self.createTokenFromSyntax(parent, info, page, obj)

    def createTokenFromSyntax(self, parent, info, page, obj):
        pass

class SyntaxCommandHeadingBase(SyntaxCommandBase):
    @staticmethod
    def defaultSettings():
        settings = SyntaxCommandBase.defaultSettings()
        settings['heading'] = (u'Input Parameters',
                               "The heading title for the input parameters table, use 'None' to " \
                               "remove the heading.")
        settings['heading-level'] = (2, "Heading level for section title.")
        return settings

    def createHeading(self, parent, page):

        heading = self.settings['heading']
        if heading is not None:
            h = tokens.Heading(parent, level=int(self.settings['heading-level']))
            self.reader.tokenize(h, heading, page, MooseDocs.INLINE)

class SyntaxDescriptionCommand(SyntaxCommandBase):
    SUBCOMMAND = 'description'
    NODE_TYPE = syntax.ObjectNode

    def createTokenFromSyntax(self, parent, info, page, obj):

        if obj.description is None:
            if not obj.hidden:
                msg = "The class description is missing for {}, it can be added using the " \
                      "'addClassDescription' method from within the objects validParams function."
                raise exceptions.TokenizeException(msg, obj.fullpath)
            else:
                tokens.Paragraph(parent, string=unicode(info[0]), class_='moose-error')
                return parent

        else:
            p = tokens.Paragraph(parent)
            self.reader.tokenize(p, unicode(obj.description), page, MooseDocs.INLINE)
            return parent


class SyntaxParametersCommand(SyntaxCommandHeadingBase):
    SUBCOMMAND = 'parameters'
    NODE_TYPE = None # allows SyntaxNode objects to report combined action parameters

    @staticmethod
    def defaultSettings():
        settings = SyntaxCommandHeadingBase.defaultSettings()
        settings['groups'] = (None, "Space separated list of groups, in desired order, to output.")
        settings['hide'] = (None, "Space separated list of parameters to remove from output.")
        settings['show'] = (None, "Space separated list of parameters to display in output.")
        settings['visible'] = (None,
                               "Space separated list of parameter groups to display with " \
                               "un-collapsed sections.")
        return settings

    def createTokenFromSyntax(self, parent, info, page, obj):

        parameters = dict()
        if isinstance(obj, syntax.SyntaxNode):
            for action in obj.actions():
                parameters.update(action.parameters)
        elif obj.parameters:
            parameters.update(obj.parameters)

        self.createHeading(parent, page)
        token = InputParametersToken(parent, parameters=parameters, **self.attributes)
        if self.settings['groups']:
            token.groups = [group.strip() for group in self.settings['groups'].split(' ')]

        if self.settings['hide']:
            token.hide = set([param.strip() for param in self.settings['hide'].split(' ')])

        if self.settings['show']:
            token.show = set([param.strip() for param in self.settings['show'].split(' ')])

        if self.settings['visible'] is not None:
            token.visible = set([group.strip().lower() for group in \
                                 self.settings['visible'].split(' ')])
        else:
            token.visible = self.extension.get('visible')

        return parent

class SyntaxChildrenCommand(SyntaxCommandHeadingBase):
    SUBCOMMAND = 'children'
    NODE_TYPE = syntax.ObjectNode

    @staticmethod
    def defaultSettings():
        settings = SyntaxCommandHeadingBase.defaultSettings()
        settings['heading'] = (u"Child Objects",
                               "Heading to include for sections, use 'None' to remove the title.")
        return settings

    def createTokenFromSyntax(self, parent, info, page, obj):

        item = self.extension.database.get(obj.name, None)
        attr = getattr(item, self.SUBCOMMAND, None)
        if item and attr:
            self.createHeading(parent, page)
            ul = tokens.UnorderedList(parent, class_='moose-list-{}'.format(self.SUBCOMMAND))
            for filename in attr:
                filename = unicode(filename)
                li = tokens.ListItem(ul)
                lang = common.get_language(filename)
                content = common.fix_moose_header(common.read(os.path.join(MooseDocs.ROOT_DIR,
                                                                           filename)))
                code = tokens.Code(None, language=lang, code=content)
                floats.create_modal_link(li,
                                         url=filename,
                                         content=code,
                                         title=filename,
                                         string=filename)
        return parent

class SyntaxInputsCommand(SyntaxChildrenCommand):
    SUBCOMMAND = 'inputs'
    NODE_TYPE = syntax.ObjectNode

    @staticmethod
    def defaultSettings():
        settings = SyntaxChildrenCommand.defaultSettings()
        settings['heading'] = (u"Input Files", settings['heading'][1])
        return settings


class SyntaxListCommand(SyntaxCommandBase):
    SUBCOMMAND = 'list'
    NODE_TYPE = syntax.SyntaxNode

    @staticmethod
    def defaultSettings():
        settings = SyntaxCommandBase.defaultSettings()
        settings['groups'] = (None, "List of groups (apps) to include in the complete syntax list.")
        settings['actions'] = (True, "Include a list of Action objects in syntax.")
        settings['objects'] = (True, "Include a list of MooseObject objects in syntax.")
        settings['subsystems'] = (True, "Include a list of sub system syntax in the output.")
        return settings

    def createTokenFromSyntax(self, parent, info, page, obj):

        master = SyntaxList(parent)

        groups = self.settings['groups'].split() if self.settings['groups'] else list(obj.groups)
        if 'MooseApp' in groups:
            groups.remove('MooseApp')
            groups.insert(0, 'MooseApp')


        for group in groups:
            header = SyntaxListItem(master, header=True, string=unicode(mooseutils.camel_to_space(group)))

            count = 0
            if self.settings['actions']:
                count += self._addItems(master, info, page, group, obj.actions())
            if self.settings['objects']:
                count += self._addItems(master, info, page, group, obj.objects())
            if self.settings['subsystems']:
                count += self._addItems(master, info, page, group, obj.syntax())

            if count == 0:
                header.parent = None

        return parent

    def _addItems(self, parent, info, page, group, objects):

        count = 0
        for obj in objects:
            if group in obj.groups:
                count += 1
                item = SyntaxListItem(parent)
                nodes = common.find_pages(page.root, obj.markdown())
                if len(nodes) == 0:
                    tokens.String(item, content=unicode(obj.name))
                else:
                    tokens.Link(item, string=unicode(obj.name),
                                url=unicode(nodes[0].relativeDestination(page)))

                if obj.description:
                    self.reader.tokenize(item, obj.description, page, MooseDocs.INLINE, info.line)

        return count

class SyntaxCompleteCommand(SyntaxListCommand):
    SUBCOMMAND = 'complete'
    NODE_TYPE = syntax.SyntaxNode

    @staticmethod
    def defaultSettings():
        settings = SyntaxListCommand.defaultSettings()
        settings['group'] = (None, "The group (app) to limit the complete syntax list.")
        settings['actions'] = (True, "Include a list of Action objects in syntax.")
        settings['objects'] = (True, "Include a list of MooseObject objects in syntax.")
        settings['subsystems'] = (True, "Include a list of sub system syntax in the output.")
        settings['level'] = (2, "Beginning heading level.")
        return settings

    def createTokenFromSyntax(self, parent, info, page, obj):
        self._addList(parent, info, page, obj, 1)
        return parent

    def _addList(self, parent, info, page, obj, level):
        groups = [self.settings['group']] if self.settings['group'] else []
        for child in obj.syntax(group=self.settings['group']):
            if child.removed:
                continue

            h = tokens.Heading(parent, level=level, string=unicode(child.fullpath.strip('/')))
            url = os.path.join('syntax', child.markdown())
            a = autolink.AutoLink(h, page=url)
            #materialicon.IconToken(a, icon=u'input', style="padding-left:10px;")

            super(SyntaxCompleteCommand, self).createTokenFromSyntax(parent, info, page, child)
            self._addList(parent, info, page, child, level + 1)

class RenderSyntaxListItem(components.RenderComponent):
    def createHTML(self, parent, token, page):
        pass

    def createMaterialize(self, parent, token, page):
        class_ = 'collection-header' if token.header else 'collection-item'
        return html.Tag(parent, 'li', class_=class_)

class RenderSyntaxList(components.RenderComponent):
    def createHTML(self, parent, token, page):
        pass

    def createMaterialize(self, parent, token, page):
        collection = html.Tag(parent, 'ul', class_='moose-syntax-list collection with-header')
        return collection

        """
        active_groups = [group.lower() for group in token.groups]
        errors = []

        groups = list(token.syntax.groups)
        if 'MooseApp' in groups:
            groups.remove('MooseApp')
            groups.insert(0, 'MooseApp')

        collection = html.Tag(None, 'ul', class_='collection with-header')
        n_groups = len(groups)
        for group in groups:

            if active_groups and group.lower() not in active_groups:
                continue


            if n_groups > 1:
                li = html.Tag(collection, 'li',
                              class_='moose-syntax-header collection-header',
                              string=unicode(mooseutils.camel_to_space(group)))

            count = len(collection.children)
            if token.actions:
                errors += self._addItems(collection, token, token.syntax.actions(group=group),
                                         'moose-syntax-actions', page)
            if token.objects:
                errors += self._addItems(collection, token, token.syntax.objects(group=group),
                                         'moose-syntax-objects', page)
            if token.subsystems:
                errors += self._addItems(collection, token, token.syntax.syntax(group=group),
                                         'moose-syntax-subsystems', page)

            if n_groups > 1 and len(collection.children) == count:
                li.parent = None

            if collection.children:
                collection.parent = parent

        if errors:
            msg = "The following errors were reported when accessing the '{}' syntax.\n\n"
            msg += '\n\n'.join(errors)
            raise exceptions.RenderException(token.info, msg, token.syntax.fullpath)
        """


    #def _addItems(self, parent, token, items, cls, page): #pylint: disable=unused-argument
    def _addItems(self, parent, items):
        for name, href, description in items:
            li = html.Tag(parent, 'li', class_='moose-syntax-item collection-item')
            html.Tag(li, 'a', class_='moose-syntax-item-name', string=unicode(name), href=href)
            if description:
                desc = html.Tag(li, 'span', class_='moose-syntax-item-description')
                html.String(desc, content=description)




        """
        errors = []

        for obj in items:

            if obj.removed:
                continue

            li = html.Tag(parent, 'li', class_='{} collection-item'.format(cls))

            href = None
            #TODO: need to figure out how to get rid of 'systems' prefix:
            #  /Executioner/Adaptivity/index.md
            #  /Adaptivity/index.md
            if isinstance(obj, syntax.SyntaxNode):
                nodes = root_page.findall(os.path.join('syntax', obj.markdown()), exc=None)
            else:
                nodes = root_page.findall(obj.markdown(), exc=None)

            if len(nodes) > 1:
                msg = "Located multiple pages with the given filename:"
                for n in nodes:
                    msg += '\n    {}'.format(n.fullpath)
                errors.append(msg)
            elif len(nodes) == 0:
                msg = "Failed to locate a page with the given filename: {}".format(obj.markdown())
                errors.append(msg)
            else:
                href = nodes[0].relativeDestination(page) # allow error

            html.Tag(li, 'a', class_='{}-name'.format(cls), string=unicode(obj.name), href=href)

            if obj.description is not None:
                desc = html.Tag(li, 'span', class_='{}-description'.format(cls))
                ast = tokens.Token(None)
                #self.translator.reader.parse(ast, unicode(obj.description), group=MooseDocs.INLINE)
                self.renderer.render(desc, ast, page)

        return errors
        """

class RenderAppSyntaxDisabledToken(components.RenderComponent):
    def createHTML(self, parent, token, page): #pylint: disable=no-self-use,unused-argument
        return html.Tag(parent, 'p', class_='moose-disabled')

    def createLatex(self, parent, token, page):
        pass

class RenderInputParametersToken(components.RenderComponent):

    def createHTML(self, parent, token, page):
        pass

    def createMaterialize(self, parent, token, page):

        groups = self._getParameters(token, token.parameters)
        for group, params in groups.iteritems():

            if not params:
                continue

            if len(groups) > 1: # only create a sub-section if more than one exists
                h = html.Tag(parent, 'h{}'.format(token.level + 1),
                             string=unicode('{} Parameters'.format(group.title())))
                if group.lower() in token.visible:
                    h['data-details-open'] = 'open'
                else:
                    h['data-details-open'] = 'close'

            ul = html.Tag(parent, 'ul', class_='collapsible')
            ul['data-collapsible'] = "expandable"

            for name, param in params.iteritems():
                _insert_parameter(ul, name, param)

        return parent

    @staticmethod
    def _getParameters(token, parameters):
        """
        Add the parameters from the supplied node to the supplied groups
        """

        # Build the list of groups to display
        groups = collections.OrderedDict()
        if token.groups:
            for group in token.groups:
                groups[group] = dict()

        else:
            groups['Required'] = dict()
            groups['Optional'] = dict()
            for param in parameters.itervalues():
                group = param['group_name']
                if group and group not in groups:
                    groups[group] = dict()

        # Populate the parameter lists by group
        for param in parameters.itervalues() or []:

            # Do nothing if the parameter is hidden or not shown
            name = param['name']
            if (name == 'type') or \
               (token.hide and name in token.hide) or \
               (token.show and name not in token.show):
                continue

            # Handle the 'ungroup' parameters
            group = param['group_name']
            if not group and param['required']:
                group = 'Required'
            elif not group and not param['required']:
                group = 'Optional'

            if group in groups:
                groups[group][name] = param

        return groups

def _insert_parameter(parent, name, param):
    """
    Insert parameter in to the supplied <ul> tag.

    Input:
        parent[html.Tag]: The 'ul' tag that parameter <li> item is to belong.
        name[str]: The name of the parameter.
        param: The parameter object from JSON dump.
    """

    if param['deprecated']:
        return

    li = html.Tag(parent, 'li')
    header = html.Tag(li, 'div', class_='collapsible-header')
    body = html.Tag(li, 'div', class_='collapsible-body')

    html.Tag(header, 'span', class_='moose-parameter-name', string=name)
    default = _format_default(param)
    if default:
        html.Tag(header, 'span', class_='moose-parameter-header-default', string=default)

        p = html.Tag(body, 'p', class_='moose-parameter-description-default')
        html.Tag(p, 'span', string=u'Default:')
        html.String(p, content=default)

    cpp_type = param['cpp_type']
    p = html.Tag(body, 'p', class_='moose-parameter-description-cpptype')
    html.Tag(p, 'span', string=u'C++ Type:')
    html.String(p, content=cpp_type)

    if 'options' in param:
        p = html.Tag(body, 'p', class_='moose-parameter-description-options')
        html.Tag(p, 'span', string=u'Options:')
        html.String(p, content=param['options'])

    p = html.Tag(body, 'p', class_='moose-parameter-description')
    desc = param['description']
    if desc:
        html.Tag(header, 'span', class_='moose-parameter-header-description', string=unicode(desc))
        html.Tag(p, 'span', string=u'Description:')
        html.String(p, content=unicode(desc))

def _format_default(parameter):
    """
    Convert the supplied parameter into a format suitable for output.

    Args:
        parameter[str]: The parameter dict() item.
        key[str]: The current key.
    """

    ptype = parameter['cpp_type']
    param = parameter.get('default', '')

    if ptype == 'bool':
        param = repr(param in ['True', '1'])

    return unicode(param) if param else None
