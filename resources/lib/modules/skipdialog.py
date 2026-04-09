# -*- coding: utf-8 -*-
import xbmcgui
import xbmc
import xbmcaddon
import time

CANCEL_ACTIONS = {
    xbmcgui.ACTION_PREVIOUS_MENU,
    xbmcgui.ACTION_NAV_BACK,
    xbmcgui.ACTION_STOP,
    xbmcgui.ACTION_PARENT_DIR,
    xbmcgui.ACTION_NAV_BACK,

}

class SkipDialog(xbmcgui.WindowXMLDialog):

    def __init__(self, xmlfilename, addon_path, defaultSkin = "Default", defaultRes = "720p", tcEnd=0, event_name=None, timeout=5, on_skip=None, on_cancel=None):
        super(SkipDialog, self).__init__(xmlfilename, addon_path, defaultSkin, defaultRes)
        self.tcEnd = tcEnd
        self.timeout = timeout
        self.start_time = time.time()*1000
        self.active = True
        self.on_skip = on_skip
        self.on_cancel = on_cancel
        self.event_name = event_name
        self.initialized = False
        self.chapterignoretimeoutmode = xbmcaddon.Addon().getSettingInt('chapterignoretimeoutmode')

    def onInit(self):
        self.label_ctrl = self.getControl(1002)
        self.progress = self.getControl(1001)
        self.label_ctrl.setLabel(self.event_name)
        self.setFocusId(1002)
        self.initialized = True
        self.progress.setPercent(100)

    def onClick(self, controlId):
        if not self.active or not self.initialized:
            return
        if controlId == 1002 and self.on_skip:
            self.on_skip(self.tcEnd)
            self.close()
            self.active = False

    def onAction(self, action):
        if self.active:
            if action.getId() in CANCEL_ACTIONS:
                if self.on_cancel:
                    self.on_cancel()
                self.close()
                self.active = False

    def update(self, player):
        if not self.active or not self.initialized:
            return

        current_time = player.getTime()
        elapsed = time.time()*1000 - self.start_time
        remaining = max(0, self.timeout*1000 - elapsed)
        percent = int((remaining / (self.timeout*1000)) * 100)
        self.progress.setPercent(percent)

        # Idő elérte a tcEnd-et → bezár
        if current_time >= self.tcEnd:
            self.close()
            self.active = False
            return

        # Timeout → bezár
        if elapsed >= self.timeout*1000:
            if self.chapterignoretimeoutmode == 0:
                if self.on_skip:
                    self.on_skip(self.tcEnd)
            else:
                if self.on_cancel:
                    self.on_cancel()
            self.close()
            self.active = False
