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


import os,sys,re,xbmc,xbmcgui,xbmcplugin,xbmcaddon,urllib,json,time,locale
from resources.lib.modules import net
from  collections import OrderedDict
from resources.lib.modules import player

if sys.version_info[0] == 3:
    import urllib.parse as urlparse
    from urllib.parse import quote_plus
else:
    import urlparse
    from urllib import quote_plus

from resources.lib.modules.utils import py2_encode


sysaddon = sys.argv[0] ; syshandle = int(sys.argv[1])
addon = xbmcaddon.Addon
addonFanart = addon().getAddonInfo('fanart')

img_link = 'https://images-fio.6play.fr/v2/images/%s/raw'
package_change_needed = 'A hozzáféréshez nagyobb csomagra váltás szükséges.\nRészletek: https://rtl.hu/rtlplusz/szolgaltatasok'
deviceID_url = 'https://e.m6web.fr/info?customer=rtlhu'
profile_url = 'https://6play-users.6play.fr/v2/platforms/m6group_web/users/%s/profiles'
api_base = 'https://layout.6cloud.fr/front/v1/rtlhu/m6group_web/main/token-web-3/%s/%s/'
defaultNumberOfPages = 2
api_url = api_base + 'layout?nbPages=%d' % defaultNumberOfPages
api_block_url = api_base + 'block/%s?nbPages=%d&page=%d'

