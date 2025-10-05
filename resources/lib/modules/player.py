# -*- coding: utf-8 -*-

'''
    RTL+ Add-on
    Copyright (C) 2023

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''


import os, sys, json, xbmc, xbmcaddon, xbmcgui, xbmcplugin, re, base64, time
from resources.lib.modules import net
from resources.lib.modules import m3u8_parser
from resources.lib.modules.utils import py2_encode
if sys.version_info[0] == 3:
    from urllib.parse import urlparse
    buildVersionStr = "System.BuildVersionCode"
else:
    from urlparse import urlparse
    buildVersionStr = "System.BuildVersion"

token_url = 'https://drm.6cloud.fr/v1/customers/rtlhu/platforms/m6group_web/services/rtlhu_rtl_klub/users/%s/%s/%s/upfront-token'
notify_url = 'https://heartbeat-v2.6cloud.fr/v2/platforms/m6group_web/notify'
session_url = '%s/session' % notify_url
view_url = '%s/view' % notify_url

class player:
    def __init__(self):
        self.uid = xbmcaddon.Addon().getSetting('userid')
        self.tracking = xbmcaddon.Addon().getSetting('tracking') == 'true'
        self.trackingwrite = xbmcaddon.Addon().getSetting('trackingwrite') == 'true'
        self.autoplaynext = xbmcaddon.Addon().getSetting('autoplaynext') == 'true'


    def play(self, ptype, id, streams, image, meta, duration, resume, heartbeat, firstplay=True):
        def sort_by_resolution_pattern(x):
            patterns = ['_1080p_', '_720p_', '_hd_', '_540p_', '_sd_']
            pattern = '|'.join('(%s)' %x for x in patterns)
            match = re.search(pattern, x)
            return match.lastindex if match != None else len(patterns)+1
        
        #dash_url = [i for i in streams if 'drmnp.ism/Manifest.mpd' in i]
        dash_url = sorted([i for i in streams if 'mpd' in i and 'live' not in i], key=sort_by_resolution_pattern)
        hls_url = sorted([i for i in streams if 'm3u8' in i and 'live' not in i])
        live_url = sorted([i for i in streams if 'mpd' in i and 'live' in i])
        li = None
        stream_url = None
        if dash_url != []:
            # Inputstream and DRM
            #manifest_url = net.request(dash_url[0], redirect=False)
            #stream_url = os.path.dirname(manifest_url) + '/Manifest.mpd'
            stream_url=dash_url[0]

            stream_url = net.request(stream_url, redirect=False)

            parsed = urlparse(stream_url)

            if len(parsed.scheme) == 0 or len(parsed.netloc) == 0:
                stream_url = dash_url[0]



            headers = {
                'x-customer-name': 'rtlhu',
                'authorization': 'Bearer %s' % self.getJwtToken(),
                'Origin': 'https://www.rtlmost.hu'}

            token_source = net.request(token_url % (self.uid, ptype, id), headers=headers)
            token_source = json.loads(token_source)
            x_dt_auth_token = py2_encode(token_source['token'])

            license_headers = 'x-dt-auth-token=' + x_dt_auth_token + '&Origin=https://www.rtlmost.hu&Content-Type='
            license_key = 'https://lic.drmtoday.com/license-proxy-widevine/cenc/' + '|' + license_headers + '|R{SSM}|JBlicense'
            DRM = 'com.widevine.alpha'
            PROTOCOL = 'mpd'

            from inputstreamhelper import Helper
            is_helper = Helper(PROTOCOL, drm=DRM)
            if is_helper.check_inputstream():
                li = xbmcgui.ListItem(path=stream_url)
                if sys.version_info < (3, 0):  # if python version < 3 is safe to assume we are running on Kodi 18
                    li.setProperty('inputstreamaddon', 'inputstream.adaptive')   # compatible with Kodi 18 API
                else:
                    li.setProperty('inputstream', 'inputstream.adaptive')  # compatible with recent builds Kodi 19 API
                li.setProperty('inputstream.adaptive.manifest_type', PROTOCOL)
                li.setProperty('inputstream.adaptive.license_type', DRM)
                li.setProperty('inputstream.adaptive.license_key', license_key)
                li.setMimeType('application/dash+xml')
                li.setContentLookup(False)
        elif hls_url != []:
            stream_url = hls_url[0]
            if "live" not in stream_url:
                manifest_url = net.request(stream_url, redirect=False)
            else:
                manifest_url = stream_url
            manifest = net.request(manifest_url)
            sources = m3u8_parser.parse(manifest)
            if len(sources) == 0:
                manifest_url = stream_url
                manifest = net.request(manifest_url)
                sources = m3u8_parser.parse(manifest)

            root = os.path.dirname(manifest_url)

            sources = sorted(sources, key=lambda x: x['resolution'])[::-1]

            auto_pick = xbmcaddon.Addon().getSetting('hls_quality') == '0'

            if len(sources) == 1 or auto_pick == True:
                source = sources[0]['uri']
            else:
                result = xbmcgui.Dialog().select(u'Min\u0151s\u00E9g', [str(source['resolution']) if 'resolution' in source else 'Unknown' for source in sources])
                if result == -1:
                    return
                else:
                    source = sources[result]['uri']
            stream_url = root + '/' + source
            li = xbmcgui.ListItem(path=stream_url)

        elif live_url != []:

            headers = {
                'x-customer-name': 'rtlhu',
                'authorization': 'Bearer %s' % self.getJwtToken(),
                'Origin': 'https://www.rtlplusz.hu'}

            token_source = net.request(token_url % (self.uid, ptype, "dashcenc_%s" % id), headers=headers)
            token_source = json.loads(token_source)
            x_dt_auth_token = py2_encode(token_source['token'])

            license_headers = 'x-dt-auth-token=' + x_dt_auth_token + '&Origin=https://www.rtlplusz.hu&Content-type='
            license_key = 'https://lic.drmtoday.com/license-proxy-widevine/cenc/' + '|' + license_headers + '|R{SSM}|JBlicense'
            DRM = 'com.widevine.alpha'
            PROTOCOL = 'mpd'

            from inputstreamhelper import Helper
            is_helper = Helper(PROTOCOL, drm=DRM)
            if is_helper.check_inputstream():
                stream_url = live_url[0]
                li = xbmcgui.ListItem(path=live_url[0])
                if sys.version_info < (3, 0):  # if python version < 3 is safe to assume we are running on Kodi 18
                    li.setProperty('inputstreamaddon', 'inputstream.adaptive')   # compatible with Kodi 18 API
                else:
                    li.setProperty('inputstream', 'inputstream.adaptive')  # compatible with recent builds Kodi 19 API
                li.setProperty('inputstream.adaptive.manifest_type', PROTOCOL)
                li.setProperty('inputstream.adaptive.license_type', DRM)
                li.setProperty('inputstream.adaptive.license_key', license_key)
                li.setMimeType('application/dash+xml')
                li.setContentLookup(False)

        if li is None:
            xbmcgui.Dialog().notification(u'Lej\u00E1tsz\u00E1s sikertelen. DRM v\u00E9dett m\u0171sor.', 'RTL+', time=8000)
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), False, xbmcgui.ListItem())
            return

        meta = json.loads(meta)
        li.setArt({'icon': image, 'thumb': image, 'poster': image, 'tvshow.poster': image})
        li.setInfo(type='Video', infoLabels = meta)
        if self.tracking and (dash_url != [] or hls_url != []):
            if resume:
                try:
                    li.getVideoInfoTag().setResumePoint(resume, duration)
                except:
                    xbmc.log('RTL+: Error on setResumePoint call, probably we are on old Kodi version', xbmc.LOGERROR)
            if self.trackingwrite:
                sessionData = json.loads(net.request(session_url, post=json.dumps(heartbeat["session"]).encode("utf-8"), headers={'authorization': 'Bearer %s' % self.getJwtToken(), 'content-type': 'application/json'}))
        player = xbmc.Player()
        if firstplay:
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, li)
        else:
            player.play(stream_url, li)
        if ((self.tracking and self.trackingwrite) or self.autoplaynext) and (dash_url != [] or hls_url != []):
            current_sec = 0
            total_sec = 0
            for i in range(0, 240):
                if player.isPlaying():
                    break
                xbmc.Monitor().waitForAbort(1)
            while not xbmc.Monitor().abortRequested() and player.isPlaying():
                try:
                    current_sec = player.getTime()
                    total_sec = player.getTotalTime()
                except:
                    pass
                xbmc.Monitor().waitForAbort(1)
            if current_sec >= total_sec - 5:
                current_sec = total_sec
            if self.tracking and self.trackingwrite and "sessionId" in sessionData:
                heartbeat["view"]["platformCode"] = heartbeat["session"]["platformCode"]
                heartbeat["view"]["tc"] = current_sec
                heartbeat["view"]["sessionId"] = sessionData["sessionId"]
                heartbeat["view"]["sequenceNumber"] = 1
                heartbeat["view"]["tcRelative"] = 0
                viewData = json.loads(net.request(view_url, post=json.dumps(heartbeat["view"]).encode("utf-8"), headers={'authorization': 'Bearer %s' % self.getJwtToken(), 'content-type': 'application/json'}))
            if current_sec == total_sec:
                return True
        return

    def getJwtToken(self):
        getJwt_url = 'https://front-auth.6cloud.fr/v2/platforms/m6group_web/getJwt'
        jwtToken = xbmcaddon.Addon().getSetting('jwttoken')
        if jwtToken != "":
            m = re.search(r'(.*)\.(.*)\.(.*)', jwtToken)
            if m:
                errMsg = ""
                try:
                    errMsg = "RTL+: cannot base64 decode the group 2: %s" % m.group(2)
                    decodedToken=base64.b64decode(m.group(2)+"===")
                    if sys.version_info[0] == 3:
                        errMsg = "RTL+: utf-8 decode error: %s" % decodedToken
                        decodedToken = decodedToken.decode("utf-8", "ignore")
                    errMsg = "RTL+: decodedToken is not a json object: %s" % decodedToken
                    jsObj = json.loads(decodedToken)
                    if "exp" in jsObj:
                        if jsObj["exp"]-int(time.time())>0:
                            return jwtToken
                        else:
                            xbmc.log("RTL+: jwtToken expired, request a new one.", xbmc.LOGINFO)
                    else:
                        xbmc.log("RTL+: match group 2 does not contains exp key: %s" % m.group(2), xbmc.LOGERROR)
                except:
                    xbmc.log(errMsg, xbmc.LOGERROR)
            else:
                xbmc.log("RTL+: jwtToken not match to (.*)\.(.*)\.(.*). jwtToken: %s" % jwtToken, xbmc.LOGERROR)
        headers = {
            'x-auth-gigya-uid': self.uid,
            'x-auth-gigya-signature': xbmcaddon.Addon().getSetting('signature'),
            'x-auth-gigya-signature-timestamp': xbmcaddon.Addon().getSetting('s.timestamp'),
            'X-Customer-Name': 'rtlhu',
            'x-auth-device-id': xbmcaddon.Addon().getSetting('deviceid'),
            'x-auth-device-name': "%s ver.: %s" % (xbmc.getInfoLabel('System.FriendlyName'), xbmc.getInfoLabel(buildVersionStr).split(" ")[0])
        }
        if xbmcaddon.Addon().getSetting('profileid') != "":
            headers['x-auth-profile-id'] = xbmcaddon.Addon().getSetting('profileid')
        jwtAnswer = json.loads(net.request(getJwt_url, headers=headers))
        xbmcaddon.Addon().setSetting('jwttoken', jwtAnswer['token'])
        return jwtAnswer['token']
