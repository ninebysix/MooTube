import ctypes, os, requests, io, sys, subprocess, gi, json, threading, locale

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, Gio, GLib

gi.require_version('GL', '1.0')
from OpenGL import GL, GLX

from mpv import MPV, MpvRenderContext, OpenGlCbGetProcAddrFn

class MediaPlayer(Gtk.GLArea, Gtk.Window):
    def __init__(self, mt, **properties):
        super().__init__(**properties)
        self.app = mt

        self._proc_addr_wrapper = OpenGlCbGetProcAddrFn(self.get_process_address)

        self.ctx = None
        self.mode("V", True)

        self.connect("realize", self.DoRealize)
        self.connect("render", self.DoRender)
        self.connect("unrealize", self.DoUnrealize)

    def DoRealize(self, area):
        self.make_current()
        self.ctx = MpvRenderContext(self.mpv, 'opengl', opengl_init_params={'get_proc_address': self._proc_addr_wrapper})
        self.ctx.update_cb = self.wrapped_c_render_func

    def DoUnrealize(self, arg):
        self.ctx.free()
        self.mpv.terminate()

    def wrapped_c_render_func(self):
        GLib.idle_add(self.call_frame_ready, None, GLib.PRIORITY_HIGH)

    def call_frame_ready(self, *args):
        if self.ctx.update():
            self.queue_render()

    def DoRender(self, arg1, arg2):
        if self.ctx:
            factor = self.get_scale_factor()
            rect = self.get_allocated_size()[0]

            width = rect.width * factor
            height = rect.height * factor

            fbo = GL.glGetIntegerv(GL.GL_DRAW_FRAMEBUFFER_BINDING)
            self.ctx.render(flip_y=True, opengl_fbo={'w': width, 'h': height, 'fbo': fbo})
            return True
        return False

    def mode(self, mode, stream):
        locale.setlocale(locale.LC_NUMERIC, 'C')

        if mode == "V":
            if stream == True:
                self.mpv = MPV(
                    input_default_bindings=True,
                    input_vo_keyboard=True,
                    osc=True,
                    stream_buffer_size='5MiB',
                    demuxer_max_bytes='1024KiB',
                    ytdl=True,
                    ytdl_format='(bestvideo[height<=720]+bestaudio)'
                )
            else:
                self.mpv = MPV(
                    input_default_bindings=True,
                    input_vo_keyboard=True,
                    osc=True
                )
        else:
            if stream == True:
                self.mpv = MPV(video=False, stream_buffer_size='5MiB', demuxer_max_bytes='1024KiB', ytdl=True, ytdl_format='(bestaudio)')
            else:
                self.mpv = MPV(video=False)

        @self.mpv.property_observer('duration')
        def duration_observer(_name, value):
            if value != None:
                self.app.OnUpdateDuration(value)

        @self.mpv.property_observer('time-pos')
        def time_observer(_name, value):
            if value != None:
                self.app.OnUpdatePosition(value)

    def play(self, media):
        self.mpv.play(media)

    def stop(self):
        self.mpv.stop()

    def pause(self):
        self.mpv._set_property('pause', True)

    def resume(self):
        self.mpv._set_property('pause', False)

    def seek(self, pos):
        self.mpv.seek(pos)

    def get_process_address(_, name):
        address = GLX.glXGetProcAddress(name.decode("utf-8"))
        return ctypes.cast(address, ctypes.c_void_p).value
