#! /usr/bin/env python
#
# Utility functions for writing glue scripts, such as implementing functionality
# available in Unix scripting (e.g., basename command).
#
# NOTE:
# - *** This module is being phased out with important functionality being moved elsewhere.
# - Some of the utilities are specific to Unix (e.g., full_mkdir and real_path). In
#   contrast, system.py attempts to be more cross platform.
#
# TODO:
# - Add more functions to facilitate command-line scripting (check bash scripts for commonly used features).
# - Add functions to facilitate functional programming (e.g., to simply debugging traces).
#

"""Helpers gluing scripts together"""

# Standard packages
from collections import defaultdict
import glob
import inspect
import os
import re
import shutil
from subprocess import getoutput
import sys
import tempfile

# Installed packages
import textwrap

# Local packages
from mezcla import debug
from mezcla import tpo_common as tpo
from mezcla.tpo_common import debug_format, debug_print, print_stderr, setenv

# note: ALLOW_SUBCOMMAND_TRACING should be interepreted in terms of detailed
# tracing. Now, basic tracing is still done unless disable_subcommand_tracing()
# invoked. (This way, subscript start/end time shown by default)
ALLOW_SUBCOMMAND_TRACING = tpo.getenv_boolean("ALLOW_SUBCOMMAND_TRACING", False)
default_subtrace_level = min(tpo.USUAL, tpo.debugging_level())
if ALLOW_SUBCOMMAND_TRACING:
    default_subtrace_level = tpo.debugging_level()

INDENT = "    "                          # default indentation

#------------------------------------------------------------------------

def get_temp_file(delete=None):
    """Return name of unique temporary file, optionally with DELETE"""
    # Note: delete defaults to False if detailed debugging
    # TODO: allow for overriding other options to NamedTemporaryFile
    if ((delete is None) and tpo.detailed_debugging()):
        delete = False
    temp_file_name = tempfile.NamedTemporaryFile(delete=delete).name
    # HACK: get rid of double backslashes in Win32 filenames
    # ex: r'c:\\temp\\fubar' => r'c:\temp\fubar' 
    ## if os.pathsep == r'\\':
    ##     double_pathspec = os.pathsep + os.pathsep
    ##     temp_file_name = temp_file_name.replace(double_pathspec, os.pathsep)
    debug_format("get_temp_file() => {r}", 5, r=temp_file_name)
    return temp_file_name
#
TEMP_LOG_FILE = tpo.getenv_text(
    # "Log file for stderr (e.g., for issue function)"
    "TEMP_LOG_FILE", get_temp_file())


def basename(filename, extension=None):
    """Remove directory from FILENAME along with optional EXTENSION, as with Unix basename command. Note: the period in the extension must be explicitly supplied (e.g., '.data' not 'data')"""
    # EX: basename("fubar.py", ".py") => "fubar"
    # EX: basename("fubar.py", "py") => "fubar."
    # EX: basename("/tmp/solr-4888.log", ".log") => "solr-4888"
    base = os.path.basename(filename)
    ## OLD: if extension != None:
    ## BAD: if extension is None:
    if extension is not None:
        pos = base.find(extension)
        if pos > -1:
            base = base[:pos]
    debug_print("basename(%s, %s) => %s" % (filename, extension, base), 5)
    return base


def remove_extension(filename, extension):
    """Returns FILENAME without EXTENSION. Note: similar to basename() but retaining directory portion."""
    # EX: remove_extension("/tmp/solr-4888.log", ".log") => "/tmp/solr-4888"
    # EX: remove_extension("/tmp/fubar.py", ".py") => "/tmp/fubar"
    # EX: remove_extension("/tmp/fubar.py", "py") => "/tmp/fubar."
    # NOTE: Unlike os.path.splitext, only the specific extension is removed (not whichever extension used).
    pos = filename.find(extension)
    base = filename[:pos] if (pos > -1) else filename
    debug_print("remove_extension(%s, %s) => %s" % (filename, extension, base), 5)
    return base


## TODO: def replace_extension(filename, old_extension, old_extension):
##           ...


def dir_path(filename):
    """Wrapper around os.path.dirname"""
    # TODO: return . for filename without directory (not "")
    # EX: dirname("/tmp/solr-4888.log") => "/tmp"
    path = os.path.dirname(filename)
    debug.trace(5, f"dirname({filename}) => {path}")
    # TODO: add realpath (i.e., canonical path)
    debug.assertion(form_path(path, basename(filename)) == filename)
    return path


