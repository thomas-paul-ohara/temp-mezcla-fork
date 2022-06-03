#! /usr/bin/env python
#
# Functions for system related access, such as running command or
# getting environment values.
#
# TODO:
# - * Add support for checking for getenv_xyz-style parameters not used!
# - Finish python 2/3 special case handling via six package (e.g., in order
#   to remove stupud pylint warnings).
# - Rename as system_utils so clear that non-standard package.
# - Add support for maintaining table of environment variables with optional descriptions.
# - Add safe_int from tpo_common, as includes support for base (e.g., 16 for hex).
# - Reconcile against functions in tpo_common.py (e.g., to make sure functionality covered and similar tracing supported).
# - Make sure format-based function tracing is well formed:
#   ex: "is_dir{p}" => "is_dir({p})".
# - ** Define generic function for creating simple wrappers:
#   ex: def fu(): r = sys.fu(); trace(N, f"fub() returned {r}"); return r
#       => fu = define_wrapper(trace_level=N, sys.fu)
#

"""System-related functions"""

# Standard packages
from collections import defaultdict, OrderedDict
import datetime
import inspect
import os
import pickle
import re
import six
import sys
import time
## OLD: import urllib

# Installed packages
## OLD: import requests

# Local packages
from mezcla import debug
from mezcla.debug import UTF8

# Constants
STRING_TYPES = six.string_types
MAX_SIZE = six.MAXSIZE
MAX_INT = MAX_SIZE
TEMP_DIR = None

#-------------------------------------------------------------------------------
# Support for needless python changes

def maxint():
    """Maximum size for an integer"""
    # Note: this is just a sanity check
    debug.assertion(MAX_INT == MAX_SIZE)
    return MAX_INT

#-------------------------------------------------------------------------------
# Support for environment variable access
# TODO: Put in separate module

env_options = {}
env_defaults = {}
#
def register_env_option(var, description, default):
    """Register environment VAR as option with DESCRIPTION and DEFAULT"""
    # Note: The default value is typically the default value passes into the
    # getenv_xyz call, not the current value from the environment.
    ## OLD: debug.trace_fmt(7, "register_env_option({v}, {d})", v=var, d=description)
    debug.trace_fmt(7, "register_env_option({v}, {dsc}, {dft})",
                    v=var, dsc=description, dft=default)
    global env_options
    global env_defaults
    ## OLD: env_options[var] = (description or "")
    env_options[var] = description
    env_defaults[var] = default
    return


def get_registered_env_options():
    """Returns list of environment options registered via register_env_option"""
    ## OLD: option_names = [k for k in env_options if (env_options[k] and env_options[k].strip())]
    option_names = [k for k in env_options if (env_options[k] is not None)]
    debug.trace_fmt(5, "get_registered_env_options() => {ON}", on=option_names)
    return option_names


def get_environment_option_descriptions(include_all=None, include_default=None, indent=" "):
    """Returns list of environment options and their descriptions"""
    # get_environment_option_descriptions() => [("TMP": "Old temp. dir. (/tmp)"), ("TMPDIR": "New temp. dir. (None)"), ("EMPTYDIR": "Empty. dir. ('')")]
    # Note: include_default is True when parameter is None
    debug.trace_fmt(5, "env_options={eo}", eo=env_options)
    debug.trace_fmt(5, "env_defaults={ed}", ed=env_defaults)
    if include_all is None:
        include_all = debug.verbose_debugging()
    if include_default is None:
        include_default = True
    #
    def _format_env_option(opt):
        """Returns OPT description and optionally default value (if INCLUDE_DEFAULT)"""
        debug.trace_fmt(7, "_format_env_option({o})", o=opt)
        ## OLD: desc_spec = env_options.get(opt, "_")
        ## TEST: Uses unicode O-with-stoke (U+00D8) to indicate n/a
        ## TEMP: desc_spec = to_text(env_options.get(opt))
        env_desc = env_options.get(opt)
        ## TEST: desc_spec = ("\u00D8 " if (env_options.get(opt) is None) else env_desc)
        desc_spec = ("n/a" if (env_options.get(opt) is None) else env_desc)
        default_spec = ""
        if include_default:
            # Note: environment default is based on prior-initialization state
            default_value = env_defaults.get(opt, None)
            has_default = (default_value is not None)
            # Note: add quotes to distinguish "None" from None (i.e., str vs. NoneType)
            default_spec = (("(%r)" % default_value) if has_default else "(None)")
        default_spec = default_spec.replace("\n", "\\n")
        result = (opt, desc_spec + indent + default_spec)
        debug.trace_fmt(9, "_format_env_option() => {r}", r=result)
        return result
    #
    option_descriptions = [_format_env_option(opt) for opt in env_options if (env_options[opt] or include_all)]
    debug.trace_fmt(5, "get_environment_option_descriptions() => {od}",
                    od=option_descriptions)
    return option_descriptions


def formatted_environment_option_descriptions(sort=False, include_all=None, indent="\t"):
    """Returns string list of environment options and their descriptions (separated by newlines and tabs), optionally SORTED"""
    option_info = get_environment_option_descriptions(include_all)
    if sort:
        option_info = sorted(option_info)
    entry_separator = "\n%s" % indent
    descriptions = entry_separator.join(["%s%s%s" % (opt, indent, (desc if desc else "n/a")) for (opt, desc) in option_info])
    debug.trace_fmt(6, "formatted_environment_option_descriptions() => {d}",
                    d=descriptions)
    return descriptions

def getenv(var, default_value=None):
    """Simple wrapper around os.getenv, with tracing"""
    # Note: Use getenv_* for type-specific versions with env. option description
    result = os.getenv(var, default_value)
    debug.trace_fmt(5, "getenv({v}, {dv}) => {r}", v=var, dv=default_value, r=result)
    return result


