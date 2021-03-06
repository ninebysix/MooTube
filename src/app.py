#----------------------------------------------------------------------
# MooTube
# by Jake Day
# v1.3
# YouTube App for Mobile Linux
#----------------------------------------------------------------------

import ctypes, os, requests, io, sys, subprocess, gi, json, threading, locale
from urllib.parse import urlparse
from youtubesearchpython import *
from ytmusicapi import YTMusic
from PIL import Image

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, Gio, GLib

from src.utils.player import MediaPlayer

class MooTube(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self)
        self.set_title("MooTube")
        self.set_border_width(10)
        self.set_default_size(300, 420)

    def draw(self):
        self.my_path = os.path.abspath(os.path.dirname(__file__))
        self.cache_path = os.path.expanduser("~/.cache/mootube/")
        self.config_path = os.path.expanduser("~/.config/mootube/")
        self.library_file = os.path.expanduser("~/.config/mootube/library.json")

        if os.path.exists(self.cache_path) == False:
            os.mkdir(self.cache_path)

        if os.path.exists(self.config_path) == False:
            os.mkdir(self.config_path)

        if os.path.exists(self.library_file):
            with open(self.library_file, "r") as jsonfile:
                self.librarydata = json.load(jsonfile)
                jsonfile.close()
        else:
            self.librarydata = []

        provider = Gtk.CssProvider()
        provider.load_from_file(Gio.File.new_for_path(os.path.join(self.my_path, 'assets/mootube.css')))
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.get_style_context().add_class('app-theme')

        self.mode = "V"
        self.playing = False
        self.seeking = False
        self.duration = "00:00"
        self.criteria = None
        self.library = False
        self.sortbyoption = 0
        self.uploaddateoption = 0
        self.durationoption = 0
        self.searchparams = None

        header = Gtk.HeaderBar(title="MooTube")
        header.get_style_context().add_class('app-theme')
        header.props.show_close_button = True

        logopb = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            filename=os.path.join(self.my_path, 'assets/mootube.png'),
            width=30, 
            height=30, 
            preserve_aspect_ratio=True)
        logoimg = Gtk.Image.new_from_pixbuf(logopb)
        header.pack_start(logoimg)

        self.set_titlebar(header)

        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(container)

        self.searchbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        container.add(self.searchbox)

        filterspb = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            filename=os.path.join(self.my_path, 'assets/filters.png'),
            width=24, 
            height=24, 
            preserve_aspect_ratio=True)
        filtersimg = Gtk.Image.new_from_pixbuf(filterspb)
        filtersbtn = Gtk.Button()
        filtersbtn.connect("clicked", self.OnLoadFilters)
        filtersbtn.add(filtersimg)
        filtersbtn.get_style_context().add_class('app-theme')
        self.searchbox.pack_start(filtersbtn, False, False, 0)

        self.searchentry = Gtk.SearchEntry()
        self.searchentry.set_text("")
        self.searchentry.connect("activate", self.OnSearch)
        self.searchentry.get_style_context().add_class('app-theme')
        self.searchbox.pack_start(self.searchentry, True, True, 0)

        searchbtn = Gtk.Button(label="Go")
        searchbtn.connect("clicked", self.OnSearch)
        searchbtn.get_style_context().add_class('app-theme')
        self.searchbox.pack_start(searchbtn, False, False, 0)

        self.modebox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        container.add(self.modebox)

        self.videoslabel = Gtk.Label(label="Videos")
        self.videoslabel.set_halign(Gtk.Align.END)
        self.modebox.pack_start(self.videoslabel, True, True, 0)

        self.modebtn = Gtk.Switch()
        self.modebtn.set_active(False)
        self.modebtn.connect("notify::active", self.OnToggleMode)
        self.modebtn.get_style_context().add_class('switch-theme')

        self.modebox.pack_start(self.modebtn, True, True, 0)

        self.musiclabel = Gtk.Label(label="Music")
        self.musiclabel.set_halign(Gtk.Align.START)
        self.modebox.pack_start(self.musiclabel, True, True, 0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.connect("edge-reached", self.DoSearchMore, 70)

        container.pack_start(scrolled, True, True, 0)

        self.videolist = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        scrolled.add(self.videolist)

        self.controls = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.controls.get_style_context().add_class('border-top')
        container.pack_start(self.controls, False, False, 0)

        playback = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.controls.pack_start(playback, False, False, 0)

        self.currentlabel = Gtk.Label(label="no media selected")
        self.currentlabel.set_justify(Gtk.Justification.CENTER)
        self.currentlabel.set_line_wrap(True)
        self.currentlabel.set_max_width_chars(68)
        self.currentlabel.get_style_context().add_class('bold')
        playback.pack_start(self.currentlabel, True, True, 0)

        self.positionlabel = Gtk.Label()
        self.positionlabel.set_justify(Gtk.Justification.CENTER)
        playback.pack_start(self.positionlabel, True, True, 0)

        self.playscale = Gtk.Scale().new(Gtk.Orientation.HORIZONTAL)
        self.playscale.set_draw_value(False)
        self.playscale.connect("button-press-event", self.OnPlayPositionSeek)
        self.playscale.connect("button-release-event", self.OnPlayPositionChange)
        playback.pack_start(self.playscale, True, True, 0)

        mediabtns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        playback.pack_start(mediabtns, True, True, 0)

        pausepb = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            filename=os.path.join(self.my_path, 'assets/pause.png'),
            width=24, 
            height=24, 
            preserve_aspect_ratio=True)
        pauseimg = Gtk.Image.new_from_pixbuf(pausepb)
        pausebtn = Gtk.Button()
        pausebtn.add(pauseimg)
        pausebtn.connect("clicked", self.OnPauseVideo)
        pausebtn.get_style_context().add_class('app-theme')
        mediabtns.pack_start(pausebtn, True, True, 0)

        stoppb = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            filename=os.path.join(self.my_path, 'assets/stop.png'),
            width=24, 
            height=24, 
            preserve_aspect_ratio=True)
        stopimg = Gtk.Image.new_from_pixbuf(stoppb)
        stopbtn = Gtk.Button()
        stopbtn.add(stopimg)
        stopbtn.connect("clicked", self.OnStopVideo)
        stopbtn.get_style_context().add_class('app-theme')
        mediabtns.pack_start(stopbtn, True, True, 0)

        self.loadinglabel = Gtk.Label()
        self.loadinglabel.set_markup("<big><b>loading media...</b></big>");
        self.loadinglabel.set_justify(Gtk.Justification.FILL)
        self.loadinglabel.set_line_wrap(True)
        self.loadinglabel.set_max_width_chars(68)
        self.loadinglabel.get_style_context().add_class('app-theme')
        container.pack_start(self.loadinglabel, False, False, 0)

        tabsbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        container.pack_start(tabsbox, False, False, 0)

        homepb = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            filename=os.path.join(self.my_path, 'assets/home.png'),
            width=24, 
            height=24, 
            preserve_aspect_ratio=True)
        homeimg = Gtk.Image.new_from_pixbuf(homepb)
        self.homebtn = Gtk.Button()
        self.homebtn.connect("clicked", self.OnLoadHome)
        self.homebtn.add(homeimg)
        self.homebtn.get_style_context().add_class('app-theme')
        tabsbox.pack_start(self.homebtn, True, True, 0)

        librarypb = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            filename=os.path.join(self.my_path, 'assets/library.png'),
            width=24, 
            height=24, 
            preserve_aspect_ratio=True)
        libraryimg = Gtk.Image.new_from_pixbuf(librarypb)
        self.librarybtn = Gtk.Button()
        self.librarybtn.connect("clicked", self.OnLoadLibrary)
        self.librarybtn.add(libraryimg)
        self.librarybtn.get_style_context().add_class('app-theme')
        tabsbox.pack_start(self.librarybtn, True, True, 0)

        self.show_all()
        self.modebtn.grab_focus()
        self.controls.hide()

        self.player = MediaPlayer(self)
        self.ytmusic = YTMusic()

        x = threading.Thread(target=self.DoOnInit)
        x.start()

    def DoOnInit(self):
        self.DoGetOriginalIdleTime()

        self.DoLoadIcons()

        self.DoSearch(None, True)

    def DoLoadIcons(self):
        self.downloadpb = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            filename=os.path.join(self.my_path, 'assets/download.png'),
            width=24, 
            height=24, 
            preserve_aspect_ratio=True)

        self.savedpb = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            filename=os.path.join(self.my_path, 'assets/saved.png'),
            width=24, 
            height=24, 
            preserve_aspect_ratio=True)

        self.removepb = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            filename=os.path.join(self.my_path, 'assets/remove.png'),
            width=24, 
            height=24, 
            preserve_aspect_ratio=True)

    def DoGetOriginalIdleTime(self):
        sbprocess = subprocess.Popen(['gsettings', 'get', 'org.gnome.desktop.session', 'idle-delay'], stdout=subprocess.PIPE)
        out, err = sbprocess.communicate()
        
        self.idleTime = out.decode('UTF-8').replace("uint32", "").strip()

    def OnToggleMode(self, switch, gparam):
        self.library = False

        if switch.get_active():
            self.mode = "M"
        else:
            self.mode = "V"

        x = threading.Thread(target=self.DoSearch, args=(self.criteria, True))
        x.start()

    def OnLoadFilters(self, button):
        dialog = FiltersDialog(self)
        response = dialog.run()

        #if response == Gtk.ResponseType.OK:
        #    print("ok")
        #elif response == Gtk.ResponseType.CANCEL:
        #    print("cancel")

        dialog.destroy()

    def OnSearch(self, button):
        x = threading.Thread(target=self.DoSearch, args=(self.searchentry.get_text(), True))
        x.start()

    def DoSearchMore(self, swin, pos, dist):
        if pos == Gtk.PositionType.BOTTOM:
            if self.library == False and self.mode == "V":
                x = threading.Thread(target=self.DoSearch, args=(self.criteria, False))
                x.start()

    def DoSearch(self, criteria, clear):
        self.criteria = criteria
        self.library = False

        self.librarybtn.get_style_context().remove_class('library-mode')

        if self.criteria == None:
            self.criteria = "linux mobile"

        if clear:
            GLib.idle_add(self.DoClearVideoList)

        GLib.idle_add(self.DoShowLoading)

        if self.mode == "V":

            if clear:
                if self.searchparams is None:
                    self.videosSearch = CustomSearch(self.criteria, searchPreferences=SearchMode.videos, limit=10)
                else:
                    self.videosSearch = CustomSearch(self.criteria, searchPreferences=self.searchparams, limit=10)
            else:
                self.videosSearch.next()
            results = self.videosSearch.result()['result']
        else:
            if clear:
                results = self.ytmusic.search(self.criteria, filter='songs', limit=20)
            else:
                return

        for vid in results:
            if self.mode == "V":
                thumbname = vid['id']
                channelthumb = vid['channel']['thumbnails'][0]['url']
                channelurl = urlparse(channelthumb)
                channelthumbname = os.path.basename(channelurl.path)

                if os.path.exists(os.path.join(self.cache_path, channelthumbname)) == False:
                    channelcontent = requests.get(channelthumb).content

                    file = open(os.path.join(self.cache_path, channelthumbname), "wb")
                    file.write(channelcontent)
                    file.close()

                    im = Image.open(os.path.join(self.cache_path, channelthumbname)).convert("RGB")
                    im.save(os.path.join(self.cache_path, channelthumbname), "jpeg")
            else:
                thumbname = vid['videoId']

            vidthumb = vid['thumbnails'][0]['url']
            vidurl = urlparse(vidthumb)
            
            if os.path.exists(os.path.join(self.cache_path, thumbname)) == False:
                content = requests.get(vidthumb).content

                file = open(os.path.join(self.cache_path, thumbname), "wb")
                file.write(content)
                file.close()

                im = Image.open(os.path.join(self.cache_path, thumbname)).convert("RGB")
                im.save(os.path.join(self.cache_path, thumbname), "jpeg")

            if self.mode == "V":
                GLib.idle_add(self.DoAddVideo, vid['id'], vid['title'], thumbname, channelthumbname, vid['channel']['name'], vid['viewCount']['short'])
            else:
                explicit = ""
                if vid['isExplicit']:
                    explicit = "explicit"
                GLib.idle_add(self.DoAddVideo, vid['videoId'], vid['title'], thumbname, thumbname, vid['artists'][0]['name'], explicit)

        GLib.idle_add(self.DoHideLoading)

    def DoClearVideoList(self):
        videos = self.videolist.get_children()
        for video in videos:
            if video is not None:
                self.videolist.remove(video)

    def DoShowLoading(self):
        self.loadinglabel.show()

    def DoHideLoading(self):
        self.loadinglabel.hide()

    def DoAddVideo(self, id, title, thumbname, channelthumbname, channelname, viewcount):
        vidcard = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.videolist.add(vidcard)

        if self.mode == "V":
            thumbpb = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                filename=os.path.join(self.cache_path, thumbname),
                width=300,
                height=200,
                preserve_aspect_ratio=True)
            thumbimg = Gtk.Image.new_from_pixbuf(thumbpb)
            vidbtn = Gtk.Button()
            vidbtn.add(thumbimg)
            vidbtn.connect("clicked", self.OnPlayVideo, None, id, title, self.mode)
            vidbtn.get_style_context().add_class('app-theme')
            vidbtn.get_style_context().add_class('no-border')
            vidcard.pack_start(vidbtn, True, True, 0)

        vidmeta = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        vidcard.pack_start(vidmeta, False, False, 0)
        
        channelpb = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            filename=os.path.join(self.cache_path, channelthumbname),
            width=68,
            height=68,
            preserve_aspect_ratio=False)
        channelimg = Gtk.Image.new_from_pixbuf(channelpb)

        if self.mode == "M":
            vidbtn = Gtk.Button()
            vidbtn.add(channelimg)
            vidbtn.connect("clicked", self.OnPlayVideo, None, id, title, self.mode)
            vidbtn.get_style_context().add_class('app-theme')
            vidbtn.get_style_context().add_class('no-border')
            vidmeta.pack_start(vidbtn, False, False, 0)
        else:
            vidmeta.pack_start(channelimg, False, False, 0)

        vidinfo = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vidmeta.pack_start(vidinfo, True, True, 0)

        vidheader = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        vidinfo.pack_start(vidheader, True, True, 0)

        titlelabel = Gtk.Label()
        titlelabel.set_markup("<a href=''><big><b>" + title.strip().replace("&", "&amp;") + "</b></big></a>")
        titlelabel.connect("activate-link", self.OnPlayVideo, id, title.strip(), self.mode)
        titlelabel.set_justify(Gtk.Justification.LEFT)
        titlelabel.set_halign(Gtk.Align.START)
        titlelabel.set_line_wrap(True)
        titlelabel.set_max_width_chars(68)
        titlelabel.get_style_context().add_class('app-theme')
        vidheader.pack_start(titlelabel, True, True, 0)

        downloadbtn = Gtk.Button()

        if self.mode == "V":
            if os.path.exists(os.path.join(self.cache_path, id + ".mp4")):
                downloadimg = Gtk.Image.new_from_pixbuf(self.savedpb)
            else:
                downloadimg = Gtk.Image.new_from_pixbuf(self.downloadpb)
                downloadbtn.connect("clicked", self.OnDownloadVideo, id, title, thumbname)
        else:
            if os.path.exists(os.path.join(self.cache_path, id + ".mp3")):
                downloadimg = Gtk.Image.new_from_pixbuf(self.savedpb)
            else:
                downloadimg = Gtk.Image.new_from_pixbuf(self.downloadpb)
                downloadbtn.connect("clicked", self.OnDownloadVideo, id, title, thumbname)

        downloadbtn.add(downloadimg)
        downloadbtn.get_style_context().add_class('app-theme')
        downloadbtn.get_style_context().add_class('no-border')
        vidheader.pack_end(downloadbtn, False, False, 0)

        viddets = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        vidinfo.pack_start(viddets, False, False, 0)

        if (channelname != None):
            channellabel = Gtk.Label()
            channellabel.set_markup("<small>" + channelname.replace("&", "&amp;") + "</small>")
            viddets.pack_start(channellabel, False, False, 0)

        if (viewcount != None):
            viewslabel = Gtk.Label()
            viewslabel.set_markup("<small>" + viewcount + "</small>")
            viddets.pack_end(viewslabel, False, False, 0)

        self.show_all()
        if self.playing:
            self.controls.show()
        else:
            self.controls.hide()
            self.currentlabel.set_text("no media selected")

    def OnLoadHome(self, button):
        self.library = False

        self.searchbox.show()
        self.modebox.show()

        self.OnSearch(self.searchentry)
        

    def OnLoadLibrary(self, button):
        self.DoClearVideoList()

        self.library = True

        for vid in self.librarydata:
            vidcard = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            self.videolist.add(vidcard)

            vidmeta = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            vidcard.pack_start(vidmeta, False, False, 0)
            
            thumbpb = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                filename=os.path.join(self.cache_path, vid['thumb']),
                width=68,
                height=68,
                preserve_aspect_ratio=False)
            thumbimg = Gtk.Image.new_from_pixbuf(thumbpb)
            vidbtn = Gtk.Button()
            vidbtn.add(thumbimg)
            vidbtn.connect("clicked", self.OnPlayVideo, None, vid['id'], vid['title'], vid['type'])
            vidbtn.get_style_context().add_class('app-theme')
            vidbtn.get_style_context().add_class('no-border')
            vidmeta.pack_start(vidbtn, False, False, 0)

            titlelabel = Gtk.Label()
            titlelabel.set_markup("<a href=''><big><b>" + vid['title'].strip().replace("&", "&amp;") + "</b></big></a>")
            titlelabel.connect("activate-link", self.OnPlayVideo, vid['id'], vid['title'].strip(), vid['type'])
            titlelabel.set_justify(Gtk.Justification.LEFT)
            titlelabel.set_halign(Gtk.Align.START)
            titlelabel.set_line_wrap(True)
            titlelabel.set_max_width_chars(68)
            titlelabel.get_style_context().add_class('app-theme')
            vidmeta.pack_start(titlelabel, True, True, 0)

            removeimg = Gtk.Image.new_from_pixbuf(self.removepb)
            removebtn = Gtk.Button()
            removebtn.add(removeimg)
            removebtn.connect("clicked", self.OnRemoveVideo, vid['id'])
            removebtn.get_style_context().add_class('app-theme')
            removebtn.get_style_context().add_class('no-border')
            vidmeta.pack_end(removebtn, False, False, 0)

        self.show_all()
        self.searchbox.hide()
        self.modebox.hide()
        self.DoHideLoading()

        if self.playing:
            self.controls.show()
        else:
            self.controls.hide()
            self.currentlabel.set_text("no media selected")

    def OnPlayVideo(self, button, uri, id, title, type):
        self.currentlabel.set_text(title)
        self.positionlabel.set_text("loading...")
        self.playscale.set_range(0, 0)
        self.playscale.set_value(0)
        self.currentposition = 0
        self.controls.show()
        
        x = threading.Thread(target=self.DoPlayVideo, args=(button, uri, id, type))
        x.start()

    def DoPlayVideo(self, button, uri, id, type):
        vidurl = 'https://www.youtube.com/watch?v=' + id

        if self.playing:
            self.player.stop()

        if type == "V":
            if os.path.exists(os.path.join(self.cache_path, id + ".mp4")):
                self.player.mode(type, False)
                self.player.play(os.path.join(self.cache_path, id + ".mp4"))
            else:
                self.player.mode(type, True)
                self.player.play(vidurl)
        else:
            if os.path.exists(os.path.join(self.cache_path, id + ".mp3")):
                self.player.mode(type, False)
                self.player.play(os.path.join(self.cache_path, id + ".mp3"))
            else:
                result = self.ytmusic.get_song(id)
                if len(result['streamingData']['adaptiveFormats']) >= 1:
                    if 'url' in result['streamingData']['adaptiveFormats'][0]:
                        vidurl = result['streamingData']['adaptiveFormats'][0]['url']
                self.player.mode(type, True)
                self.player.play(vidurl)

        self.playing = True

        sbparams = ['gsettings', 'set', 'org.gnome.desktop.session', 'idle-delay', '0']
        sbproc = subprocess.Popen(sbparams, shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=-1)

        return True

    def OnStopVideo(self, evt):
        self.player.stop()
        self.playing = False

        self.controls.hide()
        self.currentlabel.set_text("no media selected")
        self.positionlabel.set_text("")
        self.playscale.set_range(0, 0)
        self.playscale.set_value(0)
        self.currentposition = 0

        sbparams = ['gsettings', 'set', 'org.gnome.desktop.session', 'idle-delay', self.idleTime]
        sbproc = subprocess.Popen(sbparams, shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=-1)

    def OnPauseVideo(self, evt):
        if self.playing:
            self.player.pause()
            self.playing = False
        else:
            self.player.resume()
            self.playing = True

    def OnDownloadVideo(self, button, id, title, thumb):
        button.get_child().set_from_pixbuf(self.savedpb)
        
        x = threading.Thread(target=self.DoDownloadVideo, args=(id, title, thumb))
        x.start()

    def DoDownloadVideo(self, id, title, thumb):
        vidurl = 'https://www.youtube.com/watch?v=' + id

        if self.mode == "M":
            downloadparams = [
                'youtube-dl',
                '--extract-audio',
                '--audio-format', 'mp3',
                '-o', os.path.join(self.cache_path, id + ".mp3"),
                vidurl
            ]
        else:
            downloadparams = [
                'youtube-dl',
                '--recode-video', 'mp4',
                '-o', os.path.join(self.cache_path, id + ".mp4"),
                vidurl
            ]
        download = subprocess.Popen(downloadparams, shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=-1)

        videodata = {
            'id' : id,
            'title' : title,
            'type' : self.mode,
            'thumb' : thumb
        }

        vids = []
        for vid in self.librarydata:
            vids.append(vid['id'])

        if id not in vids:
            self.librarydata.append(videodata)

        with open(self.library_file, "w") as jsonfile:
            json.dump(self.librarydata, jsonfile)
            jsonfile.close()

    def OnRemoveVideo(self, button, id):
        newdata = []
        for vid in self.librarydata:
            if (vid['id'] != id):
                newdata.append(vid)

        self.librarydata = newdata

        with open(self.library_file, "w") as jsonfile:
            json.dump(self.librarydata, jsonfile)
            jsonfile.close()

        self.OnLoadLibrary(button)

    def OnUpdateDuration(self, s):
        value = "%02d:%02d" % divmod(s, 60)
        self.duration = str(value)
        self.playscale.set_range(0, s)

    def DoUpdatePosition(self, s):
        value = "%02d:%02d" % divmod(s, 60)
        self.currentposition = s
        if self.seeking == False:
            self.positionlabel.set_text(str(value) + "/" + self.duration)
            self.playscale.set_value(s)

    def OnUpdatePosition(self, s):
        GLib.idle_add(self.DoUpdatePosition, s)

    def OnPlayPositionSeek(self, s, e):
        self.seeking = True

    def OnPlayPositionChange(self, s, e):
        c = self.currentposition
        n = s.get_value()
        pos = n - c
        self.player.seek(pos)
        self.seeking = False

