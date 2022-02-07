#! /usr/bin/env python
#
# Test(s) for ../file_utils.py
#


"""Tests for file_utils module"""


# Standard packages
import unittest
import re


# Local packages
from mezcla.unittest_wrapper import TestWrapper
from mezcla import debug
from mezcla import glue_helpers as gh


# Note: Two references are used for the module to be tested:
#    THE_MODULE:	    global module object
#    TestIt.script_module   string name
import mezcla.file_utils as file_utils


class TestIt(TestWrapper):
    """Class for testcase definition"""
    script_module = TestWrapper.derive_tested_module_name(__file__)
    # TODO: use_temp_base_dir = True            # treat TEMP_BASE as directory
    # note: temp_file defined by parent (along with script_module, temp_base, and test_num)


    ## TODO: optional setup methods
    ##
    ## @classmethod
    ## def setUpClass(cls):
    ##     """One-time initialization (i.e., for entire class)"""
    ##     debug.trace(6, f"TestIt.setUpClass(); cls={cls}")
    ##     # note: should do parent processing first
    ##     super().setUpClass()
    ##     ...
    ##     return
    ##
    ## def setUp(self):
    ##     """Per-test setup"""
    ##     debug.trace(6, f"TestIt.setUp(); self={self}")
    ##     # note: must do parent processing first (e.g., for temp file support)
    ##     super().setUp()
    ##     ...
    ##     return


    def test_get_directory_listing(self):
        """
        Tests for get_directory_listing(path          = 'PATH',
                                        recursive     = False,
                                        long          = False,
                                        readable_size = False,
                                        return_string = True,
                                        make_unicode  = False)
        """

        # Setup files and folders
        test_folder = gh.run('echo test-dir-listing-"$$"')
        folders     = [test_folder, f'{test_folder}/other_folder']
        filenames   = ['analize.py', 'debug.cpp', 'main.txt', 'misc_utils.perl']

        for foldername in folders:
            gh.run(f'mkdir /tmp/{foldername}')
            for filename in filenames:
                gh.run(f'touch /tmp/{foldername}/{filename}')

        # Run Test
        list_result = file_utils.get_directory_listing(f'/tmp/{test_folder}', recursive=True, long=True, return_string=True)

        for line in list_result:
            self.assertTrue(bool(re.search(r"[\w-]+\s+\d+\s+\w+\s+\w+\s+\d+\s+\w+\s+\d+\s+\d\d:\d\d\s+[\w/]+", line)))


    def test_get_information(self):
        """Tests for def get_information(path,
                                         readable = False,
                                         return_string = False)
        """
        test_file = '/tmp/gi_test.cpp'
        gh.run(f'touch {test_file}')

        ls_result = gh.run(f'ls -l {test_file}')

        self.assertEqual(file_utils.get_information(test_file, return_string=True), ls_result)


    def test_get_permissions(self):
        """Tests for get_permissions(path)"""

        # Setup
        test_dir  = gh.run('echo /tmp/test-permissions-$$')
        test_file = test_dir + '/' + 'some-file.cpp'

        gh.run(f'mkdir {test_dir} && touch {test_file}')

        # Run
        self.assertEqual(file_utils.get_permissions(test_file), gh.run(f'ls -l {test_file}')[:10])
        self.assertEqual(file_utils.get_permissions(test_dir), gh.run(f'ls -ld {test_dir}')[:10])


    def test_get_modification_date(self):
        """Tests for get_modification_date(path)"""
        test_file = '/tmp/gm_test.cpp'
        gh.run(f'touch {test_file}')

        ls_date = gh.run(f'ls -l {test_file}')[39:51]
        ls_date = re.sub(r'\s+', ' ', ls_date)

        self.assertEqual(file_utils.get_modification_date(test_file, strftime='%b %-d %H:%M'), ls_date)


    ## TODO: optional cleanup methods
    ##
    ## def tearDown(self):
    ##     debug.trace(6, f"TestIt.tearDown(); self={self}")
    ##     super(TestIt, cls).tearDownClass()
    ##     ...
    ##     return
    ##
    ## @classmethod
    ## def tearDownClass(cls):
    ##     debug.trace(6, f"TestIt.tearDownClass(); cls={cls}")
    ##     super(TestIt, self).tearDown()
    ##     ...
    ##     return

#------------------------------------------------------------------------

if __name__ == '__main__':
    debug.trace_current_context()
    unittest.main()
