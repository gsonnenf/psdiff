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

    # --- Create Checkpoint Test ---
    @pytest.fixture
    def fixture_psdiff(self):
        base_path = Path(__file__).resolve().parent
        directory = "tmp"
        path = base_path / directory
        if path.exists(): shutil.rmtree(path)
        psdiff_instance = Psdiff( base_path,directory, 'ps_test' ) 
        return psdiff_instance

    def test_create_checkpoint(self, fixture_psdiff):
        '''
        Test that create_checkpoint writes a snapshot file and the first line matches expected string
        '''
        psdiff = fixture_psdiff
        #Act
        psdiff.create_checkpoint()

        #Assert
        expected_file = psdiff.checkpoint_dir / 'ps_test.0'
        assert expected_file.exists(), f"Checkpoint file {expected_file} does not exist"
        with expected_file.open('r') as f: first_line = f.readline().strip()  
        #pattern of form # # string 'string' 'string'
        pattern = r"^\d+\s+\d+\s+\d+\s+\w+\s+'[^']*'\s+'[^']*'$"
        assert (re.fullmatch(pattern, first_line)), f"\nOutput string: {first_line}\n did not match form of pattern: # # str 'str' 'str'"
        pass

    # --- Compare Checkpoint Test ---
    def test_compare_checkpoints(self, fixture_psdiff):
        '''
        TODO: Implement this
        '''
        psdiff = fixture_psdiff
        psdiff.create_checkpoint()
        #psdiff.compare_checkpoint()
        pass
 
    def test_live_ps_vs_saved_ps_and_ensure_proper_quotes_around_spaces(self, mocker, fixture_psdiff):
        '''
        Ensures that a saved ps snapshot will be the same as live ps snapshot with strings quoted and parsed correctly.
        Some strings are returned from ps util as a list of pieces, ensures they are reassambled.
        '''
        #arrange
        proc_row = [{'pid': 640, 'ppid': 2, 'gid':1000, 'username': 'root', 'name': 'mt76 phy0', 'cmdline': ["bin", "-c"]},
                    {'pid': 641, 'ppid': 2, 'gid':1000, 'username': 'root', 'name': "'process'", 'cmdline': ["hello"]},
                    ]
        mocker.patch.object(Psdiff, "_Psdiff__get_ps", return_value=proc_row)
        psdiff = fixture_psdiff
        
        #Act
        stream1 = io.StringIO()
        with contextlib.redirect_stdout(stream1):
            psdiff.print_checkpoint()
        
        psdiff.create_checkpoint(1)
        stream2 = io.StringIO()
        with contextlib.redirect_stdout(stream2):
            psdiff.print_checkpoint(1)

        output1 = stream1.getvalue()
        output2 = stream2.getvalue()

        #assert
        assert (output1 == output2), f"Results from calling live ps:\n{output1} differ from results of saved ps{output2}."
        pass