def getenv_text(var, default=None, description=None, helper=False):
    """Returns textual value for environment variable VAR (or DEFAULT value).
    Notes: HELPER indicates that this call is in support of another getenv-type function (e.g., getenv_bool), so that tracing is only shown at higher verbosity level (e.g., 6 not 5).
    DESCRIPTION used for get_environment_option_descriptions."""
    # Note: default is empty string to ensure result is string (not NoneType)
    ## TODO: add way to block registration
    register_env_option(var, description, default)
    if default is None:
        debug.trace(4, f"Warning: getenv_text treats default None as ''; consider using getenv_value for '{var}' instead")
        default = ""
    text_value = os.getenv(var)
    ## OLD: if not text_value:
    ## TODO?: if ((not helper and (text_value is None)) or (not text_value)):
    if (text_value is None):
        debug.trace_fmtd(6, "getenv_text: no value for var {v}", v=var)
        text_value = default
    trace_level = 6 if helper else 5
    ## DEBUG: sys.stderr.write("debug.trace_fmtd({trace_level} \"getenv_text('{v}', [def={dft}], [desc={desc}], [helper={hlpr}]) => {r}\"".format(trace_level=trace_level, v=var, dft=default, desc=description, hlpr=helper, r=text_value))
    debug.trace_fmtd(trace_level, "getenv_text('{v}', [def={dft}], [desc={desc}], [helper={hlpr}]) => {r}",
                     v=var, dft=default, desc=description, hlpr=helper, r=text_value)
    return (text_value)


def getenv_value(var, default=None, description=None):
    """Returns environment value for VAR as string or DEFAULT (can be None), with optional DESCRIPTION"""
    # EX: getenv_value("bad env var") => None
    register_env_option(var, description, default)
    value = os.getenv(var, default)
    # note: uses !r for repr()
    debug.trace_fmtd(5, "getenv_value({v!r}, [def={dft!r}], [desc={dsc!r}]]) => {val!r}",
                     v=var, dft=default, dsc=description, val=value)
    return (value)


DEFAULT_GETENV_BOOL = False
#
def getenv_bool(var, default=DEFAULT_GETENV_BOOL, description=None):
    """Returns boolean flag based on environment VAR (or DEFAULT value), with optional DESCRIPTION
    Note: "0" or "False" is interpreted as False, and any other value as True."""
    # EX: getenv_bool("bad env var", None) => False
    # TODO: * Add debugging sanity checks for type of default to help diagnose when incorrect getenv_xyz variant used (e.g., getenv_int("USE_FUBAR", False) => ... getenv_bool)!
    bool_value = default
    value_text = getenv_value(var, description=description, default=default)
    if (isinstance(value_text, str) and value_text.strip()):
        bool_value = to_bool(value_text)
    debug.trace_fmtd(5, "getenv_bool({v}, {d}) => {r}",
                     v=var, d=default, r=bool_value)
    return (bool_value)
#
getenv_boolean = getenv_bool


def getenv_number(var, default=-1.0, description=None, helper=False):
    """Returns number based on environment VAR (or DEFAULT value), with optional description"""
    # Note: use getenv_int or getenv_float for typed variants
    num_value = default
    value = getenv_value(var, description=description, default=default)
    if (isinstance(value, str) and value.strip()):
         num_value = to_float(value)
    trace_level = 6 if helper else 5
    debug.trace_fmtd(trace_level, "getenv_number({v}, {d}) => {r}",
                     v=var, d=default, r=num_value)
    return (num_value)
#
getenv_float = getenv_number



def getenv_int(var, default=-1, description=None):
    """Version of getenv_number for integers, with optional DESCRIPTION"""
    # EX: getenv_int("?", 1.5) => 1
    value = getenv_number(var, description=description, default=default, helper=True)
    if (not isinstance(value, int)):
        value = to_int(value)
    debug.trace_fmtd(5, "getenv_int({v}, {d}) => {r}",
                     v=var, d=default, r=value)
    return (value)
#
getenv_integer = getenv_int


#-------------------------------------------------------------------------------
# Miscellaneous functions

def get_exception():
    """Return information about the exception that just occurred"""
    # Note: Convenience wrapper to avoid need to import sys in simple scripts.
    return sys.exc_info()

def print_error(text):
    """Output TEXT to standard error
    Note: Use print_error_fmt to include format keyword arguments"
    """
    # ex: print_error("Fubar!")
    print(text, file=sys.stderr)
    return

def print_stderr(text, **kwargs):
    """Output TEXT to standard error, using KWARGS for formatting"""
    # NOTE: Deprecated function: use print_error_fmt instead.
    # ex: print_stderr("Error: F{oo}bar!", oo=("oo" if (time_in_secs() % 2) else "u"))
    # TODO: rename as print_error_fmt
    # TODO: weed out calls that use (text.format(...)) rather than (text, ...)
    formatted_text = text
    try:
        # Note: to avoid interpolated text as being interpreted as variable
        # references, this function should do the formatting
        # ex: print_stderr("hey {you}".format(you="{u}")) => print_stderr("hey {you}".format(you="{u}"))
        debug.assertion(kwargs or (not re.search(r"{\S*}", text)))
        formatted_text = text.format(**kwargs)
    except(KeyError, ValueError, UnicodeEncodeError):
        sys.stderr.write("Warning: Problem in print_stderr: {exc}\n".format(
            exc=get_exception()))
        if debug.verbose_debugging():
            print_full_stack()
    print(formatted_text, file=sys.stderr)
    return
#
print_error_fmt = print_stderr


def print_exception_info(task, show_stack=None):
    """Output exception information to stderr regarding TASK (e.g., function);
    Note: Optionally includes stack trace (default when detailed debugging)"""
    # Note: used to simplify exception reporting of border conditions
    # ex: print_exception_info("read_csv")
    if show_stack is None:
        show_stack = debug.verbose_debugging()
    print_error("Error during {t}: {exc}".
                 format(t=task, exc=get_exception()))
    if show_stack:
        print_full_stack()
    return


def exit(message, **namespace):    # pylint: disable=redefined-builtin
    """Display error MESSAGE to stderr and then exit, using optional
    NAMESPACE for format"""
    if namespace:
        message = message.format(**namespace)
    print_stderr(message)
    return sys.exit()


