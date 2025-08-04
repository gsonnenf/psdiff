import contextlib
import inspect
import io
import re
import pytest
import shutil
from pathlib import Path
from psdiff import Psdiff
from tests.aspect_helper import weave_aspect

@weave_aspect
class TestPsDiff:

    # --- Create snapshot Test ---
    @pytest.fixture
    def fixture_psdiff(self):
        base_path = Path(__file__).resolve().parent
        directory = "tmp"
        path = base_path / directory
        if path.exists(): shutil.rmtree(path)
        psdiff_instance = Psdiff( base_path,directory, 'ps_test' ) 
        return psdiff_instance

    def test_create_snapshot(self, fixture_psdiff):
        '''
        Test that create_snapshot writes a snapshot file and the first line matches expected string
        '''
        psdiff = fixture_psdiff
        #Act
        psdiff.create_snapshot()

        #Assert
        expected_file = psdiff.snapshot_dir / 'ps_test.0'
        assert expected_file.exists(), f"snapshot file {expected_file} does not exist"
        with expected_file.open('r') as f: first_line = f.readline().strip()  
        #pattern of form # # string 'string' 'string'
        pattern = r"^\d+\s+\d+\s+\d+\s+\w+\s+'[^']*'\s+'[^']*'$"
        assert (re.fullmatch(pattern, first_line)), f"\nOutput string: {first_line}\n did not match form of pattern: # # str 'str' 'str'"
        pass


    ###############################################
    '''
    Tests that a diff between 2 snapshots yields expected result.
    '''
    ###############################################
    dataset_compare_snapshots_1 = {
            'proc_row1': [
                {'pid': 1, 'ppid': 2, 'gid':3, 'username': 'root', 'name': 'non-changing row', 'cmdline': ["bin", "-c"]},
                {'pid': 10, 'ppid': 20, 'gid':30, 'username': 'root', 'name': "'changing row'", 'cmdline': ["cmd", "-1"]},
            ],
            'proc_row2': [
                {'pid': 1, 'ppid': 2, 'gid':3, 'username': 'root', 'name': 'non-changing row', 'cmdline': ["bin", "-c"]},
                {'pid': 10, 'ppid': 20, 'gid':30, 'username': 'root', 'name': "'changing row 2'", 'cmdline': ["cmd", "-2"]},
                {'pid': 10000, 'ppid': 0, 'gid':10, 'username': 'user', 'name': "'new row'", 'cmdline': ["test"]}
            ],
            'result': f"- 10 20 30 root changing row cmd -1\n" + 
                        "+ 10 20 30 root changing row 2 cmd -2\n" +
                        "+ 10000 0 10 user new row test"
    }
    dataset_compare_snapshots_2 = {
            'proc_row1': [{'pid': 1, 'ppid': 2, 'gid':1, 'username': 'root', 'name': 'a', 'cmdline': ["bin"]}],
            'proc_row2': [{'pid': 1, 'ppid': 2, 'gid':1, 'username': 'root', 'name': 'a', 'cmdline': ["bin"]}],
            'result': "No differences found."
    }
        
    @pytest.mark.parametrize('dataset_compare_snapshots', [ dataset_compare_snapshots_1, dataset_compare_snapshots_2 ])
    # --- Compare snapshot Test ---
    def test_compare_snapshots(self, mocker, fixture_psdiff, dataset_compare_snapshots):
        '''
        TODO: Implement this
        '''
        #arrange
        psdiff = fixture_psdiff
        input1 = dataset_compare_snapshots['proc_row1']
        input2 = dataset_compare_snapshots['proc_row2']
        expected_result = dataset_compare_snapshots['result']
        
        #act
        mocker.patch.object(Psdiff, "_Psdiff__get_ps", return_value=input1)
        psdiff.create_snapshot()
        mocker.patch.object(Psdiff, "_Psdiff__get_ps", return_value=input2)
        
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            psdiff.print_diff()
        
        #assert
        def remove_whitespace(string): return re.sub(r'\s+', ' ', string.strip())
        result = stream.getvalue()
        print(remove_whitespace(result))
        print(remove_whitespace(expected_result))
        assert (remove_whitespace(output1) == remove_whitespace(expected_result)), "Output strings did not match."
        pass
 
    ########################################
    '''
    TEST:
    Tests a Live snapshot against a saved snapshot to ensures they are same. Ensures string lists, quotes and spaces are 
    parsed,saved, and loaded correctly.
    '''
    ###########################################
    def test_live_vs_saved_snapshot_and_formatting(self, mocker, fixture_psdiff):
        #arrange
        proc_row = [{'pid': 640, 'ppid': 2, 'gid':1000, 'username': 'root', 'name': 'mt76 phy0', 'cmdline': ["bin", "-c"]},
                    {'pid': 641, 'ppid': 2, 'gid':1000, 'username': 'root', 'name': "'process'", 'cmdline': ["hello"]},
                    ]
        mocker.patch.object(Psdiff, "_Psdiff__get_ps", return_value=proc_row)
        psdiff = fixture_psdiff
        
        #Act
        stream1 = io.StringIO()
        with contextlib.redirect_stdout(stream1):
            psdiff.print_snapshot()
        
        psdiff.create_snapshot(1)
        stream2 = io.StringIO()
        with contextlib.redirect_stdout(stream2):
            psdiff.print_snapshot(1)

        output1 = stream1.getvalue()
        output2 = stream2.getvalue()
        print(output1)
        print(output2)
        #assert
        assert (output1 == output2), f"Results from calling live ps:\n{output1} differ from results of saved ps{output2}."
        pass

