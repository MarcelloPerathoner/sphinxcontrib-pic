"""sphinxcontrib.pic
    ~~~~~~~~~~~~~~~~~

    Draw pictures with 'little languages'.

    Originally I used this to draw diagrams with GNU pic.  Hence the name.  Now
    it works with many 'little languages', eg.  graphviz dot, GNU pic, plantuml,
    ...
    It is not limited to pictures either, you can insert the output of any
    commandline program into your documentation.

    To work with this directive the 'little language' program must:

    - be callable from the commandline,
    - read from stdin and write to stdout.

    If the program cannot read from stdin or write to stdout you can try these
    pseudo-files: :file:`-` or :file:`/dev/stdin` for stdin and
    :file:`/dev/stdout` for stdout.  For stubborn cases call the program from
    inside a shell script that writes and reads temporary files.

    Add to your conf.py

       .. code::

          extensions = [
             ...
             'sphinxcontrib.pic',
          ]

          ...

          pic_options = {
              'dot' : {
                  'program' : ['dot', '-Tsvg'],
                  'align'   : 'center',
              },
              'pic' : {
                  'program' : 'm4 | dpic -v',
                  'shell'   : True,
                  'align'   : 'center',
                  'prolog'  : '.PS\n',
                  'epilog'  : '\n.PE\n',
              },
              'uml' : {
                  'program' : ['plantuml', '-tsvg', '-p'],
                  'align'   : 'center',
                  'prolog'  : '@startuml\n',
                  'epilog'  : '\n@enduml\n',
              },
              'tree' : {
                  'program'     : ['xargs', 'tree', '-l', '--noreport', '-I', '*~', '-I', '__pycache__'],
                  'format'      : 'text/plain',
                  'html-prolog' : '<div class="highlight"><div class="highlight"><pre>',
                  'html-epilog' : '</pre></div></div>',
              },
          }

    Add a separate entry into the :code:`pic_options` dictionary
    for every little language you plan to use.

    :param string program: The commandline and arguments as list.
                           The little language code goes into stdin.
    :param string align: How to align the output.
    :param string shell: Boolean. Use a shell (eg. for piping).
    :param string format: The format of the output. ('text/xml', 'text/plain' or 'image/png')
                          Defaults to 'text/xml'.
    :param string caption: Output a figure with this caption.
    :param string prolog: The little language code to prepend to all program input.
    :param string epilog: The little language code to append to all program input.
    :param string html-classes: Space separated list of classes to add to the top <div>.
    :param string html-prolog: The HTML code to prepend to all program output.
    :param string html-epilog: The HTML code to append to all program output.

    In your documentation use:

       .. code::

          .. pic:: dot
             :caption: A graphviz dot graph

             digraph G { client -> server }

          .. pic:: pic
             :caption: A GNU pic diagram

             box "client";
             arrow;
             box "server";

          .. pic:: uml
             :caption: A plantuml diagram

             client -> server

          .. pic:: tree
             :caption: Server directory structure

             ../server

    The argument of the directive specifies the little language to use.
    The parameters are the same as above.

    If you need even more power you can pipe your code through a pre-processor
    like the M4 macro processor, or post-process the SVG output with a tool like
    xsltproc.

    :copyright: Copyright 2020 by Marcello Perathoner <marcello@perathoner.de>
    :license: BSD, see LICENSE for details.

"""

import base64
import re
import subprocess
import os

from typing import Any, Callable, Dict, Iterator, List, Sequence, Set, Tuple, Union # noqa

import docutils
from docutils.parsers.rst import directives

import sphinx
from sphinx.locale import _, __
from sphinx.util import logging
from sphinx.util.docutils import nodes, SphinxDirective, SphinxTranslator
from sphinx.util.nodes import set_source_info
from sphinx.errors import SphinxWarning, SphinxError, ExtensionError
from sphinx.util.logging import getLogger
from sphinx.writers.html import HTMLTranslator
from sphinx.writers.latex import LaTeXTranslator

import pbr.version

logger = getLogger (__name__)

if False:
    # For type annotations
    from typing import Any, Dict  # noqa
    from sphinx.application import Sphinx  # noqa

