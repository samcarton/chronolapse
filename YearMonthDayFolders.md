#Copy images to year/month/day folder structure

In response to [issue 26](https://code.google.com/p/chronolapse/issues/detail?id=26) - using chronolapse for long term capture and needing the images sorted into year/month/day folder hierarchy.

UPDATED - script rewritten 8/21/2013 with more flexibility.

Use at your own risk blah blah blah.

```
"""
sort_images_by_day.py
Collin Green
Chronolapse.com

Takes a folder of images captured by Chronolapse
(or anything else as long as the filename is in the form
{{prefix}}{{numerictimestamp}}{{extension}})
and sorts them out into a folder for each day.

Edit the line starting with target_folder to change how they are sorted.

As always, use this script at your own risk. No guarantees of any kind
or anything like that. Read it all the way through before you run it,
back everything up first, etc etc etc.
"""

import os, shutil, datetime, logging

def main():

    # change these as needed
    folder = 'path/to/chronolapse/images'
    output_folder = 'path/to/images/sorted'
    prefix = 'screen_'
    extension = '.jpg'


    copied, failures = 0, 0
    distinct_folders = []

    # for every file in the specified folder
    for f in os.listdir(folder):
        # if it starts with the prefix and ends with the extension
        if f.startswith(prefix) and f.endswith(extension):
            # get the timestamp out of the filename
            timestamp = f[len(prefix):-len(extension)]

            # convert the timestamp to a float if possible
            try:
                float_timestamp = float(timestamp)
            except:
                failures += 1
                logging.error("Could not parse timestamp from %s" % f)
                continue

            # convert float timestamp to datetime object
            dt = datetime.datetime.fromtimestamp(float_timestamp)

            # get year, month, day out of datetime
            year = dt.year
            month = dt.month
            day = dt.day

            # create folders if necessary
            target_folder = os.path.join(
                                output_folder,
                                str(year),
                                str(month),
                                str(day)
                            )
            if not os.path.exists(target_folder):
                os.makedirs( target_folder )


            # track for stats
            if target_folder not in distinct_folders:
                distinct_folders.append(target_folder)

            # copy image to correct folder
            shutil.copy2(os.path.join(folder, f), os.path.join(target_folder,f))
            copied += 1

    # output stats
    failure_line = ''
    if failures > 0:
        failure_line = " with %d failures" % failures

    print "Copied %d files into %d folders%s." % (copied, len(distinct_folders), failure_line)


if __name__ == '__main__':
    main()

```