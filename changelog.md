# Change Log #
  * V 1.0.7 - 2011/05/01
    * - fixed bug where audio encoding failed when video filename did NOT have a space in it :o ([issue 18](https://code.google.com/p/chronolapse/issues/detail?id=18))
    * - fixed bug like 1.0.4 where audio encoding hanged in exe form but not run from source ([issue 17](https://code.google.com/p/chronolapse/issues/detail?id=17))

  * V 1.0.6 - 2011/04/30
    * - fixed faster-than-one-second capture rates. Automatically adds microseconds to the timestamps and filenames. Note: you probably won't get regular capture times with delays this small. ([issue 16](https://code.google.com/p/chronolapse/issues/detail?id=16))

  * V 1.0.5 - 2011/04/29
    * - added subsection screen captures ([issue 15](https://code.google.com/p/chronolapse/issues/detail?id=15))

  * V 1.0.4 - 2011/04/20
    * - added a rough and dirty threading implementation for the mencoder call -- trying to fix hang in GUI form
    * - changed popen to just pop up a window with output -- was hanging on mencoder call with no window to print to
    * - fixed update check code

  * V 1.0.3 - 2010/12/23
    * - fixed a bug with times under 1 second being fired 1000 times too fast
    * - silently fails if set to capture 2 monitors but they are duplicated
    * - added system wide hotkey -- doesnt seem to work right in wx so it is only part implemented ([issue 11](https://code.google.com/p/chronolapse/issues/detail?id=11))
    * - added audio tab to dub audio onto your timelapse ([issue 10](https://code.google.com/p/chronolapse/issues/detail?id=10))
    * - added a drop shadow option for annotations ([issue 8](https://code.google.com/p/chronolapse/issues/detail?id=8))
    * - added a schedule tab for scheduling starts and/or stops ([issue 7](https://code.google.com/p/chronolapse/issues/detail?id=7))

  * V 1.0.2 - 2010/12/21
    * - Removed dependence on kml.pyc
    * - Added -a flag for auto starting ([issue 5](https://code.google.com/p/chronolapse/issues/detail?id=5))
    * - Added minimizing to tray option ([issue 5](https://code.google.com/p/chronolapse/issues/detail?id=5))
    * - Added rotate option and renamed resize tab to adjust tab ([issue 6](https://code.google.com/p/chronolapse/issues/detail?id=6))
    * - fixed dual monitor support to work with any orientation or relative resolution ([issue 4](https://code.google.com/p/chronolapse/issues/detail?id=4))

  * V 1.0.1 - 2008/09/30
    * - fixed outputting video to path with spaces - used a bit of a hack for mencoder to work ([issue 1](https://code.google.com/p/chronolapse/issues/detail?id=1))

  * V 1.0.0 - 2008/09/28 - Initial Release