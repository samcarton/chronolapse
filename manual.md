# Welcome to Chronolapse #
## Overview ##

Chronolapse (CL) is a tool for creating time lapses on windows using screen captures, webcam captures, or both at the same time. CL also provides some rudimentary tools for annotating your time lapse, as well as creating a picture-in-picture effect with two sets of images. Each piece of CL functionality has been created to work stand-alone to make the program more versatile. For example, you can easily capture with another program and create a PIP in CL, or capture with CL and annotate somewhere else.
Quick Launch

So you want to create a time lapse as quickly as possible. Here is a quick guide to making a simple screencapture timelapse.

  1. n the capture tab, set the capture frequency (default is 1 per 60 seconds)
  1. heck the screenshot checkboxes
  1. it the screenshot configure button and select the save folder to store captures in, as well as the file format
  1. it the start capture button
  1. it stop capture when finished

That's it! You now have a folder full of screenshots. Read the rest of this documentation for more detailed instructions
Capture

The capture tab is where you set up and run the actual captures. Everything that happens in real time will be done here. You can estimate how much time is left before the next capture by the blue bar at the bottom; when it fills all the way up, another capture is saved. Note: The webcam library is only supported on windows, so you cannot use webcam captures outside of windows. All the other functionality works. If someone out there has experience with a good linux/mac webcam lib (video4linux?), let me know.

Item Overview

  * Frequency: Set the number of seconds between each capture. Set this to zero to stop automatic captures(force captures only).
  * Screenshots: Check the box to enable screenshots and hit the configure button to popup a dialog with screenshot options.
    * Show Timestamp: Check this to have CL write a timestamp on your screenshots
    * File Prefix: This will be pre-pended to each screenshot file name
    * Save Folder: This is where all the images will be saved
    * File Format: This defines which image format to save the screenshots in
  * Webcam: Check the box to enable webcam captures and hit the configure button to popup two dialgos with webcam options. On the first dialog, select the correct source and video size. On the second, select capture options.
    * Test Webcam: Press this to take a sample shot from your webcam. Note, some webcams take a while to initialize - if you get a blank screen, try again a few seconds later before changing anything.
    * Show Timestamp: Check this to have CL write a timestamp on your captures
    * File Prefix: This will be pre-pended to each capture file name
    * Save Folder: This is where all the captures will be saved. Making it different from the screenshots will make your life much easier if you plan to use PIP
    * File Format: This defines which image format to save the screenshots in
  * Start Capture: Press this to begin capturing. When capturing the text will change to Stop Capture - press it again to stop.
  * Force Capture: Press this to force CL to take a screenshot and/or webcam capture at that moment. Use to make sure certain things make it into your time lapse, or use with the capture frequency set to zero for creating a stop motion video
  * Frames: This is the number of images to save when you press Force Capture.
  * Annotate: The annotation box is a way to add simple text to your time lapses. Place text in the box and hit the Add Annotation button to save the text in a special annotation file in the capture save folders. When you are finished capturing, you can add the annotation to your images using the annotation tab.
  * Add Annotation: Press this to save the text in the annotation box

## Schedule ##
On this tab you can schedule Chronolapse to start and stop capturing at specific times.
When activated, end time will stop your capturing, even if it wasn't started with the
start time scheduler. Note: All times are local to your machine.

**Item Overview**
  * Start Time - The time you want to begin capturing
  * Stop Time - The time you want to stop capturing
  * Activate Schedule: Check this to 'lock in' your times and actually schedule the start and end

## Adjust ##

On this tab you can resize or rotate a folder of images. Simple select the source folder, the output folder, and the target size or rotation. Note, if you use the same folder for the source and the output, the source images will be overwritten.

**Item Overview**

  * Source Folder - This is where the images you want to resize are
  * Output Folder - This is where the resized images will be saved
  * Width - The target width of your images, in pixels
  * Height - The target height of your images, in pixels
  * Resize - Press this to resize all the images in the source folder
  * Rotation - Target rotation, in degrees
  * Rotate - Press this to rotate all the images in the source folder

## Annotate ##

This tab is where you apply any annotations you created while capturing. See the Annotate and Add Annotation descriptions above.

There are two kinds of annotations you can apply - timed and constant. In timed, the words pop up at the correct time, last for however long you specify in the duration box, then disappear. Additionally, the text will fade in/out if you check the appropriate boxes. Constant annotation differs in that the text will remain on the timelapse until it finds a new annotation. This annotation system works great if you want to have a very simple tool for putting some information on the screen, but it isn't well suited for anything complex. If you need more versatile annotations, consider uploading to youtube and using their built in system.

**Item Overview**

  * Image/Annotation Folder: This is the folder where the images and annotation file are found
  * Output Folder: This is where the annotated images will be output. You should use a different folder from your source folder.
  * Select Font: Hit this button to show a font selection dialog. The annotations will be rendered on your images in this font.
  * Opacity: Select the opacity of the annotation text. 100 is full opacity.
  * Position: Select if you want your text to be rendered near the top or the bottom of the images
  * Timed: Check this to enable timed annotations - see above
  * Duration: If timed is checked, this is how many seconds the annotations will show up for. Note: CL uses the current framerate setting on the video tab to 'guess' at how long to display the annotations.
  * Constant: Check this to enable constant annotations - see above
  * Fade In: Check this to have timed annotations fade in
  * Fade Out: Check this to have timed annotations fade out
  * Create Annotated Images: Click this to process the images and apply the annotations

## PIP ##

Chronolapse can take two folders of images (say, from a synchronised webcam and screen capture time lapse) and merge them into a picture-in-picture composition. You have many options of size and position of the PIP, so experiment a little until you get the look you want. Note, CL sorts the images in both source folders by name then uses them sequentially, so be sure there are no extra image files lurking in the source folders that might affect your time lapse.

**Item Overview**

  * Main Image Folder: This is the folder for the 'main' source images - for corner PIP settings, this will be the main picture.
  * PIP Image Folder: This is the folder for the 'PIP' source images - for corner PIP settings, this will be the corner.
  * Output Folder: This is the folder the completed PIP images will be saved in
  * PIP Size: Select the size of the PIP
  * Pip Position: Select where the PIP should go relative to the main image
  * Create PIP: Click this to process the images

## Video ##

Chronolapse uses MEncoder to encode the folders of images into video files. You have a few options for which codecs you want to use and what kind of video file to output. If you need more control over the encoding process, you should use MEncoder directly.

**Item Overview**

  * Source Images: This is the folder for the source images CL will encode
  * Destination Folder: This is the folder where the timelapse video will be saved
  * Video Format: Select which format you want your video encoded in
  * Video Codec: Select which codec to use for encoding
  * Frame Rate: Select the frame rate you want for your movie
  * ReCalculate Estimate: Press this to estimate the length of your movie - takes the number of files in the source folder over the frame rate
  * Create Video: Press this to encode your video

## Audio ##
Chronolapse uses MEncoder to dub audio onto your video files. If you
need more control over the dubbing process, you should use MEncoder directly.

**Item Overview**

  * Video Source: This is the video file you want to add audio to
  * Audio Source: This is the file containing your audio
  * Output Folder: This is the folder in which your finished video will be placed
  * Add Audio: Pless this to begin dubbing

## About ##

Chronolapse was written by Collin 'Keeyai' Green (http://keeyai.com) and released under the MIT license, so it is free to use for pretty much whatever you want. As always, if you use the code, a link back is nice and if you are using it commercially a link back is awesome. :)

Please send feedback, comments, bug reports, questions, etc, to chronolapse at keeyai dot com. I always love to hear from people using my apps, and you guys usually have better ideas for features than I do.