def setenv(var, value):
    """Set environment VAR to VALUE"""
    debug.trace_fmtd(5, "setenv({v}, {val})", v=var, val=value)
    os.environ[var] = value
    return
## TODO: move above (e.g., after getenv)


def print_full_stack(stream=sys.stderr):
    """Prints stack trace (for use in error messages, etc.)"""
    # Notes: Developed originally for Android stack tracing support.
    # Based on http://blog.dscpl.com.au/2015/03/generating-full-stack-traces-for.html.
    # TODO: Update based on author's code update (e.g., ???)
    # TODO: Fix off-by-one error in display of offending statement!
    debug.trace_fmtd(7, "print_full_stack(stream={s})", s=stream)
    stream.write("Traceback (most recent call last):\n")
    try:
        # Note: Each tuple has the form (frame, filename, line_number, function, context, index)
        item = None
        # Show call stack excluding caller
        for item in reversed(inspect.stack()[2:]):
            stream.write('  File "{1}", line {2}, in {3}\n'.format(*item))
        for line in item[4]:
            stream.write('  ' + line.lstrip())
        # Show context of the exception from caller to offending line
        stream.write("  ----------\n")
        for item in inspect.trace():
            stream.write('  File "{1}", line {2}, in {3}\n'.format(*item))
        for line in item[4]:
            stream.write('  ' + line.lstrip())
    except:
        debug.trace_fmtd(3, "Unable to produce stack trace: {exc}", exc=get_exception())
    stream.write("\n")
    return


def trace_stack(level=debug.VERBOSE):
    """Output stack trace to stderr (if at trace LEVEL or higher)"""
    if debug.debugging(level):
        print_full_stack()
    return

    
def get_current_function_name():
    """Returns name of current function that is running"""
    function_name = "???"
    try:
        current_frame = inspect.stack()[1]
        function_name = current_frame[3]
    except:
        debug.trace_fmtd(3, "Unable to resolve function name: {exc}", exc=get_exception())
    return function_name


def open_file(filename, encoding=None, errors=None, **kwargs):
    """Wrapper around around open() with FILENAME using UTF-8 encoding and ignoring ERRORS (both by default)
    Note: mode is left at default (i.e., 'r')"""
    # TODO: implement as with-style context
    if encoding is None:
        encoding = "UTF-8"
    if errors is None:
        errors = 'ignore'
    result = None
    try:
        # pylint: disable=consider-using-with; note: bogus 'Bad option value' warning
        result = open(filename, encoding=encoding, errors=errors, **kwargs)
    except IOError:
        debug.trace_fmtd(3, "Unable to open {f}: {exc}", f=filename, exc=get_exception())
    debug.trace_fmt(5, "open({f}, [{enc}, {err}], kwargs={kw}) => {r}",
                    f=filename, enc=encoding, err=errors, kw=kwargs, r=result)
    return result


def save_object(file_name, obj):
    """Saves OBJ to FILE_NAME in pickle format"""
    # Note: The data file is created in binary mode to avoid quirk under Windows.
    # See https://stackoverflow.com/questions/556269/importerror-no-module-named-copy-reg-pickle.
    debug.trace_fmtd(6, "save_object({f}, _)", f=file_name)
    try:
        with open(file_name, 'wb') as f:
            pickle.dump(obj, f)
    except (AttributeError, IOError, TypeError, ValueError):
        debug.trace_fmtd(1, "Error: Unable to save object to {f}: {exc}",
                         f=file_name, exc=get_exception())
    return

    
def load_object(file_name, ignore_error=False):
    """Loads object from FILE_NAME in pickle format"""
    # Note: Reads in binary mode to avoid unicode decode error. See
    #    https://stackoverflow.com/questions/32957708/python-pickle-error-unicodedecodeerror
    obj = None
    try:
        with open(file_name, 'rb') as f:
            ## OLD: obj = pickle.load(f)
            try:
                obj = pickle.load(f)
            except (UnicodeDecodeError):
                if (sys.version_info.major > 2):
                    # note: treats strings in python2-pickled files as bytes (not Ascii)
                    obj = pickle.load(f, encoding='bytes') 
    except (AttributeError, IOError, TypeError, ValueError):
        if (not ignore_error):
            print_stderr("Error: Unable to load object from {f}: {exc}".
                         format(f=file_name, exc=get_exception()))
    debug.trace_fmtd(7, "load_object({f}) => {o}", f=file_name, o=obj)
    return obj


def quote_url_text(text, unquote=False):
    """(un)Quote TEXT to make suitable for use in URL. Note: This return the input if the text has encoded characters (i.e., %HH) where H is uppercase hex digit."""
    # Note: This is a wrapper around quote_plus and thus escapes slashes, along with spaces and other special characters (";?:@&=+$,\"'").
    # EX: quote_url_text("<2/") => "%3C2%2f"
    # EX: quote_url_text("Joe's hat") => "Joe%27s+hat"
    # EX: quote_url_text("Joe%27s+hat") => "Joe%27s+hat"
    debug.trace_fmtd(7, "in quote_url_text({t})", t=text)
    result = text
    quote = (not unquote)
    try:
        ## BAD: if not re.search("%[0-9A-F]{2}", text):
        proceed = True
        if proceed:
            # pylint: disable=no-member
            fn = None
            ## TODO: debug.trace_object(6, "urllib", urllib, show_all=True)
            if sys.version_info.major > 2:
                ## TODO: debug.trace_object(6, "urllib.parse", urllib.parse, show_all=True)
                import urllib.parse   # pylint: disable=redefined-outer-name, import-outside-toplevel
                ## TODO: debug.trace_fmt(6, "take 2 urllib.parse", m=urllib.parse, show_all=True)
                fn = urllib.parse.quote_plus if quote else urllib.parse.unquote_plus
            else:
                fn = urllib.quote_plus if quote else urllib.unquote_plus
                text = to_utf8(text)
            result = fn(text)
    except (TypeError, ValueError):
        debug.trace_fmtd(6, "Exception quoting url text 't': {exc}",
                         t=text, exc=get_exception())
        
    debug.trace_fmtd(6, "out quote_url_text({t}) => {r}", t=text, r=result)
    return result
