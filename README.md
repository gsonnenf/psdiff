# psdiff
## Python/linux command line tool for taking snapshots of system processes (psutil) and comparing them with other snapshots. 

### Not currently functional. Library works, cmdline does not.

### usage:
Places in bin directory. (e.g. ~/bin)


psdiff -s     <- saves a snapshot
psdiff -s #   <- saves a snapshot as a specific number
psdiff        <- Compares live ps with highest numbered (usually last saved) snapshot
psdiff -c #   <- compares two snapshots
psdiff -c # # <-
### TODO:
[X] Implement psutil, save and load snapshot, print snapshot
[ ] Fix the diff between snapshots
[ ] Fix the commandline tool
[ ] Implement compare two snapshots with uni ttest
[ ] Implement the save as specific number with unit test
[ ] Implement build to place library and cmdline in single file. 