def file_exists(filename):
    """Returns indication that FILENAME exists"""
    ok = os.path.exists(filename)
    debug_print("file_exists(%s) => %s" % (filename, ok), 7)
    return ok


def non_empty_file(filename):
    """Whether FILENAME exists and is non-empty"""
    size = (os.path.getsize(filename) if os.path.exists(filename) else -1)
    non_empty = (size > 0)
    debug_print("non_empty_file(%s) => %s (filesize=%s)" % (filename, non_empty, size), 5)
    return non_empty


def resolve_path(filename, base_dir=None):
    """Resolves path for FILENAME relative to BASE_DIR if not in current directory. Note: this uses the script directory for the calling module if BASE_DIR not specified (i.e., as if os.path.dirname(__file__) passed)."""
    # TODO: give preference to script directory over current directory
    path = filename
    if not os.path.exists(path):
        if not base_dir:
            frame = None
            try:
                frame = inspect.currentframe().f_back
                base_dir = os.path.dirname(frame.f_globals['__file__'])
            except (AttributeError, KeyError):
                base_dir = ""
                debug_print("Exception during resolve_path: " + str(sys.exc_info()), 5)
            finally:
                if frame:
                    del frame
        path = os.path.join(base_dir, path)
    debug_format("resolve_path({f}) => {p}", 4, f=filename, p=path)
    return path


def form_path(*filenames):
    """Wrapper around os.path.join over FILENAMEs (with tracing)"""
    path = os.path.join(*filenames)
    debug_format("form_path{f} => {p}", 6, f=tuple(filenames), p=path)
    return path


def is_directory(path):
    """Determins wther PATH represents a directory"""
    is_dir = os.path.isdir(path)
    debug_format("is_dir{p} => {r}", 6, p=path, r=is_dir)
    return is_dir


def create_directory(path):
    """Wrapper around os.mkdir over PATH (with tracing)"""
    ## Note: obsolete use version in system.py instead
    if not os.path.exists(path):
        os.mkdir(path)
        debug_format("os.mkdir({p})", 6, p=path)
    else:
        assertion(os.path.isdir(path))
    return


def full_mkdir(path):
    """Issues mkdir to ensure path directory, including parents (assuming Linux like shell)"""
    debug.assertion(os.name == "posix")
    issue('mkdir --parents "{p}"', p=path)
    debug.assertion(is_directory(path))
    return


def real_path(path):
    """Return resolved absolute pathname for PATH, as with Linux realpath command"""
    # EX: re.search("vmlinuz.*\d.\d", real_path("/vmlinuz"))
    result = run(f'realpath "{path}"')
    debug.trace(7, f"real_path({path}) => {result}")
    return result


def indent(text, indentation=INDENT, max_width=512):
    """Indent TEXT with INDENTATION at beginning of each line, returning string ending in a newline unless empty and with resulting lines longer than max_width characters wrapped. Text is treated as a single paragraph."""
    # Note: an empty text is returned without trailing newline
    tw = textwrap.TextWrapper(width=max_width, initial_indent=indentation, subsequent_indent=indentation)
    wrapped_text = "\n".join(tw.wrap(text))
    if wrapped_text:
        wrapped_text += "\n"
    return wrapped_text


def indent_lines(text, indentation=INDENT, max_width=512):
    """Like indent, except that each line is indented separately. That is, the text is not treated as a single paragraph."""
    # Sample usage: print("log contents: {{\n{log}\n}}".format(log=indent_lines(lines)))
    # TODO: add support to simplify above idiom (e.g., indent_lines_bracketed); rename to avoid possible confusion that input is array (as wih write_lines)
    result = ""
    for line in text.split("\n"):
        indented_line = indent(line, indentation, max_width)
        if not indented_line:
            indented_line = "\n"
        result += indented_line
    return result


MAX_ELIDED_TEXT_LEN = tpo.getenv_integer("MAX_ELIDED_TEXT_LEN", 128)
#
def elide(text: str, max_len=None):
    """Returns TEXT elided to at most MAX_LEN characters (with '...' used to indicate remainder). Note: intended for tracing long string."""
    # EX: elide("=" * 80, max_len=8) => "=====..."
    # TODO: add support for eliding at word-boundaries
    tpo.debug_print("elide(_, _)", 7)
    debug.assertion(isinstance(text, str))
    if max_len is None:
        max_len = MAX_ELIDED_TEXT_LEN
    result = text
    if len(result) > max_len:
        result = result[:max_len] + "..."
    tpo.debug_print("elide({%s}, [{%s}]) => {%s}" % (text, max_len, result), 8)
    return result