#
def unquote_url_text(text):
    """Unquotes URL TEXT:
    Note: Wrapper around quote_url_text w/ UNQUOTE set"""
    return quote_url_text(text, unquote=True)

def escape_html_text(text):
    """Add entity encoding to TEXT to make suitable for HTML"""
    # Note: This is wrapper around html.escape and just handles
    # '&', '<', '>', and '"'.
    # EX: escape_html_text("<2/") => "&lt;2/"
    # EX: escape_html_text("Joe's hat") => "Joe's hat"
    debug.trace_fmtd(7, "in escape_html_text({t})", t=text)
    result = ""
    if (sys.version_info.major > 2):
        # TODO: move import to top
        import html                    # pylint: disable=import-outside-toplevel, import-error
        result = html.escape(text)     # pylint: disable=deprecated-method, no-member
    else:
        import cgi                     # pylint: disable=import-outside-toplevel, import-error
        result = cgi.escape(text, quote=True)    # pylint: disable=deprecated-method, no-member
    debug.trace_fmtd(6, "out escape_html_text({t}) => {r}", t=text, r=result)
    return result


def unescape_html_text(text):
    """Remove entity encoding, etc. from TEXT (i.e., undo"""
    # Note: This is wrapper around html.unescape (Python 3+) or
    # HTMLParser.unescape (Python 2).
    # See https://stackoverflow.com/questions/21342549/unescaping-html-with-special-characters-in-python-2-7-3-raspberry-pi.
    # EX: unescape_html_text(escape_html_text("<2/")) => "<2/"
    debug.trace_fmtd(7, "in unescape_html_text({t})", t=text)
    result = ""
    if (sys.version_info.major > 2):
        # TODO: see if six.py supports html-vs-cgi:unescape
        import html                   # pylint: disable=import-outside-toplevel, import-error
        result = html.unescape(text)
    else:
        import HTMLParser             # pylint: disable=import-outside-toplevel, import-error
        html_parser = HTMLParser.HTMLParser()
        result = html_parser.unescape(text)
    debug.trace_fmtd(6, "out unescape_html_text({t}) => {r}", t=text, r=result)
    return result


NEWLINE = "\n"
TAB = "\t"
#
class stdin_reader(object):
    """Iterator for reading from stdin that replaces runs of whitespace by tabs"""
    # TODO: generalize to file-based iterator
    
    def __init__(self, *args, **kwargs):
        """Class constructor"""
        debug.trace_fmtd(5, "Script.__init__({a}): keywords={kw}; self={s}",
                         a=",".join(args), kw=kwargs, s=self)
        self.delimiter = kwargs.get('delimiter', "\t")
        if (sys.version_info.major > 2):
            super().__init__(*args, **kwargs)
        else:
            # pylint: disable=super-with-arguments; gives 'Bad option value' warning
            super(stdin_reader, self).__init__(*args, **kwargs)
    
    def __iter__(self):
        """Returns first line in stdin iteration (empty string upon EOF)"""
        return self.__next__()

    def __next__(self):
        """Returns next line in stdin iteration (empty string upon EOF)"""
        try:
            line = self.normalize_line(input())
        except EOFError:
            line = ""
        return line

    def normalize_line(self, original_line):
        """Normalize line (e.g., replacing spaces with single tab)"""
        debug.trace_fmtd(6, "in normalize_line({ol})", ol=original_line)
        line = original_line
        # Remove trailing newline
        if line.endswith(NEWLINE):
            line = line[:-1]
        # Replace runs of spaces with a single tab
        if (self.delimiter == TAB):
            line = re.sub(r"  *", TAB, line)
        # Trace the revised line and return it
        debug.trace_fmtd(6, "normalize_line() => {l}", l=line)
        return line


def read_all_stdin():
    """Read all STDIN and return as a string"""
    data = ''.join(sys.stdin.readlines()) if not sys.stdin.isatty() else ''
    debug.trace(debug.VERBOSE, f'read_all_stdin() => "{data}"')
    return data


def read_entire_file(filename, **kwargs):
    """Read all of FILENAME and return as a string
    Note: optional arguments to open() passed along (e.g., encoding amd error handling)"""
    ## EX: (write_file("/tmp/fu", "1\n2\n3\n"), read_entire_file("/tmp/fu"))[1] => "1\n2\n3\n"
    data = ""
    try:
        ## OLD: with open(filename) as f:
        with open_file(filename, **kwargs) as f:
            data = from_utf8(f.read())
    ## OLD except IOError:
    except (AttributeError, IOError):
        # TODO: use print_stderr so that shown in optimized version
        Level = 4 if (kwargs.get("errors") == "ignore") else 1
        debug.trace_fmtd(Level, "Error: Unable to read file '{f}': {exc}",
                         f=filename, exc=get_exception())
    debug.trace_fmtd(8, "read_entire_file({f}) => {r}", f=filename, r=data)
    return data
#
read_file = read_entire_file


def read_binary_file(filename):
    """Read FILENAME as byte stream"""
    debug.trace_fmt(7, "read_binary_file({f}, _)", f=filename)
    data = []
    try:
        with open(filename, "rb") as f:
            data = f.read()
    except (IOError, ValueError):
        debug.trace_fmtd(1, "Error: Problem reading file '{f}': {exc}",
                         f=filename, exc=get_exception())
    ## TODO: output hexdump excerpt (e.g., via https://pypi.org/project/hexdump)
    return data


def read_directory(directory):
    """Returns list of files in DIRECTORY"""
    # Note simple wrapper around os.listdir with tracing
    # EX: (intersection(["init.d", "passwd"], read_directory("/etc")))
    files = os.listdir(directory)
    debug.trace_fmtd(5, "read_directory({d}) => {r}", d=directory, r=files)
    return files

