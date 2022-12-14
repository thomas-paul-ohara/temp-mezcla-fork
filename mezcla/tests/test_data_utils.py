#! /usr/bin/env python
#
# Test(s) for ../data_utils.py
#
# Notes:
# - For debugging the tested script, the ALLOW_SUBCOMMAND_TRACING environment
#   option shows tracing output normally suppressed by  unittest_wrapper.py.
# - This can be run as follows:
#   $ PYTHONPATH=".:$PYTHONPATH" python ./mezcla/tests/test_data_utils.py
#

"""Tests for data_utils module"""

# Standard packages
import os

# Installed packages
import pytest

# Local packages
from mezcla import glue_helpers as gh
from mezcla import debug

# Note: Two references are used for the module to be tested:
#    THE_MODULE:	    global module object
import mezcla.data_utils as THE_MODULE

class TestDataUtils:
    """Class for testcase definition"""

    path = os.path.dirname(os.path.realpath(__file__))

    def test_read_csv(self):
        """Ensure read_csv works as expected"""
        debug.trace(4, "test_read_csv()")
        tf = THE_MODULE.read_csv(f"{self.path}/../examples/iris.csv")
        assert tf.shape == (150, 5)

    def test_to_csv(self):
        """Ensure to_csv works as expected"""
        debug.trace(4, "test_to_csv()")

        # Setup
        temp_file = gh.get_temp_file()
        tf = THE_MODULE.read_csv(f"{self.path}/../examples/iris.csv")
        THE_MODULE.to_csv(temp_file, tf)

        # Test to_csv
        expected = (
            'sepal_length,sepal_width,petal_length,petal_width,class'
        )
        assert expected in gh.read_file(temp_file)

    def test_lookup_df_value(self):
        """Ensure lookup_df_value works as expected"""
        debug.trace(4, "test_lookup_df_value()")
        tf = THE_MODULE.read_csv(f"{self.path}/../examples/iris.csv")
        assert THE_MODULE.lookup_df_value(tf, "sepal_length", "petal_length", "3.8") == "5.5" 

    def test_main(self, capsys):
        """Ensure main works as expected"""
        debug.trace(4, "main()")
        THE_MODULE.main()
        captured = capsys.readouterr()
        assert "Error" in captured.err


if __name__ == '__main__':
    debug.trace_current_context()
    pytest.main([__file__])