class FiltersDialog(Gtk.Dialog):
    def __init__(self, parent):
        super().__init__(title="Filters", transient_for=parent, flags=0)
        self.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK
        )
        self.set_default_size(200, 200)

        self.app = parent

        box = self.get_content_area()
        box.get_style_context().add_class('app-theme')
        box.get_style_context().add_class('dialog-theme')

        filtersbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.add(filtersbox)

        sortbylabel = Gtk.Label(label="Sort By")
        filtersbox.pack_start(sortbylabel, True, True, 0)

        sortoptions = [
            "Relevance",
            "Upload Date",
            "View Count",
            "Rating",
        ]
        self.sortbycombo = Gtk.ComboBoxText()
        self.sortbycombo.set_entry_text_column(0)
        self.sortbycombo.connect("changed", self.DoUpdateFilters)
        for sortoption in sortoptions:
            self.sortbycombo.append_text(sortoption)
        self.sortbycombo.set_active(self.app.sortbyoption)
        filtersbox.pack_start(self.sortbycombo, True, True, 0)

        uploaddatelabel = Gtk.Label(label="Upload Date")
        filtersbox.pack_start(uploaddatelabel, True, True, 0)

        uploaddates = [
            "Anytime",
            "Last Hour",
            "Today",
            "This Week",
            "This Month",
            "This Year"
        ]
        self.uploaddatecombo = Gtk.ComboBoxText()
        self.uploaddatecombo.set_entry_text_column(0)
        self.uploaddatecombo.connect("changed", self.DoUpdateFilters)
        for uploaddate in uploaddates:
            self.uploaddatecombo.append_text(uploaddate)
        self.uploaddatecombo.set_active(self.app.uploaddateoption)
        filtersbox.pack_start(self.uploaddatecombo, True, True, 0)

        durationlabel = Gtk.Label(label="Duration")
        filtersbox.pack_start(durationlabel, True, True, 0)

        durations = [
            "Any",
            "Under 4 Minutes",
            "4-20 Minutes",
            "Over 20 Minutes",
        ]
        self.durationcombo = Gtk.ComboBoxText()
        self.durationcombo.set_entry_text_column(0)
        self.durationcombo.connect("changed", self.DoUpdateFilters)
        for duration in durations:
            self.durationcombo.append_text(duration)
        self.durationcombo.set_active(self.app.durationoption)
        filtersbox.pack_start(self.durationcombo, True, True, 0)

        self.show_all()

    def DoUpdateFilters(self, combo):
        self.app.sortbyoption = self.sortbycombo.get_active()
        self.app.uploaddateoption = self.uploaddatecombo.get_active()
        self.app.durationoption = self.durationcombo.get_active()

        sp = ""

        if self.app.sortbyoption == 0:
            if self.app.uploaddateoption == 0 and self.app.durationoption == 0:
                sp += "CASSAhAB"
            elif self.app.uploaddateoption == 0 and self.app.durationoption != 0:
                sp += "Eg"

                if self.app.durationoption == 1:
                    sp += "QQARgB"
                elif self.app.durationoption == 2:
                    sp += "QQARgD"
                elif self.app.durationoption == 3:
                    sp += "QQARgC"
            else:
                sp += "Eg"

                if self.app.durationoption == 0:
                    sp += "Q"
                else:
                    sp += "Y"

                if self.app.uploaddateoption == 1:
                    sp += "IARAB"
                elif self.app.uploaddateoption == 2:
                    sp += "IAhAB"
                elif self.app.uploaddateoption == 3:
                    sp += "IAxAB"
                elif self.app.uploaddateoption == 4:
                    sp += "IBBAB"
                elif self.app.uploaddateoption == 5:
                    sp += "IBRAB"

                if self.app.durationoption == 1:
                    sp += "GAE"
                elif self.app.durationoption == 2:
                    sp += "GAM"
                elif self.app.durationoption == 3:
                    sp += "GAI"
        else:
            if self.app.sortbyoption == 1:
                sp += "CAIS"
            elif self.app.sortbyoption == 2:
                sp += "CAMS"
            elif self.app.sortbyoption == 3:
                sp += "CAES"

            if self.app.uploaddateoption == 0:
                sp += "BBAB"

            if self.app.durationoption == 0:
                sp += "BAg"
            else:
                sp += "Bgg"

            if self.app.uploaddateoption == 1:
                sp += "BEAE"
            elif self.app.uploaddateoption == 2:
                sp += "CEAE"
            elif self.app.uploaddateoption == 3:
                sp += "DEAE"
            elif self.app.uploaddateoption == 4:
                sp += "EEAE"
            elif self.app.uploaddateoption == 5:
                sp += "FEAE"

            if self.app.durationoption == 1:
                sp += "YAQ"
            elif self.app.durationoption == 2:
                sp += "YAw"
            elif self.app.durationoption == 3:
                sp += "YAg"

        self.app.searchparams = sp

app = MooTube()
app.connect("destroy", Gtk.main_quit)
app.draw()
Gtk.main()