def get_directory_filenames(directory, just_regular_files=False):
    """Returns full pathname for files in DIRECTORY, optionally restrictded to JUST_REGULAR_FILES
    Note: The files are returned in lexicographical order"""
    # EX: ("/etc/passwd" in get_directory_filenames("/etc")
    # EX: ("/boot" not in get_directory_filenames("/", just_regular_files=True))
    return_all_files = (not just_regular_files)
    files = []
    for dir_filename in sorted(read_directory(directory)):
        full_path = form_path(directory, dir_filename)
        if (return_all_files or is_regular_file(full_path)):
            files.append(full_path)
    debug.trace_fmtd(5, "get_directory_filenames({d}) => {r}", d=directory, r=files)
    return files
    
def read_lookup_table(filename, skip_header=False, delim=None, retain_case=False):
    """Reads FILENAME and returns as hash lookup, optionally SKIP[ing]_HEADER and using DELIM (tab by default).
    Note: Input is made lowercase unless RETAIN_CASE."""
    # Note: the hash lookup uses defaultdict
    debug.trace_fmt(4, "read_lookup_table({f}, [skip_header={sh}, delim={d}, retain_case={rc}])", 
                    f=filename, sh=skip_header, d=delim, rc=retain_case)
    if delim is None:
        delim = "\t"
    ## OLD: hash_table = {}
    hash_table = defaultdict(str)
    line_num = 0
    try:
        # TODO: use csv.reader
        with open(filename) as f:
            for line in f:
                line_num += 1
                if (skip_header and (line_num == 1)):
                    continue
                ## OLD: line = from_utf8(line)
                line = from_utf8(line.rstrip())
                if not retain_case:
                    line = line.lower()
                if delim in line:
                    (key, value) = line.split(delim, 1)
                    hash_table[key] = value
                else:
                    delim_spec = ("\\t" if (delim == "\t") else delim)
                    debug.trace_fmt(2, "Warning: Ignoring line {n} w/o delim ({d}): {l}", 
                                    n=line_num, d=delim_spec, l=line)
    except (IOError, ValueError):
        debug.trace_fmtd(1, "Error creating lookup from '{f}': {exc}",
                         f=filename, exc=get_exception())
    debug.trace_fmtd(7, "read_lookup_table({f}) => {r}", f=filename, r=hash_table)
    return hash_table


def create_boolean_lookup_table(filename, delim=None, retain_case=False, **kwargs):
    """Create lookup hash table from string keys to boolean occurrence indicator.
    Notes:
    - The key is first field, based on DELIM (tab by default): other values ignored.
    - The key is made lowercase, unless RETAIN_CASE.
    - The hash is of type defaultdict(bool).
    """
    if delim is None:
        delim = "\t"
    # TODO: allow for tab-delimited value to be ignored
    debug.trace_fmt(4, "create_boolean_lookup_table({f}, [retain_case={rc}])", 
                    f=filename, rc=retain_case)
    lookup_hash = defaultdict(bool)
    try:
        ## with open(filename) as f:
        with open_file(filename, **kwargs) as f:
            for line in f:
                ## OLD: key = line.strip().lower()
                key = line.strip()
                if not retain_case:
                    key = key.lower()
                ## OLD: debug.assertion(delim not in key)
                if delim in key:
                    key = key.split(delim)[0]
                lookup_hash[key] = True
    except (IOError, ValueError):
        debug.trace_fmtd(1, "Error: Creating boolean lookup from '{f}': {exc}",
                         f=filename, exc=get_exception())
    debug.trace_fmt(7, "create_boolean_lookup_table => {h}", h=lookup_hash)
    return lookup_hash


def lookup_entry(hash_table, entry, retain_case=False):
    """Return HASH_TABLE value for ENTRY, optionally RETAINing_CASE"""
    key = entry if retain_case else entry.lower()
    result = hash_table[key]
    debug.trace_fmt(6, "lookup_entry(_, {e}, [case={rc}) => {r}",
                    e=entry, rc=retain_case, r=result)
    return result

                
def write_file(filename, text, skip_newline=False):
    """Create FILENAME with TEXT.
    Note: A newline is added at the end if missing unless SKIP_NEWLINE"""
    debug.trace_fmt(7, "write_file({f}, {t})", f=filename, t=text)
    # EX: f = "/tmp/_it.list"; write_file(f, "it"); read_file(f) => "it\n"
    # EX: write_file(f, "it", skip_newline=True); read_file(f) => "it"
    try:
        if not isinstance(text, STRING_TYPES):
            text = to_string(text)
        with open(filename, "w") as f:
            f.write(to_utf8(text))
            if not text.endswith("\n"):
                if not skip_newline:
                    f.write("\n")
    except (IOError, ValueError):
        debug.trace_fmtd(1, "Error: Problem writing file '{f}': {exc}",
                         f=filename, exc=get_exception())
    return


def write_binary_file(filename, data):
    """Create FILENAME with binary DATA"""
    debug.trace_fmt(7, "write_binary_file({f}, _)", f=filename)
    try:
        with open(filename, "wb") as f:
            f.write(data)
    except (IOError, ValueError):
        debug.trace_fmtd(1, "Error: Problem writing file '{f}': {exc}",
                         f=filename, exc=get_exception())
    return


def write_lines(filename, text_lines, append=False):
    """Creates FILENAME using TEXT_LINES with newlines added and optionally for APPEND"""
    debug.trace_fmt(5, "write_lines({f}, _, {a})", f=filename, a=append)
    debug.trace_fmt(6, "    text_lines={tl}", tl=text_lines)
    f = None
    try:
        mode = 'a' if append else 'w'
        ## OLD f = open(filename, mode)
        with open(filename, mode) as f:
            for line in text_lines:
                line = to_utf8(line)
                f.write(line + "\n")
    except IOError:
        debug.trace_fmt(2, "Warning: Exception writing file {f}: {e}",
                        f=filename, e=get_exception())
    finally:
        if f:
            f.close()
    return


