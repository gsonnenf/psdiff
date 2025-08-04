import pytest
import sys
from cmdline import main
from tests.aspect_helper import weave_aspect

@weave_aspect
class TestCmdline:

    def test_cmdline_print(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["cmdline.py", "-p", "1" ])
        main()

    def test_cmdline_diff(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["cmdline.py", "-s", "0" ])
        main()
        monkeypatch.setattr(sys, "argv", ["cmdline.py", "-c", "0" ])
        main()