NAME = 'pic'

__version__ = pbr.version.VersionInfo (NAME).version_string ()


class PicError (SphinxError):
    """ The PIC exception. """
    category = NAME + ' error'


class PicNode (nodes.General, nodes.Inline, nodes.Element):

    def render (self, code: str) -> bytes:
        """Render PIC code.

        Exec the program and handle errors.
        """

        proc = subprocess.Popen (
            self['options']['program'],
            stdin    = subprocess.PIPE,
            stdout   = subprocess.PIPE,
            stderr   = subprocess.PIPE,
            cwd      = self['options']['cwd'],
            shell    = self['options']['shell'],
        )

        try:
            stdout, stderr = proc.communicate (code.encode ('utf-8'), timeout = 15)

        except subprocess.CalledProcessError as exc:
            raise PicError (__ ('The pic program exited with error:\n[stderr]\n%r\n'
                                '[stdout]\n%r') % (stderr, stdout))
        except subprocess.TimeoutExpired as exc:
            proc.kill ()
            stdout, stderr = proc.communicate ()
            raise PicError (__ ('The pic program timed out:\n[stderr]\n%r\n'
                                '[stdout]\n%r') % (stderr, stdout))
        except OSError as exc:
            raise PicError (__ ('The pic program %r cannot be run '
                                'check the pic_program setting') % program)
        if stderr:
            logger.info (__ ('The PIC Code was: %s') % code)
            raise PicError (__ ('The pic program produced errors:\n[stderr]\n%s\n') % stderr)

        return stdout


    def html_visit (self, translator: HTMLTranslator):

        classes = ['pic']
        align   = ''
        format_ = self['options']['format']

        if 'align' in self:
            classes.append ('align-%s' % self['align'])
            align = 'align="%s"' % self['align']

        classes.append ('pic-format-%s'   % format_.replace ('/', '-'))
        classes.append ('pic-language-%s' % self['options']['language'])

        if 'html-classes' in self['options']:
            classes += self['options']['html-classes'].split ()

        translator.body.append ('<div %s class="%s">\n' % (align, ' '.join (classes)))
        translator.body.append (self['options']['html-prolog'])

        if format_ == 'text/xml':
            stdout = self.render (self['code']).decode ('utf-8')

            # fix standalone SVG for embedding
            stdout = re.sub (r'<\?xml .*?\?>',  '', stdout, flags = re.S)
            stdout = re.sub (r'<!DOCTYPE .*?>', '', stdout, flags = re.S)

            # stupid plantuml sets dimensions in a style on the element
            # so you cannot override them in CSS
            stdout = re.sub (r'(<svg .*?)style=".*?"', r'\1', stdout, flags = re.S)

            translator.body.append (stdout)

        if format_ == 'text/plain':
            stdout = self.render (self['code']).decode ('utf-8')
            translator.body.append (stdout)

        if format_ == 'image/png':
            stdout = self.render (self['code'])
            translator.body.append (
                '<img src="data:image/png;base64,%s" />\n' % base64.b64encode (stdout)
            )

        translator.body.append (self['options']['html-epilog'])
        translator.body.append ('</div>\n')

        raise nodes.SkipNode


