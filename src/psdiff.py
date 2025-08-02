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

def DEBUG(string):
    print(string)


class Psdiff():
    def __init__(self, 
                 script_dir: Path, 
                 checkpoint_dir_name: str =".psdiff", 
                 checkpoint_prefix: str = "ps", 
                 max_bytes: int = 10*1024*1024):   
            
        self.script_dir = script_dir if script_dir is not None else Path(__file__).resolve().parent
        self.checkpoint_dir = self.script_dir / checkpoint_dir_name
        self.checkpoint_prefix = checkpoint_prefix
        self.max_bytes = max_bytes  # 10MB default. Generates a warning if checkpoint dir exceeds this size.
        if not self.checkpoint_dir.exists(): self.checkpoint_dir.mkdir()
       
    # --- Public methods ---
    def create_checkpoint(self, num=None):
        '''Create a new checkpoint of the current process list.'''
        outfile = self.__create_checkpoint_path(num) 
        self.__write_ps_snapshot(self.__create_ps_snapshot(), outfile)
        #TODO: add ass debug print(f"Checkpoint created: {outfile}")
        return outfile

    def compare_checkpoint(self, num=None):
        '''Compare the current process list with a saved checkpoint.'''
        if (num is None): num = self.__get_last_checkpoint_number()
        path = Path(self.__get_checkpoint_path(num))
        if not path.exists():
            print(f"Checkpoint {num} does not exist: {path}", file=sys.stderr)
            sys.exit(1)
        self.__print_ps_diff(self.__read_ps_snapshot(path), self.__create_ps_snapshot())

    def print_checkpoint(self, num=None):
        '''Prints a checkpoint that was saved or the current checkpoint'''
        ps_list = self.__create_ps_snapshot() if (num is None) else self.__get_checkpoint(num)
        print("\n")
        for proc in ps_list: print( self.__line_formatter(proc, -1) )

    # --- Internal methods -> snapshot ---
    def __create_ps_snapshot(self):
        '''
        Get a snapshot of current processes, filtering out kworker and the current process itself.
        :return: List of dicts with keys: pid, ppid, username, name, cmdline.
        '''       
        # Body
        self.__maintenance_check()
        ps_list = self.__get_ps()
        ps_list = self.__snapshot_filter(ps_list)
        for process in ps_list:
            self.__snapshot_stringlist_to_string(process, 'name')
            self.__snapshot_stringlist_to_string(process, 'cmdline')
        ps_list = sorted(ps_list, key=lambda x: x["pid"] ) 
        return ps_list

    def __read_ps_snapshot(self,input_file):
        '''Read a process snapshot from a file and return a list of process.'''
        process_list = []
        with open(input_file, 'r') as file:
            for line in file:
                try:
                    # Split into 5 parts: pid, ppid, username, name (quoted), cmdline (quoted)
                    parts = shlex.split(line)
                    if len(parts) < 6:
                        continue
                    pid = int(parts[0])
                    ppid = int(parts[1])
                    gid = int(parts[2])
                    username = parts[3]
                    name = parts[4]        # strip quotes
                    cmdline = parts[5]  # strip quotes
                    
                    process_list.append({
                        'pid': pid,
                        'ppid': ppid,
                        'gid': gid,
                        'username': username or '""',
                        'name': name or '""',
                        'cmdline': cmdline or '""'
                    })
        
                except Exception: continue
        
        process_list = sorted(process_list, key=lambda x: x["pid"] )           
        return process_list

    def __write_ps_snapshot(self, process_list, output_file):
        '''Write the process list to a file in a readable format.'''
        with open(output_file, 'w') as f:
            for proc in process_list:
                f.write(self.__line_formatter(proc,1))
        return output_file

    def __get_checkpoint(self,num=None):
        '''Get the formatted process list object from a checkpoint.'''
        if (num is None): num = self.__get_last_checkpoint_number()
        path = Path(self.__get_checkpoint_path(num))
        if not path.exists():
            print(f"Checkpoint {num} does not exist: {path}", file=sys.stderr)
            sys.exit(1)
        return self.__read_ps_snapshot(path)

    def __get_ps(self):
        ps_list = []
        for proc in psutil.process_iter(['pid', 'ppid', 'username', 'name', 'cmdline']):
            try:                    
                ps_list.append({
                    'pid': proc.info.get('pid'),
                    'ppid': proc.info.get('ppid'),
                    'gid': psutil.Process(proc.info.get('pid')).gids().real,
                    'username': proc.info.get('username', ''),
                    'name': proc.info.get('name', ''),
                    'cmdline': proc.info.get('cmdline','')
                }) 
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess): continue
        return ps_list
    
    # --- Internal Method -> Print diff ---
    def __print_ps_diff(self, lista, listb):
        '''
        Find symmetric difference between two lists of dicts by converting dicts to tuples of sorted items.
        '''
        def _dict_to_tuple(d): return tuple(sorted((k, tuple(v) if isinstance(v, list) else v) for k, v in d.items()))
        def _tuple_to_dict(t): return {k: list(v) if isinstance(v, tuple) else v for k, v in t}
        
        #region body
        set_a = set(_dict_to_tuple(d) for d in lista)
        set_b = set(_dict_to_tuple(d) for d in listb)
    
        only_in_a_tuples = set_a - set_b
        only_in_b_tuples = set_b - set_a
    
        if not only_in_a_tuples and not only_in_b_tuples: return ["No differences found.", ""]
        
        only_in_a = [_tuple_to_dict(t) for t in only_in_a_tuples]
        only_in_b = [_tuple_to_dict(t) for t in only_in_b_tuples]
     
        for proc in only_in_a: print( "-" + self.__line_formatter(proc,-1) )
        for proc in only_in_b: print( "+" + self.__line_formatter(proc,-1) )
    

    # --- Internal method -> checkpoint management --- 
    def __create_checkpoint_path(self,num = None):
        num = num if num is not None else (self.__get_last_checkpoint_number() + 1)
        path = self.checkpoint_dir / f"{self.checkpoint_prefix}.{num}"
        #if path.exists():
        #    print(f"Checkpoint {num} already exists: {path}", file=sys.stderr)
        #    sys.exit(1)
        return path

    def __get_checkpoint_path(self,num):
        path = self.checkpoint_dir / f"{self.checkpoint_prefix}.{num}"
        if not path.exists():
            print(f"Checkpoint {num} does not exist: {path}", file=sys.stderr)
            sys.exit(1)
        return path

    def __get_last_checkpoint_number(self):
        '''Calculate the next checkpoint number by finding the highest existing checkpoint number.'''
        last = -1
        for file in Path(self.checkpoint_dir).glob(f"{self.checkpoint_prefix}.*"):
            try:
                num = int(file.name.split('.')[-1])
                last = max(last, num)
            except ValueError:
                continue
        return last
    
       # --- Internal methods -> Helpers ---
    def __maintenance_check(self):
        '''Check the size of the checkpoint directory and warn if it exceeds MAX_BYTES.'''
        size_bytes = sum(f.stat().st_size for f in self.checkpoint_dir.glob('*') if f.is_file())
        if size_bytes > self.max_bytes:
            print("Warning: checkpoint directory size exceeds 10MB. Consider cleaning up old snapshots.", file=sys.stderr)
  
     #TODO: make abstract in the future
    def __snapshot_filter(self, process_list):
        '''Filter out kworker and the current running process itself.'''
        current_pid = os.getpid()
        return [
            proc for proc in process_list
            if not (
                (proc['name'].startswith('kworker/') and proc['username'] == 'root') or
                proc['pid'] == current_pid
            )
        ]     
    
    def __snapshot_stringlist_to_string(self, psdict, item_name): 
        '''Reformats list of strings from ps into a single string.'''
        item = psdict.get(item_name, "")
        if isinstance(item, list):
            item = [arg for arg in item if arg.strip()]
            item = shlex.join(item)
        psdict[item_name] = item.strip("'")

    def __line_formatter(self, proc_dict, add_quotes = 0):
        '''Render a single line of ps output for display.'''
        pid = str(proc_dict.get('pid', ''))
        ppid = str(proc_dict.get('ppid', ''))
        gid = str(proc_dict.get('gid', ''))
        username = proc_dict.get('username') or ''
        name_quote = proc_dict.get('name') or ''
        cmdline_quote = proc_dict.get('cmdline') or ''

        if add_quotes > 0: 
            name_quote = f"'{name_quote}'"
            cmdline_quote = f"'{cmdline_quote}'"
        if add_quotes < 0: 
            name_quote = name_quote.strip()
            cmdline_quote = cmdline_quote.strip()
            if (name_quote == ''): name_quote = '""'
            if (cmdline_quote == ''): cmdline_quote = '""' 

        #self.__logger.debug("Line Formatter output:")
        return (f"{pid:>6} {ppid:>6} {gid:>6} {username:<8} {name_quote:<24} {cmdline_quote}\n")
