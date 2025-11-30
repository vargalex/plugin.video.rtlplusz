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


import os,sys,re,xbmc,xbmcgui,xbmcplugin,xbmcaddon,urllib,json,time,locale, uuid
from resources.lib.modules import net, player, cache
from  collections import OrderedDict

if sys.version_info[0] == 3:
    import urllib.parse as urlparse
    from urllib.parse import quote_plus
    from xbmcvfs import translatePath
else:
    import urlparse
    from urllib import quote_plus
    from xbmc import translatePath

from resources.lib.modules.utils import py2_encode, py2_decode


sysaddon = sys.argv[0] ; syshandle = int(sys.argv[1])
addon = xbmcaddon.Addon
addonFanart = addon().getAddonInfo('fanart')

img_link = 'https://images-fio.6play.fr/v2/images/%s/raw'
package_change_needed = 'A hozzáféréshez nagyobb csomagra váltás szükséges.\nRészletek: https://rtl.hu/rtlplusz/szolgaltatasok'
account_overview_url = 'https://layout.6cloud.fr/front/v1/rtlhu/m6group_web/main/token-web-20/app/account_overview/layout?nbPages=2'
devices_management_url = 'https://layout.6cloud.fr/front/v1/rtlhu/m6group_web/main/token-web-20/frontspace/devicesmanagementcenter/layout?nbPages=2'
profile_url = 'https://6play-users.6play.fr/v2/platforms/m6group_web/users/%s/profiles'
api_base = 'https://layout.6cloud.fr/front/v1/rtlhu/m6group_web/main/token-web-20/%s/%s/'
defaultNumberOfPages = 2
api_url = api_base + 'layout?nbPages=%d' % defaultNumberOfPages
api_block_url = api_base + 'block/%s?nbPages=%d&page=%d'
search_url = 'https://nhacvivxxk-dsn.algolia.net/1/indexes/*/queries'
search_api_key = '5fce02cb376fb2cda773be8a8404598a'
search_application_id = 'NHACVIVXXK'
delete_device_url = 'https://6play-users.6play.fr/v3/rtlhu/m6group_web/devices/toRevoke'
subscriptions_url = 'https://stores.6cloud.fr/premium/v4/customers/rtlhu/platforms/m6group_web/users/%s/subscriptions'
desktop_url = 'https://layout.6cloud.fr/front/v1/rtlhu/m6group_web/main/token-web-20/navigation/desktop'
revoke_current_device_url = 'https://6play-users.6play.fr/v3/rtlhu/m6group_web/devices/revokeCurrentDevice'

