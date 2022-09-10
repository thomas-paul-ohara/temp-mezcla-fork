#! /usr/bin/env python
#
# Tests for tfidf/preprocess module
#

"""Tests for tfidf/preprocess module"""

# Standard modules
## NOTE: this is empty for now

# Installed modules
import pytest

# Local modules
from mezcla import debug

# Note: Rreference are used for the module to be tested:
#    THE_MODULE:	    global module object
import mezcla.tfidf.preprocess as THE_MODULE


## TODO: TESTS WORK-IN-PROGRESS


if __name__ == '__main__':
    debug.trace_current_context()
    pytest.main([__file__])