class PicDirective (SphinxDirective):
    """ Directive to draw a PIC diagram.

    Processes the directive into a node and adds it to the RST syntax tree.
    """

    required_arguments = 1

    # a path to a file containing the PIC program
    optional_arguments = 1

    # the PIC program
    has_content = True

    name = NAME

    base_option_spec = {
        'align'        : lambda v: directives.choice (v, ('left', 'center', 'right')),
        'format'       : lambda v: directives.choice (v, ('text/xml', 'text/plain', 'image/png')),
        'caption'      : directives.unchanged,
        'name'         : directives.unchanged,
        'html-classes' : directives.unchanged,
        # the prolog and epilog to add around the program output
        'html-prolog'  : directives.unchanged,  # prolog (overrides conf.py)
        'html-epilog'  : directives.unchanged,  # epilog (overrides conf.py)
    }

    option_spec = {
        # the prolog and epilog to add around the little language code
        'prolog'       : directives.unchanged,  # prolog (overrides conf.py)
        'epilog'       : directives.unchanged,  # epilog (overrides conf.py)
    }
    option_spec.update (base_option_spec)

    def err (self, msg):
        document = self.state.document
        return [ document.reporter.warning (msg, line = self.lineno) ]

    def figure_wrapper (self,
                        node: PicNode,
                        caption: str) -> nodes.figure:
        figure_node = nodes.figure ('', node)
        if 'align' in node:
            figure_node['align'] = node.attributes.pop ('align')

        inodes, messages = self.state.inline_text (caption, self.lineno)
        caption_node = nodes.caption (caption, '', *inodes)
        caption_node.extend (messages)
        set_source_info (self, caption_node)
        figure_node += caption_node
        return figure_node

    def get_opt (self, name, required = False):

        # opt = self.options.get (name) or getattr (self.env.config, "%s_%s" % (self.name, name))

        options  = getattr (self.env.config, self.name + '_options')
        language = self.options['language']
        if language not in options:
            raise PicError (__ ('Unknown language %s in directive.') % language)

        options = options[language]

        opt = self.options.get (name) or options.get (name)
        if required and not opt:
            raise PicError (
                ':%s: option required in directive (or set %s_%s in conf.py).' % (name, self.name, name)
            )
        return opt

    def get_code (self):
        """ Get the PIC code. """

        if len (self.arguments) > 1:
            if self.content:
                return self.err (__ ('The PIC directive cannot have both content and a filename argument.')),

            filename = self.arguments[1]
            try:
                with open (filename, encoding = 'utf-8') as fp:
                    pic_code = fp.read ()
                    self.env.note_dependency (filename)
            except OSError:
                return self.err (__ ('External PIC file %r not found or reading it failed.') % filename)
        else:
            pic_code = '\n'.join (self.content)
            if not pic_code.strip ():
                return self.err (__ ('Found PIC directive without content.'))

        prolog = self.get_opt ('prolog') or ''
        epilog = self.get_opt ('epilog') or ''
        return prolog + pic_code + epilog


    def _run (self):
        """ Turn the directive into nodes. """

        node = PicNode ()
        node['code']    = self.get_code ().strip ()
        node['options'] = {
            'program'      : self.get_opt ('program'),
            'shell'        : self.get_opt ('shell') or False,
            'cwd'          : self.get_opt ('cwd'),
            'alt'          : self.get_opt ('alt'),
            'language'     : self.get_opt ('language'),
            'format'       : self.get_opt ('format') or 'text/xml',
            'html-classes' : self.get_opt ('html-classes') or '',
            'html-prolog'  : self.get_opt ('html-prolog') or '',
            'html-epilog'  : self.get_opt ('html-epilog') or '',
        }

        node['align'] = self.get_opt ('align')

        if self.get_opt ('depends'):
            self.env.note_dependency (self.get_opt ('depends'))

        if 'caption' not in self.options:
            self.add_name (node)
            return [node]
        else:
            figure = self.figure_wrapper (node, self.options['caption'])
            self.add_name (figure)
            return [figure]


    def run (self):
        self.options['language'] = self.arguments[0]
        return self._run ()


def html_visit_pic (translator: HTMLTranslator, node: PicNode) -> None:
    node.html_visit (translator)


def dummy_visit_pic (translator: HTMLTranslator, node: PicNode) -> None:
    if node['alt']:
        self.body.append (_('[graph: %s]') % node['alt'])
    else:
        self.body.append (_('[graph]'))
    raise nodes.SkipNode


def setup (app):
    # type: (Sphinx) -> Dict[unicode, Any]

    app.add_config_value (NAME + '_options', {}, 'env')

    app.add_directive (NAME, PicDirective)

    app.add_node (
        PicNode,
        html    = (html_visit_pic,  None),
        latex   = (dummy_visit_pic, None),
        texinfo = (dummy_visit_pic, None),
        text    = (dummy_visit_pic, None),
        man     = (dummy_visit_pic, None)
    )

    return {
        'version'            : __version__,
        'parallel_read_safe' : True,
    }
