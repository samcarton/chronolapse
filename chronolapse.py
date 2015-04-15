"""
    chronolapse.py
    @author: Collin "Keeyai" Green
    @url: http://keeyai.com
    @summary:
        ChronoLapse is a tool for making time lapses.
        CL can save both screenshots and webcam captures, and can even do them both
        at the same time so they are 'synched' together. In addition to saving the
        images, CL has some processing tools to compile your images into video,
        create a picture-in-picture effect, resize images, and 'annotate' your images/videos.
    @license: MIT license - see license.txt
    @todo:

    @change: 1.0.1
        - fixed outputting video to path with spaces - used a bit of a hack for mencoder to work -- issue 1
    @change: 1.0.2
        - removed short sighted dependence on kml.pyc
        - added -a flag for autostarting
        - added minimizing to tray option
        - added rotate option and changed resize tab to adjust tab
        - fixed dual monitor support to work with any orientation or relative resolution
    @change: 1.0.3
        - fixed a bug with times under 1 second being fired 1000 times too fast
        - silently fails if set to capture 2 monitors but they are duplicated
        - added system wide hotkey -- doesnt seem to work right in wx so it is only part implemented
        - added audio tab to dub audio onto your timelapse
        - added a drop shadow option for annotations
        - added a schedule tab for scheduling starts and/or stops
    @change: 1.0.4
        - added a rough and dirty threading implementation for the mencoder call -- trying to fix hang in GUI form
        - changed popen to just pop up a window with output -- was hanging on mencoder call with no window to print to
        - fixed update check code
    @change: 1.0.5
        - added subsection option for screenshots
    @change: 1.0.6
        - fixed captures at less than 1 second interval -- adds microseconds to filename and timestamp
    @change: 1.0.7
        - fixed bug where audio encoding failed when video filename did NOT have a space in it :o
    @change: 1.0.8
        - added 'default' screenshot and webcam folders
        - added a bunch of non-windows options and checks
        - added code to automatically un-check the webcam box if no cam found
        - added code to try to initialize the webcam with default settings if checked but not configured
        - fixed bug on linux when coming back from the tray
        - added some openCV code for linux/mac but it doesn't seem to work so webcams are disabled on non-windows systems
        - added rename tab for renaming the captured files into sequential integer format (issue #20)
        - removed format option and added some codecs

    @change: 1.0.9
        - added '-b' command line option to launch minimized
"""

VERSION = '1.0.9'

import wx, time, datetime, os, sys, shutil, cPickle, tempfile, textwrap
import math, subprocess, getopt, urllib, urllib2, threading, xml.dom.minidom
import wx.lib.masked as masked



if sys.platform.startswith('win'):
    ONWINDOWS = True
    import win32con, wxkeycodes
    #import cv

    try:
        from VideoCapture import Device
    except Exception, e:
        print e
        print 'VideoCapture library not found. Aborting'
        sys.exit(1)

else:
    ONWINDOWS = False
    import cv, numpy

from PIL import Image

try:
    from agw import knobctrl as KC
except ImportError: # if it's not there locally, try the wxPython lib.
    import wx.lib.agw.knobctrl as KC



from chronolapsegui import *

# use psyco if available
try:
    import psyco
    psyco.full()
except ImportError:
    pass


class ScreenshotConfigDialog(screenshotConfigDialog):
    def __init__(self, *args, **kwargs):
        screenshotConfigDialog.__init__(self, *args, **kwargs)

    def screenshotSaveFolderBrowse(self, event):
        # dir browser
        path = self.GetParent().dirBrowser('Select folder where screenshots will be saved',
                    self.GetParent().options['screenshotsavefolder'])

        if path is not '':
            self.GetParent().options['screenshotsavefolder'] = path
            self.screenshotsavefoldertext.SetValue(path)


class WebcamConfigDialog(webcamConfigDialog):
    def __init__(self,  *args, **kwargs):
        webcamConfigDialog.__init__(self, *args, **kwargs)

        # get cam
        self.hascam = False
        try:
            if self.GetParent().initCam():
                self.hascam = True
                self.GetParent().debug('Found Camera')

                if ONWINDOWS:
                    try:
                        self.cam.displayCapturePinProperties()
                    except:
                        pass

        except Exception, e:
            self.GetParent().showWarning('No Webcam Found', 'No webcam found on your system.')
            self.hascam = False
            self.GetParent().debug(repr(e))

        if not self.hascam:
            self.GetParent().webcamcheck.SetValue(False)

    def webcamSaveFolderBrowse(self, event):
        # dir browser
        path = self.GetParent().dirBrowser('Select folder where webcam shots will be saved',
                    self.GetParent().options['webcamsavefolder'])

        if path is not '':
            self.GetParent().options['webcamsavefolder'] = path
            self.webcamsavefoldertext.SetValue(path)

    def testWebcamPressed(self, event):
        if self.hascam:
            self.temppath = tempfile.mkstemp('.jpg')[1]
            self.temppath = self.temppath[:-4]  # takeWebcam automatically appends the extension again

            # create a popup with the image
            dlg = WebcamPreviewDialog(self)
            dlg.ShowModal()
            dlg.Destroy()

            # remove the temp file
            try:
                os.unlink(self.temppath + '.jpg')
            except Exception, e:
                self.GetParent().debug(e)


class WebcamPreviewDialog(webcamPreviewDialog):

    def __init__(self, *args, **kwargs):
        webcamPreviewDialog.__init__(self, *args, **kwargs)
        self.parent = self.GetParent().GetParent()
        self.timer = Timer(self.callback)
        self.timer.Start(250)

        self.temppath = self.GetParent().temppath

        self.previewokbutton.Bind(wx.EVT_BUTTON, self.close)

    def close(self, event=None):
        self.timer.Stop()
        self.previewbitmap.SetBitmap(wx.NullBitmap)
        del self.timer
        if event:
            event.Skip()

    def callback(self):
        try:
            path = self.parent.takeWebcam(os.path.basename(self.temppath), os.path.dirname(self.temppath), '')

            if(ONWINDOWS):
                bitmap = wx.Bitmap(path, wx.BITMAP_TYPE_JPEG)
            else:
                # try this so WX doesnt freak out if the file isnt a bitmap
                pilimage = Image.open(path)
                myWxImage = wx.EmptyImage( pilimage.size[0], pilimage.size[1] )
                myWxImage.SetData( pilimage.convert( 'RGB' ).tostring() )
                bitmap = myWxImage.ConvertToBitmap()

            self.previewbitmap.SetBitmap(bitmap)
            self.previewbitmap.CenterOnParent()

        except Exception, e:
            self.parent.debug(repr(e))
            pass


class Timer(wx.Timer):
    """Timer class"""
    def __init__(self, callback):
        wx.Timer.__init__(self)
        self.callback = callback

    def Notify(self):
        self.callback()


class ProgressPanel(wx.Panel):

    def __init__(self, *args, **kwds):
        wx.Panel.__init__(self, *args, **kwds)
        self.Bind(wx.EVT_PAINT, self.OnPaint)

        self.progress = 0

    def setProgress(self, progress):
        self.progress = progress

        dc = wx.WindowDC(self)
        dc.SetPen(wx.Pen(wx.Colour(0,0,255,255)))
        dc.SetBrush(wx.Brush(wx.Colour(0,0,255,220)))

        # build rect
        width,height = self.GetSizeTuple()
        size = max(2, (width-10)*self.progress)
        rect = wx.Rect(5,8, size ,5)

        # draw rect
        dc.Clear()
        dc.DrawRoundedRectangleRect(rect, 2)

    def OnPaint(self, evt):
        # this doesnt appear to work at all...

        width,height = self.GetSizeTuple()

        # get drawing shit
        dc = wx.PaintDC(self)

        dc.SetPen(wx.Pen(wx.Colour(0,0,255,255)))
        dc.SetBrush(wx.Brush(wx.Colour(0,0,255,220)))

        # build rect
        size = max(2, (width-10)*self.progress)
        rect = wx.Rect(5,8, size ,5)

        # draw rect
        dc.Clear()
        dc.BeginDrawing()
        dc.DrawRoundedRectangleRect(rect, 2)
        dc.EndDrawing()