class navigator:
    def __init__(self):
        try:
            locale.setlocale(locale.LC_ALL, "")
        except:
            pass
        self.username = addon().getSetting('email').strip()
        self.password = addon().getSetting('password').strip()

        if not (self.username and self.password) != '':
            if xbmcgui.Dialog().ok('RTL+', u'A kieg\u00E9sz\u00EDt\u0151 haszn\u00E1lat\u00E1hoz add meg a bejelentkez\u00E9si adataidat.'):
                xbmc.executebuiltin('Dialog.Close(busydialognocancel)')
                addon(addon().getAddonInfo('id')).openSettings()
            self.username = addon().getSetting('email').strip()
            self.password = addon().getSetting('password').strip()
        self.setDeviceID()
        self.Login()
        self.base_path = py2_decode(translatePath(addon().getAddonInfo('profile')))
        self.searchFileName = os.path.join(self.base_path, "search.history")
        self.cacheTime = addon().getSettingInt('cachetime')
        self.tracking = addon().getSetting('tracking') == 'true'
        self.trackingpreload = addon().getSetting('trackingpreload') == 'true'
        self.autoplaynext = addon().getSetting('autoplaynext') == 'true'

    def root(self):
        subscriptionData = json.loads(net.request(subscriptions_url % addon().getSetting('userid'), headers={'authorization': 'Bearer %s' % player.player().getJwtToken()}))
        if len(subscriptionData['current']) > 0:
            subscriptionName = ", ".join(offer["offer"]["title"] for offer in subscriptionData["current"])
        else:
            subscriptionName = "RTL+ Light"
        if subscriptionName != addon().getSetting("subscriptionname"):
            addon().setSetting('subscriptionname', subscriptionName)
            xbmcgui.Dialog().notification("RTL+", "Jelenlegi csomagod: %s" % subscriptionName)
        self.addDirectoryItem(py2_encode('[COLOR red]Párosított eszközök törlése[/COLOR]'), 'paireddevices' , '', 'DefaultTVShows.png')
        self.addDirectoryItem(py2_encode('Keresés'), 'getsearches' , '', 'DefaultTVShows.png')
        datas = json.loads(net.request(desktop_url, headers={'authorization': 'Bearer %s' % player.player().getJwtToken()}))
        categories = []
        for data in datas:
            if data['type'] == '1':
                if data['entries']:
                    for entry in data['entries']:
                        if entry['target']['type'] == 'layout' and entry['target']['value_layout']['type'].lower() == 'folder':
                            categories.append({'caption': entry['picto']['caption'], 'id': entry['target']['value_layout']['id']})
                        for group in entry['groups']:
                            for entry in group['entries']:
                                if entry['target']['type'] == 'layout' and entry['target']['value_layout']['type'].lower() == 'folder':
                                    categories.append({'caption': entry['image']['caption'], 'id': entry['target']['value_layout']['id']})
        for category in categories:
            self.addDirectoryItem(py2_encode(category['caption']), 'programs&type=folder&id=%s' % category['id'], '', 'DefaultTVShows.png')
        self.addDirectoryItem(py2_encode("Főoldal"), 'programs&type=alias&id=home', '', 'DefaultTVShows.png')
        self.endDirectory()

    def showPrograms(self, allItems):
        prgs={}
        if allItems:
            for program in allItems:
                prg = {}
                id = program['itemContent']['id']
                title = py2_encode(program['itemContent']['extraTitle'] if program['itemContent']['extraTitle'] else program['itemContent']['title'] if program['itemContent']['title'] else program['itemContent']['image']['caption'])
                if program['itemContent']['title'] and program['itemContent']['title'].lower() not in title.lower():
                    title = "%s [I][LIGHT](%s)[/LIGHT][/I]" % (title, program['itemContent']['title'])
                try: thumb = img_link % program['itemContent']['image']['id']
                except: thumb = ''
                try: fanart = img_link % program['itemContent']['secondaryImage']['id']
                except: fanart = None
                prgType = program['itemContent']['action']['target']['value_layout']['type']
                prgId = program['itemContent']['action']['target']['value_layout']['id']
                plot = py2_encode(program['itemContent']['description'])
                extraInfo = ""
                if program['itemContent']['highlight']:
                    extraInfo = ' [I][COLOR silver](%s)[/COLOR][/I]' % py2_encode(program['itemContent']['highlight'])
                prg = {'title': title, 'type': prgType, 'id': prgId, 'extrainfo': extraInfo, 'fanart': fanart, 'thumb': thumb, 'plot': plot, 'progress': program["itemContent"]["progress"]}
                prgs[id] = prg
            prgIds = list(prgs.keys())
            if (addon().getSetting('sort_programs') == 'true'):
                prgIds = sorted(prgIds, key=lambda x: locale.strxfrm(prgs[x]['title']))
            for prg in prgIds:
                if prgs[prg]['type'] == 'program':
                    self.addDirectoryItem("%s%s" % (prgs[prg]['title'], prgs[prg]['extrainfo']), 'episodes&type=%s&id=%s&fanart=%s' % (prgs[prg]['type'], prgs[prg]['id'], prgs[prg]['fanart']), prgs[prg]['thumb'], 'DefaultTVShows.png', Fanart=prgs[prg]['fanart'], meta={'plot': prgs[prg]['plot']})
                elif prgs[prg]['type'] == 'folder':
                    self.addDirectoryItem(prgs[prg]['title'], 'programs&type=%s&id=%s' % (prgs[prg]['type'], prgs[prg]['id']), '', 'DefaultTVShows.png')
                else:
                    resume = None
                    if self.tracking:
                        if prgs[prg]['progress'] and prgs[prg]['type'] == 'video':
                            clip = json.loads(net.request(api_url % (prgs[prg]['type'], prgs[prg]['id']), headers={'authorization': 'Bearer %s' % player.player().getJwtToken()}))
                            resume = {"resumeTime": clip['blocks'][0]['content']['items'][0]['itemContent']['video']['progress']['tcResume'], "totalTime": clip['blocks'][0]['content']['items'][0]['itemContent']['video']['duration']}
                    self.addDirectoryItem(prgs[prg]['title'] if prgs[prg]['id'] != 'offers' else '[COLOR red]%s[/COLOR]' % prgs[prg]['title'], 'play&type=%s&id=%s&meta=%s&image=%s' % (quote_plus(prgs[prg]['type']), quote_plus(prgs[prg]['id']), quote_plus(json.dumps({'title': prgs[prg]['title'], 'plot': plot, 'duration': 0})), thumb), prgs[prg]['thumb'], 'DefaultTVShows.png', meta={'plot': prgs[prg]['plot']}, isFolder=False, Fanart=prgs[prg]['fanart'], resume=resume)
            self.endDirectory(type='tvshows')

    def programs(self, ptype, pid, blockid=None):
        def getPrograms(ptype, pid):
            tags = []
            currentBlock = None
            data = json.loads(net.request(api_url % (ptype, pid), headers={'authorization': 'Bearer %s' % player.player().getJwtToken()}))
            for block in data['blocks']:
                if block['type'] in ['bffPaginated'] and block['content']['contentTemplateId'] in ['CardM', 'PosterM', 'Jacket', 'Banner'] and block['content']['title']:
                    tags.append({'id': block['id'], 'title': block['content']['title']['long']})
                    currentBlock = block
            return tags, currentBlock

        def getProgramsByBlockId(ptype, pid, blockid):
            return json.loads(net.request(api_block_url % (ptype, pid, blockid, defaultNumberOfPages, 1), headers={'authorization': 'Bearer %s' % player.player().getJwtToken()}))

        def loadAllItems(processBlock, ptype, pid):
            items = processBlock['content']['items']
            if processBlock['content']['pagination']['nextPage']:
                progressDialog = None
                nbPages = (processBlock['content']['pagination']['totalItems'] + processBlock['content']['pagination']['itemsPerPage'] - 1) // processBlock['content']['pagination']['itemsPerPage']
                progressDialog = xbmcgui.DialogProgress()
                progressDialog.create("RTL+", "Programok letöltése folyamatban")
                for page in range(defaultNumberOfPages+1, nbPages + 1, defaultNumberOfPages):
                    currItems = min((page + defaultNumberOfPages - 1) * processBlock['content']['pagination']['itemsPerPage'], processBlock['content']['pagination']['totalItems'])
                    progressDialog.update(int(round(float(page)/nbPages*100)), 'Programok letöltése folyamatban (' + str(currItems) + '/' + str(processBlock['content']['pagination']['totalItems']) + ')')
                    pageData = json.loads(net.request(api_block_url % (ptype, pid, processBlock['id'], defaultNumberOfPages, page), headers={'authorization': 'Bearer %s' % player.player().getJwtToken()}))
                    try:
                        items += pageData['content']['items']
                    except:
                        pass
                    if progressDialog.iscanceled():
                        break
                progressDialog.close()
            return items
        allTags = []
        allItems = []
        processBlock = None
        if not blockid:
            allTags, processBlock = cache.get(getPrograms, self.cacheTime, ptype, pid)
            if len(allTags) > 1:
                for tag in allTags:
                    self.addDirectoryItem(py2_encode(tag['title']), 'programs&type=%s&id=%s&blockid=%s' % (ptype, pid, tag['id']), '', 'DefaultTVShows.png')
                self.endDirectory(type='tvshows')
                return
        else:
            processBlock = cache.get(getProgramsByBlockId, self.cacheTime, ptype, pid, blockid)
        allItems = cache.get(loadAllItems, self.cacheTime, processBlock, ptype, pid)
        self.showPrograms(allItems)

    def episodes(self, ptype, pid, fanart, subcat=None):
        class title_sorter:
            PATTERNS_IN_PRIORITY_ORDER = [
                re.compile(r'^(?P<YEAR>\d{2,4})-(?P<MONTH>\d{2})-(?P<DAY>\d{2})$'),          # Date-only
                re.compile(r'^(?P<SEASON>\d+)\. évad (?P<EPISODE>\d+)\. rész$'),             # Only Season + Episode
                re.compile(r'^(?P<EPISODE>\d+)\. rész$'),                                    # Only Episode
                re.compile(r'.* (?P<YEAR>\d{2,4})-(?P<MONTH>\d{2})-(?P<DAY>\d{2})$'),        # Title + Date
                re.compile(r'.* \((?P<YEAR>\d{2,4})-(?P<MONTH>\d{2})-(?P<DAY>\d{2})\)$'),    # Title + (Date)
                re.compile(r'^(?P<YEAR>\d{2,4})-(?P<MONTH>\d{2})-(?P<DAY>\d{2}) .*'),        # Date + Title
                re.compile(r'.* (?P<SEASON>\d+)\. évad (?P<EPISODE>\d+)\. rész$'),           # Title + Season + Episode
                re.compile(r'.* (?P<EPISODE>\d+)\. rész$')                                   # Title + Episode
            ]

            @classmethod
            def find_first_common_pattern(cls, episodes):
                for pattern in cls.PATTERNS_IN_PRIORITY_ORDER:
                    if all([ pattern.match(ep['itemContent']['extraTitle'] if ep['itemContent']['extraTitle'] != None else '') is not None for ep in episodes ]):
                        return pattern
                return None

            @classmethod
            def all_match_same_pattern(cls, episodes):
                return cls.find_first_common_pattern(episodes) is not None

            @classmethod
            def sorted(cls, episodes, reverse):
                def key(episode):
                    m = pattern.match(episode['itemContent']['extraTitle'] if episode['itemContent']['extraTitle'] != None else '')
                    return tuple(int(i) for i in m.groups())
                pattern = cls.find_first_common_pattern(episodes)
                return sorted(episodes, key=lambda ep: key(ep), reverse=reverse)

        def getClipID(item):
            return py2_encode(item['itemContent']['action']['target']['value_layout']['id'])

        def getSubcatBlock(content):
            for block in content['blocks']:
                if block['id'].split('--')[1] == subcat:
                    return block
            return None

        def getContent(ptype, pid):
            return json.loads(net.request(api_url % (ptype, pid), headers={'authorization': 'Bearer %s' % player.player().getJwtToken()}))

        def getEpisodes(content, currentBlock, hidePlus):
            episodes = currentBlock['content']['items']
            if currentBlock['content']['pagination']['nextPage']:
                nbPages = (currentBlock['content']['pagination']['totalItems'] + currentBlock['content']['pagination']['itemsPerPage'] - 1) // currentBlock['content']['pagination']['itemsPerPage']
                progressDialog = xbmcgui.DialogProgress()
                progressDialog.create("RTL+", "Epizódlista letöltése folyamatban")
                for page in range(defaultNumberOfPages + 1, nbPages + 1, defaultNumberOfPages):
                    currItems = min((page + defaultNumberOfPages - 1) * currentBlock['content']['pagination']['itemsPerPage'], currentBlock['content']['pagination']['totalItems'])
                    progressDialog.update(int(round(float(page)/nbPages*100)), 'Epizódlista letöltése folyamatban (' + str(currItems) + '/' + str(currentBlock['content']['pagination']['totalItems']) + ')')
                    subcontent = json.loads(net.request(api_block_url % (content['entity']['type'], content['entity']['id'], currentBlock['id'], defaultNumberOfPages, page), headers={'authorization': 'Bearer %s' % player.player().getJwtToken()}))
                    try:
                        episodes += subcontent['content']['items']
                    except:
                        pass
                    if progressDialog and progressDialog.iscanceled():
                        break
                progressDialog.close()

            sortedEpisodes = episodes
            if (addon().getSetting('sort_episodes') == 'true'):
                reverseSorting = False
                if (addon().getSetting('sort_reverse') == 'true'):
                    reverseSorting = True
                if title_sorter.all_match_same_pattern(episodes):
                    sortedEpisodes = title_sorter.sorted(episodes, reverse=reverseSorting)
                else:
                    sortedEpisodes = sorted(episodes, key=getClipID, reverse=reverseSorting)
            return sortedEpisodes

        content = cache.get(getContent, self.cacheTime, ptype, pid)
        subcats = []
        if subcat == None:
            for block in content['blocks']:
                if block['type'] in ['bffPaginated'] and block['content']['contentTemplateId'] in ['CardM', 'PosterM']:
                    title = None
                    if block['content']['title']:
                        if block['content']['title']['long']:
                            title = block['content']['title']['long']
                        else:
                            if block['content']['title']['short']:
                                title = block['content']['title']['short']
                            else:
                                title = "Általános"
                    else:
                        title = "Egyéb"
                    subcats.append({'title': title, 'subcat': block['id'].split('--')[1]})
                else:
                    if 'featureId' in block and block['featureId'] in ['channels_by_platform', 'lives_by_services']:
                        subcats = []
                        subcat = block['id'].split('--')[1]
                        break
        """if len(subcats) == 0:
            for block in content['blocks']:
                if block['featureId'] in ['info_by_program']:
                    subcats.append({'title': '', 'subcat': block['id'].split('--')[1]})
        """
        if len(subcats) > 1:
            sortedSubcats = subcats
            #sortedSubcats = sorted(subcats, key=lambda x: locale.strxfrm(x['title']))
            for s in sortedSubcats:
                self.addDirectoryItem(py2_encode(s['title']), 'episodes&type=%s&id=%s&fanart=%s&subcat=%s' % (ptype, pid, fanart, s['subcat']), '', 'DefaultFolder.png', Fanart=fanart)
            self.endDirectory(type='seasons')
            return

        if subcat == None and len(subcats) == 1:
            subcat = subcats[0]['subcat']

        currentBlock = getSubcatBlock(content)

        if currentBlock == None:
            return

        hidePlus = addon().getSetting('hide_plus') == 'true'

        sortedEpisodes = cache.get(getEpisodes, self.cacheTime, content, currentBlock, hidePlus)

        hasItemsListed = False

        if sortedEpisodes:
            for item in sortedEpisodes:
                #try:
                    eligible = item['itemContent']['action']['target']['value_layout']['id'] != 'offers'
                    if (not hidePlus) or eligible:
                        title = py2_encode("%s" % item['itemContent']['extraTitle'] if item['itemContent']['extraTitle'] != None else item['itemContent']['analytics']['googleAnalytics']['eventLabel'] if item['itemContent']['analytics'] != None and item['itemContent']['analytics']['googleAnalytics'] != None and item['itemContent']['analytics']['googleAnalytics']['eventLabel'] != None else item['itemContent']['image']['caption'] if item['itemContent']['image'] != None and item['itemContent']['image']['caption'] != None else content['entity']['metadata']['title'])
                        if item['itemContent']['title'] and item['itemContent']['title'].lower() not in title.lower():
                            title = "%s [I][LIGHT](%s)[/LIGHT][/I]" % item['itemContent']['title']
                        if not eligible:
                            title = '[COLOR red]' + title + '[/COLOR]'
                        plot = py2_encode(item['itemContent']['description'])
                        match = re.match(r'^([0-9]*):([0-9]*)$', item['itemContent']['highlight']) if item['itemContent']['highlight'] else None
                        if match:
                            duration = str(int(match.group(1))*60 + int(match.group(2)))
                        else:
                            match = re.match(r'^([0-9]*):([0-9]*):([0-9]*)$', item['itemContent']['highlight']) if item['itemContent']['highlight'] else None
                            if match:
                                duration = str(int(match.group(1))*60*60 + int(match.group(2))*60 + int(match.group(3)))
                            else:
                                duration = '0'
                        thumb = img_link % item['itemContent']['image']['id']
                        clip_id = py2_encode(item['itemContent']['action']['target']['value_layout']['id'])
                        clip_type = py2_encode(item['itemContent']['action']['target']['value_layout']['type'])
                        meta = {'title': title, 'plot': plot, 'duration': duration}
                        if clip_type == 'folder':
                            self.addDirectoryItem(title, 'episodes&type=%s&id=%s&fanart=%s' % (quote_plus(clip_type), quote_plus(clip_id), fanart), thumb, 'DefaultFolder.png', Fanart=fanart)
                        else:
                            resume = None
                            if self.tracking:
                                if item['itemContent']['progress'] and clip_type == 'video':
                                    if self.trackingpreload:
                                        clip = json.loads(net.request(api_url % (clip_type, clip_id), headers={'authorization': 'Bearer %s' % player.player().getJwtToken()}))
                                        resume = {"resumeTime": clip['blocks'][0]['content']['items'][0]['itemContent']['video']['progress']['tcResume'], "totalTime": clip['blocks'][0]['content']['items'][0]['itemContent']['video']['duration']}
                                    else:
                                        resume = {"resumeTime": int(duration)/100*item['itemContent']['progress'], "totalTime": int(duration)}
                            self.addDirectoryItem(title, 'play&type=%s&id=%s&meta=%s&image=%s' % (quote_plus(clip_type), quote_plus(clip_id), quote_plus(json.dumps(meta)), thumb), thumb, 'DefaultTVShows.png', meta=meta, isFolder=False, Fanart=fanart, resume=resume)
                        hasItemsListed = True
                #except:
                #    pass
        self.endDirectory(type='episodes')

        if hidePlus and not hasItemsListed and len(sortedEpisodes) > 0:
            xbmcgui.Dialog().ok('RTL+', package_change_needed)
            xbmc.executebuiltin("XBMC.Action(Back)")

    def get_video(self, ptype, pid, meta, image, firstplay=True):
        clip = net.request(api_url % (ptype, pid), headers={'authorization': 'Bearer %s' % player.player().getJwtToken()})
        clip = json.loads(clip)
        try:    
            assets = clip['blocks'][0]['content']['items'][0]['itemContent']['video']['assets']
        except:
            assets = None
        if assets is not None and assets != []:
            streams = [i['path'] for i in assets]
            if player.player().play(ptype, pid, streams, image, meta, clip['blocks'][0]['content']['items'][0]['itemContent']['video']['duration'], clip['blocks'][0]['content']['items'][0]['itemContent']['video']['progress']['tcResume'] if clip['blocks'][0]['content']['items'][0]['itemContent']['progress'] else None, clip['blocks'][0]['content']['items'][0]['itemContent']['analytics']['heartbeat-v2'], firstplay):
                if self.autoplaynext:
                    if len(clip['blocks'][0]['content']['items'])>0:
                        item = clip['blocks'][0]['content']['items'][1]
                        clip_id = py2_encode(item['itemContent']['action']['target']['value_layout']['id'])
                        clip_type = py2_encode(item['itemContent']['action']['target']['value_layout']['type'])
                        if clip_type == 'video':
                            title = py2_encode("%s" % item['itemContent']['extraTitle'] if item['itemContent']['extraTitle'] != None else item['itemContent']['analytics']['googleAnalytics']['eventLabel'] if item['itemContent']['analytics'] != None and item['itemContent']['analytics']['googleAnalytics'] != None and item['itemContent']['analytics']['googleAnalytics']['eventLabel'] != None else item['itemContent']['image']['caption'] if item['itemContent']['image'] != None and item['itemContent']['image']['caption'] != None else content['entity']['metadata']['title'])
                            if item['itemContent']['title'] and item['itemContent']['title'].lower() not in title.lower():
                                title = "%s (%s)" % (title, item['itemContent']['title'])
                            thumb = img_link % item['itemContent']['image']['id']
                            plot = py2_encode(item['itemContent']['description'])
                            match = re.match(r'^([0-9]*):([0-9]*)$', item['itemContent']['highlight']) if item['itemContent']['highlight'] else None
                            if match:
                                duration = str(int(match.group(1))*60 + int(match.group(2)))
                            else:
                                match = re.match(r'^([0-9]*):([0-9]*):([0-9]*)$', item['itemContent']['highlight']) if item['itemContent']['highlight'] else None
                                if match:
                                    duration = str(int(match.group(1))*60*60 + int(match.group(2))*60 + int(match.group(3)))
                                else:
                                    duration = '0'
                            meta = {'title': title, 'plot': plot, 'duration': duration}
                            progressDialog = xbmcgui.DialogProgress()
                            progressDialog.create("RTL+", "Következő videó lejátszása %d másodperc múlva:\n%s" % (10, title))
                            cancelled = False
                            for sec in range(100, 0, -1):
                                progressDialog.update(sec, 'Következő videó lejátszása %d másodperc múlva:\n%s' % (int(sec/10)+1, title))
                                xbmc.sleep(100)
                                if progressDialog.iscanceled():
                                    cancelled = True
                                    break
                            progressDialog.close()
                            if not cancelled:
                                self.get_video(clip_type, clip_id, json.dumps(meta), thumb, False)
                            return
        else:
            xbmcgui.Dialog().ok(u'Lej\u00E1tsz\u00E1s sikertelen.', package_change_needed)
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), False, xbmcgui.ListItem())

    def setDeviceID(self):
        if addon().getSetting('deviceid') == "":
            deviceID = "_luid_%s" % str(uuid.uuid4())
            addon().setSetting('deviceid', deviceID)

    def consentOnDevice(self, jwtToken):
        device_consents_url = 'https://6play-users.6play.fr/v2/platforms/m6group_web/users/deviceid-%s/consents'
        net.request(device_consents_url % addon().getSetting('deviceid'), post='{"analytics":{"consent":true,"form":"explicit"},"adtargeting":{"consent":true,"form":"explicit"},"personalization":{"consent":true,"form":"explicit"},"multidevicematching":{"consent":true,"form":"explicit"}}'.encode('utf-8'), headers={'authorization': 'Bearer %s' % jwtToken, 'content-type': 'application/json'})

    def Login(self):
        t1 = int(addon().getSetting('s.timestamp'))
        t2 = int(time.time())
        update = (abs(t2 - t1) / 3600) >= 24 or t1 == 0
        if update == False:
            return

        login_url = 'https://accounts.%s/accounts.login'
        plusz_baseUrl = 'https://www.rtlplusz.hu'

        plusz_source = net.request(plusz_baseUrl)
        scripts = re.findall(r'<script.*src="([^"]*)".*type="module"', plusz_source)
        api_cdn = None
        api_key = None
        for script in scripts:
            js_source = net.request(urlparse.urljoin(plusz_baseUrl, script))
            api_src = re.findall(r',([^}]+login.rtlmost.hu[^}]+})', js_source)
            if api_src:
                api_src = json.loads(re.sub(r'([{,:])(\w+)([},:])','\\1\"\\2\"\\3', "{%s" % api_src[0]))
                api_cdn = api_src['cdn']
                api_key = api_src['key']
                xbmc.log('RTL+: API data found in %s javascript' % script, xbmc.LOGINFO)
                break
            else:
                xbmc.log('RTL+: API data not found in %s javascripts trying to found gigya data' % script, xbmc.LOGINFO)
                js_source = net.request(urlparse.urljoin(plusz_baseUrl, script))
                gigya_start = js_source.find('"gigya":{')
                if gigya_start > 0:
                    bracketCnt = 1
                    max_possible_length = 5000
                    pos = gigya_start + len('"gigya":{')
                    while bracketCnt > 0 and pos < len(js_source) and pos < gigya_start + max_possible_length:
                        if js_source[pos] == '{':
                            bracketCnt += 1
                        if js_source[pos] == '}':
                            bracketCnt -= 1
                        pos += 1
                    if bracketCnt == 0:
                        data = json.loads("{%s}" % js_source[gigya_start:pos])
                        xbmc.log('RTL+: API data found in client js', xbmc.LOGINFO)
                        api_cdn = data['gigya']['cdn']
                        api_key = data['gigya']['key']
                        xbmc.log('RTL+: gigya API data found in %s javascript' % script, xbmc.LOGINFO)
                        break
                    else:
                        xbmc.log('RTL+: Error on finding gigya JSON end in %s javascript!' % script)
                else:
                    xbmc.log('RTL+: gigya JSON data not found in %s javascript!' % script, xbmc.LOGERROR)
        if api_cdn and api_key:
            r = net.request(login_url % api_cdn, post={'loginID': self.username, 'password': self.password, 'APIKey': api_key})
            jsonparse = json.loads(r)

            if 'errorMessage' in jsonparse:
                xbmcgui.Dialog().ok(u'Bejelentkez\u00E9si hiba', jsonparse['errorMessage'])
                addon().setSetting('loggedin', 'false')
                addon().setSetting('s.timestamp', '0')
                sys.exit(0)

            addon().setSetting('userid', jsonparse['UID'])
            addon().setSetting('signature', jsonparse['UIDSignature'])
            addon().setSetting('s.timestamp', jsonparse['signatureTimestamp'])
            addon().setSetting('loggedin', 'true')

            jwtToken = player.player().getJwtToken()
            self.consentOnDevice(jwtToken)
            r = net.request(profile_url % addon().getSetting('userid'), headers={'authorization': 'Bearer %s' % jwtToken})
            js = json.loads(r)
            addon().setSetting('profileid', js[0]['uid'])
            addon().setSetting('jwttoken', '')
            jwtToken = player.player().getJwtToken()
            accountOverview = json.loads(net.request(account_overview_url, headers={'authorization': 'Bearer %s' % jwtToken}))
            if accountOverview['redirection'] and accountOverview['redirection']['reasonCode'] == 'devices_gate':
                xbmcgui.Dialog().ok(u'RTL+ hiba', 'Elérted a párosítható eszközök maximumát! A folytatáshoz a következő ablakban, a párosított eszközök kezelése menüpontban, vagy az RTL+ weboldalán válassz le egy már csatlakoztatott eszközt!')
                addon().setSetting('loggedin', 'false')
                if self.deleteDevice():
                    addon().setSetting('s.timestamp', '0')
                    self.Login()
                else:
                    sys.exit(0)
            return
        else:
            xbmcgui.Dialog().ok(u'Bejelentkez\u00E9si hiba', 'Hiba a bejelentkezéshez szükséges adatok kinyerésekor!')
        addon().setSetting('loggedin', 'false')
        addon().setSetting('s.timestamp', '0')
        sys.exit(0)

    def Logout(self):
        dialog = xbmcgui.Dialog()
        if 1 == dialog.yesno(u'RTL+ kijelentkez\u00E9s', u'Val\u00F3ban ki szeretn\u00E9l jelentkezni?', '', ''):
            net.request(revoke_current_device_url, headers={'authorization': 'Bearer %s' % player.player().getJwtToken()}, isPatchRequest = True)
            addon().setSetting('userid', '')
            addon().setSetting('signature', '')
            addon().setSetting('s.timestamp', '0')
            addon().setSetting('loggedin', 'false')
            addon().setSetting('email', '')
            addon().setSetting('password', '')
            addon().setSetting('deviceid', '')
            addon().setSetting('jwttoken', '')
            addon().setSetting('profileid', '')
            addon().setSetting('subscriptionname', '')
            xbmc.executebuiltin("XBMC.Container.Update(path,replace)")
            xbmc.executebuiltin("XBMC.ActivateWindow(Home)")
            dialog.ok('RTL+', u'Sikeresen kijelentkezt\u00E9l.\nAz adataid t\u00F6r\u00F6lve lettek a kieg\u00E9sz\u00EDt\u0151b\u0151l.')
        
        return

    def doSearch(self, search):
        postStr = '{"requests":[{"indexName":"rtlmutu_prod_bedrock_layout_items_v2_rtlhu_main","query":"' + search + '","params":"hitsPerPage=100&clickAnalytics=false&facetFilters=%5B%5B%22metadata.item_type%3Aprogram%22%5D%2C%5B%22metadata.platforms_assets%3Am6group_web%22%5D%5D"}]}'
        data = json.loads(net.request(search_url, headers={'x-algolia-api-key': search_api_key, 'x-algolia-application-id': search_application_id},post=postStr.encode('utf-8')))
        allItems = []
        for result in data['results']:
            if result['hits']:
                for item in result['hits']:
                    allItems.append(item['item'])
                break
        self.showPrograms(allItems)

    def getSearches(self):
        self.addDirectoryItem('[COLOR lightgreen]Új keresés[/COLOR]', 'newsearch', '', 'DefaultFolder.png')
        try:
            file = open(self.searchFileName, "r")
            olditems = file.read().splitlines()
            file.close()
            items = list(set(olditems))
            items.sort(key=locale.strxfrm)
            if len(items) != len(olditems):
                file = open(self.searchFileName, "w")
                file.write("\n".join(items))
                file.close()
            for item in items:
                self.addDirectoryItem(item, 'search&search=%s' % quote_plus(item), '', 'DefaultFolder.png')
            if len(items) > 0:
                self.addDirectoryItem('[COLOR red]Keresési előzmények törlése[/COLOR]', 'deletesearchhistory', '', 'DefaultFolder.png')
        except:
            pass
        self.endDirectory()

    def newSearch(self):
        search_text = self.getSearchText()
        if search_text != '':
            if not os.path.exists(self.base_path):
                os.mkdir(self.base_path)
            file = open(self.searchFileName, "a")
            file.write("%s\n" % search_text)
            file.close()
            self.doSearch(search_text)

    def deleteSearchHistory(self):
        if xbmcgui.Dialog().yesno("RTL+", "Biztosan törli a keresési előzményeket?"):
            if os.path.exists(self.searchFileName):
                os.remove(self.searchFileName)

    def getSearchText(self):
        search_text = ''
        keyb = xbmc.Keyboard('',u'Add meg a keresend\xF5 film c\xEDm\xE9t')
        keyb.doModal()

        if (keyb.isConfirmed()):
            search_text = keyb.getText()

        return search_text

    def addDirectoryItem(self, name, query, thumb, icon, context=None, queue=False, isAction=True, isFolder=True, Fanart=None, meta=None, resume=None):
        url = '%s?action=%s' % (sysaddon, query) if isAction == True else query
        if thumb == '': thumb = icon
        cm = []
        if queue == True: cm.append((queueMenu, 'RunPlugin(%s?action=queueItem)' % sysaddon))
        if not context == None: cm.append((py2_encode(context[0]), 'RunPlugin(%s?action=%s)' % (sysaddon, context[1])))
        item = xbmcgui.ListItem(label=name)
        item.addContextMenuItems(cm)
        item.setArt({'icon': thumb, 'thumb': thumb, 'poster': thumb})
        if Fanart == None: Fanart = addonFanart
        item.setProperty('Fanart_Image', Fanart)
        if isFolder == False: 
            item.setProperty('IsPlayable', 'true')
            if resume:
                if resume["resumeTime"] > resume["totalTime"]-10:
                    item.setInfo('video', {'playcount': 1})
                else:
                    try:
                        item.getVideoInfoTag().setResumePoint(resume["resumeTime"], resume["totalTime"])
                    except:
                        xbmc.log('RTL+: Error on setResumePoint call, probably we are on old Kodi version', xbmc.LOGERROR)
        if not meta == None: item.setInfo(type='Video', infoLabels = meta)
        xbmcplugin.addDirectoryItem(handle=syshandle, url=url, listitem=item, isFolder=isFolder)

    def endDirectory(self, type='addons'):
        xbmcplugin.setContent(syshandle, type)
        #xbmcplugin.addSortMethod(syshandle, xbmcplugin.SORT_METHOD_TITLE)
        xbmcplugin.endOfDirectory(syshandle, cacheToDisc=True)

    def deleteDevice(self):
        data = json.loads(net.request(devices_management_url, headers={'authorization': 'Bearer %s' % player.player().getJwtToken()}))
        devicesBlock = None
        for block in data['blocks']:
            if block['analytics']['googleAnalytics']['eventCategory'] == 'devices_by_user':
                devicesBlock = block
                break
        if devicesBlock:
            devices = devicesBlock['content']['items']
            connectedItems = []
            for item in devices:
                li = xbmcgui.ListItem(item['itemContent']['title'], "%s%s" % (py2_encode(item['itemContent']['extraTitle']), " - [COLOR red]Jelenlegi eszköz[/COLOR]" if 'Jelenlegi' in py2_encode(item['itemContent']['action']['label']) else ""))
                connectedItems.append(li)
            itemIndex = xbmcgui.Dialog().select("RTL+ - Párosított eszköz törlése", connectedItems, useDetails = True)
            if itemIndex >= 0:
                if 'Jelenlegi' in py2_encode(devices[itemIndex]['itemContent']['action']['label']):
                    xbmcgui.Dialog().ok("RTL+", "A jelenlegi eszköz párosítása nem törölhető!")
                else:
                    if xbmcgui.Dialog().yesno("RTL+", "Biztosan törli a %s párosítását?" % py2_encode(devices[itemIndex]['itemContent']['title'])):
                        postData = '{"deviceId": "%s"}' % devices[itemIndex]['itemContent']['action']['target']['value_lock']['reasonAttributes']['deviceId']
                        result = json.loads(net.request(delete_device_url, post=postData.encode('utf-8'), headers={'authorization': 'Bearer %s' % player.player().getJwtToken()}, isPatchRequest = True))
                        if result["status"] == "torevoke":
                            return True
                        else:
                            xbmcgui.Dialog().ok("RTL+", "A párosítás törlése sikertelen!")
        else:
            xbmcgui.Dialog().ok("RTL+", "Hiba az eszközök lekérése során! Kérlek töröld a beállításokat, vagy jelentkezz ki a kiegészítő beállításaiban!")
        return False

    def clearCache(self):
        cache.clear()
