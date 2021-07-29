#! /usr/bin/env python
# 
# TODO what the script does (detailed)
#
# The software is Open Source, licensed under the GNU Lesser General Public Version 3 (LGPLv3). See LICENSE.txt in repository.
#

"""TODO: what module does (brief)"""

# Standard packages
import re

# Installed packages
## TODO: import numpy

# Local packages
# TODO: def tomas_import(name): ... components = eval(name).split(); ... import nameN-1.nameN as nameN
from tomas_misc import debug
from tomas_misc.main import Main
from tomas_misc import system
## TODO:
## from tomas_misc.my_regex import my_re
## from tomas_misc import glue_helpers as gh

## TODO: Constants for switches omitting leading dashes (e.g., DEBUG_MODE = "debug-mode")
## Note: Run following in Emacs to interactively replace TODO_ARGn with option label
##    M-: (query-replace-regexp "todo\\([-_]\\)argn" "arg\\1name")
## where M-: is the emacs keystroke short-cut for eval-expression.
TODO_ARG1 = "TODO-arg1"
## TODO_ARG2 = "TODO-arg2"
## TODO_FILENAME = "TODO-filename"

## TODO:
## # Environment options
## # Note: These are intended for internal options not intended for end users.
## # It also allows for enabling options in one place rather than four
## # (e.g., [Main member] initialization, run-time value, and argument spec., along
## # with string constant definition).
## #
## FUBAR = system.getenv_bool("FUBAR", False,
##                            description="Fouled Up Beyond All Recognition processing")

class Script(Main):
    """Input processing class"""
    # TODO: -or-: """Adhoc script class (e.g., no I/O loop, just run calls)"""
    ## TODO: class-level member variables for arguments (avoids need for class constructor)
    TODO_arg1 = False
    ## TODO_arg2 = ""

    # TODO: add class constructor if needed for non-standard initialization
    ## def __init__(self, *args, **kwargs):
    ##     debug.trace_fmtd(5, "Script.__init__({a}): keywords={kw}; self={s}",
    ##                      a=",".join(args), kw=kwargs, s=self)
    ##     super(Script, self).__init__(*args, **kwargs)
    
    def setup(self):
        """Check results of command line processing"""
        debug.trace_fmtd(5, "Script.setup(): self={s}", s=self)
        ## TODO: extract argument values
        self.TODO_arg1 = self.get_parsed_option(TODO_ARG1, self.TODO_arg1)
        ## self.TODO_arg2 = self.get_parsed_option(TODO_ARG2, self.TODO_arg2)
        # TODO: self.TODO_filename = self.get_parsed_argument(TODO_FILENAME)
        debug.trace_object(5, self, label="Script instance")

    def process_line(self, line):
        """Processes current line from input"""
        debug.trace_fmtd(6, "Script.process_line({l})", l=line)
        # TODO: flesh out
        if self.TODO_arg1 and "TODO" in line:
            print("arg1 line: %s" % line)
        ## TODO: regex pattern matching
        ## elif my_re.search(self.TODO_arg2, line):
        ##     print("arg2 line: %s" % line)

    ## TODO: if no input proocessed, customize run_main_step instead
    ## and specify skip_input below
    ##
    ## def run_main_step(self):
    ##     """Main processing step"""
    ##     debug.trace_fmtd(5, "Script.run_main_step(): self={s}", s=self)
    ##

    ## TODO: def wrap_up(self):
    ##           # ...

    ## TODO: def clean_up(self):
    ##           # ...
    ##           super(Script, self).clean_up()

#-------------------------------------------------------------------------------
    
if __name__ == '__main__':
    debug.trace_current_context(level=debug.QUITE_DETAILED)
    debug.trace_fmt(4, "Environment options: {eo}",
                    eo=system.formatted_environment_option_descriptions())
    app = Script(
        description=__doc__,
        # Note: skip_input controls the line-by-line processing, which is inefficient but simple to
        # understand; in contrast, manual_input controls iterator-based input (the opposite of both).
        skip_input=False,
        manual_input=False,
        ## TODO: specify options and (required) arguments
        boolean_options=[(TODO_ARG1, "TODO-desc")],
        # Note: FILENAME is default argument unless skip_input
        ## positional_arguments=[FILENAME1, FILENAME2], 
        ## text_options=[(TODO_ARG2, "TODO-desc")],
        # Note: Following added for indentation: float options are not common
        float_options=None)
    app.run()
    debug.assertion(not any([re.search(r"^TODO_", m, re.IGNORECASE)
                             for m in dir(app)]))