def write_temp_file(filename, text):
    """Create FILENAME in temp. directory using TEXT"""
    temp_path = form_path(TEMP_DIR, filename)
    return write_file(temp_path, text)


def get_file_modification_time(filename, as_float=False):
    """Get the time the FILENAME was last modified, optional AS_FLOAT (instead of default string).
    Note: Returns None if file doesn't exist."""
    # TODO: document how the floating point version is interpretted
    # See https://stackoverflow.com/questions/237079/how-to-get-file-creation-modification-date-times-in-python
    mod_time = None
    if file_exists(filename):
        mod_time = os.path.getmtime(filename)
        if not as_float:
            mod_time = str(datetime.datetime.fromtimestamp(mod_time))
    debug.trace_fmtd(5, "get_file_modification_time({f}) => {t}", f=filename, t=mod_time)
    return mod_time


def remove_extension(filename, extension=None):
    """Return FILENAME without final EXTENSION
    Note: Unless extension specified, only last dot is included"""
    # EX: remove_extension("/tmp/document.pdf") => "/tmp/document")
    # EX: remove_extension("it.abc.def") => "it.abc")
    # EX: remove_extension("it.abc.def", "abc.def") => "it")
    in_extension = extension
    if extension is None:
        new_filename = re.sub(r"\.[^\.]*$", "", filename)
    else:
        if not extension.startswith("."):
            extension = "." + extension
        if filename.endswith(extension):
            new_filename = filename[0: -len(extension)]
    debug.trace_fmtd(5, "remove_extension({f}, [{ex}]) => {r}",
                     f=filename, ex=in_extension, r=new_filename)
    return new_filename


def file_exists(filename):
    """Returns True iff FILENAME exists"""
    does_exist = os.path.exists(filename)
    debug.trace_fmtd(5, "file_exists({f}) => {r}", f=filename, r=does_exist)
    return does_exist


def get_file_size(filename):
    """Returns size of FILENAME or -1 if not found"""
    size = -1
    if file_exists(filename):
        size = os.path.getsize(filename)
    debug.trace_fmtd(5, "get_file_size({f}) => {s}", f=filename, s=size)
    return size


def form_path(*filenames):
    """Wrapper around os.path.join over FILENAMEs (with tracing)"""
    path = os.path.join(*filenames)
    debug.trace_fmt(6, "form_path({f}) => {p}", f=tuple(filenames), p=path)
    return path


def is_directory(path):
    """Determines whether PATH represents a directory"""
    # EX: is_directory("/etc")
    is_dir = os.path.isdir(path)
    debug.trace_fmt(6, "is_dir({p} => {r}", p=path, r=is_dir)
    return is_dir


def is_regular_file(path):
    """Determines whether PATH represents a directory"""
    # EX: (not is_regular_file("/etc"))
    ok = os.path.isfile(path)
    debug.trace_fmt(6, "is_regular_file({p}) => {r}", p=path, r=ok)
    return ok


def create_directory(path):
    """Wrapper around os.mkdir over PATH (with tracing)"""
    # Note: doesn't create intermediate directories (see glue_helper.py)
    # TODO: pass along keyword parameters (e.g., mode)
    debug.trace_fmt(7, "create_directory({p})", p=path)
    if not os.path.exists(path):
        os.mkdir(path)
        debug.trace_fmt(6, "os.mkdir({p})", p=path)
    else:
        debug.assertion(os.path.isdir(path))
    return


def get_current_directory():
    """Tracing wrapper around os.getcwd"""
    current_dir = os.getcwd()
    debug.trace_fmt(6, "get_current_directory() => {r}", r=current_dir)
    return current_dir


def set_current_directory(PATH):
    """Tracing wrapper around os.chdir(PATH)"""
    result = os.chdir(PATH)
    debug.trace_fmt(6, "set_current_directory({p}) => {r}", r=result)
    return result


def to_utf8(text):
    """obsolete no-op: Convert TEXT to UTF-8 (e.g., for I/O)"""
    # EX: to_utf8(u"\ufeff") => "\xEF\xBB\xBF"
    result = text
    if ((sys.version_info.major < 3) and (isinstance(text, unicode))):   # pylint: disable=undefined-variable
        result = result.encode(UTF8, 'ignore')
    debug.trace_fmtd(8, "to_utf8({t}) => {r}", t=text, r=result)
    return result


def to_str(value):
    """Convert VALUE to text (i.e., of type str)
    Note: use to_utf8 for output or to_string to use default string type"""
    # Note: included for sake of completeness with other basic types
    # EX: to_str(math.pi) = "3.141592653589793"
    result = "%s" % value
    debug.trace_fmtd(8, "to_str({v}) => {r}", v=value, r=result)
    debug.assertion(isinstance(result, str))
    return result


def from_utf8(text):
    """Convert TEXT to Unicode from UTF-8"""
    # EX: to_utf8("\xEF\xBB\xBF") => u"\ufeff"
    result = text
    if ((sys.version_info.major < 3) and (not isinstance(result, unicode))):     # pylint: disable=undefined-variable
        result = result.decode(UTF8, 'ignore')
    debug.trace_fmtd(8, "from_utf8({t}) => {r}", t=text, r=result)
    return result


def to_unicode(text, encoding=None):
    """Ensure TEXT in ENCODING is Unicode, such as from the default UTF8"""
    # EX: to_unicode("\xEF\xBB\xBF") => u"\ufeff"
    # TODO: rework from_utf8 in terms of this
    result = text
    if ((sys.version_info.major < 3) and (not isinstance(result, unicode))):     # pylint: disable=undefined-variable
        if not encoding:
            encoding = UTF8
        result = result.decode(encoding, 'ignore')
    debug.trace_fmtd(8, "to_unicode({t}, [{e}]) => {r}", t=text, e=encoding, r=result)
    return result