def elide_values(values: list, **kwargs):
    """List version of elide [q.v.]"""
    # EX: elide_values(["1", "22", "333"], max_len=2) => ["1", "22", "33..."]
    tpo.debug_print("elide_values(_, _)", 7)
    return list(map(lambda v: elide(str(v), **kwargs),
                    values))


def disable_subcommand_tracing():
    """Disables tracing in scripts invoked via run().""" 
    # Note this works by having run() temporarily setting DEBUG_LEVEL to 0."""
    global default_subtrace_level
    default_subtrace_level = 0


def run(command, trace_level=4, subtrace_level=None, just_issue=False, **namespace):
    """Invokes COMMAND via system shell, using TRACE_LEVEL for debugging output, returning result. The command can use format-style templates, resolved from caller's namespace. The optional SUBTRACE_LEVEL sets tracing for invoked commands (default is same as TRACE_LEVEL); this works around problem with stderr not being separated, which can be a problem when tracing unit tests.
   Notes:
   - The result includes stderr, so direct if not desired:
         gh.run("ls /tmp/fubar 2> /dev/null")
   - This is only intended for running simple commands. It would be better to create a subprocess for any complex interactions.
   - This function doesn't work fully under Win32. Tabs are not preserved, so redirect stdout to a file if needed.
   """
    # TODO: add automatic log file support as in run_script from unittest_wrapper.py
    # TODO: make sure no template markers left in command text (e.g., "tar cvfz {tar_file}")
    # EX: "root" in run("ls /")
    # Note: Script tracing controlled DEBUG_LEVEL environment variable.
    assertion(isinstance(trace_level, int))
    debug_print("run(%s, [trace_level=%s], [subtrace_level=%s])" % (command, trace_level, subtrace_level), (trace_level + 2))
    global default_subtrace_level
    # Keep track of current debug level setting
    debug_level_env = None
    if subtrace_level is None:
        subtrace_level = default_subtrace_level
    if subtrace_level != trace_level:
        debug_level_env = os.getenv("DEBUG_LEVEL")
        setenv("DEBUG_LEVEL", str(subtrace_level))
    # Expand the command template
    # TODO: make this optional
    command_line = command
    if re.search("{.*}", command):
        command_line = tpo.format(command_line, indirect_caller=True, ignore_exception=False, **namespace)
    debug_print("issuing: %s" % command_line, trace_level)
    # Run the command
    # TODO: check for errors (e.g., "sh: filter_file.py: not found"); make wait explicit
    wait = not command.endswith("&")
    assertion(wait or not just_issue)
    # Note: Unix supports the '>|' pipe operator (i.e., output with overwrite); but,
    # it is not supported under Windows. To avoid unexpected porting issues, clients
    # should replace 'run("... >| f")' usages with 'delete_file(f); run(...)'.
    assertion(">|" not in command_line)
    result = None
    ## TODO: if (just_issue or not wait): ... else: ...
    result = getoutput(command_line) if wait else str(os.system(command_line))
    # Restore debug level setting in environment
    if debug_level_env:
        setenv("DEBUG_LEVEL", debug_level_env)
    debug_print("run(_) => {\n%s\n}" % indent_lines(result), (trace_level + 1))
    return result


def issue(command, trace_level=4, subtrace_level=None, **namespace):
    """Wrapper around run() for when output is not being saved (i.e., just issues command). 
    Note:
    - Nothing is returned.
    - Traces stdout when debugging at quite-detailed level (6).
    - Captures stderr unless redirected and traces at error level (1)."""
    # EX: issue("ls /") => None
    # EX: issue("xeyes &")
    debug_print("issue(%s, [trace_level=%s], [subtrace_level=%s], [ns=%s])"
                % (command, trace_level, subtrace_level, namespace), (trace_level + 1))
    # Add stderr redirect to temporary log file, unless redirection already present
    log_file = None
    if tpo.debugging() and (not "2>" in command) and (not "2|&1" in command):
        ## TODO: use a different suffix each time to aid in debugging
        log_file = TEMP_LOG_FILE
        delete_existing_file(log_file)
        command += " 2> " + log_file
    # Run the command and trace output
    command_line = command
    if re.search("{.*}", command_line):
        command_line = tpo.format(command_line, indirect_caller=True, ignore_exception=False, **namespace)
    output = run(command_line, trace_level, subtrace_level, just_issue=True)
    tpo.debug_print("stdout from command: {\n%s\n}\n" % indent(output), (2 + trace_level))
    # Trace out any standard error output and remove temporary log file (unless debugging)
    if log_file:
        if tpo.debugging() and non_empty_file(log_file):
            stderr_output = indent(read_file(log_file))
            tpo.debug_print("stderr output from command: {\n%s\n}\n" % indent(stderr_output))
        if not tpo.detailed_debugging():
            delete_file(log_file)
    return