class ChronoFrame(chronoFrame):

    def __init__(self, *args, **kwargs):
        chronoFrame.__init__(self, *args, **kwargs)

        # bind OnClose method
        self.Bind(wx.EVT_CLOSE, self.OnClose)

        # hotkey stuff
        self.hotkeyid = wx.NewId()
        self.Bind(wx.EVT_HOTKEY, self.handleHotKey)
        self.hotkeytext.Bind(wx.EVT_KEY_DOWN, self.hotkeyTextEntered)
        self.hotkeyraw = 0
        self.hotkeymods = 0

        # schedule stuff
        self.Bind(wx.EVT_DATE_CHANGED, self.startDateChanged, self.startdate)
        self.Bind(wx.EVT_DATE_CHANGED, self.endDateChanged, self.enddate)
        self.Bind(masked.EVT_TIMEUPDATE, self.startTimeChanged, self.starttime)
        self.Bind(masked.EVT_TIMEUPDATE, self.endTimeChanged, self.endtime)
        self.starttimer = Timer(self.startTimerCallBack)
        self.endtimer = Timer(self.endTimerCallBack)
        self.schedulestartdate = ''
        self.schedulestarttime = ''
        self.scheduleenddate = ''
        self.scheduleendtime = ''

        # constants
        self.VERSION = VERSION
        self.ANNOTATIONFILE = 'chronolapse.annotate'
        self.CONFIGFILE = 'chronolapse.config'
        self.FILETIMEFORMAT = '%Y-%m-%d_%H-%M-%S'
        self.TIMESTAMPFORMAT = '%Y-%m-%d %H:%M:%S'
        self.DOCFILE = 'manual.html'
        self.VERSIONCHECKPATH = 'http://keeyai.com/versioncheck.php?application=chronolapse'
        self.UPDATECHECKFREQUENCY = 604800      # 1 week, in seconds

        # fill in codecs available
        self.videocodeccombo.SetItems(['mpeg4', 'msmpeg4', 'msmpeg4v2', 'wmv1', 'mjpeg', 'h263p'])

        # fill in formats
        #self.videoformatcombo.SetItems(['divx4', 'xvid', 'ffmpeg', 'msmpeg4'])

        # save file path
        self.CHRONOLAPSEPATH = os.path.dirname( os.path.abspath(sys.argv[0]))

        # verbosity
        self.NORMAL = 0
        self.VERBOSE = 1
        self.DEBUG = 2
        # get command line options
        self.verbosity = self.NORMAL
        self.autostart = False
        self.start_in_background = False
        try:
            optlist, args = getopt.getopt(sys.argv[1:], 'vqab')
            for opt in optlist:
                if opt[0] == '-v':
                    self.verbosity = max(0, min( 2, self.verbosity + 1) )
                elif opt[0] == '-q':
                    self.verbosity = max(0, min( 2, self.verbosity - 1) )
                elif opt[0] == '-a':
                    self.autostart = True
                    self.debug('Autostarting', self.VERBOSE)

                elif opt[0] == '-b':
                    self.start_in_background = True

            if self.verbosity == self.VERBOSE:
                self.debug("Verbosity set to: VERBOSE", self.VERBOSE)
            elif self.verbosity == self.DEBUG:
                self.debug("Verbosity set to: DEBUG", self.DEBUG)
        except Exception, e:
            print e

        if ONWINDOWS and os.path.isfile( os.path.join(self.CHRONOLAPSEPATH, 'chronolapse.ico')):
            self.SetIcon(wx.Icon(os.path.join(self.CHRONOLAPSEPATH, 'chronolapse.ico'), wx.BITMAP_TYPE_ICO))
        elif not ONWINDOWS and os.path.isfile( os.path.join(self.CHRONOLAPSEPATH, 'chronolapse_24.ico')):
            self.SetIcon(wx.Icon(os.path.join(self.CHRONOLAPSEPATH, 'chronolapse_24.ico'), wx.BITMAP_TYPE_ICO))

            # disable webcams for now
            self.webcamcheck.Disable()
            self.configurewebcambutton.Disable()

        else:
            self.debug( 'Could not find %s' % os.path.join(self.CHRONOLAPSEPATH, 'chronolapse.ico'))

         # set X to close to taskbar -- windows only
        # http://code.activestate.com/recipes/475155/
        self.TBFrame = TaskBarFrame(None, self, -1, " ", self.CHRONOLAPSEPATH)
        self.TBFrame.Show(False)

        # option defaults
        self.options = {

        'font': wx.Font(22, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL),
        'fontdata': wx.FontData(),

        'screenshottimestamp':  True,
        'screenshotsavefolder':     'screenshots',
        'screenshotprefix':     'screen_',
        'screenshotformat':     'jpg',
        'screenshotdualmonitor': False,

        'screenshotsubsection': False,
        'screenshotsubsectiontop': '0',
        'screenshotsubsectionleft': '0',
        'screenshotsubsectionwidth': '800',
        'screenshotsubsectionheight': '600',

        'webcamtimestamp':  True,
        'webcamsavefolder':     'webcam',
        'webcamprefix':     'cam_',
        'webcamformat':     'jpg',
        'webcamresolution': '800, 600',

        'pipmainfolder':    '',
        'pippipfolder':     '',

        'videosourcefolder':    '',
        'videooutputfolder':    '',

        'lastupdate': time.strftime('%Y-%m-%d')
        }

        # load config
        self.parseConfig()

        # webcam
        self.cam = None

        # image countdown
        self.countdown = 60.0

        # create timer
        self.timer = Timer(self.timerCallBack)

        # default states
        self.annotatebutton.Disable()

        # check version
        self.checkVersion()

        # autostart
        if self.autostart:
            self.startCapturePressed(None)

    def doShow(self, *args, **kwargs):
        if self.start_in_background:
            self.debug("Starting minimized")
            self.TBFrame.set_icon_action_text(True)
            #self.ShowWithoutActivating(*args, **kwargs)
        else:
            self.debug("Showing main frame")
            self.Show(*args, **kwargs)

    def debug(self, message, verbosity=-1):
        # set default
        if verbosity == -1:
            verbosity = self.DEBUG

        if verbosity <= self.verbosity:
            print message

    def OnClose(self, event):
        # save config before closing
        self.saveConfig()

        try:
            if hasattr(self, 'TBFrame') and self.TBFrame:
                self.TBFrame.kill(event)
        except:
            pass

        event.Skip()

    def startTimer(self):

        # set countdown
        self.countdown = float(self.frequencytext.GetValue())

        # start timer - if frequency < 1 second, use small increments, otherwise, 1 second will be plenty fast
        if self.countdown < 1:
            self.timer.Start( self.countdown * 1000)
        else:
            self.timer.Start(1000)

    def stopTimer(self):
        self.timer.Stop()

    def timerCallBack(self):

        # decrement timer
        self.countdown -= 1

        # adjust progress bar
        self.progresspanel.setProgress(1- (self.countdown / float(self.frequencytext.GetValue())))

        # on countdown
        if self.countdown <= 0:
            self.capture()      # take screenshot and webcam capture
            self.countdown = float(self.frequencytext.GetValue()) # reset timer

    def fileBrowser(self, message, defaultFile=''):
        dlg = wx.FileDialog(self, message, defaultFile=defaultFile,
                        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
        else:
            path = ''
        dlg.Destroy()
        return path

    def saveFileBrowser(self, message, defaultFile=''):
        dlg = wx.FileDialog(self, message, defaultFile=defaultFile,
                        style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
        else:
            path = ''
        dlg.Destroy()
        return path

    def dirBrowser(self, message, defaultpath):
        # show dir dialog
        dlg = wx.DirDialog(
            self, message=message,
            defaultPath= defaultpath,
            style=wx.DD_DEFAULT_STYLE)

        # Show the dialog and retrieve the user response.
        if dlg.ShowModal() == wx.ID_OK:
            # load directory
            path = dlg.GetPath()

        else:
            path = ''

        # Destroy the dialog.
        dlg.Destroy()

        return path

    def capture(self):

        # get filename from time
        filename = time.strftime(self.FILETIMEFORMAT)

        # use microseconds if capture speed is less than 1
        if self.countdown < 1:
            filename = str( time.time() )

        self.debug('Capturing - ' + filename)

        # if screenshots
        if self.screenshotcheck.IsChecked():
            # take screenshot
            self.saveScreenshot(filename)

        # if webcam
        if self.webcamcheck.IsChecked():
            # take webcam shot
            self.saveWebcam(filename)

        return filename

    def parseConfig(self):

        if os.path.isfile( os.path.join(self.CHRONOLAPSEPATH, self.CONFIGFILE)):
            try:
                configfile = open( os.path.join(self.CHRONOLAPSEPATH, self.CONFIGFILE), 'rb')
                config = cPickle.load(configfile)
            except Exception, e:
                self.debug(str(e))
                self.showWarning('Config Error', 'The Chronolapse config file is corrupted. Your settings have been lost')
                f = open(os.path.join(self.CHRONOLAPSEPATH, self.CONFIGFILE), 'w+b')
                f.close()

            try:
                self.frequencytext.SetValue(config['frequency'])
                self.screenshotcheck.SetValue(config['usescreenshot'])
                self.webcamcheck.SetValue(config['usewebcam'])
                self.forcecaptureframestext.SetValue(str(config['forcecaptureframes']))
            except Exception, e:
                self.debug(str(e))

            try:
                self.resizewidthtext.SetValue(config['resizewidth'])
                self.resizeheighttext.SetValue(config['resizeheight'])
                self.resizesourcetext.SetValue(config['resizesourcefolder'])
                self.resizeoutputtext.SetValue(config['resizeoutputfolder'])

                for opt in self.rotatecombo.GetStrings():
                    if opt == config['rotateangle']:
                        self.rotatecombo.SetValue(opt)
                        break

            except Exception, e:
                self.debug(str(e))

            try:
                self.annotatesourcefoldertext.SetValue(config['annotatesourcefolder'])
                self.annotateoutputfoldertext.SetValue(config['annotateoutputfolder'])
                self.annotateopacityslider.SetValue(float(config['annotateopacity']))
                self.annotatepositioncombo.SetStringSelection(config['annotateposition'])
                self.annotatetimedradio.SetValue(config['annotatetimed'])
                self.annotateconstantradio.SetValue(config['annotateconstant'])
                self.annotatedurationtext.SetValue(str(config['annotateduration']))
                self.annotatefadeincheck.SetValue(config['annotatefadein'])
                self.annotatefadeoutcheck.SetValue(config['annotatefadeout'])
            except Exception, e:
                self.debug(str(e))

            try:
                self.pipmainimagefoldertext.SetValue(config['pipmainsourcefolder'])
                self.pippipimagefoldertext.SetValue(config['pippipsourcefolder'])
                self.pipoutputimagefoldertext.SetValue(config['pipoutputfolder'])
                self.pipsizecombo.SetStringSelection(config['pipsize'])
                self.pippositioncombo.SetStringSelection(config['pipposition'])
                self.pipignoreunmatchedcheck.SetValue(config['pipignoreunmatched'])
            except Exception, e:
                self.debug(str(e))

            try:
                self.videosourcetext.SetValue(config['videosourcefolder'])
                self.videodestinationtext.SetValue(config['videooutputfolder'])
                #self.videoformatcombo.SetStringSelection(config['videoformat'])
                self.videocodeccombo.SetStringSelection(config['videocodec'])
                self.videoframeratetext.SetValue(config['videoframerate'])
                self.mencoderpathtext.SetValue(config['mencoderpath'])
            except Exception, e:
                self.debug(str(e))

            try:
                self.audiosourcevideotext.SetValue(config['audiosourcevideo'])
                self.audiosourcetext.SetValue(config['audiosource'])
                self.audiooutputfoldertext.SetValue(config['audiooutputfolder'])
            except Exception, e:
                self.debug(str(e))

            try:
                # copy self.options values over for program use
                for key in self.options.keys():
                    if key in config:
                        self.options[key] = config[key]

                # special behaviour

                # font
                if config['fontfamily'] == 'decorative':
                    fam = wx.FONTFAMILY_DECORATIVE
                elif config['fontfamily'] == 'roman':
                    fam = wx.FONTFAMILY_ROMAN
                elif config['fontfamily'] == 'script':
                    fam = wx.FONTFAMILY_SCRIPT
                elif config['fontfamily'] == 'swiss':
                    fam = wx.FONTFAMILY_SWISS
                elif config['fontfamily'] == 'modern':
                    fam = wx.FONTFAMILY_MODERN
                elif config['fontfamily'] == 'teletype':
                    fam = wx.FONTFAMILY_TELETYPE
                else:
                    fam = wx.FONTFAMILY_DEFAULT

                if config['fontweight'] == 'bold':
                    weight = wx.FONTWEIGHT_BOLD
                elif config['fontweight'] == 'light':
                    weight = wx.FONTWEIGHT_LIGHT
                else:
                    weight = wx.FONTWEIGHT_NORMAL

                if config['fontstyle'] == 'italic':
                    style = wx.FONTSTYLE_ITALIC
                elif config['fontstyle'] == 'slant':
                    style = wx.FONTSTYLE_SLANT
                else:
                    style = wx.FONTSTYLE_NORMAL

                font = wx.Font(config['fontsize'], fam, style, weight, config['fontunderline'], config['fontname'])
                self.options['font'] = font

                data = wx.FontData()
                color = wx.Colour()
                color.SetRGB(config['fontcolor'])

                data.SetColour(color)
                self.options['fontdata'] = data

                self.fontexampletext.SetValue('Font: %s %d pt' % (font.GetFaceName(), font.GetPointSize()))
                self.fontexampletext.SetFont(font)
                self.fontexampletext.SetForegroundColour(color)

            except Exception, e:
                self.debug(str(e))

        else: # not found
            configfile = open(os.path.join(self.CHRONOLAPSEPATH, self.CONFIGFILE), 'wb')

            # OS specific defaults
            if ONWINDOWS:
                mencoderpath = os.path.join(self.CHRONOLAPSEPATH, 'mencoder.exe')
            else:
                mencoderpath = 'mencoder'

            # create defaults
            config = {
                'frequency':        '60',
                'usescreenshot':   True,
                'usewebcam':        False,
                'forcecaptureframes':   '1',

                'fontfamily':       'roman',
                'fontsize':         14,
                'fontunderline':    False,
                'fontname':         'Arial',
                'fontstyle':        'normal',
                'fontweight':       'normal',
                'fontcolor':        12632256,   # default to silver

                'resizesourcefolder':   '',
                'resizeoutputfolder':   '',
                'resizewidth':          '800',
                'resizeheight':         '600',
                'rotateangle':          '0',

                'annotatesourcefolder': '',
                'annotateoutputfolder': '',
                'annotateopacity':  '100',
                'annotateposition': 'Bottom',
                'annotatetimed':    True,
                'annotateconstant': False,
                'annotateduration': '5',
                'annotatefadein':   True,
                'annotatefadeout':  True,

                'pipmainsourcefolder': '',
                'pippipsourcefolder': '',
                'pipoutputfolder':  '',
                'pipsize':          'Small',
                'pipposition':      'Top-Right',
                'pipignoreunmatched':True,

                'videosourcefolder':    '',
                'videooutputfolder':    '',
                'videoformat':          '',
                'videocodec':           'wmv2',
                'videoframerate':       '10',
                'mencoderpath':         str(mencoderpath),

                'audiosourcevideo':     '',
                'audiosource':          '',
                'audiooutputfolder':    ''
            }

            # pickle it
            cPickle.dump(config, configfile)
            configfile.close()

            # try again
            self.parseConfig()

    def saveConfig(self):
        try:

            # get all the options
            config = {
                'frequency':            self.frequencytext.GetValue(),
                'usescreenshot':        self.screenshotcheck.GetValue(),
                'usewebcam':            self.webcamcheck.GetValue(),
                'forcecaptureframes':   self.forcecaptureframestext.GetValue(),

                'resizesourcefolder':   self.resizesourcetext.GetValue(),
                'resizeoutputfolder':   self.resizeoutputtext.GetValue(),
                'resizewidth':          self.resizewidthtext.GetValue(),
                'resizeheight':         self.resizeheighttext.GetValue(),
                'rotateangle':          self.rotatecombo.GetValue(),

                'annotatesourcefolder': self.annotatesourcefoldertext.GetValue(),
                'annotateoutputfolder': self.annotateoutputfoldertext.GetValue(),
                'annotateopacity':      self.annotateopacityslider.GetValue(),
                'annotateposition':     self.annotatepositioncombo.GetStringSelection(),
                'annotatetimed':        self.annotatetimedradio.GetValue(),
                'annotateconstant':     self.annotateconstantradio.GetValue(),
                'annotateduration':     self.annotatedurationtext.GetValue(),
                'annotatefadein':       self.annotatefadeincheck.GetValue(),
                'annotatefadeout':      self.annotatefadeoutcheck.GetValue(),

                'pipmainsourcefolder':  self.pipmainimagefoldertext.GetValue(),
                'pippipsourcefolder':   self.pippipimagefoldertext.GetValue(),
                'pipoutputfolder':      self.pipoutputimagefoldertext.GetValue(),
                'pipsize':              self.pipsizecombo.GetStringSelection(),
                'pipposition':          self.pippositioncombo.GetStringSelection(),
                'pipignoreunmatched':   self.pipignoreunmatchedcheck.GetValue(),

                'videosourcefolder':    self.videosourcetext.GetValue(),
                'videooutputfolder':    self.videodestinationtext.GetValue(),
                #'videoformat':          self.videoformatcombo.GetStringSelection(),
                'videocodec':           self.videocodeccombo.GetStringSelection(),
                'videoframerate':       self.videoframeratetext.GetValue(),
                'mencoderpath':         self.mencoderpathtext.GetValue(),

                'audiosourcevideo':     self.audiosourcevideotext.GetValue(),
                'audiosource':          self.audiosourcetext.GetValue(),
                'audiooutputfolder':    self.audiooutputfoldertext.GetValue()


            }

            # append to self.options
            for key, value in self.options.iteritems():
                config[key] = value

            # special behaviour

            # font
            config['fontname'] = config['font'].GetFaceName()

            fam = config['font'].GetFamily()
            if fam == wx.FONTFAMILY_DECORATIVE:
                config['fontfamily'] = 'decorative'
            elif fam == wx.FONTFAMILY_ROMAN:
                config['fontfamily'] = 'roman'
            elif fam == wx.FONTFAMILY_SCRIPT:
                config['fontfamily'] = 'script'
            elif fam == wx.FONTFAMILY_SWISS:
                config['fontfamily'] = 'swiss'
            elif fam == wx.FONTFAMILY_MODERN:
                config['fontfamily'] = 'modern'
            elif fam == wx.FONTFAMILY_TELETYPE:
                config['fontfamily'] = 'teletype'
            else:
                config['fontfamily'] = 'default'

            weight = config['font'].GetWeight()
            if weight == wx.FONTWEIGHT_BOLD:
                config['fontweight'] = 'bold'
            elif weight == wx.FONTWEIGHT_LIGHT:
                config['fontweight'] = 'light'
            else:
                config['fontweight'] = 'normal'

            style = config['font'].GetStyle()
            if style == wx.FONTSTYLE_ITALIC:
                config['fontstyle'] = 'italic'
            elif style == wx.FONTSTYLE_SLANT:
                config['fontstyle'] = 'slant'
            else:
                config['fontstyle'] = 'normal'

            config['fontsize'] = config['font'].GetPointSize()
            config['fontunderline'] = config['font'].GetUnderlined()
            config['fontsize'] = config['font'].GetPointSize()

            color = config['fontdata'].GetColour()
            config['fontcolor'] = color.GetRGB()

            del config['font']
            del config['fontdata']


            # pickle it
            configfile = file(os.path.join(self.CHRONOLAPSEPATH, self.CONFIGFILE), 'wb')
            cPickle.dump(config, configfile)

        except Exception, e:
            print "Error: failed to save options to config file"
            print e

    def initCam(self, devnum=0):
        if self.cam is None:
            if ONWINDOWS:
                try:
                    self.cam = Device(devnum,0)

                    try:
                        self.cam.setResolution(640, 480)
                    except:
                        pass

                    return True
                except Exception, e:
                    self.debug('initCam -- failed to initialize camera')
                    self.debug('Exception: %s' % repr(e))
                    self.showWarning('No Webcam Found', 'No webcam found on your system')
                    self.cam = None
                return False
            else:
                try:
                    self.cam = cv.CaptureFromCAM(devnum)
                    if not self.cam:
                        self.cam = None
                        self.debug('initCam -- failed to initialize camera')
                    else:
                        return True
                except:
                    self.debug('initCam -- failed to initialize camera')
        return False

    def saveScreenshot(self, filename):
        timestamp = self.options['screenshottimestamp']
        folder = self.options['screenshotsavefolder']
        prefix = self.options['screenshotprefix']
        format = self.options['screenshotformat']

        rect = None
        if self.options['screenshotsubsection']:
            if (self.options['screenshotsubsectiontop'] > 0 and
                self.options['screenshotsubsectionleft'] > 0 and
                self.options['screenshotsubsectionwidth'] > 0 and
                self.options['screenshotsubsectionheight'] > 0):
                rect = wx.Rect(
                        int(self.options['screenshotsubsectionleft']),
                        int(self.options['screenshotsubsectiontop']),
                        int(self.options['screenshotsubsectionwidth']),
                        int(self.options['screenshotsubsectionheight'])
                    )

        img = self.takeScreenshot(rect, timestamp)
        self.saveImage(img, filename, folder, prefix, format)

    def takeScreenshot(self, rect = None, timestamp=False):
        """ Takes a screenshot of the screen at give pos & size (rect).
        Code from Andrea - http://lists.wxwidgets.org/pipermail/wxpython-users/2007-October/069666.html"""

        # use whole screen if none specified
        if not rect:
            #width, height = wx.DisplaySize()
            #rect = wx.Rect(0,0,width,height)

            x, y, width, height = wx.Display().GetGeometry()
            rect = wx.Rect(x,y,width,height)

            try:
                # use two monitors if checked and available
                if self.options['screenshotdualmonitor'] and wx.Display_GetCount() > 0:
                    second = wx.Display(1)
                    x2, y2, width2, height2 = second.GetGeometry()

                    x3 = min(x,x2)
                    y3 = min(y, y2)
                    width3 = max(x+width, x2+width2) - x3
                    height3 = max(height-y3, height2-y3)

                    rect = wx.Rect(x3, y3, width3, height3)
            except Exception, e:
                self.debug("Exception while attempting to capture second monitor: %s"%repr(e))

        #Create a DC for the whole screen area
        dcScreen = wx.ScreenDC()

        #Create a Bitmap that will later on hold the screenshot image
        #Note that the Bitmap must have a size big enough to hold the screenshot
        #-1 means using the current default colour depth
        bmp = wx.EmptyBitmap(rect.width, rect.height)

        #Create a memory DC that will be used for actually taking the screenshot
        memDC = wx.MemoryDC()

        #Tell the memory DC to use our Bitmap
        #all drawing action on the memory DC will go to the Bitmap now
        memDC.SelectObject(bmp)

        #Blit (in this case copy) the actual screen on the memory DC
        #and thus the Bitmap
        memDC.Blit( 0,      #Copy to this X coordinate
            0,              #Copy to this Y coordinate
            rect.width,     #Copy this width
            rect.height,    #Copy this height
            dcScreen,       #From where do we copy?
            rect.x,         #What's the X offset in the original DC?
            rect.y          #What's the Y offset in the original DC?
            )

        # write timestamp on image
        if timestamp:
            stamp = time.strftime(self.TIMESTAMPFORMAT)
            if self.countdown < 1:
                now = time.time()
                micro = str(now - math.floor(now))[0:4]
                stamp = stamp + micro

            memDC.DrawText(stamp, 20, rect.height-30)

        #Select the Bitmap out of the memory DC by selecting a new
        #uninitialized Bitmap
        memDC.SelectObject(wx.NullBitmap)

        return bmp

    def saveImage(self, bmp, filename, folder, prefix, format='jpg'):
        # convert
        img = bmp.ConvertToImage()

        # save
        if format == 'gif':
            fileName = os.path.join(folder,"%s%s.gif" % (prefix, filename))
            img.SaveFile(fileName, wx.BITMAP_TYPE_GIF)

        elif format == 'png':
            fileName = os.path.join(folder,"%s%s.png" % (prefix, filename))
            img.SaveFile(fileName, wx.BITMAP_TYPE_PNG)

        else:
            fileName = os.path.join(folder,"%s%s.jpg" % (prefix, filename))
            img.SaveFile(fileName, wx.BITMAP_TYPE_JPEG)

    def saveWebcam(self, filename):
        timestamp = self.options['webcamtimestamp']
        folder = self.options['webcamsavefolder']
        prefix = self.options['webcamprefix']
        format = self.options['webcamformat']

        self.takeWebcam(filename, folder, prefix, format, timestamp)

    def takeWebcam(self, filename, folder, prefix, format='jpg', usetimestamp=False):

        if self.cam is None:
            self.debug('takeWebcam called with no camera')
            try:
                self.initCam()
            except:
                return False

        filepath = os.path.join(folder,"%s%s.%s" % (prefix, filename, format))

        if ONWINDOWS:
            if usetimestamp:
                self.cam.saveSnapshot(filepath, quality=80, timestamp=1)
            else:
                self.cam.saveSnapshot(filepath, quality=80, timestamp=0)


        else:
            # JohnColburn says you need to grab a bunch of frames to underflow
            # the buffer to have a time-accurate frame
            camera = self.cam
            cv.GrabFrame(camera)
    ##        cv.GrabFrame(camera)
    ##        cv.GrabFrame(camera)
    ##        cv.GrabFrame(camera)
    ##        cv.GrabFrame(camera)
            im = cv.RetrieveFrame(camera)

            if im is False:
                self.debug('Error - could not get frame from camera')
                return False

            #cv.Flip(im, None, 1)

            # write timestamp as necessary
            if usetimestamp:

                # build timestamp
                stamp = time.strftime(self.TIMESTAMPFORMAT)
                now = time.time()
                micro = str(now - math.floor(now))[0:4]
                stamp = stamp + micro

                # TODO: try to write timestamp out with PIL or something else
                # this *might* be the cause of weird ubuntu errors
                mark = (20, 30)
                font = cv.InitFont(cv.CV_FONT_HERSHEY_COMPLEX, 0.75, 0.75, 0.0, 2, cv.CV_AA)
                cv.PutText(im,stamp,mark,font,cv.RGB(0,0,0))

            self.debug('Saving image to %s' % filepath)
            cv.SaveImage(filepath, im)

        return filepath

    def showWarning(self, title, message):
        dlg = wx.MessageDialog(self, message, title, wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

# buttons!
    def screenshotConfigurePressed(self, event): # wxGlade: chronoFrame.<event_handler>
        dlg = ScreenshotConfigDialog(self)

        # save reference to this
        self.screenshotdialog = dlg

        # set current options in dlg
        dlg.dualmonitorscheck.SetValue(self.options['screenshotdualmonitor'])

        dlg.subsectioncheck.SetValue(self.options['screenshotsubsection'])
        dlg.subsectiontop.SetValue(str(self.options['screenshotsubsectiontop']))
        dlg.subsectionleft.SetValue(str(self.options['screenshotsubsectionleft']))
        dlg.subsectionwidth.SetValue(str(self.options['screenshotsubsectionwidth']))
        dlg.subsectionheight.SetValue(str(self.options['screenshotsubsectionheight']))

        # call this to toggle subsection option enabled/disabled
        dlg.Bind(wx.EVT_CHECKBOX, self.subsectionchecked)
        self.subsectionchecked()

        dlg.timestampcheck.SetValue(self.options['screenshottimestamp'])
        dlg.screenshotprefixtext.SetValue(self.options['screenshotprefix'])
        dlg.screenshotsavefoldertext.SetValue(self.options['screenshotsavefolder'])
        dlg.screenshotformatcombo.SetStringSelection(self.options['screenshotformat'])


        if dlg.ShowModal() == wx.ID_OK:

            # save dialog info
            self.options['screenshotdualmonitor'] = dlg.dualmonitorscheck.IsChecked()

            self.options['screenshotsubsection'] = dlg.subsectioncheck.IsChecked()
            self.options['screenshotsubsectiontop'] = dlg.subsectiontop.GetValue()
            self.options['screenshotsubsectionleft'] = dlg.subsectionleft.GetValue()
            self.options['screenshotsubsectionwidth'] = dlg.subsectionwidth.GetValue()
            self.options['screenshotsubsectionheight'] = dlg.subsectionheight.GetValue()

            self.options['screenshottimestamp'] = dlg.timestampcheck.IsChecked()
            self.options['screenshotprefix'] = dlg.screenshotprefixtext.GetValue()
            self.options['screenshotsavefolder'] = dlg.screenshotsavefoldertext.GetValue()
            self.options['screenshotformat'] = dlg.screenshotformatcombo.GetStringSelection()

            # save to file
            self.saveConfig()

        dlg.Destroy()

    def webcamConfigurePressed(self, event): # wxGlade: chronoFrame.<event_handler>
        dlg = WebcamConfigDialog(self)

        if dlg.hascam:
            # set current options in dlg
            dlg.webcamtimestampcheck.SetValue(self.options['webcamtimestamp'])
            dlg.webcamresolutioncombo.SetStringSelection(self.options['webcamresolution'])
            dlg.webcamprefixtext.SetValue(self.options['webcamprefix'])
            dlg.webcamsavefoldertext.SetValue(self.options['webcamsavefolder'])
            dlg.webcamformatcombo.SetStringSelection(self.options['webcamformat'])

            if dlg.ShowModal() == wx.ID_OK:

                # save dialog info
                self.options['webcamtimestamp'] = dlg.webcamtimestampcheck.IsChecked()
                self.options['webcamresolution'] = dlg.webcamresolutioncombo.GetStringSelection()
                self.options['webcamprefix'] = dlg.webcamprefixtext.GetValue()
                self.options['webcamsavefolder'] = dlg.webcamsavefoldertext.GetValue()
                self.options['webcamformat'] = dlg.webcamformatcombo.GetStringSelection()

                # save to file
                self.saveConfig()

        dlg.Destroy()

    def startCapturePressed(self, event): # wxGlade: chronoFrame.<event_handler>
        text = self.startbutton.GetLabel()

        if text == 'Start Capture':

            # check that screenshot and webcam folders are available
            if self.screenshotcheck.GetValue() and not os.access(self.options['screenshotsavefolder'], os.W_OK):
                self.showWarning('Cannot Write to Screenshot Folder',
                'Error: Cannot write to screenshot folder %s. Please add write permission and try again.'%self.options['screenshotsavefolder'])
                return False

            if self.webcamcheck.GetValue() and not os.access(self.options['webcamsavefolder'], os.W_OK):
                self.showWarning('Cannot Write to Webcam Folder',
                'Error: Cannot write to webcam folder %s. Please add write permission and try again.'%self.options['webcamsavefolder'])
                return False

            # disable  config buttons, frequency, annotate
            self.screenshotcheck.Disable()
            self.screenshotconfigurebutton.Disable()
            self.configurewebcambutton.Disable()
            self.webcamcheck.Disable()
            self.frequencytext.Disable()

            # enable annotate button
            self.annotatebutton.Enable()

            # change start button text to stop capture
            self.startbutton.SetLabel('Stop Capture')

            # if webcam set, initialize webcam - use resolution setting
            if self.webcamcheck.IsChecked():
                # initialize webcam
                self.initCam()

            # start timer
            if float(self.frequencytext.GetValue()) > 0:
                self.startTimer()

        elif text == 'Stop Capture':

            # enable config buttons, frequency
            self.screenshotcheck.Enable()
            self.screenshotconfigurebutton.Enable()
            self.configurewebcambutton.Enable()
            self.webcamcheck.Enable()
            self.frequencytext.Enable()

            # disable annotate
            self.annotatebutton.Disable()

            # change start button text to start capture
            self.startbutton.SetLabel('Start Capture')

            # stop timer
            self.stopTimer()

    def forceCapturePressed(self, event): # wxGlade: chronoFrame.<event_handler>

        # save a capture right now
        filename = self.capture()

        # strip extension
        index = filename.rfind('.') # skip error checking - should never be user-input data
        name = filename[:index]
        ext = filename[index+1:]

        # copy file(s) as many times as in force capture frames box
        captureframes = int(self.forcecaptureframestext.GetValue())
        if captureframes > 1:

            if self.screenshotcheck.GetValue():
                screensource = os.path.join( self.options['screenshotsavefolder'], filename)

            if self.webcamcheck.GetValue():
                websource = os.path.join( self.options['webcamsavefolder'], filename)

            for i in xrange(captureframes-1):
                if self.screenshotcheck.GetValue():
                    shutil.copyfile(screensource, name + str(i+1) + '.' + ext)

                if self.webcamcheck:
                    shutil.copyfile(websource, name + str(i+1) + '.' + ext)

    def addAnnotationPressed(self, event): # wxGlade: chronoFrame.<event_handler>

        folders=[]
        if self.screenshotcheck.GetValue():
            folders.append( self.options['screenshotsavefolder'])
        if self.webcamcheck.GetValue():
            folders.append( self.options['webcamsavefolder'])

        timestamp = time.strftime(self.FILETIMEFORMAT)

        # look for annotation file
        for folder in folders:
            annopath = os.path.join( folder, self.ANNOTATIONFILE)

            if not os.path.exists(annopath):
                annofile = open(annopath, 'wb')
                annotation = {}
            else:
                annofile = open(annopath, 'rb')
                try:
                    annotation = cPickle.load(annofile)
                except:
                    self.showWarning('Annotation file corrupted', 'Annotation file %s seems corrupt and will be replaced' % annopath)
                    annotation = {}

                annofile = open(annopath, 'wb')

            # add annotation to dictionary
            annotation[timestamp] = self.annotatetext.GetValue()

            # save annotation in file
            cPickle.dump(annotation, annofile)
            annofile.close()

        self.annotatetext.SetValue('')

    def annotationSourceBrowsePressed(self, event): # wxGlade: chronoFrame.<event_handler>
        # dir browser
        path = self.dirBrowser('Select folder of images with annotation file present',
                    self.annotatesourcefoldertext.GetValue())

        if path is not '':
            # update path in gui
            self.annotatesourcefoldertext.SetValue(path)

            # check for annotation file -- if not, warn user
            if not os.path.exists( os.path.join(path, self.ANNOTATIONFILE)):

                # pop up warning
                self.showWarning('Annotation file not found',
                'Error: %s was not found in %s. Annotation cannot continue without it' % (self.ANNOTATIONFILE, path))

    def annotationOutputBrowsePressed(self, event): # wxGlade: chronoFrame.<event_handler>
        path = self.dirBrowser('Select folder to write annotated images to',
                    self.annotateoutputfoldertext.GetValue())

        if path != '':
            self.annotateoutputfoldertext.SetValue(path)

            # create folder if necessary
            if not os.path.exists( path):
                os.makedirs(path)

            # check for write permission - if not, alert user
            if not os.access(path, os.W_OK):
                    self.showWarning('No write permission',
                    'Error: Cannot write to %s. Please set write permissions and try again' % path)

    def resizeSourceBrowsePressed(self, event): # wxGlade: chronoFrame.<event_handler>
        path = self.dirBrowser('Select folder of images to resize',
                    self.resizesourcetext.GetValue())

        if path != '':
            self.resizesourcetext.SetValue(path)

    def resizeOutputBrowsePressed(self, event): # wxGlade: chronoFrame.<event_handler>
        path = self.dirBrowser('Select folder to write resized images to',
                    self.resizeoutputtext.GetValue())

        if path != '':
            self.resizeoutputtext.SetValue(path)

            # create folder if necessary
            if not os.path.exists( path):
                os.makedirs(path)

            # check for write permission - if not, alert user
            if not os.access(path, os.W_OK):
                    self.showWarning('No write permission',
                    'Error: Cannot write to %s. Please set write permissions and try again' % path)

    def resizePressed(self, event): # wxGlade: chronoFrame.<event_handler>

        # check source dir
        if not os.path.isdir(self.resizesourcetext.GetValue()):
            self.showWarning('Invalid Path', 'The source path is invalid')
            return False

        # check output dir
        if not os.path.isdir(self.resizeoutputtext.GetValue()):
            self.showWarning('Invalid Path', 'The output path is invalid')
            return False

        # check write permission
        if not os.access(self.resizeoutputtext.GetValue(), os.W_OK):
            self.showWarning('No write permission',
            'Error: Cannot write to %s. Please set write permissions and try again' % self.resizeoutputtext.GetValue())
            return False

        # check size
        try:
            width = int(self.resizewidthtext.GetValue())

            if width <= 0:
                raise Exception()
        except:
            self.showWarning('Invalid Width',
            'Error: Width is invalid. Must be a positive integer')
            return False

        try:
            height = int(self.resizeheighttext.GetValue())

            if height <= 0:
                raise Exception()
        except:
            self.showWarning('Invalid Height',
            'Error: Height is invalid. Must be a positive integer')
            return False

        # check for images
        images = os.listdir(self.resizesourcetext.GetValue())
        if len(images) == 0:
            self.showWarning('No files found',
            'No files found in source directory')
            return False

        # show progress dialog
        progressdialog = wx.ProgressDialog('Resize Progress', 'Processing Images',
                        maximum=len(images), parent=self, style= wx.PD_CAN_ABORT | wx.PD_APP_MODAL | wx.PD_ELAPSED_TIME | wx.PD_REMAINING_TIME)

        # for all images in main folder
        count = 0
        for f in images:

            # update progress dialog
            count += 1
            cancel, somethingelse = progressdialog.Update(count, 'Processing %s'%f)
            # update progress dialog
            if not cancel:
                progressdialog.Destroy()
                break

            try:
                # open with PIL -- will skip non-images
                source = Image.open(os.path.join(self.resizesourcetext.GetValue(), f))

                # resize image
                source.thumbnail((width, height))

                # save image
                source.save(os.path.join(self.resizeoutputtext.GetValue(), f))

            except Exception, e:
                pass
                #self.debug(str(e))

        progressdialog.Update( len(images), 'Resizing Complete')


    def rotatePressed(self, event): # wxGlade: chronoFrame.<event_handler>

        # check source dir
        if not os.path.isdir(self.resizesourcetext.GetValue()):
            self.showWarning('Invalid Path', 'The source path is invalid')
            return False

        # check output dir
        if not os.path.isdir(self.resizeoutputtext.GetValue()):
            self.showWarning('Invalid Path', 'The output path is invalid')
            return False

        # check write permission
        if not os.access(self.resizeoutputtext.GetValue(), os.W_OK):
            self.showWarning('No write permission',
            'Error: Cannot write to %s. Please set write permissions and try again' % self.resizeoutputtext.GetValue())
            return False

        try:
            rot = int(self.rotatecombo.GetValue())

            if rot < 0 or rot > 360:
                raise Exception()
            self.debug('Setting rotation: %d' % rot)
        except:
            self.showWarning('Invalid Rotation',
            'Error: Rotation is invalid. Must be a positive integer less than 360')
            return False

        # check for images
        images = os.listdir(self.resizesourcetext.GetValue())
        if len(images) == 0:
            self.showWarning('No files found',
            'No files found in source directory')
            return False

        # show progress dialog
        progressdialog = wx.ProgressDialog('Resize Progress', 'Processing Images',
                        maximum=len(images), parent=self, style= wx.PD_CAN_ABORT | wx.PD_APP_MODAL | wx.PD_ELAPSED_TIME | wx.PD_REMAINING_TIME)

        # for all images in main folder
        count = 0
        for f in images:

            # update progress dialog
            count += 1
            cancel, somethingelse = progressdialog.Update(count, 'Processing %s'%f)
            # update progress dialog
            if not cancel:
                progressdialog.Destroy()
                break

            try:
                # open with PIL -- will skip non-images
                source = Image.open(os.path.join(self.resizesourcetext.GetValue(), f))

                # rotate image
                if rot > 0:
                    rotated = source.rotate(rot, expand=True)

                # save image
                rotated.save(os.path.join(self.resizeoutputtext.GetValue(), f))

            except Exception, e:
                pass

        progressdialog.Update( len(images), 'Rotating Complete')

    def fontSelectPressed(self, event): # wxGlade: chronoFrame.<event_handler>
        data = wx.FontData()
        data.EnableEffects(True)
        data.SetColour(self.options['fontdata'].GetColour())
        if self.options['font']:
            data.SetInitialFont(self.options['font'])

        dlg = wx.FontDialog(self, data)

        if dlg.ShowModal() == wx.ID_OK:
            data = dlg.GetFontData()
            font = data.GetChosenFont()
            colour = data.GetColour()

            self.options['font'] = font
            self.options['fontdata'] = data

            self.fontexampletext.SetValue('Font: %s %d pt' % (font.GetFaceName(), font.GetPointSize()))
            self.fontexampletext.SetFont(font)
            self.fontexampletext.SetForegroundColour(colour)

            # save selections
            self.saveConfig()

        dlg.Destroy()

    def viewAnnotationContentPressed(self, event):

        annofolder = self.annotatesourcefoldertext.GetValue()

        if not os.path.isdir(annofolder):
            self.showWarning('Source folder invalid', 'The source folder is invalid')
            return False

        # check for annotation file
        if not os.path.exists( os.path.join(self.annotatesourcefoldertext.GetValue(), self.ANNOTATIONFILE)):
            self.showWarning('Annotation file not found', 'Annotation file not found in folder.')
            return False

        # parse annotation file
        annofile = open(os.path.join(annofolder, self.ANNOTATIONFILE), 'rb')
        try:
            annotation = cPickle.load(annofile)
        except:
            self.showWarning('Annotation Corrupted','Annotation file appears corrupted. Cannot continue.')
            return False

        # get list of annotation times
        times = annotation.keys()

        if len(times) == 0:
            self.showWarning('Annotation Has No Entries','Annotation file has no entries.')
            return False

        # sort times
        times.sort()

        dlg = annotationContentsDialog(self)
        for time in times:
            anno = annotation[time]
            dlg.annotationtext.AppendText("%s - %s\n" % (time, anno))

        dlg.ShowModal()
        dlg.Destroy()

    def createAnnotationPressed(self, event): # wxGlade: chronoFrame.<event_handler>

        # check that paths are valid
        annofolder = self.annotatesourcefoldertext.GetValue()
        annodestfolder = self.annotateoutputfoldertext.GetValue()

        if not os.path.isdir(annofolder):
            self.showWarning('Source folder invalid', 'The source folder is invalid')
            return False

        # check for annotation file
        if not os.path.exists( os.path.join(self.annotatesourcefoldertext.GetValue(), self.ANNOTATIONFILE)):
            self.showWarning('Annotation file not found', 'Annotation file not found in folder.')
            return False

        # check that destination folder exists and is writable
        if not os.access( annodestfolder, os.W_OK):
            self.showWarning('Permission Denied', 'The output folder %s is not writable. Please change the permissions and try again.'%annodestfolder)
            return False

        # parse annotation file
        annofile = open(os.path.join(annofolder, self.ANNOTATIONFILE), 'rb')
        try:
            annotation = cPickle.load(annofile)
        except:
            self.showWarning('Annotation Corrupted','Annotation file appears corrupted. Cannot continue.')
            return False

        # get list of annotation times
        times = annotation.keys()

        if len(times) == 0:
            self.showWarning('Annotation Has No Entries','Annotation file has no entries.')
            return False

        # get number of images
        numimages = len(os.listdir(annofolder))
        self.debug('Preparing to apply annotation to %d images' % numimages, self.VERBOSE)

        # make a list of sorted timestamps
        times.sort()
        annotime = time.mktime(time.strptime(times[0], self.FILETIMEFORMAT))

        # for files in source
        sourcefiles = os.listdir(annofolder)

        # sort by mtime
        sourcefiles.sort( lambda x,y: int(os.path.getmtime(os.path.join(annofolder,x))-os.path.getmtime(os.path.join(annofolder,y))))

        progressdialog = wx.ProgressDialog('Annotation Progress', 'Processing annotation data',
                        maximum=numimages, parent=self, style= wx.PD_CAN_ABORT | wx.PD_APP_MODAL | wx.PD_ELAPSED_TIME | wx.PD_REMAINING_TIME)

        # if timed
        if self.annotatetimedradio.GetValue():

            # get duration
            if self.annotatedurationtext.GetValue() != '':
                duration = float(self.annotatedurationtext.GetValue())
            else:
                duration = 5.0

            # adjust duration by framerate to get timestamp duration
            framerate = self.videoframeratetext.GetValue()
            if framerate == '':
                framerate = 25
            else:
                framerate = int(framerate)

            # guess at duration by comparing 2 creation times
            f1 = None
            f2 = None
            index = 0
            while f1 is None and f2 is None and index < len(sourcefiles):
                try:
                    Image.open(os.path.join(annofolder, sourcefiles[index]))
                    Image.open(os.path.join(annofolder, sourcefiles[index+1]))

                    f1 = os.path.join(annofolder, sourcefiles[index])
                    f2 = os.path.join(annofolder, sourcefiles[index+1])
                except Exception, e:
                    index += 1

            # couldnt compare
            if f1 is None or f2 is None:
                dlg = wx.MessageDialog(self,"Failed to estimate timelapse frequency for source files by comparing consecutive file creation times. Continue with default (and probably wrong) 1 minute guess?",
                            'Annotation Warning', wx.YES_NO)
                result = dlg.ShowModal()
                if result == wx.ID_NO:
                    dlg.Destroy()
                    progressdialog.Destroy()
                    return
                else:
                    timelapseinterval = 60.0
                    dlg.Destroy()
            else:
                timelapseinterval = round(os.path.getmtime(f2) - os.path.getmtime(f1))

            # calculate new duration
            duration = duration * timelapseinterval * framerate
            self.debug('Annotation duration = %s (duration in seconds) * %d (timelapse interval) * %d (framerate) = %d' % (self.annotatedurationtext.GetValue(),timelapseinterval, framerate, duration))

            if self.annotatefadeoutcheck.GetValue():
                fadetimeout = duration/3.0
            else:
                fadetimeout = 0.0

            if self.annotatefadeincheck.GetValue():
                fadetimein = duration/3.0
            else:
                fadetimein = 0.0

            count = 0
            for f in sourcefiles:

                count += 1

                sourcefile = os.path.join(annofolder, f)
                # test if image
                try:
                    Image.open( sourcefile)
                except:
                    self.debug('Skipping %s - not an image file'%sourcefile)
                    continue

                cancel, somethingelse = progressdialog.Update(count, 'Processing %s'%f)
                self.debug('Processing %s'%f)
                # update progress dialog
                if not cancel:
                    self.debug('Annotation Cancelled by User')
                    progressdialog.Destroy()
                    break

                # get creation time
                creationtime = os.path.getctime(sourcefile)

                # if creation time is before, skip it
                if creationtime < annotime:
                    shutil.copyfile(sourcefile, os.path.join(annodestfolder, f))
                    continue

                # if same time or within the time limit
                elif creationtime <= annotime + duration:
                    elapsed = creationtime - annotime

                    # fade in
                    if elapsed < fadetimein:
                        opacity = elapsed / fadetimein

                    # full opacity
                    elif elapsed < duration - fadetimeout:
                        opacity = 1.0

                    # fade out
                    elif elapsed < duration:
                        opacity = (duration - elapsed) / fadetimeout

                    # create annotated file
                    self.applyAnnotation(f, annofolder, annodestfolder, annotation[times[0]],
                        self.options['font'], self.options['fontdata'], opacity, self.annotatepositioncombo.GetStringSelection() )

                # after annotation time
                else:
                    # copy file
                    shutil.copyfile(sourcefile, os.path.join(annodestfolder, f))

                    # move to next annotation time
                    if len(times) > 1:
                        times = times[1:]
                        annotime = time.mktime(time.strptime(times[0], self.FILETIMEFORMAT))

                        # get next applicable time
                        while len(times) > 1 and creationtime > time.mktime(time.strptime(times[1], self.FILETIMEFORMAT)):
                            times = times[1:]
                            annotime = time.mktime(time.strptime(times[0], self.FILETIMEFORMAT))

        else:   # constant annotation
            count = 0
            for f in sourcefiles:
                count += 1

                sourcefile = os.path.join(annofolder, f)
                # test if image
                try:
                    Image.open( sourcefile)
                except:
                    print self.debug('Skipped %s - not an image file'%sourcefile)
                    continue

                cancel, somethingelse = progressdialog.Update(count, 'Processing %s'%f)
                # update progress dialog
                if not cancel:
                    progressdialog.Destroy()
                    break

                # get creation time
                creationtime = os.path.getctime(sourcefile)

                # if creation time is before, skip it
                if creationtime < annotime:
                    shutil.copyfile(sourcefile, os.path.join(annodestfolder, f))
                    continue

                # make sure we aren't early
                while len(times) > 1 and creationtime > time.mktime(time.strptime(times[1], self.FILETIMEFORMAT)):
                    times = times[1:]
                    annotime = time.mktime(time.strptime(times[0], self.FILETIMEFORMAT))

                # create annotated file
                self.applyAnnotation(f, annofolder, annodestfolder, annotation[times[0]],
                        self.options['font'], self.options['fontdata'], 1.0, self.annotatepositioncombo.GetStringSelection() )

        # close dialog
        progressdialog.Update(count, 'Annotation Complete')
        progressdialog.Destroy()

        self.debug('Annotation Complete', self.VERBOSE)

    def applyAnnotation( self, filename, sourcefolder, destfolder, text, font, fontdata, opacity, position):
        self.debug('Applying annotation: file: %s  text: %s opacity: %s' % (filename, text, opacity))

        sourcefile = os.path.join(sourcefolder, filename)
        fontcolor = fontdata.GetColour()

        # apply text with opacity
        bmp = wx.Bitmap(sourcefile)

        #Create a memory DC so we can draw on it
        memDC = wx.MemoryDC()

        #Tell the memory DC to use our Bitmap
        memDC.SelectObject(bmp)

        # get image size
        width, height = bmp.GetWidth(), bmp.GetHeight()

        # get text size
        fontwidth, fontheight, somethingelse = memDC.GetMultiLineTextExtent(text, font)

        # TODO: wrap

        # decide on placement
        if position == 'Top':
            x = (width-fontwidth)/2
            y = 40
        else:
            x = (width-fontwidth)/2
            y = height - fontheight - 40

        # set font
        memDC.SetFont(font)

        # save colors
        red = fontcolor.Red()
        green = fontcolor.Green()
        blue = fontcolor.Blue()

        # write drop shadow if selected
        if self.dropshadowcheck.IsChecked():
            # set opacity and color
            fontcolor.Set( 0,0,0, int(255*opacity))
            memDC.SetTextForeground(fontcolor)
            memDC.DrawText(text, x+2, y+2)

        # set opacity and color
        fontcolor.Set( red, green, blue, int(255*opacity))
        memDC.SetTextForeground(fontcolor)

        # write annotation on image
        memDC.DrawText(text, x, y)

        # save image
        img = bmp.ConvertToImage()

        # find image type by extension
        index = filename.rfind('.')
        if index == -1:
            ext = 'jpg'
        else:
            ext = filename[index+1:]

        filename = os.path.join(destfolder, filename)
        if ext == 'gif':
            img.SaveFile(filename, wx.BITMAP_TYPE_GIF)

        elif ext == 'png':
            filename = os.path.join(destfolder, filename)
            img.SaveFile(filename, wx.BITMAP_TYPE_PNG)

        else:
            filename = os.path.join(destfolder, filename)
            img.SaveFile(filename, wx.BITMAP_TYPE_JPEG)

        self.debug('Wrote annotated image to %s'%filename, self.DEBUG)

    def pipMainImageBrowsePressed(self, event): # wxGlade: chronoFrame.<event_handler>
        path = self.dirBrowser('Select folder containing main images',
                    self.pipmainimagefoldertext.GetValue())

        if path != '':
            self.options['pipmainfolder'] = path
            self.pipmainimagefoldertext.SetValue(path)

            self.saveConfig()

    def pipPipImageBrowsePressed(self, event): # wxGlade: chronoFrame.<event_handler>
        path = self.dirBrowser('Select folder containing PIP images',
                    self.pippipimagefoldertext.GetValue())

        if path != '':
            self.options['pippipfolder'] = path
            self.pippipimagefoldertext.SetValue(path)

            self.saveConfig()

    def pipOutputBrowsePressed(self, event): # wxGlade: chronoFrame.<event_handler>
        path = self.dirBrowser('Select save folder for PIP images',
                    self.pipoutputimagefoldertext.GetValue())

        if path != '':
            self.options['pipoutfolder'] = path
            self.pipoutputimagefoldertext.SetValue(path)

            if not os.access( path, os.W_OK):
                self.showWarning("Permission Error",
                    'Error: the PIP output path %s is not writable. Please set write permissions and try again.'%path)

            self.saveConfig()

    def createPipPressed(self, event): # wxGlade: chronoFrame.<event_handler>

        # make sure output file is writable
        if not os.access( self.pipoutputimagefoldertext.GetValue(), os.W_OK):
            self.showWarning('Permission Error','Error: Output file is not writable. Please adjust your permissions and try again.')
            return False

        # get pip settings
        sourcefolder = self.pipmainimagefoldertext.GetValue()
        pipfolder = self.pippipimagefoldertext.GetValue()
        outfolder = self.pipoutputimagefoldertext.GetValue()

        # pip size and position
        pipsizestring = self.pipsizecombo.GetStringSelection()
        pippositionstring = self.pippositioncombo.GetStringSelection()

        # sort files - match up by sorting so prefixes work
        sourcefiles = os.listdir(sourcefolder)
        sourcefiles.sort()
        pipfiles = os.listdir(pipfolder)
        pipfiles.sort()

        self.debug('Creating PIP')

        # progress dialog
        progressdialog = wx.ProgressDialog('PIP Progress', 'Processing Images',
                        maximum=len(sourcefiles), parent=self, style= wx.PD_CAN_ABORT | wx.PD_APP_MODAL | wx.PD_ELAPSED_TIME | wx.PD_REMAINING_TIME)

        # for all images in main folder
        count = 0
        for i in xrange( min(len(sourcefiles), len(pipfiles))):
            sourcefile = sourcefiles[i]
            pipfile = pipfiles[i]

            # update progress dialog
            count += 1
            cancel, somethingelse = progressdialog.Update(count, 'Processing %s'%sourcefile)
            # update progress dialog
            if not cancel:
                progressdialog.Destroy()
                break

            try:
                # open with PIL -- will skip non-images
                source = Image.open(os.path.join(sourcefolder, sourcefile))
                pip = Image.open(os.path.join(pipfolder, pipfile))

                # get pip size - sides
                if pippositionstring == 'Left' or pippositionstring == 'Right':
                    if pipsizestring == 'Small':
                        pipsize = ( source.size[0] / 4, source.size[1])
                    elif pipsizestring == 'Medium':
                        pipsize = ( source.size[0] / 3, source.size[1])
                    else:
                        pipsize = ( source.size[0] / 2, source.size[1])

                # get pip size - top/bottom
                elif pippositionstring == 'Top' or pippositionstring == 'Bottom':
                    if pipsizestring == 'Small':
                        pipsize = ( source.size[0], source.size[1] / 4)
                    elif pipsizestring == 'Medium':
                        pipsize = ( source.size[0], source.size[1] / 3)
                    else:
                        pipsize = ( source.size[0], source.size[1] / 2)

                # get pip size - corners
                else:
                    if pipsizestring == 'Small':
                        pipsize = ( source.size[0] / 4, source.size[1] / 4)
                    elif pipsizestring == 'Medium':
                        pipsize = ( source.size[0] / 3, source.size[1] / 3)
                    else:
                        pipsize = ( source.size[0] / 2, source.size[1] / 2)

                # resize pip
                pip.thumbnail(pipsize)

                # paste on main - left
                if pippositionstring == 'Left':
                    source.paste(pip, (0,0))

                # paste on main - Right
                elif pippositionstring == 'Right':
                    source.paste(pip, ( source.size[0]-pip.size[0], 0))

                # paste on main - top
                elif pippositionstring == 'Top':
                    source.paste(pip, (0,0))

                # paste on main - bottom
                elif pippositionstring == 'Bottom':
                    source.paste(pip, (0, source.size[1]-pip.size[1]))

                # paste on main - top right
                elif pippositionstring == 'Top-Right':
                    source.paste(pip, ( source.size[0]-pip.size[0], 0))

                # paste on main - bottom right
                elif pippositionstring == 'Bottom-Right':
                    source.paste(pip, ( source.size[0]-pip.size[0], source.size[1]-pip.size[1]))

                # paste on main - bottom left
                elif pippositionstring == 'Bottom-Left':
                    source.paste(pip, (0, source.size[1]-pip.size[1]))

                # paste on main - top left
                elif pippositionstring == 'Top-Left':
                    source.paste(pip, (0, 0))

                # save in destination
                outpath = os.path.join( outfolder, sourcefiles[i])
                source.save( outpath)

                # modify creation time to match source file
                ctime = os.path.getctime(os.path.join(sourcefolder, sourcefile))
                os.utime(outpath, (ctime, ctime))

            except Exception, e:
                pass
                #print e

        # copy source annotation file if found
        if os.path.isfile( os.path.join(sourcefolder, self.ANNOTATIONFILE)):
            shutil.copy(os.path.join(sourcefolder, self.ANNOTATIONFILE), os.path.join(outfolder, self.ANNOTATIONFILE))

        progressdialog.Destroy()

    def videoSourceBrowsePressed(self, event): # wxGlade: chronoFrame.<event_handler>
        path = self.dirBrowser('Select folder containing source images',
                    self.videosourcetext.GetValue())

        if path != '':
            self.options['videosourcefolder'] = path
            self.videosourcetext.SetValue(path)

            self.saveConfig()

    def videoDestinationBrowsePressed(self, event): # wxGlade: chronoFrame.<event_handler>
        path = self.dirBrowser('Select save folder for video ',
                    self.videodestinationtext.GetValue())

        if path != '':
            self.options['videooutputfolder'] = path
            self.videodestinationtext.SetValue(path)

            if not os.access( path, os.W_OK):
                self.showWarning("Permission Error",
                    'Error: the video output path %s is not writable. Please set write permissions and try again.'%path)

            self.saveConfig()

    def videoRecalculatePressed(self, event): # wxGlade: chronoFrame.<event_handler>
        sourcepath = self.videosourcetext.GetValue()

        # get number of files in source dir
        numfiles = 0
        for f in os.listdir(sourcepath):
            if os.path.isfile(os.path.join(sourcepath,f)):
                numfiles += 1

        # framerate
        framerate = int(self.videoframeratetext.GetValue())
        if numfiles == 0 or framerate == 0:
            self.movielengthlabel.SetLabel("Estimated Movie Length: 0 m 0 s")
            return

        # divide by frames/second to get seconds
        seconds = numfiles/framerate

        minutes = seconds//60
        seconds = seconds%60

        # change label
        self.movielengthlabel.SetLabel("Estimated Movie Length: %d m %d s" % (minutes, seconds))

    def mencoderPathBrowsePressed(self, event): # wxGlade: chronoFrame.<event_handler>
        # file browser
        dlg = wx.FileDialog(self, 'Select MEncoder Executable', self.CHRONOLAPSEPATH)
        result = dlg.ShowModal()
        if result == wx.ID_OK:
            path = dlg.GetPath()
            self.mencoderpathtext.SetValue(path)
        dlg.Destroy()

    def createVideoPressed(self, event): # wxGlade: chronoFrame.<event_handler>

        # check that paths are valid
        sourcefolder = self.videosourcetext.GetValue()
        destfolder = self.videodestinationtext.GetValue()

        if not os.path.isdir(sourcefolder):
            self.showWarning('Source folder invalid', 'The source folder is invalid')
            return False

        # check that destination folder exists and is writable
        if not os.access( destfolder, os.W_OK):
            self.showWarning('Permission Denied', 'The output folder %s is not writable. Please change the permissions and try again.'%destfolder)
            return False

        # check mencoder path
        mencoderpath = self.mencoderpathtext.GetValue()
        if mencoderpath == 'mencoder':
            self.showWarning('MEncoder path not set', 'Chronolapse uses MEncoder to process video. Either point to MEncoder directly or ensure it is on your path.')

        elif not os.path.isfile(mencoderpath):
            # look for mencoder
            if not os.path.isfile( os.path.join(self.CHRONOLAPSEPATH, 'mencoder')):
                self.showWarning('MEncoder Not Found', 'Chronolapse uses MEncoder to process video, but could not find mencoder')
                return False
            elif ONWINDOWS:
                mencoderpath = os.path.join(self.CHRONOLAPSEPATH, 'mencoder')

        fps = self.videoframeratetext.GetValue()
        try:
            fps = int(fps)
        except:
            self.showWarning('Frame Rate Invalid', 'The frame rate setting is invalid. Frame rate must be a positive integer')
            return False


        # get dimensions of first image file
        found = False
        count = 0
        sourcefiles = os.listdir(sourcefolder)
        while not found and count < len(sourcefiles):
            count += 1
            try:
                imagepath = os.path.join(sourcefolder, sourcefiles[count])
                img = Image.open(imagepath)
                found = True
                width, height = img.size

                imagepath = imagepath.lower()
                if imagepath.endswith(('.gif')):
                    imagetype = 'gif'
                    path = '*.gif'
                elif imagepath.endswith('.png'):
                    imagetype = 'png'
                    path = '*.png'
                else:
                    imagetype = 'jpg'

                    index = imagepath.rfind('.')
                    if index > 0:
                        path = '*.%s'%imagepath[index+1:]
                    else:
                        path = '*.jpg'

                #path = os.path.join(sourcefolder, path)

            except:
                pass

        if not found:
            self.showWarning('No Images Found', 'No images were found in the source folder %s'%sourcefolder)
            return False

        # get video type from select box
        #format = '-of %s' % self.videoformatcombo.GetStringSelection()

        # get codec from select box
        codec = self.videocodeccombo.GetStringSelection()

        # get output file name  ---  create in source folder then move bc of ANOTHER mencoder bug
        timestamp = time.strftime('%Y-%m-%d_%H-%M-%S')
        outextension = 'avi'

        if (os.path.isfile(os.path.join(destfolder, 'timelapse_%s.%s' % (timestamp, outextension)))
               or os.path.isfile( os.path.join(sourcefolder, 'timelapse_%s.%s' % (timestamp, outextension)))):

            count = 2
            while(os.path.isfile(os.path.join(destfolder, 'timelapse_%s_%d.%s' % (timestamp, count, outextension)))
               or os.path.isfile( os.path.join(sourcefolder, 'timelapse_%s_%d.%s' % (timestamp, count, outextension)))):
                count += 1

            outfile = 'timelapse_%s_%d.%s' % (timestamp, count, outextension)

        else:
            outfile = 'timelapse_%s.%s' % (timestamp, outextension)

        # change cwd to image folder to stop mencoder bug
        try:
            os.chdir(sourcefolder)
        except Exception, e:
            self.showWarning('CWD Error', "Could not change current directory. %s" % str(e))
            return False

        # create progress dialog
        progressdialog = wx.ProgressDialog('Encoding Progress', 'Encoding - Please Wait')
        progressdialog.Pulse('Encoding - Please Wait')

        # run mencoder with options from GUI
##         mf://%s -mf w=%d:h=%d:fps=%s:type=%s -ovc lavc -lavcopts vcodec=%s:mbd=2:trell %s -oac copy -o %s' % (
##        path, width, height, fps, imagetype, codec, format, outfile ))
        # http://web.njit.edu/all_topics/Prog_Lang_Docs/html/mplayer/encoding.html

##        if codec == 'uncompressed':
##            command = '"%s" mf://%s -mf fps=%s -ovc rawrgb -o %s' % (
##                    mencoderpath, path, fps, outfile )
##            command = '"%s" mf://fps=%s:type=png  -ovc rawrgb -o %s \*.png' % (mencoderpath, fps, outfile)
##        else:
        command = '"%s" mf://%s -mf fps=%s-ovc lavc -lavcopts vcodec=%s -o %s' % (
                    mencoderpath, path, fps, codec, outfile )

        self.debug("Calling: %s"%command)

        self.returncode = None
        self.mencodererror = 'Unknown'
        mencoderthread = threading.Thread(None, self.runMencoderInThread, 'mencoderthread', (command,))
        mencoderthread.start()

        while self.returncode is None:
            time.sleep(.5)
            progressdialog.Pulse()

        # mencoder error
        if self.returncode > 0:
            progressdialog.Destroy()

            self.showWarning('MEncoder Error', "Error while encoding video. Check the MEncoder console or try a different codec")
            return

        # move video file to destination folder
        self.debug("Moving file from %s to %s" % (os.path.join(sourcefolder,outfile), os.path.join(destfolder, outfile)))
        shutil.move(os.path.join(sourcefolder,outfile), os.path.join(destfolder, outfile))

        progressdialog.Destroy()

        dlg = wx.MessageDialog(self, 'Encoding Complete!\nFile saved as %s'%os.path.join(destfolder, outfile), 'Encoding Complete', style=wx.OK)
        dlg.ShowModal()
        dlg.Destroy()

    def runMencoderInThread(self, command):
        #proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE)

        self.debug('Running mencoder in thread')
        #proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  #      mencoder mf://*.jpg -mf w=800:h=600:fps=25:type=jpg -ovc lavc -lavcopts vcodec=mpeg4:mbd=2:trell -oac copy -o output.avi

        try:
            if ONWINDOWS:
                proc = subprocess.Popen(command, close_fds=True)
            else:
                proc = subprocess.Popen(command, close_fds=True, shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE)

            stdout, stderr = proc.communicate()
            self.mencodererror = stderr
            self.returncode = proc.returncode
        except Exception, e:
            self.mencodererror = repr(e)
            self.returncode = 1

    def audioSourceVideoBrowsePressed(self, event): # wxGlade: chronoFrame.<event_handler>
        path = self.fileBrowser('Select video source',
                    self.audiosourcevideotext.GetValue())

        if path != '':
            self.options['audiosourcevideo'] = path
            self.audiosourcevideotext.SetValue(path)

            self.saveConfig()

    def audioSourceBrowsePressed(self, event): # wxGlade: chronoFrame.<event_handler>
        path = self.fileBrowser('Select audio source',
                    self.audiosourcetext.GetValue())

        if path != '':
            self.options['audiosource'] = path
            self.audiosourcetext.SetValue(path)

            if not os.access( path, os.W_OK):
                self.showWarning("Permission Error",
                    'Error: the video output path %s is not writable. Please set write permissions and try again.'%path)

            self.saveConfig()

    def audioOutputFolderBrowsePressed(self, event): # wxGlade: chronoFrame.<event_handler>
        path = self.dirBrowser('Select save folder for new video ',
                    self.audiooutputfoldertext.GetValue())

        if path != '':
            self.options['audiooutputfolder'] = path
            self.audiooutputfoldertext.SetValue(path)

            if not os.access( path, os.W_OK):
                self.showWarning("Permission Error",
                    'Error: the video output path %s is not writable. Please set write permissions and try again.'%path)

            self.saveConfig()

    def createAudioPressed(self, event): # wxGlade: chronoFrame.<event_handler>

        # check that paths are valid
        videosource = self.audiosourcevideotext.GetValue()
        videofolder = os.path.dirname(videosource)
        videobase = os.path.basename(videosource)
        audiosource = self.audiosourcetext.GetValue()
        destfolder = self.audiooutputfoldertext.GetValue()

        if not os.path.isfile(videosource):
            self.showWarning('Video path invalid', 'The source video path appears is invalid')
            return False

        if not os.path.isfile(audiosource):
            self.showWarning('Audio path invalid', 'The source audio path appears is invalid')
            return False

        # check that destination folder exists and is writable
        if not os.access( destfolder, os.W_OK):
            self.showWarning('Permission Denied', 'The output folder %s is not writable. Please change the permissions and try again.'%destfolder)
            return False

        # check mencoder path
        mencoderpath = self.mencoderpathtext.GetValue()
        if not os.path.isfile(mencoderpath):
            # look for mencoder
            if not os.path.isfile( os.path.join(self.CHRONOLAPSEPATH, 'mencoder')):
                self.showWarning('MEncoder Not Found', 'Chronolapse uses MEncoder to process video, but could not find mencoder')
                return False
            else:
                mencoderpath = os.path.join(self.CHRONOLAPSEPATH, 'mencoder')

        # make sure video name has no spaces
        if videobase.find(' ') != -1:

            try:
                # copy audio to video source folder
                self.debug('Creating temporary file for video')
                handle, safevideoname = tempfile.mkstemp('_deleteme' + os.path.splitext(videobase)[1], 'chrono_', videofolder)
                os.close(handle)
                self.debug('Copying video file to %s' % safevideoname)
                shutil.copy(videosource, safevideoname)
            except Exception, e:
                self.showWarning('Temp Audio Error', "Exception while copying audio to video folder: %s" % repr(e))
        else:
            # no spaces, use this
            safevideoname = videobase

        # get output file name  ---  create in source folder then move bc of ANOTHER mencoder bug
        outfile = "%s-audio%s"%(os.path.splitext(safevideoname)[0], os.path.splitext(safevideoname)[1])
        if os.path.isfile(os.path.join(destfolder, outfile)):
            count = 2
            while os.path.isfile(os.path.join(destfolder, "%s-audio%d%s"%(os.path.splitext(safevideoname)[0], count,os.path.splitext(safevideoname)[1]))):
                count += 1
            outfile = "%s-audio%d%s"%(os.path.splitext(safevideoname)[0], count,os.path.splitext(safevideoname)[1])

        # change cwd to video folder to stop mencoder bug
        try:
            self.debug('Changing directory to %s' % videofolder)
            os.chdir( videofolder)
        except Exception, e:
            self.showWarning('CWD Error', "Could not change current directory. %s" % repr(e))

            # delete temp video file
            if safevideoname != videobase:
                try:
                    os.remove(safevideoname)
                except:
                    pass

            return False

        newaudiopath = ''
        try:
            # copy audio to video source folder
            self.debug('Creating temporary file for audio')
            handle, newaudiopath = tempfile.mkstemp('_deleteme' + os.path.splitext(audiosource)[1], 'chrono_', videofolder)
            os.close(handle)
            self.debug('Copying audio file to %s' % newaudiopath)
            shutil.copy(audiosource, newaudiopath)
        except Exception, e:
            self.showWarning('Temp Audio Error', "Exception while copying audio to video folder: %s" % repr(e))

        # create progress dialog
        progressdialog = wx.ProgressDialog('Dubbing Progress', 'Dubbing - Please Wait')
        progressdialog.Pulse('Dubbing - Please Wait')

        # mencoder -ovc copy -audiofile silent.mp3 -oac copy input.avi -o output.avi
        command = '"%s" -ovc copy -audiofile %s -oac copy %s -o %s' % (
        mencoderpath, os.path.basename(newaudiopath), safevideoname, outfile )

        self.debug("Calling: %s"%command)
        #proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE)

        proc = subprocess.Popen(command, close_fds=True)

        stdout, stderr = proc.communicate()
        returncode = proc.returncode

        # mencoder error
        if returncode > 0:
            progressdialog.Destroy()
            self.showWarning('MEncoder Error', stderr)

            # delete temporary audio file
            if newaudiopath != '':
                try:
                    os.remove(newaudiopath)
                except Exception, e:
                    self.debug('Exception while deleting temp audio file %s: %s' % (newaudiopath, repr(e)))

            # delete temp video file
            if safevideoname != videobase:
                try:
                    os.remove(safevideoname)
                except:
                    pass

            return

        # move video file to destination folder
        if videofolder != destfolder:
            self.debug("Moving file from %s to %s" % (os.path.join(videodir,outfile), os.path.join(destfolder, outfile)))
            shutil.move(os.path.join(os.path.dirname(videosource),outfile), os.path.join(destfolder, outfile))

        progressdialog.Destroy()

        # delete temporary audio file
        if newaudiopath != '':
            try:
                os.remove(newaudiopath)
            except Exception, e:
                self.debug('Exception while deleting temp audio file %s: %s' % (newaudiopath, repr(e)))

        # delete temp video file
        if safevideoname != videobase:
            try:
                os.remove(safevideoname)
            except:
                pass

        dlg = wx.MessageDialog(self, 'Dubbing Complete!\nFile saved as %s'%os.path.join(destfolder, outfile), 'Dubbing Complete', style=wx.OK)
        dlg.ShowModal()
        dlg.Destroy()

    def instructionsMenuClicked(self, event):
        path = os.path.join(self.CHRONOLAPSEPATH, self.DOCFILE)
        if os.path.isfile(path):
            wx.LaunchDefaultBrowser(path)

    def aboutMenuClicked(self, event):
        info = wx.AboutDialogInfo()
        info.Name = "Chronolapse"
        info.Version = self.VERSION
        info.Copyright = '(C) 2008 Collin "Keeyai" Green'

        description = """Chronolapse (CL) is a tool for creating time lapses on windows using
screen captures, webcam captures, or both at the same time. CL also provides
some rudimentary tools for annotating your time lapse, resizing images, and creating
a picture-in-picture (PIP) effect with two sets of images. Finally, CL provides
a front end to mencode to take your series of images and turn them into a movie."""

        info.Description = '\n'.join(textwrap.wrap(description, 70))
        info.WebSite = ("http://keeyai.com/projects-and-releases/chronolapse/", "Chronolapse")
        info.Developers = [ 'Collin "Keeyai" Green']

        if os.path.isfile( os.path.join( self.CHRONOLAPSEPATH, 'license.txt')):
            licensefile = file(os.path.join( self.CHRONOLAPSEPATH, 'license.txt'), 'r')
            licensetext = licensefile.read()
            licensefile.close()
        else:
            licensetext = 'License file not found. Please contact the developers for a copy of the license.'

        licensetext.replace('\n', ' ')
        info.License = '\n'.join(textwrap.wrap(licensetext,70))

        # Then we call wx.AboutBox giving it that info object
        wx.AboutBox(info)

    def iconClose(self, event):
        self.debug('Closing from taskbar')
        self.Close(True)

    def registerHotkey(self, event):
        # prompt user to ask if they are sure bc
        # the hotkeys dont work right in wx yet

        if self.hotkeyraw in [0]:
            return

        dlg = wx.MessageDialog(self,
"""Are you sure you want to register a hotkey?
This does NOT work right in WX and will
prevent any other application from receiving
the hotkey press, therefore we recommend
you use a complicated hotkey or avoid using
one at all.

Note: You must close Chronolapse
to end the hotkey binding.
""",
                           'Register Hotkey?',
                           #wx.OK | wx.ICON_INFORMATION
                           wx.YES_NO #| wx.NO_DEFAULT | wx.CANCEL | wx.ICON_INFORMATION
                           )
        choice = dlg.ShowModal()
        dlg.Destroy()

        # if user wants to check
        if choice == wx.ID_YES:
            if self.hotkeyraw not in [0]:
                self.RegisterHotKey(self.hotkeyid, self.hotkeymods, self.hotkeyraw)
                self.debug('Registered hotkey - mods: %d  rawcode: %d'% (self.hotkeymods,self.hotkeyraw))

    def hotkeyTextEntered(self, event):
        if type(event) is not type(wx.KeyEvent()):
            return

        # read keys used
        keycode = event.GetKeyCode()
        rawcode = event.GetRawKeyCode()
        mods = event.GetModifiers()

        # generate hotkey text
        text = ''
        if mods is not 0:
            text = wxkeycodes.wxmodtoname[mods]

        if keycode in wxkeycodes.wxtoname.keys():
            if text is not '':
                text += '+'
            text += '%s' % wxkeycodes.wxtoname[keycode]

        elif keycode not in [306, 307, 308]:
            if text is not '':
                text += '+'
            text += '?'

        # save in config
            # TODO

        # put text in hotkey box
        self.hotkeytext.SetValue(text)

        # save keys
        self.hotkeyraw = rawcode
        self.hotkeymods = mods

    def unregisterHotkey(self):
        self.debug('Attempting to Unregister Hotkey')
        self.UnregisterHotKey(self.hotkeyid)
        #self.hotkeyid = wx.NewId()

    def hotkeycheckChecked(self, event):
        if not self.hotkeycheck.IsChecked():
            self.unregisterHotkey()
        else:
            print "NEED TO REGISTER HOTKEY BASED ON TEXT"

    def handleHotKey(self, event):
        self.debug('Hotkey Pressed')
        event.Skip()
        self.forceCapturePressed(None)

    def startDateChanged(self, event):
        self.debug('Start Date: %s'% event.GetDate())
        self.schedulestartdate = event.GetDate()

    def endDateChanged(self, event):
        self.debug('End Date: %s'% event.GetDate())
        self.scheduleenddate = event.GetDate()

    def startTimeChanged(self, event):
        self.debug('Start Time: %s' % self.starttime.GetValue())
        self.schedulestarttime = self.starttime.GetValue()

    def endTimeChanged(self, event):
        self.debug('End Time: %s'% self.endtime.GetValue())
        self.scheduleendtime = self.endtime.GetValue()

    def startTimerCallBack(self):
        self.debug('Schedule start timer call back - starting capture')
        self.startTimer()

    def endTimerCallBack(self):
        self.debug('Schedule end timer call back - ending capture')
        self.stopTimer()

    def activateScheduleCheck(self, event):
        # if becoming checked
        if self.activateschedulecheck.IsChecked():
            # disable the other schedule options
            self.starttime.Disable()
            self.startdate.Disable()
            self.endtime.Disable()
            self.enddate.Disable()

            # schedule start and stop
            self.activateSchedule()

        # if becoming unchecked
        else:
            # enable other schedule options
            self.starttime.Enable()
            self.startdate.Enable()
            self.endtime.Enable()
            self.enddate.Enable()

            # deactivate schedule
            self.deactivateSchedule()

    def activateSchedule(self):
        self.debug('Activating Schedule')

        # if nothing has been changed yet, this will either be correct or already passed anyway
        if self.schedulestartdate == '':
            self.schedulestartdate = datetime.datetime.now()
            self.schedulestartdate = self.schedulestartdate.replace(hour=0, minute=0, second=0, microsecond=0)
        if self.scheduleenddate == '':
            self.scheduleenddate = datetime.datetime.now()
            self.scheduleenddate = self.scheduleenddate.replace(hour=0, minute=0, second=0, microsecond=0)

        if self.schedulestarttime == '':
            self.schedulestarttime = self.starttime.GetValue()
        if self.scheduleendtime == '':
            self.scheduleendtime = self.endtime.GetValue()

        # add together date and time
        startsplit = self.schedulestarttime.split(':')
        starttimedelta = datetime.timedelta(hours=int(startsplit[0]), minutes=int(startsplit[1]), seconds=int(startsplit[2]))
        start = self.schedulestartdate + starttimedelta
        # add together date and time
        endsplit = self.scheduleendtime.split(':')
        endtimedelta = datetime.timedelta(hours=int(endsplit[0]), minutes=int(endsplit[1]), seconds=int(endsplit[2]))
        end = self.scheduleenddate + endtimedelta

        # get seconds since epoch
        startseconds = self.dttoseconds(start)
        endseconds = self.dttoseconds(end)

        # get seconds from now until times
        startin = startseconds - time.time()
        endin = endseconds - time.time()

        # schedule timers
        if startin > 0:
            self.debug('Scheduled start for %d seconds' % int(startin))
            self.starttimer.Start(startin * 1000, True)
        if endin > 0:
            self.debug("Scheduled end for %d seconds" % int(endin))
            self.endtimer.Start(endin * 1000, True)

    def dttoseconds(self, dt):
        string = dt.strftime('%Y-%m-%d %H:%M:%S')
        timetuple = time.strptime(string,'%Y-%m-%d %H:%M:%S')
        return time.mktime(timetuple)

    def deactivateSchedule(self):
        self.debug('Deactivating Schedule')

        if self.starttimer.IsRunning():
            self.starttimer.Stop()

        if self.endtimer.IsRunning():
            self.endtimer.Stop()

    def checkVersion(self):
        try:
            # if it has been more than a week since the last check
            lastupdate = self.options['lastupdate']

            # convert for comparison?
            parsedtime = time.mktime(time.strptime( lastupdate, '%Y-%m-%d'))

            # calculate time since last update
            timesince = time.mktime(time.localtime()) - parsedtime

            if timesince > self.UPDATECHECKFREQUENCY:
                # show popup to confirm user wants to access the net
                dlg = wx.MessageDialog(self, "Do you want Chronolapse to check for updates now?",
                                   'Check for Updates?',
                                   #wx.OK | wx.ICON_INFORMATION
                                   wx.YES_NO #| wx.NO_DEFAULT | wx.CANCEL | wx.ICON_INFORMATION
                                   )
                choice = dlg.ShowModal()
                dlg.Destroy()

                # if user wants to check
                if choice == wx.ID_YES:

                    # check URL
                    request = urllib2.Request(self.VERSIONCHECKPATH, urllib.urlencode([('version',self.VERSION)]))
                    page = urllib2.urlopen(request)

                    #parse page
                    content = page.read()
                    dom = xml.dom.minidom.parseString(content)

                    version = dom.getElementsByTagName('version')[0].childNodes[0].data
                    url = dom.getElementsByTagName('url')[0].childNodes[0].data
                    changedate = dom.getElementsByTagName('changedate')[0].childNodes[0].data

                    # if version is different, show popup
                    if version.lower() != self.VERSION.lower():
                        versionmessage = """
A new version of Chronolapse is available.
Your current version is %s. The latest available version is %s.
You can download the new version at:
%s""" % (self.VERSION, version, url)
                        dlg = wx.MessageDialog(self, versionmessage,
                                       'A new version is available',
                                       wx.OK | wx.ICON_INFORMATION
                                       )
                        dlg.ShowModal()
                        dlg.Destroy()

                    # otherwise, write to log
                    else:
                        dlg = wx.MessageDialog(self, "Chronolapse is up to date","Chronolapse is up to date",wx.OK | wx.ICON_INFORMATION)
                        dlg.ShowModal()
                        dlg.Destroy()

            # reset update time
            self.options['lastupdate'] = time.strftime('%Y-%m-%d')
            self.saveConfig()

        except Exception, e:
            self.showWarning('Failed to check version', 'Failed to check version. %s' % str(e))
            self.debug( repr(e), self.NORMAL)

    def subsectionchecked(self, event=None):
#        try:

            if self.screenshotdialog.subsectioncheck.IsChecked():
                self.screenshotdialog.subsectiontop.Enable()
                self.screenshotdialog.subsectionleft.Enable()
                self.screenshotdialog.subsectionwidth.Enable()
                self.screenshotdialog.subsectionheight.Enable()
            else:
                self.screenshotdialog.subsectiontop.Disable()
                self.screenshotdialog.subsectionleft.Disable()
                self.screenshotdialog.subsectionwidth.Disable()
                self.screenshotdialog.subsectionheight.Disable()
 #       except:
  #          pass

    def convertSourceBrowsePressed(self, event=None):
        path = self.dirBrowser('Select source capture folder',
                    self.convertsourcetext.GetValue())

        if path != '':
            self.convertsourcetext.SetValue(path)

            if not os.access( path, os.R_OK):
                self.showWarning("Permission Error",
                    'Error: the source path %s is not readable. Please set read permissions and try again.'%path)

    def convertOutputBrowsePressed(self, event=None):
        path = self.dirBrowser('Select save folder for images', self.convertoutputtext.GetValue())

        if path != '':
            self.convertoutputtext.SetValue(path)

            if not os.access( path, os.W_OK):
                self.showWarning("Permission Error",
                    'Error: the output path %s is not writable. Please set write permissions and try again.'%path)

    def convertFilesPressed(self, event=None):
        source = self.convertsourcetext.GetValue()
        output = self.convertoutputtext.GetValue()

        if source == '':
            self.showWarning('Source Folder Required', 'Please select a source folder containing your captures you want renamed')
        elif not os.access(source, os.R_OK):
            self.showWarning("Permission Error", 'Error: the source path %s is not readable. Please set read permissions and try again.'%source)
        elif output == '':
            self.showWarning('Output Folder Required', 'Please select an output folder for the renamed captures')
        elif not os.access(output, os.W_OK):
            self.showWarning("Permission Error", 'Error: the output path %s is not writable. Please set write permissions and try again.'%output)
        elif source == output:
            self.showWarning("Headache Protection", 'Error: the source and output paths are the same. Please select a different output folder.')
        else:
            # start at one
            counter = 1

            # get the files from the folder
            files = os.listdir(source)

            # get just our desired files
            imagefiles = []
            for f in files:
                if f.endswith(('jpg','JPG','jpeg','JPEG','png','PNG','gif','GIF')):
                    imagefiles.append(f)

            # calculate the filename padding necessary based on number of files
            padding = int(round( math.log( len(imagefiles), 10))) + 1
            padding = max(4, padding)

            # process the files
            for f in imagefiles:

                newname = "%s%s" % (str(counter).rjust(padding, '0'), os.path.splitext(f)[1])
                shutil.copy( os.path.join(source,f), os.path.join(output, newname))
                counter += 1

            dlg = wx.MessageDialog(self,"%d files renamed"%(counter-1), "Renaming Complete",wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()

class TaskBarIcon(wx.TaskBarIcon):

    def __init__(self, parent, MainFrame, workingdir):
        wx.TaskBarIcon.__init__(self)
        self.parentApp = parent
        self.MainFrame = MainFrame
        self.wx_id = wx.NewId()
        if ONWINDOWS and os.path.isfile( os.path.join(os.path.abspath(workingdir), 'chronolapse.ico')):
            self.SetIcon(wx.Icon( os.path.join( os.path.abspath(workingdir), "chronolapse.ico"),wx.BITMAP_TYPE_ICO), 'Chronolapse')
        elif not ONWINDOWS and os.path.isfile( os.path.join(os.path.abspath(workingdir), 'chronolapse_24.ico')):
            self.SetIcon(wx.Icon( os.path.join( os.path.abspath(workingdir), "chronolapse_24.ico"),wx.BITMAP_TYPE_ICO), 'Chronolapse')
        self.CreateMenu()

    def toggle_window_visibility(self, event):
        if self.MainFrame.IsIconized() or not self.MainFrame.IsShown():
            self.set_window_visible_on(event)
        else:
            self.set_window_visible_off(event)

    def set_window_visible_off(self, event):
        self.MainFrame.Show(False)
        self.set_icon_action_text(True)

    def set_window_visible_on(self, event):
        self.MainFrame.Iconize(False)
        self.MainFrame.Show(True)
        self.MainFrame.Raise()
        self.set_icon_action_text(False)

    def set_icon_action_text(self, minimized=True):
        if minimized:
            self.menu.FindItemById(self.wx_id).SetText("Restore")
        else:
            self.menu.FindItemById(self.wx_id).SetText("Minimize")

    def iconized(self, event):
        # bound on non-windows only
        if self.MainFrame.IsIconized():
            #print "Main Frame Is Iconized"
            self.set_icon_action_text(True)
            self.MainFrame.Show(False)
        else:
            #print "Main Frame Is Not Iconized"
            self.set_icon_action_text(False)
            self.MainFrame.Show(True)
            self.MainFrame.Raise()

    def CreateMenu(self):
        self.Bind(wx.EVT_TASKBAR_RIGHT_UP, self.ShowMenu)
        self.Bind(wx.EVT_TASKBAR_LEFT_DCLICK, self.toggle_window_visibility)
        self.Bind(wx.EVT_MENU, self.toggle_window_visibility, id=self.wx_id)
        self.Bind(wx.EVT_MENU, self.MainFrame.iconClose, id=wx.ID_EXIT)
        if ONWINDOWS:
            self.MainFrame.Bind(wx.EVT_ICONIZE, self.set_window_visible_off)
        else:
            self.MainFrame.Bind(wx.EVT_ICONIZE, self.iconized)
        self.menu=wx.Menu()
        self.menu.Append(self.wx_id, "Minimize","...")
        self.menu.AppendSeparator()
        self.menu.Append(wx.ID_EXIT, "Close Chronolapse")

    def ShowMenu(self,event):
        self.PopupMenu(self.menu)
##        if self.MainFrame.IsShown() and not self.MainFrame.IsIconized():
##            self.menu.FindItemById(self.wx_id).SetText("Minimize")
##        else:
##            self.menu.FindItemById(self.wx_id).SetText("Restore")


class TaskBarFrame(wx.Frame):
    def __init__(self, parent, MainFrame, id, title, workingdir):
        wx.Frame.__init__(self, parent, -1, title, size = (1, 1),
            style=wx.FRAME_NO_TASKBAR|wx.NO_FULL_REPAINT_ON_RESIZE)
        self.tbicon = TaskBarIcon(self, MainFrame, workingdir)
        self.Show(True)
        self.MainFrame = MainFrame

    def kill(self, event):
        event.Skip()
        self.tbicon.RemoveIcon()
        self.tbicon.Destroy()
        self.Close()

    def toggle_window_visibility(self, event):
        self.tbicon.toggle_window_visibility(event)

    def set_icon_action_text(self, minimized):
        self.tbicon.set_icon_action_text(minimized)


# run it!
if __name__ == "__main__":
    app = wx.PySimpleApp(0)
    wx.InitAllImageHandlers()
    chronoframe = ChronoFrame(None, -1, "")
    app.SetTopWindow(chronoframe)
    chronoframe.doShow()
    app.MainLoop()
