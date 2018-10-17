"""Tool for loading MooseDocs config hit file."""
import collections
import types
import importlib
import logging

from mooseutils.yaml_load import yaml_load
import MooseDocs
from MooseDocs.common import check_type, exceptions

LOG = logging.getLogger(__name__)

# Set of extensions to load by default
DEFAULT_EXTENSIONS = ['MooseDocs.extensions.core',
                      'MooseDocs.extensions.floats',
                      'MooseDocs.extensions.command',
                      'MooseDocs.extensions.include',
                      'MooseDocs.extensions.media',
                      'MooseDocs.extensions.listing',
                      'MooseDocs.extensions.table',
                      'MooseDocs.extensions.autolink',
                      'MooseDocs.extensions.devel',
                      'MooseDocs.extensions.package',
                      'MooseDocs.extensions.alert',
                      'MooseDocs.extensions.katex',
                      'MooseDocs.extensions.appsyntax',
                      'MooseDocs.extensions.bibtex',
                      'MooseDocs.extensions.panoptic',
                      'MooseDocs.extensions.layout',
                      'MooseDocs.extensions.config',
                      'MooseDocs.extensions.materialicon',
                      'MooseDocs.extensions.acronym',
                      'MooseDocs.extensions.content',
                      'MooseDocs.extensions.plotly']

DEFAULT_READER = 'MooseDocs.base.MarkdownReader'
DEFAULT_RENDERER = 'MooseDocs.base.MarkdownReader'
DEFAULT_TRANSLATOR = 'MooseDocs.base.Translator'

def load_config(filename):
    """
    Read the config.yml file and create the Translator object.
    """
    config = yaml_load(filename, root=MooseDocs.ROOT_DIR)

    extensions = _yaml_load_extensions(config)
    reader = _yaml_load_object('Reader', config, DEFAULT_READER)
    renderer = _yaml_load_object('Renderer', config, DEFAULT_RENDERER)
    content = _yaml_load_content(config, reader.EXTENSIONS, renderer.EXTENSION)
    translator = _yaml_load_object('Translator', config, DEFAULT_TRANSLATOR,
                                   content, reader, renderer, extensions)
    return translator, config

def load_extensions(ext_list, ext_configs=None):
    """
    Convert the supplied list into MooseDocs extension objects by calling the make_extension method.

    Inputs:
        ext_list[list]: List of extension modules or module names.
        ext_configs[dict]: A dict() connecting configurations to the module, the key is the
                           complete module name.
    """
    if ext_configs is None:
        ext_configs = dict()
    check_type('ext_list', ext_list, list)
    check_type('ext_configs', ext_configs, dict)

    extensions = []
    for ext in ext_list:
        name, mod = _get_module(ext)
        if not hasattr(mod, 'make_extension'):
            msg = "The supplied module {} does not contain the required 'make_extension' function."
            raise exceptions.MooseDocsException(msg, name)
        else:
            obj = mod.make_extension(**ext_configs.get(name, dict()))
            extensions.append(obj)

    return extensions

def _get_module(ext):
    """Helper for loading a module."""

    if isinstance(ext, types.ModuleType):
        name = ext.__name__
    elif isinstance(ext, str):
        name = ext
        try:
            ext = importlib.import_module(name)
        except ImportError as e:
            msg = "Failed to import the supplied '{}' module.\n{}"
            raise exceptions.MooseDocsException(msg, name, e.message)
    else:
        msg = "The supplied module ({}) must be a module type or a string, but a {} object "\
              "was provided."
        raise exceptions.MooseDocsException(msg, ext, type(ext))

    return name, ext

def _yaml_load_extensions(config):
    """Load extensions from the Extensions block of the YAML configuration file."""

    # Extensions block
    options = config.get('Extensions', dict())

    # Load default configuration
    ext_configs = collections.OrderedDict()
    disable_defaults = options.pop('disable_defaults', False)
    if not disable_defaults:
        for ext in DEFAULT_EXTENSIONS:
            ext_configs[ext] = dict()

    # Get configuration items from configuration
    for ext_type, settings in options.iteritems():
        if 'type' in settings:
            msg = "Using 'type' for the extensions is deprecated, the type should be supplied " \
                  "as the key to the dictionary, rather than an arbitrary name."
            LOG.warning(msg)
            ext_type = settings.pop('type')

        if ext_type not in ext_configs:
            ext_configs[ext_type] = dict()

        if isinstance(settings, dict):
            ext_configs[ext_type].update(settings)

        elif (isinstance(settings, str) and settings == 'default'):
            continue

        else:
            msg = "The supplied settings for the '%s' extension must be dict() or the 'default' " \
                  "keyword should be used."
            LOG.error(msg, ext_type)

    return load_extensions(ext_configs.keys(), ext_configs)

def _yaml_load_object(name, config, default, *args):
    """Helper for loading MooseDocs objects: Reader, Renderer, Translator"""

    options = config.get(name, dict())
    obj_type = options.pop('type', default)
    #try:
    return eval(obj_type)(*args, **options)
    #except NameError:
    #    msg = "ERROR: The %s block must contain a valid object name."
    #    LOG.error(msg, name)

def _yaml_load_content(config, in_ext, out_ext):
    """Load the 'Content' section."""

    options = config.get('Content', None)
    if options is None:
        msg = "The 'Content' section is required."
        raise exceptions.MooseDocsException(msg)

    items = []
    if isinstance(options, list):
        for value in options:
            items.append(dict(root_dir=value, content=None))
    elif isinstance(options, dict):
        for _, value in options.iteritems():
            content = value.get('content', None)
            items.append(dict(root_dir=value['root_dir'], content=content))

    return MooseDocs.tree.build_page_tree.doc_tree(items, in_ext, out_ext)