def from_unicode(text, encoding=None):
    """Convert TEXT to ENCODING from Unicode, such as to the default UTF8"""
    # TODO: rework to_utf8 in terms of this
    result = text
    if ((sys.version_info.major < 3) and (isinstance(text, unicode))):    # pylint: disable=undefined-variable
        if not encoding:
            encoding = UTF8
        result = result.encode(encoding, 'ignore')
    debug.trace_fmtd(8, "from_unicode({t}, [{e}]) => {r}", t=text, e=encoding, r=result)
    return result


def to_string(text):
    ## OLD: """Ensure TEXT is a string type
    """Ensure VALUE is a string type
    Note: under Python 2, result is str or Unicode; but for Python 3+, it is always str"""
    # EX: to_string(123) => "123"
    # EX: to_string(u"\u1234") => u"\u1234"
    # EX: to_string(None) => "None"
    # Notes: Uses string formatting operator % for proper Unicode handling.
    # Gotta hate Python: doubly stupid changes from version 2 to 3 required special case handling: Unicode type dropped and bytes not automatically treated as string!
    result = text
    if isinstance(result, bytes):
        result = result.decode(UTF8)
    if (not isinstance(result, STRING_TYPES)):
        result = "%s" % text
    debug.trace_fmtd(8, "to_string({t}) => {r}", t=text, r=result)
    return result
#
to_text = to_string

def chomp(text, line_separator=os.linesep):
    """Removes trailing occurrence of LINE_SEPARATOR from TEXT"""
    # EX: chomp("abc\n") => "abc"
    # EX: chomp("http://localhost/", "/") => "http://localhost"
    result = text
    if result.endswith(line_separator):
        new_len = len(result) - len(line_separator)
        result = result[:new_len]
    debug.trace_fmt(8, "chomp({t}, {sep}) => {r}", 
                    t=text, sep=line_separator, r=result)
    return result


def non_empty_file(filename):
    """Whether file exists and is non-empty"""
    non_empty = (file_exists(filename) and (os.path.getsize(filename) > 0))
    debug.trace_fmtd(5, "non_empty_file({f}) => {r}", f=filename, r=non_empty)
    return non_empty


def absolute_path(path):
    """Return resolved absolute pathname for PATH, as with Linux realpath command w/ --no-symlinks"""
    # EX: absolute_path("/etc/mtab").startswith("/etc")
    result = os.path.abspath(path)
    debug.trace(7, f"real_path({path}) => {result}")
    return result


def real_path(path):
    """Return resolved absolute pathname for PATH, as with Linux realpath command"""
    # EX: real_path("/etc/mtab").startswith("/proc")
    result = os.path.realpath(path)
    debug.trace(7, f"real_path({path}) => {result}")
    return result


def get_module_version(module_name):
    """Get version number for MODULE_NAME (string)"""
    # note: used in bash function (alias):
    #     python-module-version() = { python -c "print(get_module_version('$1))"; }'

    # Try to load the module with given name
    # TODO: eliminate eval and just import directly
    try:
        eval("import {m}".format(m=module_name))             # pylint: disable=eval-used
    except:
        debug.trace_fmtd(6, "Exception importing module '{m}': {exc}",
                         m=module_name, exc=get_exception())
        return "-1.-1.-1"

    # Try to get the version number for the module
    # TODO: eliminate eval and use getattr()
    # TODO: try other conventions besides module.__version__ member variable
    version = "?.?.?"
    try:
        version = eval("module_name.__version__")            # pylint: disable=eval-used
    except:
        debug.trace_fmtd(6, "Exception evaluating '{m}.__version__': {exc}",
                         m=module_name, exc=get_exception())
        ## TODO: version = "0.0.0"
    return version


def intersection(list1, list2):
    """Return intersection of LIST1 and LIST2"""
    # note: wrapper around set.intersection used for tracing
    # EX: intersection([1, 2, 3, 4, 5], [2, 4]) => {1, 3, 5}
    # TODO: have option for returning list
    result = set(list1).intersection(set(list2))
    debug.trace_fmtd(7, "intersection({l1}, {l2}) => {r}",
                     l1=list1, l2=list2, r=result)
    return result


def union(list1, list2):
    """Return union of LIST1 and LIST2"""
    # note: wrapper around set.union used for tracing
    result = set(list1).union(set(list2))
    debug.trace_fmtd(7, "union({l1}, {l2}) => {r}",
                     l1=list1, l2=list2, r=result)
    return result


def difference(list1, list2):
    """Return set difference from LIST1 vs LIST2, preserving order"""
    # TODO: optmize (e.g., via a hash table)
    # EX: difference([5, 4, 3, 2, 1], [1, 2, 3]) => [5, 4]
    # TODO: add option for returning set
    diff = []
    for item1 in list1:
        if item1 not in list2:
            diff.append(item1)
    debug.trace_fmtd(7, "difference({l1}, {l2}) => {d}",
                     l1=list1, l2=list2, d=diff)
    return diff


def append_new(in_list, item):
    """Returns copy of LIST with ITEM included unless already in it"""
    # ex: append_new([1, 2], 3]) => [1, 2, 3]
    # ex: append_new([1, 2, 3], 3]) => [1, 2, 3]
    result = in_list[:]
    if item not in result:
        result.append(item)
    debug.trace_fmt(7, "append_new({l}, {i}) => {r}",
                    l=in_list, i=item, r=result)
    return result


def just_one_true(in_list, strict=False):
    """True iff only one element of IN_LIST is considered True (or all None unless STRICT)"""
    # Note: Consider using misc_utils.just1 (based on more_itertools.exactly_n)
    # TODO: Trap exceptions (e.g., string input)
    min_count = 1 if strict else 0
    ## OLD: is_true = (1 == sum([int(bool(b)) for b in in_list]))         # pylint: disable=misplaced-comparison-constant
    is_true = (min_count <= sum([int(bool(b)) for b in in_list]) <= 1)    # pylint: disable=misplaced-comparison-constant
    debug.trace_fmt(6, "just_one_true({l}) => {r}", l=in_list, r=is_true)
    return is_true


