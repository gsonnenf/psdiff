#!/usr/bin/env python3
import json
import logging
import os
import sys
import argparse
import psutil
from pathlib import Path
import shlex
from collections import OrderedDict
from urllib.parse import quote, unquote

import urllib

def DEBUG(string):
    print(string)


class Psdiff():
    def __init__(self, 
                 script_dir: Path, 
                 snapshot_dir_name: str =".psdiff", 
                 snapshot_prefix: str = "ps", 
                 max_bytes: int = 10*1024*1024):   
            
        self.script_dir = script_dir if script_dir is not None else Path(__file__).resolve().parent
        self.snapshot_dir = self.script_dir / snapshot_dir_name
        self.snapshot_prefix = snapshot_prefix
        self.max_bytes = max_bytes  # 10MB default. Generates a warning if snapshot dir exceeds this size.
        if not self.snapshot_dir.exists(): self.snapshot_dir.mkdir()
       
    # --- Public methods ---
    def create_snapshot(self, num=None):
        '''Create a new snapshot of the current process list.'''
        outfile = self.__create_snapshot_path(num) 
        self.__write_snapshot_to_file(self.__create_ps_snapshot(), outfile)
        print(f"snapshot created: {outfile}")
        return outfile
    
    def print_snapshot(self, num=None):
        '''Prints a snapshot that was saved or the current snapshot'''       
        ps_list = self.__create_ps_snapshot() if (num is None) else self.__load_saved_snapshot(num)
        print("\n")
        for proc in ps_list: print( self.__line_formatter_display(proc) )

    def print_diff(self, num1 = None, num2 = None):
        list1 = self.__load_saved_snapshot(num1) 
        list2 = self.__load_saved_snapshot(num2) if (num2 != None) else self.__create_ps_snapshot()

        (diff1,diff2) = self.__get_diff(list1, list2)
        if not diff1 and not diff2: 
            print ("No differences found.")
        else:
            for proc in diff1: print( "-" + self.__line_formatter_display(proc) )
            for proc in diff2: print( "+" + self.__line_formatter_display(proc) )


    def delete_snapshots(self):
        '''
        Deletes all the snapshots out of the snapshot directory
        '''
        for file in self.snapshot_dir.glob(f"{self.snapshot_prefix}.*"):
            if file.is_file(): file.unlink()

     # --- Internal Method -> Print diff ---
    def __get_diff(self, lista, listb):
        '''
        Find symmetric difference between two lists of dicts by converting dicts to tuples of sorted items.
        '''
        def _dict_to_tuple(d): return tuple((k, tuple(v) if isinstance(v, list) else v) for k, v in d.items())
        #def _dict_to_tuple(d): return tuple(sorted((k, tuple(v) if isinstance(v, list) else v) for k, v in d.items()))
        def _tuple_to_dict(t): return {k: list(v) if isinstance(v, tuple) else v for k, v in t}
        
        #region body
        set_a = set(_dict_to_tuple(d) for d in lista)
        set_b = set(_dict_to_tuple(d) for d in listb)

        only_in_a_tuples = set_a - set_b
        only_in_b_tuples = set_b - set_a
            
        only_in_a = sorted( (_tuple_to_dict(t) for t in only_in_a_tuples), key=lambda d: d['pid'])
        only_in_b = sorted((_tuple_to_dict(t) for t in only_in_b_tuples), key=lambda d: d['pid'] )

        return (only_in_a, only_in_b)

    # --- Internal methods -> snapshot generation ---
    def __create_ps_snapshot(self):
        '''
        Get a snapshot of current processes, filtering out kworker and the current process itself.
        :return: List of dicts with keys: pid, ppid, username, name, cmdline.
        '''       
        # Body
        self.__maintenance_check()
        ps_list = self.__get_ps()
        ps_list = self.__snapshot_filter(ps_list)
        ps_list.sort(key=lambda x: x["pid"])
        return ps_list
    
    def __get_ps(self):
        ps_list = []
        for proc in psutil.process_iter(['pid', 'ppid', 'username', 'name', 'cmdline']):
            try:
                proc.info['gid'] = 0
                #proc.info['gid'] = psutil.Process(proc.info.get('pid')).gids()                    
                ps_list.append(self.__line_formatter_import(proc.info)) 
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess): continue
        return ps_list

     # --- Internal methods -> File I/O ---
    def __load_saved_snapshot(self,num=None):
        '''Get the formatted process list object from a snapshot.'''
        if (num is None): num = self.__get_last_snapshot_number()
        if (num < 0):
            print("There are no saved snapshots.")
            sys.exit(1)
        path = Path(self.__get_snapshot_path(num))
        if not path.exists():
            print(f"snapshot {num} does not exist: {path}", file=sys.stderr)
            sys.exit(1)
        return self.__read_snapshot_from_file(path)
    
    
    def __read_snapshot_from_file(self,input_file):
        '''Read a process snapshot from a file and return a list of process.'''
        ps_list = []  
        with open(input_file, 'r') as file:
            for line in file:
                try:
                    ps_list.append(self.__line_formatter_read_file(line))        
                except Exception as e: 
                    print (f"Error in snapshot file: {e}" )
                    continue               
        ps_list.sort(key=lambda x: x["pid"])
        return ps_list

    def __write_snapshot_to_file(self, ps_list, output_file):
        '''Write the process list to a file in a readable format.'''
        with open(output_file, 'w') as f:
            for proc in ps_list:
                f.write(self.__line_formatter_write_file(proc) + "\n")
        return output_file

    
   
    # --- Internal method -> snapshot management --- 
    def __create_snapshot_path(self,num = None):
        num = num if num is not None else (self.__get_last_snapshot_number() + 1)
        if (num < 0): 
            print("File number must not be negative")
            sys.exit(1)
        path = self.snapshot_dir / f"{self.snapshot_prefix}.{num}"
        return path

    def __get_snapshot_path(self,num):
        path = self.snapshot_dir / f"{self.snapshot_prefix}.{num}"
        if not path.exists():
            print(f"snapshot {num} does not exist: {path}", file=sys.stderr)
            sys.exit(1)
        return path

    def __get_last_snapshot_number(self):
        '''Calculate the next snapshot number by finding the highest existing snapshot number.'''
        last = -1
        for file in Path(self.snapshot_dir).glob(f"{self.snapshot_prefix}.*"):
            try:
                num = int(file.name.split('.')[-1])
                last = max(last, num)
            except ValueError:
                continue
        return last
    
     
    # --- Internal methods -> Text Rendering ---  
    def __line_formatter_import(self, proc_info):
        '''Formats a string based process dictionary from the proc.info format'''
        def _reformat_string_list(param): return ' '.join(param) if isinstance(param,list) else param
        
        return {
                'pid': proc_info.get('pid', -1),
                'ppid':  proc_info.get('ppid', -1),
                'gid': proc_info.get('gid').real,
                'username':  _reformat_string_list(proc_info.get('username','')),
                'name':_reformat_string_list(proc_info.get('name','')),
                'cmdline':_reformat_string_list(proc_info.get('cmdline',''))
            }

    def __line_formatter_display(self, ps_dict ):
        '''Render a single line of ps output for display.'''
        pid = ps_dict['pid']
        ppid = ps_dict['ppid']
        gid = ps_dict['gid']
        username = ps_dict['username']
        name = ps_dict['name']
        cmdline = ps_dict['cmdline']

        if (username == ""): username = "''"
        if (name == ""): name = "''"
        if (cmdline == ""): cmdline = "''"

        return f"{pid:>6} {ppid:>6} {gid:>6} {username:<8} {name:<24} {cmdline}"
    

    def __line_formatter_read_file(self, ps_line):
        '''Parses a single line of ps from a file input'''
        parts = shlex.split(ps_line)
        return { 
            'pid':int(parts[0]),
            'ppid':int(parts[1]),
            'gid':int(parts[2]),
            'username': parts[3],
            'name': parts[4],     
            'cmdline': parts[5] 
        }
    
    def __line_formatter_write_file(self, ps_dict): #urllib.parse
        '''Render a single line of ps output for file output.'''
        pid = ps_dict['pid']
        ppid = ps_dict['ppid']
        gid = ps_dict['gid']
        username = json.dumps(ps_dict['username'])
        name = json.dumps(ps_dict['name'])
        cmdline = json.dumps(ps_dict['cmdline'])
        '''Render a single line of ps output for display.'''
              
        return (f"{pid:>6} {ppid:>6} {gid:>6} {username:<8} {name:<24} {cmdline}")
    

     # --- Internal methods -> Helpers ---  
     #make abstract in the future
    def __snapshot_filter(self, ps_list):
        '''Filter out kworker and the current running process itself.'''
        current_pid = os.getpid()
        return [
            proc for proc in ps_list
            if not (
                (proc['name'].startswith('kworker/') and proc['username'] == 'root') or
                proc['pid'] == current_pid
            )
        ]     
    
    
    def __maintenance_check(self):
        '''Check the size of the snapshot directory and warn if it exceeds MAX_BYTES.'''
        size_bytes = sum(f.stat().st_size for f in self.snapshot_dir.glob('*') if f.is_file())
        if size_bytes > self.max_bytes:
            print("Warning: snapshot directory size exceeds 10MB. Consider cleaning up old snapshots.", file=sys.stderr)

