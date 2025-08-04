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

    def _display_results(self, result, expected_result):
        print("\nresults:")
        print(result)
        print("\nexpected result:")
        print(expected_result)
        print("")

    ###############################################
    '''
    Tests cases where difficult paths are imported.
    '''
    ###############################################
    dataset_line_formatter_import = [
        { 'row': {'pid': 0, 'ppid': 0, 'gid':0, 'username': '0', 'name': '0', 'cmdline': ["t", "-space"]}, 
         'result': "t -space" },
        { 'row': {'pid': 0, 'ppid': 0, 'gid':0, 'username': '0', 'name': '0', 'cmdline': ["t", "'quotes'", f'"dbl_quotes"']}, 
         'result': f"t 'quotes' \"dbl_quotes\""},
    ]

    @pytest.mark.parametrize('dataset_line_formatter_import', dataset_line_formatter_import)
    def test_line_formatter_import(self, fixture_psdiff, dataset_line_formatter_import):
        #arrange
        line_formatter_import = fixture_psdiff._Psdiff__line_formatter_import
        row = dataset_line_formatter_import['row']
        expected_result = dataset_line_formatter_import['result']
        
        #act
        result = line_formatter_import(row)['cmdline']
        
        #arrange
        print("results:")
        print(result)
        print("expected result:")
        print(expected_result) 
        assert (result == expected_result), f"\nGenerated result:\n {result}\n did not match expected result:\n{expected_result}"
        pass


    ###############################################
    '''
    Test
    '''
    ###############################################
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
        #pattern of form # # # "string" "string" "string"
        pattern = r'^\d+\s+\d+\s+\d+\s+"[^"]*"\s+"[^"]*"\s+"[^"]*"$'
        assert (re.fullmatch(pattern, first_line)), f"\nOutput string:\n {first_line}\n did not match form of pattern: # # # \"str\" \"str\" \"str\""
        pass


    ###############################################
    '''
    Tests that a diff between 2 snapshots yields expected result.
    '''
    ###############################################
    dataset_compare_snapshots_1 = {
            'proc_set1': [
                {'pid': 1, 'ppid': 1, 'gid':1, 'username': 'root', 'name': 'static row', 'cmdline': ["bin", "-c"]},
                {'pid': 2, 'ppid': 2, 'gid':2, 'username': 'root', 'name': "'change row minus'", 'cmdline': ["cmd", "1"]},
            ],
            'proc_set2': [
                {'pid': 1, 'ppid': 1, 'gid':1, 'username': 'root', 'name': 'static row', 'cmdline': ["bin", "-c"]},
                {'pid': 2, 'ppid': 2, 'gid':2, 'username': 'root', 'name': "'change row plus'", 'cmdline': ["cmd", "\"2\""]},
                {'pid': 3, 'ppid': 3, 'gid':3, 'username': 'user', 'name': "'added row'", 'cmdline': [""]}
            ],
            'result': f"- 1 1 1 root 'change row minus' cmd 1\n" + 
                        "+ 2 2 2 root 'changing row plus' cmd \"2\"\n" +
                        "+ 3 3 3 user added row test"
    }
    dataset_compare_snapshots_2 = {
            'proc_set1': [{'pid': 1, 'ppid': 1, 'gid':1, 'username': 'root', 'name': 'a', 'cmdline': ["bin"]}],
            'proc_set2': [{'pid': 1, 'ppid': 1, 'gid':1, 'username': 'root', 'name': 'a', 'cmdline': ["bin"]}],
            'result': "No differences found."
    }


        
    @pytest.mark.parametrize('dataset_compare_snapshots', [ dataset_compare_snapshots_1, dataset_compare_snapshots_2 ])
    # --- Compare snapshot Test ---
    def test_compare_snapshots(self, mocker, fixture_psdiff, dataset_compare_snapshots):
        '''
        TODO: Implement this
        '''
        #arrange
        
        def _build_process_iter(dataset):
            list = []
            for dict in dataset:
                row = mocker.MagicMock()
                row.info = dict
                list.append(row)
            return list
        
        psdiff = fixture_psdiff
        set1 = _build_process_iter(dataset_compare_snapshots['proc_set1'])
        set2 = _build_process_iter(dataset_compare_snapshots['proc_set2'])
        expected_result = dataset_compare_snapshots['result']
        
        #act
        mocker.patch("psutil.process_iter", return_value=set1)
        psdiff.create_snapshot(50)
        mocker.patch("psutil.process_iter", return_value=set2)
        
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            psdiff.print_diff()
        
        #assert
        def remove_whitespace(string): return re.sub(r'\s+', ' ', string.strip())
        result = stream.getvalue()
        self._display_results(remove_whitespace(result),remove_whitespace(expected_result))  
        #assert (remove_whitespace(result) == remove_whitespace(expected_result)), "Output strings did not match."
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
        proc_row = [{'pid': 0, 'ppid': 0, 'gid':0, 'username': 'root', 'name': 'two part', 'cmdline': ""},
                    {'pid': 1, 'ppid': 1, 'gid':1, 'username': 'root', 'name': "'quotes'", 'cmdline': f"nginx: 'off;'"},
                    {'pid': 2, 'ppid': 2, 'gid':2, 'username': 'root', 'name': '"even more quotes"', 'cmdline': f'more "quotes"'},
                    ]
        mocker.patch.object(Psdiff, "_Psdiff__get_ps", return_value=proc_row) 
        psdiff = fixture_psdiff
        
        #Act
        stream1 = io.StringIO()
        with contextlib.redirect_stdout(stream1):
            psdiff.print_snapshot()
        
        psdiff.create_snapshot(100)
        stream2 = io.StringIO()
        with contextlib.redirect_stdout(stream2):
            psdiff.print_snapshot(100)

        output1 = stream1.getvalue()
        output2 = stream2.getvalue()
        print("live:" + output1)
        print("saved:" + output2)
        #assert
        assert (output1 == output2), f"Results from calling live ps:\n{output1} differ from results of saved ps:\n{output2}."
        pass

