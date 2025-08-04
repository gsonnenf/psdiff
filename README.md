# psdiff
## Python/linux command line tool for taking snapshots of system processes (psutil) and comparing them with other snapshots. 

### State: In alpha. Library works, cmdline works. Still needs to be packaged.

### usage:
Places in bin directory. (e.g. ~/bin)

```
diff/compare:
psdiff           #Compares live ps with highest numbered (usually last saved) snapshot
psdiff -c 5      #Compares live ps with snapshot number 5
psdiff -c 5 6    #Compares snapshot 5 to snapshot 6

save:
psdiff -s        #saves a snapshot numbered in sequence
psdiff -s 5      #saves a snapshot as a specific number

print:
psdiff -p        #prints the current snapshot (similar to 
psdiff -p 5      #prints a saved snapshot

psdiff --delete  # Deletes all snapshots in the snapshot directory with [y/N] Prompt.

```
### TODO:
- [ ] Implement build to place library and cmdline in single file.
- [ ] Finish cmd line unit tests
- [X] Implement psutil, save and load snapshot, print snapshot with unit test
- [x] Use unit test tools Aspect and Fixture
- [X] Fix the diff between snapshots
- [X] Fix the commandline tool
- [X] Implement compare two snapshots with unittest
- [X] Implement the save as specific number with unit test

