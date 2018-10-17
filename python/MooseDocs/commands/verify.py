#pylint: disable=missing-docstring
#* This file is part of the MOOSE framework
#* https://www.mooseframework.org
#*
#* All rights reserved, see COPYRIGHT for full restrictions
#* https://github.com/idaholab/moose/blob/master/COPYRIGHT
#*
#* Licensed under LGPL 2.1, please see LICENSE for details
#* https://www.gnu.org/licenses/lgpl-2.1.html
#pylint: enable=missing-docstring
import os
import sys
import re
import subprocess
import mooseutils
import MooseDocs

try:
    import bs4
except ImportError:
    print("The BeutifulSoup package (bs4) is required for the verify command, "
              "it may be downloaded by running the following:\n"
              "    pip install --user bs4")
    sys.exit(1)

def command_line_options(subparser, parent):
    """Command line options for 'verify' command."""
    parser = subparser.add_parser('verify', parents=[parent],
                                  help="Verify that rendering is working as expected.")

    parser.add_argument('-f', '--form', default='materialize',
                        choices=['materialize', 'html', 'json', 'latex'],
                        help="The desired output format to verify.")
    parser.add_argument('--update-gold', action='store_true',
                        help="Copy the rendered results to the gold directory.")

def insert_moose_dir(content):
    """Helper for adding '${MOOSE_DIR}' to content."""
    return content.replace(os.getenv('MOOSE_DIR'), '${MOOSE_DIR}')

def replace_moose_dir(content):
    """Helper for replacing '${MOOSE_DIR}' in contents."""
    return content.replace('${MOOSE_DIR}', os.getenv('MOOSE_DIR'))

def replace_uuid4(content):
    """Replace uuid.uuid4() numbers."""
    return re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
                  r'XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX', content)

def main(options):
    """Test all files in output with those in the gold."""

    # Create the content
    config = options.form + '.yml'
    subprocess.check_output(['python', 'moosedocs.py', 'build', '--config', config],
                            cwd=os.path.join(MooseDocs.MOOSE_DIR, 'python', 'MooseDocs', 'test'))

    # Define output and gold directories
    out_dir = os.path.join('output', options.form)
    gold_dir = os.path.join('gold', options.form)

    # Setup extensions
    if options.form in ['materialize', 'html']:
        extensions = ['.html']
    elif options.form == 'json':
        extensions = ['.json']
    elif options.form == 'latex':
        extensions = ['.tex']

    # Compare all files
    errno = 0
    for root, _, files in os.walk(out_dir):
        for fname in files:
            _, ext = os.path.splitext(fname)
            if ext in extensions:
                out = os.path.join(root, fname)
                with open(out, 'r') as fid:
                    out_content = replace_moose_dir(fid.read())
                    out_content = replace_uuid4(out_content)

                out = os.path.join(root, fname)
                gold = out.replace(out_dir, gold_dir)

                if options.update_gold:
                    dirname = os.path.dirname(gold)
                    if not os.path.isdir(dirname):
                        os.makedirs(dirname)
                    with open(gold, 'w+') as fid:
                        print("UPDATE GOLD: {}".format(gold))
                        fid.write(insert_moose_dir(out_content))

                out_content = bs4.BeautifulSoup(out_content, 'lxml').prettify()

                if not os.path.exists(gold):
                    print('MISSING GOLD: {}'.format(gold))
                    errno = 1
                else:
                    with open(gold, 'r') as fid:
                        gold_content = replace_moose_dir(fid.read())
                        gold_content = bs4.BeautifulSoup(gold_content, 'lxml').prettify()

                    diff = mooseutils.text_unidiff(out_content, gold_content,
                                                   out_fname=out, gold_fname=gold,
                                                   color=True, num_lines=2)
                    if diff:
                        print diff
                        errno = 1

    sys.exit(errno)
