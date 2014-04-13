"""

    Use this script to generate an executable

    Usage: makeexe.py [--pyinstaller=pyinstallerpath]

    If pyinstallerpath is specified, script will use pyinstaller. Otherwise
    it will attempt to use cx_freeze.

    TODO:
        optionally create zips?
            source zip
            exe zip

"""

import subprocess, os, sys, shutil, getopt, re


if sys.platform.startswith('win'):
    ONWINDOWS = True
else:
    ONWINDOWS = False


appname = 'Chronolapse'
shortname = 'chronolapse'
entrypoint = 'chronolapse.py'

reshackpath = 'c:\\Program Files\\Resource Hacker\\ResHacker.exe'

if ONWINDOWS:
    files = ['manual.html', 'license.txt', 'mencoder.exe', 'chronolapse.ico',
                'helvetica-10.png', 'helvetica-10.pil',
                'helvB08.png', 'helvB08.pil']
    folders = ['mplayer','screenshots', 'webcam']
    iconpath = 'chronolapse.ico'
else:
    files = ['manual.html', 'license.txt', 'chronolapse_24.ico']
    iconpath = 'chronolapse.ico'
    folders = ['screenshots','webcam']

SCRIPTPATH = os.path.dirname( sys.argv[0] )
DISTFOLDER = os.path.join( SCRIPTPATH, 'dist%s'%shortname)
BUILDFOLDER = os.path.join( SCRIPTPATH, 'build%s'%shortname)

# get version number
try:
    import chronolapse
    version = chronolapse.VERSION
except:
    version = ''


# header
print ' '*50
print "%s EXE Generator"%appname
print "-"*50
# parse command line
optlist, args = getopt.getopt(sys.argv[1:], 'w', ['pyinstaller='])

# default to cx_freeze
exebuilder = 'cx_freeze'
noconsole=True

for opt, value in optlist:
    if opt == '--pyinstaller':
        # if pyinstaller path seems correct :P
        if os.path.isfile( os.path.join(value, 'pyinstaller.py')):
            exebuilder = 'pyinstaller'
            pyinstallerpath = value
            break
        else:
            print "PyInstaller directory seems invalid. Falling back to cx_Freeze"

    elif opt == '-w':
        noconsole = False

print "DELETING OLD BUILD AND DIST FOLDERS"
if os.path.exists( DISTFOLDER):
    shutil.rmtree(DISTFOLDER)
if os.path.exists(BUILDFOLDER):
    shutil.rmtree(BUILDFOLDER)

if exebuilder == 'pyinstaller':
    print "RUNNING PYINSTALLER"

    # if not on windows, make sure it has proper line endings bc pyinstaller cant handle it
    if not ONWINDOWS:
        # from http://www.java2s.com/Code/Python/Utility/ChangeLFlineendingstoCRLFUnixtoWindows.htm
        data = open(entrypoint, 'rb').read()
        newdata = re.sub("\r?\n", "\n", data)
        f = open(entrypoint, 'wb')
        f.write(newdata)
        f.close()
##
##    if noconsole:
##        proc = subprocess.Popen( "%s -F -X -w -n %s --icon=%s %s"% (os.path.join(pyinstallerpath, "pyinstaller.py"), shortname, iconpath, entrypoint), shell=True)
##    else:
##        proc = subprocess.Popen( "%s -F -X -n %s --icon=%s %s"% (os.path.join(pyinstallerpath, "pyinstaller.py"), shortname, iconpath, entrypoint), shell=True)

    if noconsole:
        proc = subprocess.Popen( "%s -F -w -n %s --icon=%s %s"% (os.path.join(pyinstallerpath, "pyinstaller.py"), shortname, iconpath, entrypoint), shell=True)
    else:
        proc = subprocess.Popen( "%s -F -n %s --icon=%s %s"% (os.path.join(pyinstallerpath, "pyinstaller.py"), shortname, iconpath, entrypoint), shell=True)

    proc.communicate()