def get_hex_dump(text, break_newlines=False):
    """Get hex dump for TEXT, optionally BREAKing lines on NEWLINES"""
    # TODO: implement entirely within Pyton (e.g., via binascii.hexlify)
    # EX: get_hex_dump
    debug.trace_fmt(6, "get_hex_dump{{t}, {bn})", t=text, bn=break_newlines)
    in_file = get_temp_file() + ".in.list"
    out_file = get_temp_file() + ".out.list"
    write_file(in_file, text)
    run("perl -Ss hexview.perl -newlines {i} > {o}", i=in_file, o=out_file)
    result = read_file(out_file)    
    return result


def extract_matches(pattern, lines, fields=1, multiple=False, re_flags=0, para_mode=False):
    """Checks for PATTERN matches in LINES of text returning list of tuples with replacement groups.
    Notes: The number of FIELDS can be greater than 1.
    Optionally allows for MULTIPLE matches within a line.
    The lines are concatenated if DOTALL
    Matching optionally uses perl-style PARA_MODE
    """
    ## TODO: If unspecified, the regex flags default to DOTALL.
    # ex: extract_matches(r"^(\S+) \S+", ["John D.", "Jane D.", "Plato"]) => ["John", "Jane"]
    # Note: modelled after extract_matches.perl
    # TODO: make multiple the default
    debug_print("extract_matches(%s, _, [fld=%s], [m=%s], [flg=%s], [para=%s])" % (pattern, fields, multiple, re_flags, para_mode), 6)
    ## TODO
    ## if re_flags is None:
    ##     re_flags = re.DOTALL
    debug.trace_values(6, lines, "lines")
    ## assert type(lines) == list
    assert isinstance(lines, list)
    if pattern.find("(") == -1:
        pattern = "(" + pattern + ")"
    if (re_flags and (re_flags & re.DOTALL)):
        lines = [ "\n".join(lines) + "\n" ]
        debug.trace_expr(6, lines)
    if para_mode:
        lines = re.split(r"\n\s*\n", ("\n".join(lines)))
    matches = []
    for i, line in enumerate(lines):
        while line:
            debug.trace(6, f"L{i}: {line}")
            try:
                # Extract match field(s)
                debug.trace_expr(7, pattern, line, re_flags, fields)
                match = re.search(pattern, line, flags=re_flags)
                if not match:
                    break
                result = match.group(1) if (fields == 1) else [match.group(i + 1) for i in range(fields)]
                matches.append(result)
                if not multiple:
                    break

                # Revise line
                debug.assertion(match.end() > 0)
                new_line = line[match.end():]
                if (new_line == line):
                    break
                line = new_line
            except (re.error, IndexError):
                debug_print("Warning: Exception in pattern matching: %s" % str(sys.exc_info()), 2)
                line = None
    debug_print("extract_matches() => %s" % (matches), 7)
    double_indent = INDENT + INDENT
    debug_format("{ind}input lines: {{\n{res}\n{ind}}}", 8,
                 ind=INDENT, res=indent_lines("\n".join(lines), double_indent))
    return matches


def extract_match(pattern, lines, fields=1, multiple=False, re_flags=0, para_mode=None):
    """Extracts first match of PATTERN in LINES for FIELDS"""
    matches = extract_matches(pattern, lines, fields, multiple, re_flags, para_mode)
    result = (matches[0] if matches else None)
    debug_print("match: %s" % result, 5)
    return result


def extract_match_from_text(pattern, text, fields=1, multiple=False, re_flags=0, para_mode=None):
    """Wrapper around extract_match for text input"""
    ## TODO: rework to allow for multiple-line matching
    return extract_match(pattern, text.split("\n"), fields, multiple, re_flags, para_mode)


def extract_matches_from_text(pattern, text, fields=1, multiple=None, re_flags=0, para_mode=None):
    """Wrapper around extract_matches for text input
    Note: By default MULTIPLE matches are returned"""
    # EX: extract_matches_from_text(".", "abc") => ["a", "b", "c"]
    # EX: extract_matches_from_text(".", "abc", multiple=False) => ["a"]
    if multiple is None:
        multiple = True
    # TODO: make multiple True by default
    return extract_matches(pattern, text.split("\n"), fields, multiple, re_flags, para_mode)