class navigator:
    def __init__(self):
        try:
            locale.setlocale(locale.LC_ALL, "")
        except:
            pass
        self.username = xbmcaddon.Addon().getSetting('email').strip()
        self.password = xbmcaddon.Addon().getSetting('password').strip()

        if not (self.username and self.password) != '':
            if xbmcgui.Dialog().ok('RTL+', u'A kieg\u00E9sz\u00EDt\u0151 haszn\u00E1lat\u00E1hoz add meg a bejelentkez\u00E9si adataidat.'):
                xbmc.executebuiltin('Dialog.Close(busydialognocancel)')
                addon(addon().getAddonInfo('id')).openSettings()
            self.username = xbmcaddon.Addon().getSetting('email').strip()
            self.password = xbmcaddon.Addon().getSetting('password').strip()
        if xbmcaddon.Addon().getSetting('deviceid') == "":
            r = net.request(deviceID_url)
            jsonparse = json.loads(r)
            xbmcaddon.Addon().setSetting('deviceid', jsonparse['device_id'])
        self.Login()


    def root(self):
        data = json.loads(net.request(api_url % ('alias', 'home'), headers={'authorization': 'Bearer %s' % player.player().getJwtToken()}))
        for block in data['blocks']:
            if block['featureId'] == 'folders_by_service' and block['title']:
                xbmcgui.Dialog().notification("RTL+", block['title']['long'])
                allCategory = block['content']['items']
                if block['content']['pagination']['nextPage']:
                    progressDialog = xbmcgui.DialogProgress()
                    progressDialog.create("RTL+", "Kategóriák letöltése folyamatban")
                    nbPages = (block['content']['pagination']['totalItems'] + block['content']['pagination']['itemsPerPage'] -1) // block['content']['pagination']['itemsPerPage']
                    for page in range(defaultNumberOfPages + 1, nbPages + 1, defaultNumberOfPages):
                        currItems = min((page + defaultNumberOfPages + 1) * block['content']['pagination']['itemsPerPage'], block['content']['pagination']['totalItems'])
                        progressDialog.update(round(page/nbPages*100), 'Kategóriák letöltése folyamatban (' + str(currItems) + '/' + str(block['content']['pagination']['totalItems']) + ')')
                        pageData = json.loads(net.request(api_block_url % (data['entity']['type'], data['entity']['id'], block['id'], defaultNumberOfPages, page), headers={'authorization': 'Bearer %s' % player.player().getJwtToken()}))
                        try:
                            allCategory += pageData['content']['items']
                        except:
                            pass
                        if progressDialog.iscanceled():
                            break
                    progressDialog.close()
                for category in allCategory:
                    if category['itemContent']['id'] != 'ec439707a9ef0bfc8f74a020859513ab1c022b91':
                        self.addDirectoryItem(py2_encode(category['itemContent']['image']['caption']), 'programs&type=%s&id=%s' % (category['itemContent']['action']['target']['value_layout']['type'], category['itemContent']['action']['target']['value_layout']['id']), '', 'DefaultTVShows.png')
                break
        self.endDirectory()

    def programs(self, ptype, pid):
        data = json.loads(net.request(api_url % (ptype, pid), headers={'authorization': 'Bearer %s' % player.player().getJwtToken()}))
        prgs={}
        for block in data['blocks']:
            if block['featureId'] == 'programs_by_folder_by_service' and (not block['title'] or (block['title'] and block['title']['long'] and 'TOP' not in block['title']['long'])):
                allItems = block['content']['items']
                if block['content']['pagination']['nextPage']:
                    progressDialog = None
                    nbPages = (block['content']['pagination']['totalItems'] + block['content']['pagination']['itemsPerPage'] - 1) // block['content']['pagination']['itemsPerPage']
                    progressDialog = xbmcgui.DialogProgress()
                    progressDialog.create("RTL+", "Programok letöltése folyamatban")
                    for page in range(defaultNumberOfPages+1, nbPages + 1, defaultNumberOfPages):
                        currItems = min((page + defaultNumberOfPages - 1) * block['content']['pagination']['itemsPerPage'], block['content']['pagination']['totalItems'])
                        progressDialog.update(round(page/nbPages*100), 'Programok letöltése folyamatban (' + str(currItems) + '/' + str(block['content']['pagination']['totalItems']) + ')')
                        pageData = json.loads(net.request(api_block_url % (data['entity']['type'], data['entity']['id'], block['id'], defaultNumberOfPages, page), headers={'authorization': 'Bearer %s' % player.player().getJwtToken()}))
                        try:
                            allItems += pageData['content']['items']
                        except:
                            pass
                        if progressDialog.iscanceled():
                            break
                    progressDialog.close()
                for program in allItems:
                    prg = {}
                    title = py2_encode(program['itemContent']['title'])
                    try: thumb = img_link % program['itemContent']['image']['id']
                    except: thumb = ''
                    try: fanart = img_link % program['itemContent']['secondaryImage']['id']
                    except: fanart = None
                    prgType = program['itemContent']['action']['target']['value_layout']['type']
                    prgId = program['itemContent']['action']['target']['value_layout']['id']
                    plot = py2_encode(program['itemContent']['description'])
                    extraInfo = ""
                    if program['itemContent']['highlight']:
                        extraInfo = ' [I][COLOR silver](%s)[/COLOR][/I]' % program['itemContent']['highlight']
                    prg = {'type': prgType, 'id': prgId, 'extrainfo': extraInfo, 'fanart': fanart, 'thumb': thumb, 'plot': plot}
                    prgs[title] = prg
                break
        prgTitles = list(prgs.keys())
        if (xbmcaddon.Addon().getSetting('sort_programs') == 'true'):
            prgTitles.sort(key=locale.strxfrm)
        for prg in prgTitles:
            self.addDirectoryItem("%s%s" % (prg, prgs[prg]['extrainfo']), 'episodes&type=%s&id=%s&fanart=%s' % (prgs[prg]['type'], prgs[prg]['id'], prgs[prg]['fanart']), prgs[prg]['thumb'], 'DefaultTVShows.png', Fanart=prgs[prg]['fanart'], meta={'plot': prgs[prg]['plot']})
        self.endDirectory(type='tvshows')

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

        content = json.loads(net.request(api_url % (ptype, pid), headers={'authorization': 'Bearer %s' % player.player().getJwtToken()}))
        subcats = []
        if subcat == None:
            for block in content['blocks']:
                if block['featureId'] in ['videos_by_subcat_by_program', 'videos_by_season_by_program']:
                    subcats.append({'title': block['title']['long'], 'subcat': block['id'].split('--')[1]})

        if len(subcats) == 0:
            for block in content['blocks']:
                if block['featureId'] == 'info_by_program':
                    subcats.append({'title': '', 'subcat': block['id'].split('--')[1]})

        if len(subcats) > 1:
            for s in subcats:
                self.addDirectoryItem(py2_encode(s['title']), 'episodes&type=%s&id=%s&fanart=%s&subcat=%s' % (ptype, pid, fanart, s['subcat']), '', 'DefaultFolder.png', Fanart=fanart)
            self.endDirectory(type='seasons')
            return

        if subcat == None and len(subcats) == 1:
            subcat = subcats[0]['subcat']

        currentBlock = getSubcatBlock(content)

        if currentBlock == None:
            return

        episodes = currentBlock['content']['items']
        if currentBlock['content']['pagination']['nextPage']:
            nbPages = (currentBlock['content']['pagination']['totalItems'] + currentBlock['content']['pagination']['itemsPerPage'] - 1) // currentBlock['content']['pagination']['itemsPerPage']
            progressDialog = xbmcgui.DialogProgress()
            progressDialog.create("RTL+", "Epizódlista letöltése folyamatban")
            for page in range(defaultNumberOfPages + 1, nbPages + 1, defaultNumberOfPages):
                currItems = min((page + defaultNumberOfPages - 1) * currentBlock['content']['pagination']['itemsPerPage'], currentBlock['content']['pagination']['totalItems'])
                progressDialog.update(round(page/nbPages*100), 'Epizódlista letöltése folyamatban (' + str(currItems) + '/' + str(currentBlock['content']['pagination']['totalItems']) + ')')
                subcontent = json.loads(net.request(api_block_url % (content['entity']['type'], content['entity']['id'], currentBlock['id'], defaultNumberOfPages, page), headers={'authorization': 'Bearer %s' % player.player().getJwtToken()}))
                try:
                    episodes += subcontent['content']['items']
                except:
                    pass
                if progressDialog and progressDialog.iscanceled():
                    break
            progressDialog.close()
        hidePlus = xbmcaddon.Addon().getSetting('hide_plus') == 'true'

        sortedEpisodes = episodes
        if (xbmcaddon.Addon().getSetting('sort_episodes') == 'true'):
            reverseSorting = False
            if (xbmcaddon.Addon().getSetting('sort_reverse') == 'true'):
                reverseSorting = True
            if title_sorter.all_match_same_pattern(episodes):
                sortedEpisodes = title_sorter.sorted(episodes, reverse=reverseSorting)
            else:
                sortedEpisodes = sorted(episodes, key=getClipID, reverse=reverseSorting)

        hasItemsListed = False

        for item in sortedEpisodes:
            try:
                eligible = item['itemContent']['action']['target']['value_layout']['id'] != 'offers'
                if (not hidePlus) or eligible:
                    title = py2_encode(item['itemContent']['extraTitle'] if item['itemContent']['extraTitle'] != None else content['entity']['metadata']['title'])
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
                    self.addDirectoryItem(title, 'play&type=%s&id=%s&meta=%s&image=%s' % (quote_plus(clip_type), quote_plus(clip_id), quote_plus(json.dumps(meta)), thumb), thumb, 'DefaultTVShows.png', meta=meta, isFolder=False, Fanart=fanart)
                    hasItemsListed = True
            except:
                pass

        self.endDirectory(type='episodes')

        if hidePlus and not hasItemsListed and len(sortedEpisodes) > 0:
            xbmcgui.Dialog().ok('RTL+', package_change_needed)
            xbmc.executebuiltin("XBMC.Action(Back)")

    def get_video(self, ptype, pid, meta, image):
        clip = net.request(api_url % (ptype, pid), headers={'authorization': 'Bearer %s' % player.player().getJwtToken()})
        clip = json.loads(clip)
        try:
            assets = clip['blocks'][0]['content']['items'][0]['itemContent']['video']['assets']
        except:
            assets = None
        if assets is not None and assets != []:
            streams = [i['path'] for i in assets]
            player.player().play(ptype, pid, streams, image, meta)
        else:
            xbmcgui.Dialog().ok(u'Lej\u00E1tsz\u00E1s sikertelen.', package_change_needed)
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), False, xbmcgui.ListItem())

    def Login(self):
        t1 = int(xbmcaddon.Addon().getSetting('s.timestamp'))
        t2 = int(time.time())
        update = (abs(t2 - t1) / 3600) >= 24 or t1 == 0
        if update == False:
            return

        login_url = 'https://accounts.%s/accounts.login?loginID=%s&password=%s&targetEnv=mobile&format=jsonp&apiKey=%s&callback=jsonp&include=data'
        most_baseUrl = 'https://www.rtlmost.hu'

        most_source = net.request(most_baseUrl)
        main_js = re.search('''<script async data-chunk="main" src=['"](\/main-.+?)['"]''', most_source).group(1)
        api_src = net.request(urlparse.urljoin(most_baseUrl, main_js))
        api_src = re.findall('gigya\s*:\s*(\{[^\}]+\})', api_src)
        api_src = [i for i in api_src if 'login.rtlmost.hu' in i][0]
        api_src = json.loads(re.sub('([{,:])(\w+)([},:])','\\1\"\\2\"\\3', api_src))

        r = net.request(login_url % (api_src['cdn'], self.username, quote_plus(self.password), api_src['key']))
        r = re.search('\(([^\)]+)', r).group(1)
        jsonparse = json.loads(r)

        if 'errorMessage' in jsonparse:
            xbmcgui.Dialog().ok(u'Bejelentkez\u00E9si hiba', jsonparse['errorMessage'])
            xbmcaddon.Addon().setSetting('loggedin', 'false')
            xbmcaddon.Addon().setSetting('s.timestamp', '0')
            sys.exit(0)

        xbmcaddon.Addon().setSetting('userid', jsonparse['UID'])
        xbmcaddon.Addon().setSetting('signature', jsonparse['UIDSignature'])
        xbmcaddon.Addon().setSetting('s.timestamp', jsonparse['signatureTimestamp'])
        xbmcaddon.Addon().setSetting('loggedin', 'true')

        r = net.request(deviceID_url)
        jsonparse = json.loads(r)
        xbmcaddon.Addon().setSetting('deviceid', jsonparse['device_id'])
        jwtToken = player.player().getJwtToken()
        r = net.request(profile_url % xbmcaddon.Addon().getSetting('userid'), headers={'authorization': 'Bearer %s' % jwtToken})
        js = json.loads(r)
        xbmcaddon.Addon().setSetting('profileid', js[0]['uid'])
        xbmcaddon.Addon().setSetting('jwttoken', '')
        player.player().getJwtToken()



    def Logout(self):
        dialog = xbmcgui.Dialog()
        if 1 == dialog.yesno(u'RTL+ kijelentkez\u00E9s', u'Val\u00F3ban ki szeretn\u00E9l jelentkezni?', '', ''):
            xbmcaddon.Addon().setSetting('userid', '')
            xbmcaddon.Addon().setSetting('signature', '')
            xbmcaddon.Addon().setSetting('s.timestamp', '0')
            xbmcaddon.Addon().setSetting('loggedin', 'false')
            xbmcaddon.Addon().setSetting('email', '')
            xbmcaddon.Addon().setSetting('password', '')
            xbmcaddon.Addon().setSetting('deviceid', '')
            xbmcaddon.Addon().setSetting('jwttoken', '')
            xbmcaddon.Addon().setSetting('deviceid', '')
            xbmc.executebuiltin("XBMC.Container.Update(path,replace)")
            xbmc.executebuiltin("XBMC.ActivateWindow(Home)")
            dialog.ok('RTL+', u'Sikeresen kijelentkezt\u00E9l.\nAz adataid t\u00F6r\u00F6lve lettek a kieg\u00E9sz\u00EDt\u0151b\u0151l.')
        
        return


    def addDirectoryItem(self, name, query, thumb, icon, context=None, queue=False, isAction=True, isFolder=True, Fanart=None, meta=None):
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
        if isFolder == False: item.setProperty('IsPlayable', 'true')
        if not meta == None: item.setInfo(type='Video', infoLabels = meta)
        xbmcplugin.addDirectoryItem(handle=syshandle, url=url, listitem=item, isFolder=isFolder)


    def endDirectory(self, type='addons'):
        xbmcplugin.setContent(syshandle, type)
        #xbmcplugin.addSortMethod(syshandle, xbmcplugin.SORT_METHOD_TITLE)
        xbmcplugin.endOfDirectory(syshandle, cacheToDisc=True)