def just_one_non_null(in_list, strict=False):
    """True iff only one element of IN_LIST is not None (or all None unless STRICT)"""
    min_count = 1 if strict else 0
    is_true = (min_count <= sum([int(x is not None) for x in in_list]) <= 1)    # pylint: disable=misplaced-comparison-constant
    debug.trace_fmt(6, "just_one_non_null({l}) => {r}", l=in_list, r=is_true)
    return is_true


def unique_items(in_list, prune_empty=False):
    """Returns unique items from IN_LIST, preserving order and optionally PRUN[ing]_EMPTY items"""
    # EX: unique_items([1, 2, 3, 2, 1]) => [1, 2, 3]
    ordered_hash = OrderedDict()
    for item in in_list:
        if item or (not prune_empty):
            ordered_hash[item] = True
    result = list(ordered_hash.keys())
    debug.trace_fmt(8, "unique_items({l}) => {r}", l=in_list, r=result)
    return result


def to_float(text, default_value=0.0):
    """Interpret TEXT as float, using DEFAULT_VALUE"""
    result = default_value
    try:
        result = float(text)
    except (TypeError, ValueError):
        debug.trace_fmtd(6, "Exception in to_float: {exc}", exc=get_exception())
    debug.trace_fmtd(8, "to_float({v}) => {r}", v=text, r=result)
    return result
#
safe_float = to_float


## OLD: def to_int(text, default_value=0):
def to_int(text, default_value=0, base=None):
    ## OLD: """Interpret TEXT as integer, using DEFAULT_VALUE"""
    """Interpret TEXT as integer with optional DEFAULT_VALUE and BASE"""
    # TODO: use generic to_num with argument specifying type
    result = default_value
    try:
        ## OLD: result = int(text)
        result = int(text, base) if (base and isinstance(text, str)) else int(text)
    except (TypeError, ValueError):
        debug.trace_fmtd(6, "Exception in to_int: {exc}", exc=get_exception())
    debug.trace_fmtd(8, "to_int({v}) => {r}", v=text, r=result)
    return result
#
safe_int = to_int


def to_bool(value):
    """Converts VALUE to boolean value, returning False iff in {0, False, None, "False", "None", "Off", and ""}, ignoring case.
    Note: ensures the result is of type bool.""" 
    # EX: to_bool("off") => False
    result = value
    if isinstance(value, str):
        result = (value.lower() not in ["false", "none", "off", "0", ""])
    if not isinstance(result, bool):
        result = bool(result)
    debug.trace_fmtd(7, "to_bool({v}) => {r}", v=value, r=result)
    return result
#
# EX: to_bool(None) => False
# EX: to_bool(333) => True
# EX: to_bool("") => False


PRECISION = getenv_int("PRECISION", 6,
                       "Precision for rounding (e.g., decimal places)")
#
def round_num(value, precision=None):
    """Round VALUE [to PRECISION places, {p} by default]""".format(p=PRECISION)
    # EX: round_num(3.15914, 3) => 3.159
    if precision is None:
        precision = PRECISION
    rounded_value = round(value, precision)
    debug.trace_fmtd(8, "round_num({v}, [prec={p}]) => {r}",
                     v=value, p=precision, r=rounded_value)
    return rounded_value


def round_as_str(value, precision=PRECISION):
    """Returns round_num(VALUE, PRECISION) as string"""
    # EX: round_as_str(3.15914, 3) => "3.159"
    result = f"{round_num(value, precision):.{precision}f}"
    debug.trace_fmtd(8, "round_as_str({v}, [prec={p}]) => {r}",
                     v=value, p=precision, r=result)
    return result


def sleep(num_seconds, trace_level=5):
    """Sleep for NUM_SECONDS"""
    # TODO: annotate num_seconds with float
    debug.trace_fmtd(trace_level, "sleep({ns}, [tl={tl}])",
                     ns=num_seconds, tl=trace_level)
    time.sleep(num_seconds)
    return


def current_time(integral=False):
    """Return current time in seconds since 1970, optionally INTEGRAL"""
    secs = time.time()
    if integral:
        secs = int(round_num(secs, precision=0))
    debug.trace(5, f"current_time([integral={integral}]) => {secs}")
    return secs

def time_in_secs():
    """Wrapper around current_time"""
    return current_time(integral=True)

def python_maj_min_version():
    """Return Python version as a float of form Major.Minor"""
    # EX: debug.assertion(python_maj_min_version() >= 3.6, "F-Strings are used")
    version = sys.version_info
    py_maj_min = to_float("{M}.{m}".format(M=version.major, m=version.minor))
    debug.trace_fmt(5, "Python version (maj.min): {v}", v=py_maj_min)
    debug.assertion(py_maj_min > 0)
    return py_maj_min


def get_args():
    """Return command-line arguments (as a list of strings)"""
    result = sys.argv
    debug.trace_fmtd(7, "get_args() => {r}", r=result)
    return result

def init():
    """Performs module initilization"""
    # TODO: rework global initialization to avoid the need for this
    global TEMP_DIR
    TEMP_DIR = getenv_text("TMPDIR", "/tmp")

    ## TODO: # Register DEBUG_LEVEL for sake of new users
    ## test_debug_level = getenv_integer("DEBUG_LEVEL", debug.get_level(), 
    ##                                   "Debugging level for script tracing")
    ## debug.assertion(debug.get_level() == test_debug_level)

    return
#
init()

#-------------------------------------------------------------------------------
# Command line usage

def main(args):
    """Supporting code for command-line processing"""
    debug.trace_fmtd(6, "main({a})", a=args)
    user = getenv_text("USER")
    print_stderr("Warning, {u}: Not intended for direct invocation".format(u=user))
    debug.trace_fmt(4, "FYI: maximum integer is {maxi}", maxi=maxint())
    return

if __name__ == '__main__':
    main(get_args())
else:
    debug.assertion(TEMP_DIR is not None)
