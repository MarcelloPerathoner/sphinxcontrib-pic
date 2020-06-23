sphinxcontrib.pic
~~~~~~~~~~~~~~~~~

Draw pictures with 'little languages'.

Originally I used this to draw diagrams with GNU pic.  Hence the name.  Now
it works with many 'little languages', eg.  graphviz dot, GNU pic, plantuml, ...
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
