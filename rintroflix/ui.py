# -*- coding: utf-8 -*-
"""RintrofliX handheld media-centre UI primitives (640x480, gamepad-first)."""
from __future__ import annotations

import math
import os
import pygame

W, H = 640, 480
BG = (7, 11, 19)
PANEL = (15, 23, 35)
PANEL_ALT = (21, 32, 47)
PANEL_HI = (29, 43, 59)
SELECTED = (21, 58, 72)
FG = (241, 246, 252)
DIM = (163, 180, 198)
FAINT = (91, 111, 132)
OK = (78, 222, 169)
ERR = (255, 105, 119)
ACCENTS = {
    "cyan": (71, 221, 226),
    "violet": (177, 139, 255),
    "amber": (255, 190, 86),
    "crimson": (246, 91, 125),
}

_ASSET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resources", "fonts")

def _font(name, size):
    try:
        return pygame.font.Font(os.path.join(_ASSET, name), size)
    except (OSError, pygame.error):
        return pygame.font.Font(None, size)


def draw_icon(surface, name, center, color, size=28, selected=False):
    """Draw a small consistent line icon without relying on missing glyphs."""
    x, y = int(center[0]), int(center[1])
    r = max(8, int(size * .36))
    w = max(2, size // 12)
    c = color
    rect = lambda ox, oy, ww, hh: pygame.Rect(x + ox, y + oy, ww, hh)
    if name in ("tv", "watch", "live"):
        pygame.draw.rect(surface, c, rect(-r, -r + 3, r * 2, r + 5), w, border_radius=4)
        pygame.draw.line(surface, c, (x - r // 2, y + r + 9), (x + r // 2, y + r + 9), w)
        pygame.draw.line(surface, c, (x, y + r + 7), (x, y + r + 13), w)
        pygame.draw.line(surface, c, (x - r // 2, y - r - 5), (x, y - r + 1), w)
        pygame.draw.line(surface, c, (x + r // 2, y - r - 5), (x, y - r + 1), w)
    elif name in ("library", "folder", "video"):
        pts = [(x-r, y-r//2), (x-r//3, y-r//2), (x, y-r//4), (x+r, y-r//4), (x+r, y+r), (x-r, y+r)]
        pygame.draw.polygon(surface, c, pts, w)
        pygame.draw.line(surface, c, (x-r, y), (x+r, y), w)
    elif name in ("addons", "puzzle"):
        pygame.draw.rect(surface, c, rect(-r, -r, r*2, r*2), w, border_radius=4)
        pygame.draw.circle(surface, c, (x, y-r), r//3, w)
        pygame.draw.circle(surface, c, (x+r, y), r//3, w)
        pygame.draw.circle(surface, c, (x, y+r), r//3, w)
    elif name in ("sources", "satellite"):
        pygame.draw.circle(surface, c, (x, y), r//2, w)
        pygame.draw.arc(surface, c, rect(-r, -r, r*2, r*2), math.radians(205), math.radians(335), w)
        pygame.draw.arc(surface, c, rect(-r-6, -r-6, r*2+12, r*2+12), math.radians(215), math.radians(325), w)
        pygame.draw.line(surface, c, (x, y+r//2), (x-r//2, y+r), w)
    elif name in ("settings", "gear"):
        pygame.draw.circle(surface, c, (x, y), r, w)
        pygame.draw.circle(surface, c, (x, y), r//3, w)
        for a in range(0, 360, 45):
            rad = math.radians(a)
            pygame.draw.line(surface, c, (x+int(math.cos(rad)*(r+1)), y+int(math.sin(rad)*(r+1))),
                             (x+int(math.cos(rad)*(r+6)), y+int(math.sin(rad)*(r+6))), w+1)
    elif name in ("search",):
        pygame.draw.circle(surface, c, (x-3, y-3), r-3, w)
        pygame.draw.line(surface, c, (x+r//2, y+r//2), (x+r+5, y+r+5), w+1)
    elif name in ("guide", "calendar", "epg"):
        pygame.draw.rect(surface, c, rect(-r, -r+3, r*2, r*2-3), w, border_radius=3)
        pygame.draw.line(surface, c, (x-r, y-2), (x+r, y-2), w)
        pygame.draw.line(surface, c, (x-r//2, y-r-3), (x-r//2, y), w)
        pygame.draw.line(surface, c, (x+r//2, y-r-3), (x+r//2, y), w)
        for oy in (r//3, r*2//3):
            for ox in (-r//2, r//3): pygame.draw.circle(surface, c, (x+ox, y+oy), 2)
    elif name in ("star", "favourites"):
        pts=[]
        for i in range(10):
            a=-math.pi/2+i*math.pi/5
            rr=r if i%2==0 else r*.46
            pts.append((x+int(math.cos(a)*rr), y+int(math.sin(a)*rr)))
        pygame.draw.polygon(surface, c, pts, 0 if selected else w)
    elif name in ("play",):
        pygame.draw.polygon(surface, c, [(x-r//2,y-r),(x-r//2,y+r),(x+r,y)], 0)
    elif name in ("info", "about"):
        pygame.draw.circle(surface, c, (x,y), r, w)
        pygame.draw.circle(surface, c, (x,y-r//2), 2)
        pygame.draw.line(surface,c,(x,y),(x,y+r//2),w+1)
    elif name in ("back",):
        pygame.draw.line(surface,c,(x+r,y),(x-r,y),w+2)
        pygame.draw.line(surface,c,(x-r,y),(x,y-r),w+2)
        pygame.draw.line(surface,c,(x-r,y),(x,y+r),w+2)
    else:
        pygame.draw.circle(surface, c, (x, y), r, w)
        pygame.draw.circle(surface, c, (x, y), max(2, r//3), w)


class Theme:
    def __init__(self, accent_name="cyan", scale=125):
        pygame.font.init()
        self.accent_name = accent_name if accent_name in ACCENTS else "cyan"
        self.accent = ACCENTS[self.accent_name]
        self.scale = max(100, min(175, int(scale)))
        self.f_brand = _font("Cabin-Bold.otf", self.sz(31))
        self.f_header = _font("Cabin-Bold.otf", self.sz(23))
        self.f_big = _font("Cabin-Bold.otf", self.sz(24))
        self.f_med = _font("Cabin-SemiBold.otf", self.sz(19))
        self.f_small = _font("Cabin-Regular.otf", self.sz(16))
        self.f_tiny = _font("Cabin-Regular.otf", self.sz(13))
        self.row_h = max(54, self.f_med.get_height() + self.f_small.get_height() + 13)
        self.header_brand_y = 5
        self.header_section_y = self.header_brand_y + self.f_brand.get_height() + 2
        self.header_h = max(68, self.header_section_y + self.f_tiny.get_height() + 10)
        self.footer_h = max(34, self.f_tiny.get_height() + 13)
        self.logo = None
        self.logo_small = None
        self.logo_hero = None
        self._background = pygame.Surface((W, H))
        # Premium midnight gradient with restrained ambient light. Build once;
        # the handheld only blits this cached surface during the frame loop.
        for y in range(H):
            t = y / float(H)
            col = (int(5 + 7*t), int(8 + 9*t), int(18 + 19*t))
            pygame.draw.line(self._background, col, (0, y), (W, y))
        glow = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*self.accent, 24), (570, 55), 210)
        pygame.draw.circle(glow, (92, 65, 170, 15), (80, 390), 205)
        self._background.blit(glow, (0, 0))
        # Subtle star points add depth without looking like a noisy wallpaper.
        for i in range(54):
            x = (i * 137 + 29) % W
            y = (i * 83 + 17) % H
            shade = 36 + (i * 17) % 45
            self._background.set_at((x, y), (shade//2, shade, min(150, shade+35)))
        try:
            p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resources", "rintroflix.png")
            # Do not call convert_alpha here: Theme is constructed before
            # pygame.display.set_mode() on some muOS launch paths.
            self.logo = pygame.image.load(p)
            self.logo_small = pygame.transform.smoothscale(self.logo, (44, 44))
            self.logo_hero = pygame.transform.smoothscale(self.logo, (68, 68))
        except (OSError, pygame.error):
            pass

    def sz(self, value):
        return max(12, round(value * self.scale / 125.0))

    def text(self, surface, value, pos, font=None, color=FG, maxw=None):
        font = font or self.f_med
        value = str(value).replace("\t", " ")
        if maxw is not None and maxw > 0 and font.size(value)[0] > maxw:
            ellipsis = "…"
            while value and font.size(value + ellipsis)[0] > maxw:
                value = value[:-1]
            value = value.rstrip() + ellipsis
        surface.blit(font.render(value, True, color), pos)

    def background(self, surface):
        surface.blit(self._background, (0, 0))

    def header(self, surface, title, subtitle=""):
        pygame.draw.rect(surface, (10,16,26), (0,0,W,self.header_h))
        pygame.draw.line(surface, (30,47,65), (0,self.header_h-1),(W,self.header_h-1),1)
        if self.logo_small:
            surface.blit(self.logo_small, (13, 10))
            bx = 66
        else:
            bx = 18
        self.text(surface, "Rintro", (bx, 5), self.f_brand, FG)
        self.text(surface, "fliX", (bx+self.f_brand.size("Rintro")[0], 5), self.f_brand, self.accent)
        self.text(surface, title.upper(), (bx, self.header_section_y), self.f_tiny, DIM, W-bx-20)
        if subtitle:
            sw = self.f_tiny.size(subtitle)[0]
            self.text(surface, subtitle, (W-sw-16, self.header_h-22), self.f_tiny, FAINT, W//2)
        pygame.draw.line(surface, self.accent, (14,self.header_h-2),(W-14,self.header_h-2),2)

    def section_title(self, surface, title, subtitle="", y=None):
        y = self.header_h+10 if y is None else y
        self.text(surface,title,(20,y),self.f_big,FG,W-40)
        if subtitle: self.text(surface,subtitle,(22,y+self.f_big.get_height()+3),self.f_tiny,DIM,W-44)

    def footer(self, surface, hints):
        y = H-self.footer_h
        pygame.draw.rect(surface,(10,16,26),(0,y,W,self.footer_h))
        pygame.draw.line(surface,(37,53,70),(0,y),(W,y),1)
        x=15
        for key,label in hints:
            key,label=str(key),str(label)
            keyw=self.f_tiny.size(key)[0]
            self.text(surface,key,(x,y+6),self.f_tiny,self.accent)
            x += keyw+5
            self.text(surface,label,(x,y+6),self.f_tiny,DIM)
            x += self.f_tiny.size(label)[0]+15
            if x>W-50: break

    def panel(self, surface, rect, fill=PANEL, border=None, radius=10, width=1):
        # Two cached-size-free shadow passes give panels depth while keeping
        # rendering inexpensive on the H700 framebuffer.
        shadow = pygame.Rect(rect.x, rect.y + 4, rect.w, rect.h)
        pygame.draw.rect(surface, (3, 5, 12), shadow, border_radius=radius + 2)
        pygame.draw.rect(surface, fill, rect, border_radius=radius)
        # Fine top highlight creates a glass-like edge, not a heavy bevel.
        pygame.draw.line(surface, (48, 69, 91), (rect.x + radius, rect.y + 1),
                         (rect.right - radius, rect.y + 1), 1)
        if border:
            pygame.draw.rect(surface,border,rect,width,border_radius=radius)

    def chip(self,surface,x,y,label,active=False,max_width=None,icon=None):
        font=self.f_tiny
        textw=font.size(label)[0]
        width=textw+24+(22 if icon else 0)
        if max_width: width=min(width,max_width)
        height=max(27,font.get_height()+12)
        rect=pygame.Rect(x,y,width,height)
        pygame.draw.rect(surface,SELECTED if active else PANEL,rect,border_radius=13)
        pygame.draw.rect(surface,self.accent if active else (39,56,74),rect,1,border_radius=13)
        tx=x+11
        if icon:
            draw_icon(surface,icon,(x+14,y+height//2),self.accent if active else DIM,15,active)
            tx=x+26
        self.text(surface,label,(tx,y+(height-font.get_height())//2),font,FG if active else DIM,width-(tx-x)-7)
        return width

    def home_card(self,surface,rect,title,subtitle,icon,active=False,badge=None):
        fill=(17,48,68) if active else (14,22,37)
        edge=self.accent if active else (42,57,79)
        self.panel(surface, rect, fill, edge, 14, 2 if active else 1)
        # Accent rail and icon medallion establish a clear focus hierarchy.
        if active:
            pygame.draw.rect(surface,self.accent,(rect.x+2,rect.y+12,3,rect.h-24),border_radius=2)
        ix,iy=rect.x+38,rect.centery
        pygame.draw.circle(surface,(10,29,47),(ix,iy),25)
        pygame.draw.circle(surface,(35,76,101) if active else (35,49,68),(ix,iy),25,1)
        draw_icon(surface,icon,(ix,iy),self.accent if active else DIM,31,active)
        title_y=rect.y+8 if rect.h < 70 else rect.y+12
        self.text(surface,title,(rect.x+78,title_y),self.f_med,FG,rect.w-94)
        self.text(surface,subtitle,(rect.x+79,title_y+self.f_med.get_height()+2),self.f_tiny,DIM,rect.w-96)
        if badge:
            self.chip(surface,rect.right-67,rect.y+7,badge,True,60)


class MenuList:
    def __init__(self, theme, items=None, row_h=None, top=None, bottom=None,
                 logos=None, x=12, width=None, icon_default=None):
        self.theme=theme; self.items=items or []; self.sel=0
        self.row_h=row_h or theme.row_h
        self.top=top if top is not None else theme.header_h+12
        self.bottom=bottom if bottom is not None else H-theme.footer_h-8
        self.logos=logos; self.x=x; self.width=width or W-2*x
        self.icon_default=icon_default

    def visible_rows(self): return max(1,(self.bottom-self.top)//self.row_h)
    def move(self,delta):
        if self.items: self.sel=(self.sel+delta)%len(self.items)
    def page(self,delta):
        if self.items: self.sel=max(0,min(len(self.items)-1,self.sel+delta*self.visible_rows()))
    def norm(self,item):
        if isinstance(item,str): return item,"","","",self.icon_default
        values=list(item)+["","","","",None]
        icon=values[4] if len(values)>4 else self.icon_default
        return str(values[0]),str(values[1]),str(values[2]),str(values[3]),icon

    def draw(self,surface):
        if not self.items:
            self.theme.panel(surface,(self.x,self.top+8,self.width,72),PANEL,(35,51,69))
            self.theme.text(surface,"Nothing here yet",(self.x+18,self.top+26),self.theme.f_med,DIM)
            return
        vis=self.visible_rows(); count=len(self.items)
        first=max(0,min(self.sel-vis//2,count-vis)); y=self.top
        for index in range(first,min(first+vis,count)):
            label,sub,badge,logo,icon=self.norm(self.items[index])
            selected=index==self.sel
            rect=pygame.Rect(self.x,y,self.width,self.row_h-5)
            pygame.draw.rect(surface,SELECTED if selected else PANEL,rect,border_radius=9)
            pygame.draw.rect(surface,self.theme.accent if selected else (34,48,64),rect,2 if selected else 1,border_radius=9)
            tx=self.x+16
            if self.logos and logo:
                image=self.logos.get(logo,min(46,self.row_h-12))
                if image is not None:
                    surface.blit(image,(self.x+12,y+(self.row_h-image.get_height()-5)//2))
                else:
                    draw_icon(surface, icon or "tv", (self.x+35,y+(self.row_h-5)//2),
                              self.theme.accent if selected else DIM, 24, selected)
                tx=self.x+68
            elif icon:
                draw_icon(surface,icon,(self.x+35,y+(self.row_h-5)//2),self.theme.accent if selected else DIM,25,selected); tx=self.x+68
            self.theme.text(surface,label,(tx,y+5),self.theme.f_med,FG if selected else DIM,
                            self.width-(tx-self.x)-18-(self.theme.f_tiny.size(badge)[0] if badge else 0))
            if sub:
                self.theme.text(surface,sub,(tx+1,y+7+self.theme.f_med.get_height()),self.theme.f_tiny,
                                DIM if selected else FAINT,self.width-(tx-self.x)-24)
            if badge:
                bw=self.theme.f_tiny.size(badge)[0]
                self.theme.text(surface,badge,(self.x+self.width-bw-14,y+11),self.theme.f_tiny,
                                self.theme.accent if selected else DIM)
            y+=self.row_h
        if count>vis:
            track=self.bottom-self.top; bar=max(18,track*vis//count)
            by=self.top+(track-bar)*self.sel//max(1,count-1)
            pygame.draw.rect(surface,(32,48,64),(self.x+self.width-4,self.top,2,track))
            pygame.draw.rect(surface,self.theme.accent,(self.x+self.width-5,by,4,bar),border_radius=3)


class Toast:
    def __init__(self,theme): self.theme=theme; self.message=""; self.until=0; self.ok=True
    def show(self,message,ok=True,seconds=2.4):
        import time
        self.message=str(message); self.ok=ok; self.until=time.monotonic()+seconds
    def draw(self,surface):
        import time
        if not self.message or time.monotonic()>self.until: return
        font=self.theme.f_small; width=min(W-36,font.size(self.message)[0]+46)
        x,y=(W-width)//2,H-self.theme.footer_h-54
        pygame.draw.rect(surface,PANEL_ALT,(x,y,width,42),border_radius=9)
        pygame.draw.rect(surface,OK if self.ok else ERR,(x,y,width,2),border_radius=2)
        self.theme.text(surface,self.message,(x+18,y+10),font,FG,width-36)
