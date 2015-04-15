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
imagefiles = [.md](.md)
for f in files:
> if f.endswith(extension):
> > imagefiles.append(f)

# calculate the filename padding necessary based on number of files
padding = int(round( math.log( len(imagefiles), 10))) + 1
padding = max(minpadding, padding)


# process the files
for f in imagefiles:

> newname = str(counter).rjust(padding, '0') + '.' + extension
> os.rename( os.path.join(path,f), os.path.join(path, newname))
> counter += 1