def count_it(pattern, text, field=1, multiple=None):
    """Counts how often PATTERN's FIELD occurs in TEXT, returning hash.
    Note: By default MULTIPLE matches are tabulated"""
    # EX: dict(count_it("[a-z]", "Panama")) => {"a": 3, "n": 1, "m": 1"}
    # EX: count_it("\w+", "My d@wg's fleas have fleas")["fleas"] => 2
    debug.trace(7, f"count_it({pattern}, _, {field}, {multiple}")
    value_counts = defaultdict(int)
    for value in extract_matches_from_text(pattern, text, field, multiple):
        value_counts[value] += 1
    debug.trace_values(6, value_counts, "count_it()")
    return value_counts


def read_lines(filename=None, make_unicode=False):
    """Returns list of lines from FILENAME without newlines (or other extra whitespace)
    @notes: Uses stdin if filename is None. Optionally returned as unicode."""
    # TODO: use enumerate(f); refine exception in except; 
    # TODO: force unicode if UTF8 encountered
    lines = []
    f = None
    try:
        # Open the file
        if not filename:
            tpo.debug_format("Reading from stdin", 4)
            f = sys.stdin
        else:
            f = open(filename)
            if not f:
                raise IOError
        # Read line by line
        for line in f:
            line = line.strip("\n")
            if make_unicode:
                line = tpo.ensure_unicode(line)
            lines.append(line)
    except IOError:
        debug_print("Warning: Exception reading file %s: %s" % (filename, str(sys.exc_info())), 2)
    finally:
        if f:
            f.close()
    debug_print("read_lines(%s) => %s" % (filename, lines), 6)
    return lines


def write_lines(filename, text_lines, append=False):
    """Creates FILENAME using TEXT_LINES with newlines added and optionally for APPEND"""
    debug_print("write_lines(%s, _)" % (filename), 5)
    debug_print("    text_lines=%s" % text_lines, 6)
    debug.assertion(isinstance(text_lines, list) and all(isinstance(x, str) for x in text_lines))
    f = None
    try:
        mode = 'a' if append else 'w'
        f = open(filename, mode)
        for line in text_lines:
            line = tpo.normalize_unicode(line)
            f.write(line + "\n")
    except IOError:
        debug_print("Warning: Exception writing file %s: %s" % (filename, str(sys.exc_info())), 2)
    finally:
        if f:
            f.close()
    return


def read_file(filename, make_unicode=False):
    """Returns text from FILENAME (single string), including newline(s).
    Note: optionally returned as unicde."""
    debug_print("read_file(%s)" % filename, 7)
    text = "\n".join(read_lines(filename, make_unicode=make_unicode))
    return (text + "\n") if text else ""


def write_file(filename, text, append=False):
    """Writes FILENAME using contents in TEXT, adding trailing newline and optionally for APPEND"""
    ## TEST: debug_print(u"write_file(%s, %s)" % (filename, text), 7)
    ## TEST: debug_print(u"write_file(%s, %s)" % (filename, tpo.normalize_unicode(text)), 7)
    debug_print("write_file(%s, %s)" % (tpo.normalize_unicode(filename), tpo.normalize_unicode(text)), 7)
    text_lines = text.rstrip("\n").split("\n")
    return write_lines(filename, text_lines, append)


def copy_file(source, target):
    """Copy SOURCE file to TARGET file"""
    # Note: meta data is not copied (e.g., access control lists)); see
    #    https://docs.python.org/2/library/shutil.html
    # TODO: have option to skip if non-dir target exists
    debug_print("copy_file(%s, %s)" % (tpo.normalize_unicode(source), tpo.normalize_unicode(target)), 5)
    assertion(non_empty_file(source))
    shutil.copy(source, target)
    assertion(non_empty_file(target))
    return


def rename_file(source, target):
    """Rename SOURCE file as TARGET file"""
    # TODO: have option to skip if target exists
    debug_print("rename_file(%s, %s)" % (tpo.normalize_unicode(source), tpo.normalize_unicode(target)), 5)
    assertion(non_empty_file(source))
    os.rename(source, target)
    assertion(non_empty_file(target))
    return


