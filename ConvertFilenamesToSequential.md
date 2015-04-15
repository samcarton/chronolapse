
```
# script to convert a batch of image files from any ordering into sequential numeric filenames
# eg:  chronolapse timestamped files into  0001.jpg 0002.jpg 0003.jpg 0004.jpg
# Written by Collin Green -- May 2, 2011

# note - you can use d instead of Y/N for a dry run

import os, math

###############################
# ADJUST THESE
path = 'test'
extension = 'jpg'
minpadding = 3
###############################

# start at one
counter = 1

# get the files from the folder
files = os.listdir(path)

# get just our desired files
imagefiles = []
for f in files:
    if f.endswith(extension):
        imagefiles.append(f)

# calculate the filename padding necessary based on number of files
padding = int(round( math.log( len(imagefiles), 10))) + 1
padding = max(minpadding, padding)

choice = raw_input('Found %d files with extensions %s: Continue with rename? (Y)es / (N)o / (D)ry run:  ' % (len(imagefiles), extension))

if choice in ['Y', 'y', 'd', 'D']:
    # process the files
    for f in imagefiles:
        newname = "%s.%s" % (str(counter).rjust(padding, '0'), extension)
        if choice in ['d', 'D']:
            print "%s  -- %s" % (f, newname)
        else:
            os.rename( os.path.join(path,f), os.path.join(path, newname))
        counter += 1
```