##    print "CREATING SPEC FILE"
##    proc = subprocess.Popen( "%s -F -X -w -n %s --icon=%s %s"% (os.path.join(pyinstallerpath, "Makespec.py"), shortname, iconpath, entrypoint), shell=True)
##    proc.communicate()
##
##    print "BUILDING EXECUTABLE"
##    proc = subprocess.Popen( "%s %s"% ( os.path.join(pyinstallerpath, "Build.py"),  '%s.spec'%shortname ), shell=True)
##    proc.communicate()

    # create dist folder
    os.mkdir( DISTFOLDER)

    # copy exe there
    if ONWINDOWS:
        exename = '%s.exe' % shortname
    else:
        exename = shortname

    if os.path.isfile(os.path.join('dist', exename)):
        shutil.move( os.path.join('dist',exename), os.path.join(DISTFOLDER, exename))
    elif os.path.isfile(exename):
        shutil.move( exename, os.path.join(DISTFOLDER, exename))
    else:
        print "Executable not found... Locate and move it manually :D"

##    # delete spec if found
##    if os.path.isfile( '%s.spec'%shortname):
##        os.remove( '%s.spec'%shortname)

elif exebuilder == 'cx_freeze':
    print "RUNNING CX_FREEZE"

    try:
        from cx_Freeze import main
        sys.argv = [sys.argv[0], '--target-dir', '%s'%DISTFOLDER, entrypoint]
        main()
    except Exception, e:
        print e
        sys.exit(1)


##    proc = subprocess.Popen( "%s clg.py --target-dir %s"% (os.path.join(freezepath, "freeze"), DISTFOLDER), shell=True)
##    proc.communicate()


if not os.path.isdir(DISTFOLDER):
    print "BUILD FAILED"
    sys.exit(1)

else:
    print "MOVING FILES"

    for f in files:
        try:
            shutil.copy( f, os.path.join(DISTFOLDER, f))
        except Exception, e:
            print e

    for fold in folders:
        try:

            # create folder
            os.makedirs(os.path.join(DISTFOLDER, fold))

            # copy files
            for fi in os.listdir(fold):
                # skip files starting with . (.svn)
                if not fi.startswith('.'):
                    shutil.copy2(os.path.join(fold,fi), os.path.join(DISTFOLDER, fold, fi))

            #shutil.copytree(f, DISTFOLDER + os.path.sep + f)
        except Exception, e:
            print e

    # get OS guess
    prefixes = {'win':'win',
                'linux':'linux',
                'darwin':'mac',
                'mac':'mac'}
    plat = sys.platform
    osname = 'other'
    for prefix in prefixes.keys():
        if plat.startswith(prefix):
            osname = prefixes[prefix]

    # rename to something useful
    foldername = "%s-exe-%s_%s" % (shortname, osname, version)
    foldername = foldername.lower()

    # check if already exists
    movefolder = True
    if os.path.exists( foldername ):
        # prompt overwrite
        result = raw_input("%s already exists. Overwrite? Y/N:  "%foldername)
        if result.startswith( ('y', 'Y')):
            shutil.rmtree( foldername )
        else:
            print "NOT OVERWRITING - EXE IN %s" % DISTFOLDER
            movefolder = False
            exelocation = DISTFOLDER


    # rename
    if movefolder:
        shutil.move( DISTFOLDER, foldername)
        exelocation = foldername
        print "EXE IN %s" % foldername

##    # change icon
##    if iconpath != '':
##        print "UPDATING ICON"
##        command = '"%s" -addoverwrite %s, %s, %s, ICONGROUP, MAINICON, 0'%(
##                    reshackpath,
##                    os.path.join(exelocation, '%s.exe'%shortname),
##                    os.path.join(exelocation, '%s.exe'%shortname),
##                    iconpath)
##        print command
##        proc = subprocess.Popen(command, shell=True)
##        proc.communicate()

    # clean up build folder
    print "CLEANING UP"
    if os.path.exists(BUILDFOLDER):
        shutil.rmtree(BUILDFOLDER)

    print "BUILD FINISHED"
    sys.exit(0)