def delete_file(filename):
    """Deletes FILENAME"""
    debug_print("delete_file(%s)" % tpo.normalize_unicode(filename), 5)
    assertion(os.path.exists(filename))
    ok = False
    try:
        ok = os.remove(filename)
        debug_format("remove{f} => {r}", 6, f=filename, r=ok)
    except OSError:
        debug_print("Exception during deletion of {filename}: " + str(sys.exc_info()), 5)
    return ok


def delete_existing_file(filename):
    """Deletes FILENAME if it exists and is not a directory or other special file"""
    ok = False
    if file_exists(filename):
        ok = delete_file(filename)
    tpo.debug_format("delete_existing_file({f}) => {r}", 5, f=filename, r=ok)
    return ok


def file_size(filename):
    """Returns size of FILENAME in bytes (or -1 if not found)"""
    size = -1
    if os.path.exists(filename):
        size = os.path.getsize(filename)
    tpo.debug_format("file_size({f}) => {s}", 5, f=filename, s=size)
    return size


def get_matching_files(pattern):
    """Get list of files matching PATTERN via shell globbing"""
    # NOTE: Multiple glob specs not allowed in PATTERN
    # TODO: See whether the result should be sorted lexicographically
    files = glob.glob(pattern)
    tpo.debug_format("get_matching_files({p}) => {l}", 5,
                     p=pattern, l=files)
    return files


def get_files_matching_specs(patterns):
    """Get list of files matching PATTERNS via shell globbing"""
    files = []
    for spec in patterns:
        files += get_matching_files(spec)
    tpo.debug_format("get_files_matching_specs({p}) => {l}", 6,
                     p=patterns, l=files)
    return files


def get_directory_listing(dirname, make_unicode=False):
    """Returns files in DIRNAME"""
    all_file_names = []
    try:
        all_file_names = os.listdir(dirname)
    except OSError:
        tpo.debug_format("Exception during get_directory_listing: {exc}", 4,
                         exc=str(sys.exc_info()))
    if make_unicode:
        all_file_names = [tpo.ensure_unicode(f) for f in all_file_names]
    tpo.debug_format("get_directory_listing({dir}) => {files}", 5,
                     dir=dirname, files=all_file_names)
    return all_file_names

#-------------------------------------------------------------------------------
# Extensions to tpo_common included here due to inclusion of functions 
# defined here.

def getenv_filename(var, default="", description=None):
    """Returns text filename based on environment variable VAR (or string version of DEFAULT) 
    with optional DESCRIPTION. This includes a sanity check for file being non-empty."""
    debug_format("getenv_filename({v}, {d}, {desc})", 6,
                 v=var, d=default, desc=description)
    filename = tpo.getenv_text(var, default, description)
    if filename and not non_empty_file(filename):
        tpo.print_stderr("Error: filename %s empty or missing for environment option %s" % (filename, var))
    return filename


if __debug__:

    def assertion(condition):
        """Issues warning if CONDITION doesn't hold"""
        # EX: assertion(2 + 2 != 5)
        # TODO: rename as soft_assertion???; add to tpo_common.py (along with run???)
        if not condition:
            # Try to get file and line number from stack frame
            # note: not available during interactive use
            filename = None
            line_num = -1
            frame = None
            try:
                frame = inspect.currentframe().f_back
                tpo.debug_trace("frame=%s", frame, level=8)
                tpo.trace_object(frame, 9, "frame")
                filename = frame.f_globals.get("__file__")
                if filename and filename.endswith(".pyc"):
                    filename = filename[:-1]
                line_num = frame.f_lineno
            finally:
                if frame:
                    del frame
            
            # Get text for line and extract the condition from invocation,
            # ignoring comments and function name.
            # TODO: define function for extracting line, so this can be put in tpo_common.py
            line = "???"
            if filename:
                line = run("tail --lines=+{l} '{f}' | head -1", 
                           subtrace_level=8, f=filename, l=line_num)
            condition = re.sub(r"^\s*\S*assertion\((.*)\)\s*(\#.*)?$", 
                               "\\1", line)
    
            # Print the assertion warning
            line_spec = "???"
            if filename:
                line_spec = "{f}:{l}".format(f=filename, l=line_num)
            debug_format("*** Warning: assertion failed: ({c}) at {ls}", 
                         tpo.WARNING, c=condition, ls=line_spec)
        return

else:

    def assertion(_condition):
        """Non-debug stub for assertion"""
        return

#------------------------------------------------------------------------

# Warn if invoked standalone
#
if __name__ == '__main__':
    print_stderr("Warning: %s is not intended to be run standalone" % __file__)
