#pylint: disable=missing-docstring
import os
import re

import anytree

import MooseDocs
from MooseDocs import base, common
from MooseDocs.common import exceptions
from MooseDocs.base import components
from MooseDocs.extensions import core, floats
from MooseDocs.tree import tokens, html
from MooseDocs.tree.base import Property

def make_extension(**kwargs):
    return AutoLinkExtension(**kwargs)

PAGE_LINK_RE = re.compile(r'(?P<filename>.*?\.md)?(?P<bookmark>#.*)?', flags=re.UNICODE)

class LocalLink(tokens.Token):
    PROPERTIES = [tokens.Property('bookmark', ptype=unicode, required=True)]

class AutoLink(tokens.Token):
    PROPERTIES = [tokens.Property('page', ptype=unicode, required=True),
                  tokens.Property('bookmark', ptype=unicode)]

class AutoLinkExtension(components.Extension):
    """
    Extension that replaces the default Link and LinkShortcut behavior and handles linking to
    other files. This includes the ability to extract the content from the linked page (i.e.,
    headers) for display on the current page.
    """

    @staticmethod
    def defaultConfig():
        config = components.Extension.defaultConfig()
        return config

    def extend(self, reader, renderer):
        """Replace default core link components on reader and provide auto link rendering."""

        self.requires(core, floats)

        reader.addInline(PageLinkComponent(), location='=Link')
        reader.addInline(PageShortcutLinkComponent(), location='=ShortcutLink')

        renderer.add(LocalLink, RenderLocalLink())
        renderer.add(AutoLink, RenderAutoLink())

class PageShortcutLinkComponent(core.ShortcutLink):
    """
    Creates correct Shortcutlink when *.md files is provide, modal links when a source files is
    given, otherwise a core.ShortcutLink token.
    """

    def createToken(self, parent, info, page):

        match = PAGE_LINK_RE.search(info['key'])
        bookmark = match.group('bookmark')[1:] if match.group('bookmark') else None
        filename = match.group('filename')

        # The link is local (i.e., [#foo]), the heading will be gathered on render because it
        # could be after the current position.
        if (filename is None) and (bookmark is not None):
            return LocalLink(parent, bookmark=bookmark)

        elif (filename is not None):
            AutoLink(parent, page=filename, bookmark=bookmark)
            return parent

        else:
            source = common.project_find(info['key'])
            if len(source) == 1:
                src = unicode(source[0])
                content = common.fix_moose_header(common.read(os.path.join(MooseDocs.ROOT_DIR, src)))
                code = tokens.Code(None, language=common.get_language(src), code=content)
                local = src.replace(MooseDocs.ROOT_DIR, '')
                floats.create_modal_link(parent,
                                         content=code,
                                         title=local,
                                         string=os.path.basename(info['key']))
                return parent

        return core.ShortcutLink.createToken(self, parent, info, page)

class PageLinkComponent(core.Link):
    """
    Creates correct link when *.md files is provide, modal links when a source files is given,
    otherwise a core.Link token.
    """

    def createToken(self, parent, info, page):

        match = PAGE_LINK_RE.search(info['url'])
        bookmark = match.group('bookmark')[1:] if match.group('bookmark') else None
        filename = match.group('filename')

        if (filename is not None):
            desired = common.find_page(page.root, filename)

            url=unicode(desired.relativeDestination(page))
            if bookmark is not None:
                url += '#{}'.format(bookmark)
            return tokens.Link(parent, url=url)


        else:
            source = common.project_find(info['url'])
            if len(source) == 1:
                src = unicode(source[0])
                content = common.fix_moose_header(common.read(os.path.join(MooseDocs.ROOT_DIR, src)))
                code = tokens.Code(None, language=common.get_language(src), code=content)
                local = src.replace(MooseDocs.ROOT_DIR, '')
                link = floats.create_modal_link(parent, content=code, title=local)
                return link

        return core.Link.createToken(self, parent, info, page)

class RenderLocalLink(components.RenderComponent):
    """
    Creates a link to a local item.
    """
    def createHTML(self, parent, token, page):

        heading = common.find_heading(page, token.bookmark)
        a = html.Tag(parent, 'a', href=u'#{}'.format(token.bookmark))
        self.renderer.render(a, heading, page)
        return parent

class RenderAutoLink(components.RenderComponent):
    """
    Create link to another page and extract the heading for the text, if no children provided.
    """

    def createHTML(self, parent, token, page):
        desired = common.find_page(page.root, token.page)
        if desired.ast is None:
            msg = "The located page, {}, does not contain an AST."
            print page.name, desired, desired.content, desired.ast
            raise exceptions.MooseDocsException(msg, desired.source)

        url = unicode(desired.relativeDestination(page))
        if token.bookmark is not None:
            url += '#{}'.format(token.bookmark)


        link = tokens.Link(token.parent, url=url)
        if token.children:
            for child in token.children:
                child.parent = link

        else:
            heading = common.find_heading(desired, token.bookmark)
            if heading is not None:
                for child in heading:
                    child.parent = link
            else:
                tokens.String(link, content=url)

        self.renderer.render(parent, link, page)
        return parent
