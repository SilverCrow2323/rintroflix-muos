# -*- coding: utf-8 -*-
"""RintrofliX — controller-first IPTV application for muOS / RG35XX H."""
from __future__ import annotations

import os
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame

from rintroflix import config as C
from rintroflix import epg as epg_mod
from rintroflix.addons import AddonError, AddonManager
from rintroflix import m3u
from rintroflix.input import InputReader
from rintroflix.logos import LogoCache
from rintroflix.player import Player, RESULT_BACK, RESULT_ERROR, RESULT_FAV, RESULT_NEXT, RESULT_PREV
from rintroflix.ui import ACCENTS, BG, DIM, FG, FAINT, PANEL, PANEL_ALT, SELECTED, H, W, MenuList, Theme, Toast, draw_icon

FPS = 30


def log(message):
    try:
        with open(C.LOG_PATH, "a", encoding="utf-8") as stream:
            stream.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), message))
    except OSError:
        pass


def env_button_map():
    """Read SDL's game-controller mapping supplied by muOS."""
    raw = os.environ.get("SDL_GAMECONTROLLERCONFIG", "")
    names = {"a": "A", "b": "B", "x": "X", "y": "Y",
             "leftshoulder": "L1", "rightshoulder": "R1",
             "lefttrigger": "L2", "righttrigger": "R2",
             "start": "START", "back": "SELECT"}
    result = {}
    for part in raw.split(","):
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        if key in names and value.startswith("b") and value[1:].isdigit():
            result[int(value[1:])] = names[key]
    return result


_ENV_BUTTONS = env_button_map()
KEYBOARD_MAP = {
    pygame.K_UP: "UP", pygame.K_DOWN: "DOWN", pygame.K_LEFT: "LEFT", pygame.K_RIGHT: "RIGHT",
    pygame.K_z: "A", pygame.K_x: "B", pygame.K_a: "X", pygame.K_s: "Y",
    pygame.K_q: "L1", pygame.K_w: "R1", pygame.K_RETURN: "START",
    pygame.K_RSHIFT: "SELECT", pygame.K_ESCAPE: "B", pygame.K_BACKSPACE: "B",
}


class Screen:
    def __init__(self, app):
        self.app = app
        self.theme = app.theme
        self.menu = None

    def on_button(self, button):
        if button == "B":
            self.app.pop()

    def draw(self, surface):
        pass


def draw_detail_panel(theme, surface, rect, title, description, icon="info", facts=(), status=None):
    """Consistent contextual panel used by source, library, add-on and settings screens."""
    theme.panel(surface, rect, PANEL_ALT, (42, 62, 82), 12)
    x, y = rect.x + 16, rect.y + 14
    draw_icon(surface, icon, (x + 17, y + 17), theme.accent, 29, True)
    theme.text(surface, title, (x + 43, y + 5), theme.f_med, FG, rect.w - 70)
    if status:
        badge_color = (78, 222, 169) if status.lower() in ("ready", "enabled", "loaded", "available") else (255, 190, 86)
        theme.chip(surface, x, y + 48, status.upper(), True, min(112, rect.w - 32))
        desc_y = y + 85
    else:
        desc_y = y + 48
    maxw = rect.w - 32
    words = str(description).split()
    lines, line = [], ""
    for word in words:
        candidate = (line + " " + word).strip()
        if theme.f_tiny.size(candidate)[0] > maxw and line:
            lines.append(line); line = word
        else:
            line = candidate
    if line: lines.append(line)
    for index, value in enumerate(lines[:4]):
        theme.text(surface, value, (x, desc_y + index * (theme.f_tiny.get_height() + 3)),
                   theme.f_tiny, DIM, maxw)
    if facts:
        sep_y = rect.bottom - min(100, 20 + len(facts) * 21)
        pygame.draw.line(surface, (44, 64, 83), (x, sep_y), (rect.right - 16, sep_y), 1)
        for index, fact in enumerate(facts[:4]):
            theme.text(surface, str(fact), (x, sep_y + 10 + index * 20), theme.f_tiny,
                       theme.accent if index == 0 else DIM, maxw)


class HomeScreen(Screen):
    """Kodi-inspired handheld dashboard with clear destinations and live context."""
    DESTINATIONS = [
        ("Watch TV", "Live channels, favourites and guide", "tv"),
        ("Local Library", "Browse films and videos on your SD card", "library"),
        ("Add-ons", "Install and manage extensions", "addons"),
        ("Sources", "Playlists and TV guide data", "sources"),
        ("Settings", "Appearance, playback and system info", "settings"),
    ]

    def __init__(self, app):
        super().__init__(app)
        self.selected = 0

    def on_button(self, button):
        if button == "UP":
            if self.selected >= 2:
                self.selected -= 2
        elif button == "DOWN":
            if self.selected + 2 < len(self.DESTINATIONS):
                self.selected += 2
            elif self.selected % 2 == 1 and self.selected + 1 < len(self.DESTINATIONS):
                self.selected += 1
        elif button == "LEFT":
            if self.selected % 2 == 1:
                self.selected -= 1
        elif button == "RIGHT":
            if self.selected % 2 == 0 and self.selected + 1 < len(self.DESTINATIONS):
                self.selected += 1
        elif button == "A":
            target = self.selected
            if target == 0: self.app.push(WatchTVScreen(self.app))
            elif target == 1: self.app.push(LocalLibraryScreen(self.app))
            elif target == 2: self.app.push(AddonsScreen(self.app))
            elif target == 3: self.app.push(SourcesScreen(self.app))
            elif target == 4: self.app.push(SettingsScreen(self.app))
        elif button == "START": self.app.running = False

    def draw(self, surface):
        t = self.theme
        t.header(surface, "Home", "HANDHELD MEDIA CENTRE")
        active = self.app.cfg.active_playlist()
        channel_count = len(self.app.playlist.channels) if self.app.playlist else 0
        guide_sources = len(self.app.epg.sources_ok) if self.app.epg else 0
        addon_count = len(self.app.addons.items)

        # Compact hero: reserve enough vertical space for every destination and
        # the footer at all supported UI scales on the native 640x480 panel.
        hero = pygame.Rect(16, t.header_h + 10, W - 32, 94)
        t.panel(surface, hero, PANEL_ALT, (39, 64, 83), 14)
        pygame.draw.rect(surface, t.accent, (hero.x + 1, hero.y + 11, 4, hero.h - 22), border_radius=2)
        t.text(surface, "YOUR MEDIA. YOUR WAY.", (hero.x + 19, hero.y + 9), t.f_big, FG, 390)
        t.text(surface, "Live TV and your local collection, built for handheld.",
               (hero.x + 21, hero.y + 42), t.f_tiny, DIM, 405)
        playlist_name = active.get("name", "No source configured") if active else "No source configured"
        source_label = ("SOURCE  ·  " + playlist_name) if active else "NO PLAYLIST CONFIGURED  ·  OPEN SOURCES"
        t.text(surface, source_label, (hero.x + 21, hero.bottom - t.f_tiny.get_height() - 7),
               t.f_tiny, t.accent if active else (255, 190, 86), 430)
        if t.logo_hero:
            surface.blit(t.logo_hero, (hero.right - 83, hero.y + 13))

        # Status chips sit on their own line and never collide with the cards.
        chip_y = hero.bottom + 8
        chips = [
            ("%d CHANNELS" % channel_count, "tv", 142, True),
            ("%d GUIDE SOURCES" % guide_sources, "guide", 174, False),
            ("%d ADD-ONS" % addon_count, "addons", 132, False),
        ]
        x = 18
        for label, icon_name, max_width, selected in chips:
            used = t.chip(surface, x, chip_y, label, selected, max_width, icon_name)
            x += used + 9

        # Four primary destinations in a 2x2 grid; Settings spans the final
        # row. This keeps the hierarchy balanced and all five cards visible.
        card_y = chip_y + 35
        card_h, gap = 57, 7
        x1, x2, half_w = 16, 326, 298
        for i, (title, subtitle, icon_name) in enumerate(self.DESTINATIONS):
            if i == 4:
                rect = pygame.Rect(16, card_y + 2 * (card_h + gap), W - 32, card_h)
            else:
                col, row = i % 2, i // 2
                rect = pygame.Rect(x1 if col == 0 else x2,
                                   card_y + row * (card_h + gap), half_w, card_h)
            badge = "LIVE" if i == 0 and channel_count else None
            t.home_card(surface, rect, title, subtitle, icon_name, i == self.selected, badge)

        t.footer(surface, [("A", "Open"), ("D-PAD", "Navigate"), ("START", "Exit")])


class WatchTVScreen(Screen):
    """Unified browsing surface for channels, favourites, search and programme guide."""
    TABS = (("All channels", "tv"), ("Favourites", "star"), ("Search", "search"), ("TV guide", "guide"))

    def __init__(self, app, tab=0, query=""):
        super().__init__(app)
        self.tab = max(0, min(len(self.TABS) - 1, tab))
        self.query = query
        self.guide_offset = 0
        self.group_index = 0
        self.groups = ["All groups"]
        available = app.available_channels()
        self.groups.extend(dict.fromkeys(ch.group for ch in available if ch.group))
        saved = app.cfg.get("last_group", "*")
        if saved in self.groups:
            self.group_index = self.groups.index(saved)
        self.menu = MenuList(self.theme, logos=app.logos if app.cfg.get("show_logos", True) else None, x=12, width=376,
                             top=self.theme.header_h + 92,
                             bottom=H - self.theme.footer_h - 8)
        self.channels = []
        self.rebuild()
        if self.tab == 2 and not self.query:
            self._ask_search()

    def _ask_search(self):
        self.app.push(KeyboardScreen(self.app, "SEARCH CHANNELS", self.query, self.set_query))

    def set_query(self, value):
        self.query = value.strip()
        self.tab = 2
        self.rebuild()

    def rebuild(self):
        playlist_channels = self.app.available_channels()
        if self.tab == 1:
            favourites = set(self.app.cfg.get("favorites", []))
            channels = [ch for ch in playlist_channels if ch.url in favourites]
        else:
            channels = playlist_channels
        if self.tab in (0, 1, 2) and self.groups:
            group = self.groups[self.group_index]
            if group != "All groups":
                channels = [ch for ch in channels if ch.group == group]
        if self.tab == 2 and self.query:
            needle = self.query.casefold()
            channels = [ch for ch in channels if needle in ch.name.casefold() or needle in ch.group.casefold() or needle in ch.tvg_name.casefold()]
        self.channels = channels
        items = []
        favourites = set(self.app.cfg.get("favorites", []))
        for channel in channels:
            current, following = self.app.epg.now_next(channel) if self.app.epg else (None, None)
            if current:
                sub = "NOW  ·  " + current.title
            else:
                sub = channel.group
            badge = "★" if channel.url in favourites else ""
            items.append((channel.name, sub, badge, channel.logo, "tv"))
        self.menu.items = items
        self.menu.sel = min(self.menu.sel, max(0, len(items) - 1))

    def current(self):
        return self.channels[self.menu.sel] if self.channels and self.menu.sel < len(self.channels) else None

    def on_button(self, button):
        if button == "B":
            self.app.pop()
            return
        if button == "SELECT":
            self.tab = (self.tab + 1) % len(self.TABS)
            self.menu.sel = 0
            self.rebuild()
            if self.tab == 2 and not self.query:
                self._ask_search()
            return
        if button == "X":
            self._ask_search()
            return
        if button in ("L1", "R1") and self.groups:
            self.group_index = (self.group_index + (1 if button == "R1" else -1)) % len(self.groups)
            group = self.groups[self.group_index]
            self.app.cfg.set("last_group", "*" if group == "All groups" else group)
            self.rebuild()
            return
        if button == "UP":
            self.menu.move(-1)
        elif button == "DOWN":
            self.menu.move(1)
        elif button == "LEFT":
            if self.tab == 3:
                self.guide_offset = max(-12, self.guide_offset - 1)
            else:
                self.menu.page(-1)
        elif button == "RIGHT":
            if self.tab == 3:
                self.guide_offset = min(24, self.guide_offset + 1)
            else:
                self.menu.page(1)
        elif button == "Y":
            channel = self.current()
            if channel:
                added = self.app.cfg.toggle_favorite(channel.url)
                self.app.toast(("Added to favourites: " if added else "Removed from favourites: ") + channel.name)
                self.rebuild()
        elif button == "START":
            channel = self.current()
            if channel:
                self.app.push(ChannelInfoScreen(self.app, channel))
        elif button == "A":
            if self.tab == 2 and not self.query:
                self._ask_search()
                return
            channel = self.current()
            if channel:
                self.app.play_channel(self.channels, self.menu.sel)
                self.rebuild()

    def _draw_details(self, surface, channel):
        x, y, width, height = 400, self.menu.top, 228, self.menu.bottom - self.menu.top
        self.theme.panel(surface, (x, y, width, height), PANEL, (34, 52, 72), 10)
        if not channel:
            self.theme.text(surface, "Select a channel", (x + 18, y + 25), self.theme.f_med, DIM)
            self.theme.text(surface, "Channel information and", (x + 18, y + 64), self.theme.f_tiny, FAINT)
            self.theme.text(surface, "programme details appear here.", (x + 18, y + 84), self.theme.f_tiny, FAINT)
            return
        logo = self.app.logos.get(channel.logo, 76) if (channel.logo and self.app.cfg.get("show_logos", True)) else None
        if logo:
            surface.blit(logo, (x + 16, y + 14))
        else:
            badge = pygame.Rect(x + 16, y + 14, 76, 58)
            pygame.draw.rect(surface, PANEL_ALT, badge, border_radius=8)
            initials = "".join(part[:1] for part in channel.name.split()[:2]).upper() or "TV"
            self.theme.text(surface, initials, (badge.x + 12, badge.y + 9), self.theme.f_big, self.theme.accent, 55)
        self.theme.text(surface, channel.name, (x + 102, y + 17), self.theme.f_med, FG, width - 116)
        self.theme.text(surface, channel.group, (x + 102, y + 48), self.theme.f_tiny, DIM, width - 116)
        line_y = y + 92
        pygame.draw.line(surface, (42, 60, 78), (x + 14, line_y), (x + width - 14, line_y), 1)
        current, following = self.app.epg.now_next(channel) if self.app.epg else (None, None)
        self.theme.text(surface, "ON NOW", (x + 16, line_y + 12), self.theme.f_tiny, self.theme.accent)
        self.theme.text(surface, current.title if current else "No programme data", (x + 16, line_y + 34), self.theme.f_small, FG, width - 32)
        if current:
            now = time.time()
            duration = max(1.0, current.stop - current.start)
            progress = max(0.0, min(1.0, (now - current.start) / duration))
            bx, by, bw = x + 16, line_y + 63, width - 32
            pygame.draw.rect(surface, (44, 60, 77), (bx, by, bw, 5), border_radius=3)
            pygame.draw.rect(surface, self.theme.accent, (bx, by, int(bw * progress), 5), border_radius=3)
        next_y = line_y + 88
        self.theme.text(surface, "UP NEXT", (x + 16, next_y), self.theme.f_tiny, self.theme.accent)
        self.theme.text(surface, following.title if following else "Schedule unavailable", (x + 16, next_y + 22), self.theme.f_small, FG, width - 32)
        if following:
            self.theme.text(surface, time.strftime("%H:%M", time.localtime(following.start)),
                            (x + 16, next_y + 51), self.theme.f_tiny, DIM)

    def _draw_guide(self, surface):
        """Compact EPG timeline: channel rail plus a 2-hour programme grid."""
        now = time.time()
        start = now + self.guide_offset * 1800
        end = start + 2 * 3600
        top = self.menu.top + 4
        bottom = self.menu.bottom
        row_h = 49
        visible = max(1, (bottom - top) // row_h)
        first = max(0, min(self.menu.sel - visible // 2, len(self.channels) - visible))
        rail_x, rail_w = 12, 202
        grid_x, grid_w = 220, W - 234
        # Half-hour ticks keep the schedule readable on the 3.5-inch display.
        for tick in range(5):
            ts = start + tick * 1800
            xx = grid_x + int(grid_w * tick / 4)
            label = time.strftime("%H:%M", time.localtime(ts))
            self.theme.text(surface, label, (xx + 4, top - 23), self.theme.f_tiny, DIM)
            pygame.draw.line(surface, (39, 56, 73), (xx, top - 3), (xx, bottom), 1)
        for row, channel_index in enumerate(range(first, min(first + visible, len(self.channels)))):
            channel = self.channels[channel_index]
            y = top + row * row_h
            selected = channel_index == self.menu.sel
            bg = SELECTED if selected else PANEL
            pygame.draw.rect(surface, bg, (rail_x, y, W - 24, row_h - 4), border_radius=7)
            if selected:
                pygame.draw.rect(surface, self.theme.accent, (rail_x, y, 3, row_h - 4), border_radius=2)
            if channel.logo and self.app.cfg.get("show_logos", True):
                logo = self.app.logos.get(channel.logo, 30)
            else:
                logo = None
            if logo:
                surface.blit(logo, (rail_x + 9, y + (row_h - logo.get_height() - 4) // 2))
            else:
                draw_icon(surface, "tv", (rail_x + 26, y + 21), self.theme.accent if selected else FAINT, 21)
            self.theme.text(surface, channel.name, (rail_x + 54, y + 7), self.theme.f_small,
                            FG if selected else DIM, rail_w - 62)
            pygame.draw.line(surface, (43, 59, 76), (grid_x, y + 3), (grid_x, y + row_h - 8), 1)
            programmes = self.app.epg.window(channel, start, end) if self.app.epg else []
            if not programmes:
                self.theme.text(surface, "No guide data", (grid_x + 10, y + 12), self.theme.f_tiny, FAINT, grid_w - 20)
            for programme in programmes:
                left = max(0.0, programme.start - start)
                right = min(end - start, programme.stop - start)
                if right <= left:
                    continue
                px = grid_x + int(grid_w * left / (end - start))
                pw = max(5, int(grid_w * (right-left) / (end-start)) - 3)
                is_current = programme.start <= now < programme.stop
                pr = pygame.Rect(px + 2, y + 6, pw, row_h - 16)
                pygame.draw.rect(surface, (28, 70, 82) if is_current else PANEL_ALT, pr, border_radius=5)
                pygame.draw.rect(surface, self.theme.accent if is_current else (53, 72, 91), pr, 1, border_radius=5)
                self.theme.text(surface, programme.title, (pr.x + 7, pr.y + 7), self.theme.f_tiny,
                                FG if is_current else DIM, pr.w - 12)
        if not self.channels:
            self.theme.text(surface, "No channels to show. Add a playlist in Sources.", (24, top + 18), self.theme.f_small, DIM)
        self.theme.text(surface, "LEFT / RIGHT  ·  SHIFT TIME WINDOW", (18, bottom - 18), self.theme.f_tiny, FAINT)

    def draw(self, surface):
        self.theme.header(surface, "Watch TV", "LIVE CHANNELS  /  FAVOURITES  /  SEARCH  /  PROGRAMME GUIDE")
        y = self.theme.header_h + 10
        x = 16
        for index, (label, tab_icon) in enumerate(self.TABS):
            width = self.theme.chip(surface, x, y, label, self.tab == index, icon=tab_icon)
            x += width + 7
        group_y = y + 38
        if self.tab == 2:
            search_text = self.query if self.query else "Press A or X to enter a channel name"
            self.theme.panel(surface, (16, group_y, W - 32, 32), PANEL, (38, 56, 74), 8)
            self.theme.text(surface, "⌕  " + search_text, (28, group_y + 6), self.theme.f_tiny, DIM, W - 56)
        elif self.tab != 3:
            group = self.groups[self.group_index] if self.groups else "All groups"
            self.theme.text(surface, "GROUP", (20, group_y + 5), self.theme.f_tiny, FAINT)
            self.theme.chip(surface, 80, group_y, group, True, 240)
            self.theme.text(surface, "L1 / R1  ·  CHANGE GROUP", (350, group_y + 6), self.theme.f_tiny, FAINT)
        else:
            self.theme.text(surface, "NOW / NEXT PROGRAMME SCHEDULE", (20, group_y + 5), self.theme.f_tiny, FAINT)
        self.menu.width = 376 if self.tab != 3 else W - 24
        self.menu.logos = self.app.logos if self.app.cfg.get("show_logos", True) else None
        self.menu.top = group_y + 40
        self.menu.bottom = H - self.theme.footer_h - 9
        self.menu.x = 12
        if self.tab == 3:
            self._draw_guide(surface)
        else:
            favourite_urls = set(self.app.cfg.get("favorites", []))
            channel_rows = []
            for channel in self.channels:
                current, _following = self.app.epg.now_next(channel) if self.app.epg else (None, None)
                subtitle = "NOW  ·  " + current.title if current else channel.group
                channel_rows.append((channel.name, subtitle,
                                     "★" if channel.url in favourite_urls else "",
                                     channel.logo, "tv"))
            self.menu.items = channel_rows
            self.menu.draw(surface)
            self._draw_details(surface, self.current())
        count = len(self.channels)
        if self.tab == 2 and not self.query:
            self.theme.text(surface, "Enter a name or group to find a channel.", (24, self.menu.top + 16), self.theme.f_small, DIM)
        elif count == 0:
            message = "No favourite channels yet" if self.tab == 1 else "No matching channels"
            self.theme.text(surface, message, (24, self.menu.top + 16), self.theme.f_med, DIM)
        self.theme.footer(surface, [("A", "Play"), ("Y", "Favourite"), ("X", "Search"),
                                    ("SELECT", "Next tab"), ("START", "Details"), ("B", "Back")])


class SourcesScreen(Screen):
    """Keep playlist and TV-guide source management together in one place."""
    def __init__(self, app):
        super().__init__(app)
        self.menu = MenuList(self.theme, row_h=max(70, self.theme.row_h + 6),
                             top=self.theme.header_h + 42, bottom=H - self.theme.footer_h - 10)
        self.refresh()

    def refresh(self):
        playlists = self.app.cfg.playlists()
        active = self.app.cfg.active_playlist()
        channels = len(self.app.playlist.channels) if self.app.playlist else 0
        sources = len(self.app.epg.sources_ok)
        self.menu.items = [
            ("Playlists", "%d configured · %d channels loaded" % (len(playlists), channels), "M3U", "", "sources"),
            ("TV guide data", "%d XMLTV sources loaded" % sources, "EPG", "", "guide"),
        ]

    def on_button(self, button):
        if button == "UP":
            self.menu.move(-1)
        elif button == "DOWN":
            self.menu.move(1)
        elif button == "B":
            self.app.pop()
        elif button == "A":
            if self.menu.sel == 0:
                self.app.push(PlaylistScreen(self.app))
            else:
                self.app.push(EpgScreen(self.app))

    def draw(self, surface):
        self.theme.header(surface, "Sources & guide data", "PLAYLISTS  /  XMLTV  /  CHANNEL METADATA")
        self.theme.section_title(surface, "Content sources", "Keep channel lists and programme data in sync",
                                 y=self.theme.header_h + 10)
        top = self.theme.header_h + 76
        bottom = H - self.theme.footer_h - 10
        self.menu.x, self.menu.width, self.menu.top, self.menu.bottom = 14, 284, top, bottom
        self.menu.row_h = max(76, self.theme.row_h + 12)
        self.menu.draw(surface)
        active = self.app.cfg.active_playlist()
        channels = len(self.app.playlist.channels) if self.app.playlist else 0
        if self.menu.sel == 0:
            title = "Playlists"
            desc = "Add M3U or M3U8 playlists, choose the active source and refresh your channel catalogue."
            facts = ["%d configured playlist(s)" % len(self.app.cfg.playlists()),
                     "%d channels currently loaded" % channels,
                     ("Active: " + str(active.get("name", "Playlist"))) if active else "No active playlist"]
            status = "Ready" if channels else "Setup needed"
            icon = "sources"
        else:
            title = "TV guide data"
            desc = "Manage XMLTV URLs, automatic playlist discovery and guide refreshes."
            facts = ["%d guide source(s) loaded" % len(self.app.epg.sources_ok),
                     "%d channel keys indexed" % len(self.app.epg.by_key),
                     "Current and next programme details"]
            status = "Loaded" if self.app.epg.sources_ok else "Setup needed"
            icon = "guide"
        draw_detail_panel(self.theme, surface, pygame.Rect(310, top, 314, bottom-top),
                          title, desc, icon, facts, status)
        self.theme.footer(surface, [("A", "Open"), ("UP / DOWN", "Select"), ("B", "Back")])


class ChannelsScreen(Screen):
    def __init__(self, app, channels, label="playlist"):
        super().__init__(app)
        self.channels_all = list(channels)
        self.label = label
        groups = []
        seen_groups = set()
        for channel in self.channels_all:
            if channel.group not in seen_groups:
                seen_groups.add(channel.group)
                groups.append(channel.group)
        self.groups = ["All groups"] + groups
        saved = app.cfg.get("last_group", "*")
        self.group_index = self.groups.index(saved) if saved in self.groups else 0
        self.mode = app.cfg.get("view_mode", "list")
        if self.mode not in ("list", "grid", "guide"):
            self.mode = "list"
        self.menu = MenuList(self.theme)
        self.rebuild()

    @property
    def channels(self):
        group = self.groups[self.group_index]
        if group == "All groups":
            return self.channels_all
        return [ch for ch in self.channels_all if ch.group == group]

    def rebuild(self):
        favs = set(self.app.cfg.get("favorites", []))
        items = []
        for ch in self.channels:
            current, following = self.app.epg.now_next(ch) if self.app.epg else (None, None)
            if self.mode == "guide":
                desc = "NOW: %s · NEXT: %s" % (
                    current.title if current else "—",
                    following.title if following else "—")
            else:
                desc = ("NOW · " + current.title) if current else ch.group
            badge = "★" if ch.url in favs else ""
            items.append((ch.name, desc, badge))
        self.menu.items = items
        self.menu.sel = min(self.menu.sel, max(0, len(items) - 1))

    def current(self):
        items = self.channels
        return items[self.menu.sel] if items and self.menu.sel < len(items) else None

    def on_button(self, button):
        if button == "SELECT":
            order = ["list", "grid", "guide"]
            self.mode = order[(order.index(self.mode) + 1) % len(order)]
            self.app.cfg.set("view_mode", self.mode)
            self.rebuild()
        elif button == "UP":
            self.menu.move(-4 if self.mode == "grid" else -1)
        elif button == "DOWN":
            self.menu.move(4 if self.mode == "grid" else 1)
        elif button == "LEFT":
            self.menu.move(-1) if self.mode == "grid" else self.menu.page(-1)
        elif button == "RIGHT":
            self.menu.move(1) if self.mode == "grid" else self.menu.page(1)
        elif button in ("L1", "R1"):
            self.group_index = (self.group_index + (1 if button == "R1" else -1)) % len(self.groups)
            self.app.cfg.set("last_group", "*" if self.group_index == 0 else self.groups[self.group_index])
            self.rebuild()
        elif button == "Y":
            channel = self.current()
            if channel:
                added = self.app.cfg.toggle_favorite(channel.url)
                self.app.toast(("Added to favourites: " if added else "Removed from favourites: ") + channel.name)
                self.rebuild()
        elif button == "START":
            channel = self.current()
            if channel:
                self.app.push(ChannelInfoScreen(self.app, channel))
        elif button == "A":
            if self.tab == 2 and not self.query:
                self._ask_search()
                return
            channel = self.current()
            if channel:
                self.app.play_channel(self.channels, self.menu.sel)
                self.rebuild()
        elif button == "B":
            self.app.pop()

    def draw(self, surface):
        group = self.groups[self.group_index]
        mode_label = {"list": "LIST", "grid": "GRID", "guide": "GUIDE"}[self.mode]
        self.theme.header(surface, "CHANNELS · " + mode_label,
                          "%s  ·  %s  ·  %d channels" % (self.label, group, len(self.channels)))
        if self.mode != "grid":
            self.menu.draw(surface)
        else:
            per_page = 12
            page = self.menu.sel // per_page
            first = page * per_page
            columns, rows = 4, 3
            card_w = 151
            card_h = max(80, (H - self.theme.header_h - self.theme.footer_h - 22) // rows - 6)
            start_x, start_y = 8, self.theme.header_h + 8
            favourites = set(self.app.cfg.get("favorites", []))
            for index in range(first, min(first + per_page, len(self.channels))):
                local = index - first
                col, row = local % columns, local // columns
                x = start_x + col * (card_w + 5)
                y = start_y + row * (card_h + 5)
                selected = index == self.menu.sel
                pygame.draw.rect(surface, (25, 55, 72) if selected else (15, 22, 33),
                                 (x, y, card_w, card_h), border_radius=5)
                pygame.draw.rect(surface, self.theme.accent if selected else FAINT,
                                 (x, y, card_w, card_h), 2 if selected else 1, border_radius=5)
                channel = self.channels[index]
                self.theme.text(surface, channel.name, (x + 8, y + 7), self.theme.f_tiny,
                                FG if selected else DIM, card_w - 40)
                self.theme.text(surface, "★" if channel.url in favourites else "",
                                (x + card_w - 28, y + 7), self.theme.f_tiny, self.theme.accent)
                # On compact 200% layouts, keep the card uncluttered rather than
                # letting a second line collide with the favorite marker.
                if card_h >= self.theme.f_tiny.get_height() * 2 + 18:
                    current, following = self.app.epg.now_next(channel) if self.app.epg else (None, None)
                    sub = current.title if current else channel.group
                    self.theme.text(surface, sub, (x + 8, y + self.theme.f_tiny.get_height() + 13),
                                    self.theme.f_tiny, DIM if selected else FAINT, card_w - 16)
            pages = max(1, (len(self.channels) + per_page - 1) // per_page)
            self.theme.text(surface, "PAGE %d/%d" % (page + 1, pages),
                            (W - 112, self.theme.header_h + 4), self.theme.f_tiny, DIM)
        self.theme.footer(surface, [("A", "Play"), ("Y", "Favourite"),
                                    ("L/R", "Group"), ("SELECT", "View"), ("B", "Back")])


class GuideScreen(Screen):
    def __init__(self, app):
        super().__init__(app)
        self.channels = list(app.playlist.channels) if app.playlist else []
        self.menu = MenuList(self.theme)
        self.rebuild()

    def rebuild(self):
        items = []
        for ch in self.channels:
            current, following = self.app.epg.now_next(ch) if self.app.epg else (None, None)
            title = current.title if current else "Schedule unavailable"
            later = following.title if following else ch.group
            items.append((ch.name, "NOW: %s   ·   NEXT: %s" % (title, later), ""))
        self.menu.items = items

    def on_button(self, button):
        if button == "UP":
            self.menu.move(-1)
        elif button == "DOWN":
            self.menu.move(1)
        elif button == "LEFT":
            self.menu.page(-1)
        elif button == "RIGHT":
            self.menu.page(1)
        elif button == "A" and self.channels:
            self.app.play_channel(self.channels, self.menu.sel)
            self.rebuild()
        elif button == "B":
            self.app.pop()

    def draw(self, surface):
        self.theme.header(surface, "PROGRAMME GUIDE", "%d channels · current and next programme" % len(self.channels))
        self.menu.draw(surface)
        self.theme.footer(surface, [("A", "Watch"), ("LEFT/RIGHT", "Pages"), ("B", "Back")])


class PlaylistScreen(Screen):
    def __init__(self, app):
        super().__init__(app)
        self.menu = MenuList(self.theme)
        self.rebuild()

    def rebuild(self):
        entries = self.app.cfg.playlists()
        active = self.app.cfg.get("active_playlist")
        self.count = len(entries)
        items = [(p.get("name", "Playlist"), p.get("source", ""), "ACTIVE" if p.get("id") == active else "", "", "sources") for p in entries]
        items.extend([
            ("+ ADD FROM URL", "M3U / M3U8 via HTTP(S)", "+", "", "sources"),
            ("+ ADD FROM FILE", "Browse the SD card or USB storage", "+", "", "folder"),
            ("PUBLIC PRESETS", "IPTV-Org · public channel lists", "", "", "tv"),
            ("RELOAD PLAYLIST", "Download the active list again", "↻", "", "sources"),
        ])
        self.menu.items = items
        self.menu.sel = min(self.menu.sel, len(items) - 1)

    def on_button(self, button):
        if button == "UP":
            self.menu.move(-1)
        elif button == "DOWN":
            self.menu.move(1)
        elif button == "B":
            self.app.pop()
        elif button == "X" and self.menu.sel < self.count:
            entry = self.app.cfg.playlists()[self.menu.sel]
            self.app.cfg.remove_playlist(entry["id"])
            self.app.reload_playlist()
            self.rebuild()
        elif button == "A":
            index = self.menu.sel
            if index < self.count:
                entry = self.app.cfg.playlists()[index]
                self.app.cfg.set("active_playlist", entry["id"])
                self.app.reload_playlist()
                self.rebuild()
            elif index == self.count:
                self.app.push(KeyboardScreen(self.app, "PLAYLIST URL", "https://", self.add_url))
            elif index == self.count + 1:
                self.app.push(FileBrowserScreen(self.app, self.add_file))
            elif index == self.count + 2:
                self.app.push(PresetScreen(self.app, self.rebuild))
            elif index == self.count + 3:
                self.app.reload_playlist(force=True)
                self.rebuild()

    def add_url(self, url):
        name = url.rstrip("/").rsplit("/", 1)[-1] or "Playlist IPTV"
        self.app.cfg.add_playlist(name[:70], url, "url")
        self.app.cfg.set("active_playlist", self.app.cfg.playlists()[-1]["id"])
        self.app.reload_playlist(force=True)
        self.rebuild()

    def add_file(self, path):
        self.app.cfg.add_playlist(Path(path).name, path, "file")
        self.app.cfg.set("active_playlist", self.app.cfg.playlists()[-1]["id"])
        self.app.reload_playlist(force=True)
        self.rebuild()

    def draw(self, surface):
        self.theme.header(surface, "PLAYLIST", "%d playlists configured" % self.count)
        self.menu.draw(surface)
        self.theme.footer(surface, [("A", "Open / activate"), ("X", "Remove"), ("B", "Back")])


class PresetScreen(Screen):
    def __init__(self, app, on_done):
        super().__init__(app)
        self.on_done = on_done
        self.menu = MenuList(self.theme)
        self.menu.items = [(name, url, "", "", "sources") for name, url in C.PRESET_PLAYLISTS]

    def on_button(self, button):
        if button == "UP":
            self.menu.move(-1)
        elif button == "DOWN":
            self.menu.move(1)
        elif button == "B":
            self.app.pop()
        elif button == "A":
            name, url = C.PRESET_PLAYLISTS[self.menu.sel]
            item = self.app.cfg.add_playlist(name, url, "url")
            self.app.cfg.set("active_playlist", item["id"])
            self.app.pop()
            self.app.reload_playlist(force=True)
            self.on_done()

    def draw(self, surface):
        self.theme.header(surface, "PUBLIC PRESETS", "IPTV-Org · choose a playlist")
        self.menu.draw(surface)
        self.theme.footer(surface, [("A", "Add"), ("B", "Back")])


class FileBrowserScreen(Screen):
    """Controller file picker shared by playlists, add-ons and library folders."""
    ROOTS = ["/run/muos/storage", "/mnt/mmc", "/mnt/sdcard", "/mnt/usb", "/media", str(Path.home())]
    EXTS = (".m3u", ".m3u8")

    def __init__(self, app, on_pick, path=None, extensions=None, directory_mode=False, title="Browse files"):
        super().__init__(app)
        self.on_pick = on_pick
        self.path = path
        self.extensions = tuple(extensions if extensions is not None else self.EXTS)
        self.directory_mode = directory_mode
        self.title = title
        self.entries = []
        self.menu = MenuList(self.theme)
        self.refresh()

    def refresh(self):
        self.entries = []
        if self.path is None:
            for root in self.ROOTS:
                if os.path.isdir(root):
                    self.entries.append((root, "root"))
        else:
            if self.directory_mode:
                self.entries.append(("Use this folder", "pick"))
            self.entries.append(("..", "parent"))
            try:
                for name in sorted(os.listdir(self.path), key=str.casefold):
                    if name.startswith("."):
                        continue
                    full = os.path.join(self.path, name)
                    if os.path.isdir(full):
                        self.entries.append((name, "dir"))
                    elif self.extensions and name.lower().endswith(self.extensions):
                        self.entries.append((name, "file"))
            except OSError:
                pass
        self.menu.items = []
        for name, kind in self.entries:
            if kind in ("dir", "root", "parent"):
                self.menu.items.append((name, "Folder", "", "", "folder"))
            elif kind == "pick":
                self.menu.items.append(("Use this folder", self.path, "SELECT", "", "library"))
            else:
                self.menu.items.append((name, "File", "", "", "video"))
        self.menu.sel = min(self.menu.sel, max(0, len(self.entries)-1))

    def on_button(self, button):
        if button == "UP": self.menu.move(-1)
        elif button == "DOWN": self.menu.move(1)
        elif button == "B": self.app.pop()
        elif button == "A" and self.entries:
            name, kind = self.entries[self.menu.sel]
            if kind == "pick":
                chosen = self.path
                self.app.pop()
                self.on_pick(chosen)
                return
            if kind == "root": self.path = name
            elif kind == "parent":
                parent = os.path.dirname(self.path.rstrip("/"))
                self.path = parent if parent and parent != "/" else None
            elif kind == "dir": self.path = os.path.join(self.path, name)
            elif kind == "file":
                chosen = os.path.join(self.path, name)
                self.app.pop()
                self.on_pick(chosen)
                return
            self.refresh()

    def draw(self, surface):
        self.theme.header(surface, self.title, self.path or "Available locations")
        self.menu.draw(surface)
        self.theme.footer(surface, [("A", "Open / select"), ("B", "Back")])


class LocalLibraryScreen(Screen):
    """User-defined local media roots; browsing is on-demand, never a full SD crawl."""
    def __init__(self, app):
        super().__init__(app)
        self.menu = MenuList(self.theme)
        self.refresh()

    def refresh(self):
        self.sources = list(self.app.cfg.get("library_sources", []))
        self.rows = [("source", path) for path in self.sources] + [("add", None)]
        self.menu.items = [(Path(path).name or path, path, "FOLDER", "", "library") for path in self.sources]
        self.menu.items.append(("+ Add library folder", "Choose a folder on SD card or USB storage", "+", "", "folder"))
        self.menu.sel = min(self.menu.sel, len(self.menu.items)-1)

    def add_folder(self, path):
        if not path or not os.path.isdir(path):
            self.app.toast("The selected folder is not available.", ok=False)
            return
        sources = list(self.app.cfg.get("library_sources", []))
        if path not in sources:
            sources.append(path)
            self.app.cfg.set("library_sources", sources)
        self.refresh()
        self.app.toast("Library location added")

    def on_button(self, button):
        if button == "UP": self.menu.move(-1)
        elif button == "DOWN": self.menu.move(1)
        elif button == "B": self.app.pop()
        elif button == "X" and self.menu.sel < len(self.sources):
            path = self.sources[self.menu.sel]
            values = [p for p in self.sources if p != path]
            self.app.cfg.set("library_sources", values)
            self.refresh()
        elif button == "A":
            index = self.menu.sel
            if index < len(self.sources):
                path = self.sources[index]
                if os.path.isdir(path): self.app.push(MediaBrowserScreen(self.app, path, path))
                else: self.app.toast("Folder is missing. Remove it and add it again.", ok=False)
            else:
                self.app.push(FileBrowserScreen(self.app, self.add_folder, directory_mode=True,
                                                title="ADD LOCAL LIBRARY FOLDER"))

    def draw(self, surface):
        self.theme.header(surface, "Local Library", "YOUR MEDIA  /  LOCAL STORAGE  /  ON-DEMAND BROWSING")
        self.theme.section_title(surface, "Library locations", "Choose a saved folder or add another location",
                                 y=self.theme.header_h + 10)
        top = self.theme.header_h + 76
        bottom = H - self.theme.footer_h - 10
        self.menu.x, self.menu.width, self.menu.top, self.menu.bottom = 14, 284, top, bottom
        self.menu.draw(surface)
        if self.menu.sel < len(self.sources):
            path = self.sources[self.menu.sel]
            exists = os.path.isdir(path)
            title = Path(path).name or path
            desc = "Browse this folder to find supported video files. RintrofliX scans only when you open it; it does not crawl the whole SD card."
            facts = [path, "Folder is available" if exists else "Folder is missing",
                     "Supported: MKV · MP4 · AVI · MOV · TS"]
            status = "Available" if exists else "Missing"
        else:
            title, desc = "Add a library folder", "Select a directory on your SD card or USB storage. It will be saved as a library location for quick access."
            facts = ["No automatic full-card scan", "Browse folders on demand", "Use X on a saved entry to remove it"]
            status = "Add location"
        draw_detail_panel(self.theme, surface, pygame.Rect(310, top, 314, bottom-top),
                          title, desc, "library", facts, status)
        self.theme.footer(surface, [("A", "Browse / add"), ("X", "Remove"), ("UP / DOWN", "Select"), ("B", "Back")])


class MediaBrowserScreen(Screen):
    EXTENSIONS = (".mkv", ".mp4", ".avi", ".mov", ".m4v", ".webm", ".ts", ".mpg", ".mpeg", ".m2ts", ".flv")

    def __init__(self, app, root, path=None):
        super().__init__(app)
        self.root = os.path.abspath(root)
        self.path = os.path.abspath(path or root)
        self.menu = MenuList(self.theme)
        self.refresh()

    def refresh(self):
        self.entries = []
        if self.path != self.root:
            self.entries.append(("..", "parent"))
        try:
            names = sorted(os.listdir(self.path), key=str.casefold)
        except OSError:
            names = []
        for name in names:
            if name.startswith("."): continue
            full = os.path.join(self.path, name)
            if os.path.isdir(full): self.entries.append((name, "folder"))
            elif name.lower().endswith(self.EXTENSIONS): self.entries.append((name, "media"))
        self.menu.items = [(name, "Folder" if kind != "media" else Path(name).suffix[1:].upper(),
                            "", "", "folder" if kind != "media" else "video") for name, kind in self.entries]
        self.menu.sel = min(self.menu.sel, max(0, len(self.entries)-1))

    def on_button(self, button):
        if button == "UP": self.menu.move(-1)
        elif button == "DOWN": self.menu.move(1)
        elif button == "B":
            if self.path != self.root:
                self.path = os.path.dirname(self.path)
                self.refresh()
            else: self.app.pop()
        elif button == "A" and self.entries:
            name, kind = self.entries[self.menu.sel]
            if kind == "parent":
                self.path = os.path.dirname(self.path)
                self.refresh()
            elif kind == "folder":
                self.path = os.path.join(self.path, name)
                self.refresh()
            else:
                media_paths = [os.path.join(self.path, entry_name)
                               for entry_name, entry_kind in self.entries if entry_kind == "media"]
                queue = [m3u.Channel(Path(item).stem, item, group="Local Library") for item in media_paths]
                position = next((i for i, item in enumerate(queue) if item.url == os.path.join(self.path, name)), 0)
                self.app.play_channel(queue, position)
                self.refresh()

    def draw(self, surface):
        self.theme.header(surface, "Local Library", self.path)
        self.menu.draw(surface)
        self.theme.footer(surface, [("A", "Open / play"), ("B", "Back")])


class AddonsScreen(Screen):
    """Manage optional Python extensions installed from local .rfxaddon packages."""
    def __init__(self, app):
        super().__init__(app)
        self.manager = app.addons
        self.menu = MenuList(self.theme)
        self.confirm_remove = None
        self.confirm_enable = None
        self.refresh()

    def refresh(self):
        self.manager.discover(load_enabled=True)
        self.rows = []
        items = []
        for item in self.manager.items:
            manifest = item["manifest"]
            enabled = item["enabled"]
            self.rows.append(("addon", manifest["id"]))
            items.append((manifest.get("name", manifest["id"]),
                          "v%s · %s" % (manifest.get("version", "?"), manifest.get("description", "")),
                          "ENABLED" if enabled else "DISABLED", "", "addons"))
        for action in self.manager.actions:
            self.rows.append(("action", action))
            items.append((action["label"], action.get("description", "Add-on action"),
                          action["addon_id"].upper(), "", "play"))
        self.rows.append(("install", None))
        items.append(("+ Install add-on package", "Browse for a .rfxaddon or .zip package", "+", "", "addons"))
        self.menu.items = items
        self.menu.sel = min(self.menu.sel, len(items)-1)

    def install(self, path):
        try:
            manifest = self.manager.install_archive(path)
            self.app.toast("Installed %s. Review it before enabling." % manifest.get("name", manifest["id"]))
        except (AddonError, OSError, ValueError) as exc:
            self.app.toast("Add-on install failed: %s" % str(exc)[:70], ok=False)
        self.refresh()

    def on_button(self, button):
        if button == "UP": self.menu.move(-1); self.confirm_remove = None; self.confirm_enable = None
        elif button == "DOWN": self.menu.move(1); self.confirm_remove = None; self.confirm_enable = None
        elif button == "B": self.confirm_remove = None; self.confirm_enable = None; self.app.pop()
        elif button == "X":
            if self.menu.sel < len(self.rows) and self.rows[self.menu.sel][0] == "addon":
                addon_id = self.rows[self.menu.sel][1]
                if self.confirm_remove == addon_id:
                    try:
                        self.manager.remove(addon_id)
                        self.app.toast("Add-on removed")
                    except OSError as exc:
                        self.app.toast("Could not remove add-on: " + str(exc)[:60], ok=False)
                    self.confirm_remove = None
                    self.refresh()
                else:
                    self.confirm_remove = addon_id
                    self.app.toast("Press X again to remove this add-on", ok=False)
        elif button == "A":
            if self.menu.sel >= len(self.rows): return
            kind, value = self.rows[self.menu.sel]
            if kind == "addon":
                item = next((x for x in self.manager.items if x["manifest"]["id"] == value), None)
                if item and item["enabled"]:
                    try:
                        self.manager.set_enabled(value, False)
                        self.app.toast("Add-on disabled")
                    except AddonError as exc:
                        self.app.toast(str(exc)[:90], ok=False)
                    self.confirm_enable = None
                    self.refresh()
                elif item and self.confirm_enable == value:
                    try:
                        self.manager.set_enabled(value, True)
                        self.app.toast("Add-on enabled")
                    except AddonError as exc:
                        self.app.toast(str(exc)[:90], ok=False)
                    self.confirm_enable = None
                    self.refresh()
                elif item:
                    self.confirm_enable = value
                    self.app.toast("Press A again to run this add-on's Python code", ok=False)
            elif kind == "action":
                try: value["action"]()
                except Exception as exc: self.app.toast("Add-on action failed: " + str(exc)[:70], ok=False)
            else:
                self.app.push(FileBrowserScreen(self.app, self.install,
                                                extensions=(".rfxaddon", ".zip"),
                                                title="INSTALL ADD-ON PACKAGE"))

    def draw(self, surface):
        self.theme.header(surface, "Add-ons", "EXTENSIONS  /  OPTIONAL FEATURES  /  COMMUNITY PACKAGES")
        top = self.theme.header_h + 12
        bottom = H - self.theme.footer_h - 10
        self.menu.x, self.menu.width, self.menu.top, self.menu.bottom = 14, 354, top, bottom
        self.menu.draw(surface)
        if self.menu.sel < len(self.rows) and self.rows[self.menu.sel][0] == "addon":
            addon_id = self.rows[self.menu.sel][1]
            item = next((x for x in self.manager.items if x["manifest"]["id"] == addon_id), None)
            if item:
                manifest = item["manifest"]
                enabled = item["enabled"]
                title = manifest.get("name", addon_id)
                desc = manifest.get("description", "Optional RintrofliX extension.")
                facts = ["ID: " + addon_id, "Version: " + str(manifest.get("version", "?")),
                         "API: v" + str(manifest.get("api_version", "?"))]
                facts.extend(self.manager.compatibility_errors(manifest)[:2])
                facts.extend(["A second A confirms enabling Python code" if not enabled else "A disables this extension",
                              "X twice removes the installed package"])
                status = "Enabled" if enabled else "Disabled"
            else:
                title, desc, facts, status = "Add-on", "Package details unavailable.", [], "Unavailable"
            icon = "addons"
        elif self.menu.sel < len(self.rows) and self.rows[self.menu.sel][0] == "action":
            action = self.rows[self.menu.sel][1]
            title, desc = action["label"], action.get("description", "Extension action")
            facts, status, icon = ["Provided by: " + action.get("addon_id", "unknown")], "Available", "play"
        else:
            title, desc = "Install an add-on", "Browse for a .rfxaddon or ZIP package. Review its publisher and contents before enabling it."
            facts, status, icon = ["Python extensions are not sandboxed", "Only install packages you trust"], "Install", "addons"
        draw_detail_panel(self.theme, surface, pygame.Rect(380, top, 244, bottom-top),
                          title, desc, icon, facts, status)
        self.theme.footer(surface, [("A", "Enable / run / install"), ("X", "Remove"), ("B", "Back")])


class EpgScreen(Screen):
    def __init__(self, app):
        super().__init__(app)
        self.menu = MenuList(self.theme)
        self.rebuild()

    def rebuild(self):
        self.slots = []
        auto = self.app.playlist.epg_urls if self.app.playlist else []
        loaded = set((u.split(" [", 1)[0] for u in self.app.epg.sources_ok))
        errors = dict(self.app.epg.sources_err)
        items = []
        for url in auto:
            items.append((url, "Declared by the playlist", "OK" if url in loaded else ("ERR" if url in errors else "AUTO"), "", "guide"))
            self.slots.append(("auto", url))
        for url in self.app.cfg.get("epg_manual_urls", []):
            items.append((url, "Manual source · X to remove", "OK" if url in loaded else ("ERR" if url in errors else "MAN"), "", "guide"))
            self.slots.append(("manual", url))
        items.extend([
            ("+ ADD XMLTV URL", "XMLTV source · .xml / .xml.gz", "+", "", "guide"),
            ("REFRESH TV GUIDE", "Download all guide sources again", "↻", "", "guide"),
            ("AUTO-DISCOVERY: %s" % ("ON" if self.app.cfg.get("epg_use_playlist_sources", True) else "OFF"), "Use url-tvg sources declared by the playlist", "", "", "settings"),
        ])
        self.slots.extend([("add", None), ("reload", None), ("toggle", None)])
        self.menu.items = items
        self.menu.sel = min(self.menu.sel, len(items) - 1)

    def on_button(self, button):
        if button == "UP":
            self.menu.move(-1)
        elif button == "DOWN":
            self.menu.move(1)
        elif button == "B":
            self.app.pop()
        elif button == "X" and self.slots[self.menu.sel][0] == "manual":
            url = self.slots[self.menu.sel][1]
            urls = self.app.cfg.get("epg_manual_urls", [])
            if url in urls:
                urls.remove(url)
                self.app.cfg.set("epg_manual_urls", urls)
                self.rebuild()
        elif button == "A":
            kind = self.slots[self.menu.sel][0]
            if kind == "add":
                self.app.push(KeyboardScreen(self.app, "XMLTV GUIDE URL", "https://", self.add_url))
            elif kind == "reload":
                self.app.reload_epg(force=True)
                self.rebuild()
            elif kind == "toggle":
                self.app.cfg.set("epg_use_playlist_sources", not self.app.cfg.get("epg_use_playlist_sources", True))
                self.app.reload_epg(force=True)
                self.rebuild()

    def add_url(self, url):
        urls = self.app.cfg.get("epg_manual_urls", [])
        if url not in urls:
            urls.append(url)
        self.app.cfg.set("epg_manual_urls", urls)
        self.app.reload_epg(force=True)
        self.rebuild()

    def draw(self, surface):
        n = len(self.app.epg.by_key)
        self.theme.header(surface, "TV GUIDE SOURCES", "%d channel keys · %d sources loaded" % (n, len(self.app.epg.sources_ok)))
        self.menu.draw(surface)
        self.theme.footer(surface, [("A", "Confirm"), ("X", "Remove"), ("B", "Back")])


class SettingsScreen(Screen):
    """Settings are grouped by domain; About is deliberately the final entry."""
    def __init__(self, app):
        super().__init__(app)
        self.menu = MenuList(self.theme, row_h=max(54, self.theme.row_h))

    def items(self):
        cfg = self.app.cfg
        return [
            ("Interface size: %d%%" % cfg.get("ui_scale", 125), "APPEARANCE · 100 / 125 / 150 / 175", "↔", "", "settings"),
            ("Accent colour: %s" % cfg.get("theme_accent", "cyan").title(), "APPEARANCE · Cyan / Violet / Amber / Crimson", "↔", "", "settings"),
            ("Channel logos: %s" % ("ON" if cfg.get("show_logos", True) else "OFF"), "APPEARANCE · Download and show tvg-logo artwork", "↔", "", "tv"),
            ("Boot animation: %s" % ("ON" if cfg.get("boot_animation", True) else "OFF"), "APPEARANCE · Short RintrofliX startup sequence", "↔", "", "play"),
            ("Player backend: %s" % cfg.get("player_backend", "mpv").upper(), "PLAYBACK · MPV recommended / FFplay fallback", "↔", "", "play"),
            ("Stream buffer: %d sec" % cfg.get("player_cache_secs", 5), "PLAYBACK · Network cache, 0–30 seconds", "↔", "", "settings"),
            ("TV guide cache: %d hours" % cfg.get("epg_max_age_hours", 12), "SOURCES · XMLTV refresh interval, 1–48 hours", "↔", "", "guide"),
            ("User-Agent", cfg.get("user_agent", "")[:70], "A", "", "sources"),
            ("About RintrofliX", "INFORMATION · Version, platform and components", "INFO", "", "info"),
        ]

    def on_button(self, button):
        if button == "UP": self.menu.move(-1); return
        if button == "DOWN": self.menu.move(1); return
        if button == "B": self.app.pop(); return
        if button not in ("LEFT", "RIGHT", "A"): return
        index = self.menu.sel
        delta = -1 if button == "LEFT" else 1
        cfg = self.app.cfg
        if index == 0:
            options = [100, 125, 150, 175]
            old = cfg.get("ui_scale", 125)
            current = options.index(old) if old in options else 2
            cfg.set("ui_scale", options[(current + delta) % len(options)])
            self.app.rebuild_theme()
            self.theme = self.app.theme
            self.menu = MenuList(self.theme, self.items(), row_h=max(54, self.theme.row_h))
            self.menu.sel = index
        elif index == 1:
            options = list(ACCENTS)
            old = cfg.get("theme_accent", "cyan")
            current = options.index(old) if old in options else 0
            cfg.set("theme_accent", options[(current + delta) % len(options)])
            self.app.rebuild_theme()
            self.theme = self.app.theme
            self.menu = MenuList(self.theme, self.items(), row_h=max(54, self.theme.row_h))
            self.menu.sel = index
        elif index == 2:
            cfg.set("show_logos", not cfg.get("show_logos", True))
            if cfg.get("show_logos", True) and self.app.playlist:
                self.app.logos.prefetch(self.app.playlist.channels)
        elif index == 3:
            cfg.set("boot_animation", not cfg.get("boot_animation", True))
        elif index == 4:
            options = ["mpv", "auto", "ffplay"]
            old = cfg.get("player_backend", "mpv")
            current = options.index(old) if old in options else 0
            cfg.set("player_backend", options[(current + delta) % len(options)])
            self.app.player = Player(cfg)
        elif index == 5:
            cfg.set("player_cache_secs", max(0, min(30, cfg.get("player_cache_secs", 5) + delta)))
        elif index == 6:
            cfg.set("epg_max_age_hours", max(1, min(48, cfg.get("epg_max_age_hours", 12) + delta)))
        elif index == 7 and button == "A":
            self.app.push(KeyboardScreen(self.app, "EDIT USER-AGENT", cfg.get("user_agent", ""),
                                         lambda value: cfg.set("user_agent", value)))
        elif index == 8 and button == "A":
            self.app.push(InfoScreen(self.app))
        self.menu.items = self.items()

    def draw(self, surface):
        self.theme.header(surface, "Settings", "APPEARANCE  /  PLAYBACK  /  GUIDE  /  ABOUT")
        self.theme.section_title(surface, "Preferences", "Select an option, then use LEFT / RIGHT to adjust",
                                 y=self.theme.header_h + 8)
        top = self.theme.header_h + 66
        bottom = H - self.theme.footer_h - 10
        self.menu.x, self.menu.width, self.menu.top, self.menu.bottom = 14, 354, top, bottom
        self.menu.items = self.items()
        self.menu.draw(surface)
        index = self.menu.sel
        entries = [
            ("Interface size", "Changes the size of text and controls throughout the interface.", "settings", ["100% · 125% · 150% · 175%", "Larger settings use more screen space"]),
            ("Accent colour", "Choose the highlight colour used for focus, selection and active indicators.", "settings", ["Cyan · Violet · Amber · Crimson", "Applied across all screens"]),
            ("Channel logos", "Show artwork supplied by tvg-logo in your M3U playlist. Logos are cached locally.", "tv", ["Can be disabled to reduce visual clutter", "Downloads happen in the background"]),
            ("Boot animation", "Show the short RintrofliX startup sequence before opening the home screen.", "play", ["Can be skipped with a button press", "Disable for a faster startup"]),
            ("Player backend", "Choose the playback engine used for streams and local video files.", "play", ["MPV is recommended", "Auto can fall back to FFplay"]),
            ("Stream buffer", "Adjust the network cache duration. Higher values may help unstable connections but add delay.", "settings", ["Range: 0–30 seconds", "Use LEFT / RIGHT to change by one second"]),
            ("TV guide cache", "Controls how old cached XMLTV data may be before a refresh is needed.", "guide", ["Range: 1–48 hours", "Manual refresh is available in Sources"]),
            ("User-Agent", "Set the HTTP User-Agent sent when retrieving playlists and guide data.", "sources", ["Some providers require a specific value", "Press A to edit the text"]),
            ("About RintrofliX", "Version, platform, runtime components and project information.", "info", ["About is intentionally the final entry", "Press A to inspect build information"]),
        ]
        title, desc, icon, facts = entries[index]
        value = self.items()[index][0]
        draw_detail_panel(self.theme, surface, pygame.Rect(380, top, 244, bottom-top),
                          title, desc, icon, [value] + facts[:3], "Selected")
        self.theme.footer(surface, [("LEFT / RIGHT", "Adjust"), ("A", "Edit / open"), ("B", "Back")])


class KeyboardScreen(Screen):
    PAGES = [
        "1234567890abcdefghijklmnopqrstuvwxyz-_.:/@?&=%+#,",
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ!$()*[]{};~'\"\\\\",
    ]
    COLS = 10

    def __init__(self, app, title, initial, callback):
        super().__init__(app)
        self.title = title
        self.value = initial
        self.callback = callback
        self.page = 0
        self.sel = 0
        self.done = False

    def keys(self):
        return self.PAGES[self.page]

    def on_button(self, button):
        keys = self.keys()
        rows = (len(keys) + self.COLS - 1) // self.COLS
        row, col = divmod(self.sel, self.COLS)
        if button == "UP":
            row = (row - 1) % rows
        elif button == "DOWN":
            row = (row + 1) % rows
        elif button == "LEFT":
            col = (col - 1) % self.COLS
        elif button == "RIGHT":
            col = (col + 1) % self.COLS
        elif button == "A":
            self.value += keys[min(self.sel, len(keys) - 1)]
        elif button == "B":
            if self.value:
                self.value = self.value[:-1]
            else:
                self.app.pop()
        elif button == "Y":
            self.value += " "
        elif button in ("L1", "R1"):
            self.page = (self.page + 1) % len(self.PAGES)
            self.sel = 0
        elif button == "START":
            value = self.value.strip()
            self.app.pop()
            if value:
                self.callback(value)
            return
        elif button == "X":
            self.app.pop()
            return
        self.sel = min(row * self.COLS + col, len(self.keys()) - 1)

    def draw(self, surface):
        self.theme.header(surface, self.title, "L/R changes keyboard · B deletes · START confirms")
        field_y = self.theme.header_h + 8
        pygame.draw.rect(surface, (17, 29, 43), (12, field_y, W - 24, 50), border_radius=5)
        pygame.draw.rect(surface, self.theme.accent, (12, field_y, W - 24, 50), 2, border_radius=5)
        shown = self.value[-66:]
        self.theme.text(surface, shown + "_", (22, field_y + 8), self.theme.f_small, FG, W - 44)
        keys = self.keys()
        key_w, key_h = 56, 40
        start_x, start_y = 34, field_y + 62
        for index, char in enumerate(keys):
            row, col = divmod(index, self.COLS)
            x, y = start_x + col * key_w, start_y + row * key_h
            selected = index == self.sel
            pygame.draw.rect(surface, (29, 64, 80) if selected else (17, 28, 41), (x, y, key_w - 5, key_h - 5), border_radius=4)
            pygame.draw.rect(surface, self.theme.accent if selected else FAINT, (x, y, key_w - 5, key_h - 5), 2 if selected else 1, border_radius=4)
            rendered = self.theme.f_small.render(char, True, FG if selected else DIM)
            surface.blit(rendered, (x + (key_w - 5 - rendered.get_width()) // 2, y + 5))
        self.theme.footer(surface, [("A", "Type"), ("B", "Delete"), ("Y", "Space"), ("START", "OK"), ("X", "Cancel")])


class ChannelInfoScreen(Screen):
    def __init__(self, app, channel):
        super().__init__(app)
        self.channel = channel

    def draw(self, surface):
        channel = self.channel
        self.theme.header(surface, "CHANNEL DETAILS", channel.name)
        y = self.theme.header_h + 16
        rows = [("GROUP", channel.group), ("TVG-ID", channel.tvg_id or "—"),
                ("TVG-NAME", channel.tvg_name or "—"), ("URL", channel.url)]
        current, following = self.app.epg.now_next(channel) if self.app.epg else (None, None)
        rows.append(("NOW", current.title if current else "—"))
        rows.append(("NEXT", following.title if following else "—"))
        for label, value in rows:
            self.theme.text(surface, label, (18, y), self.theme.f_tiny, self.theme.accent)
            self.theme.text(surface, value, (150, y), self.theme.f_tiny, FG, W - 168)
            y += 42
        self.theme.footer(surface, [("B", "Back")])


class InfoScreen(Screen):
    def draw(self, surface):
        self.theme.header(surface, "About RintrofliX", "THE HANDHELD MEDIA CENTRE")
        rows = [
            ("Version", C.APP_VERSION),
            ("Platform", "muOS Andromeda · RG35XX H / H700"),
            ("Interface", "Python · Pygame / SDL2"),
            ("Playback", "MPV with IPC controls · FFplay fallback"),
            ("Live TV", "M3U / M3U8 · channel logos · favourites"),
            ("TV guide", "XMLTV · multiple sources · timeline"),
            ("Local Library", "On-demand browsing of local video folders"),
            ("Add-ons", "Local .rfxaddon packages · API v2"),
            ("Design", "Kodi-inspired layout, built for a gamepad"),
        ]
        y = self.theme.header_h + 20
        for label, value in rows:
            self.theme.text(surface, label.upper(), (20, y), self.theme.f_tiny, self.theme.accent)
            self.theme.text(surface, value, (175, y-1), self.theme.f_small, FG, W-195)
            y += max(30, self.theme.f_small.get_height()+8)
        self.theme.footer(surface, [("B", "Back")])


class App:
    def __init__(self):
        self.cfg = C.Config()
        self.theme = Theme(self.cfg.get("theme_accent", "cyan"), self.cfg.get("ui_scale", 125))
        self.toast_ui = Toast(self.theme)
        self.player = Player(self.cfg)
        self.input = InputReader()
        self.logos = LogoCache(self.cfg.get("user_agent", ""))
        self.playlist = None
        self.epg = epg_mod.EPG()
        self.addons = AddonManager(self)
        self.running = True
        self.stack = []
        self.joysticks = []
        self._dpad_last = (0, 0)
        self._dpad_time = 0
        self.surface = None
        # Load only add-ons the user explicitly enabled, after the app is ready.
        self.addons.load_enabled()

    def rebuild_theme(self):
        self.theme = Theme(self.cfg.get("theme_accent", "cyan"), self.cfg.get("ui_scale", 125))
        self.toast_ui.theme = self.theme
        for screen in self.stack:
            screen.theme = self.theme
            if screen.menu:
                screen.menu.theme = self.theme
                screen.menu.row_h = self.theme.row_h
        self.player.cfg = self.cfg

    def init_display(self):
        use_fb = os.environ.get("RINTROFLIX_FB") == "1"
        pygame.font.init()
        pygame.event.init()

        # muOS handheld path: render to a software surface and copy frames
        # directly to /dev/fb0. Do not require an SDL video driver.
        if use_fb:
            from rintroflix import fbdisplay
            self.surface = pygame.Surface((W, H), depth=32)
            if fbdisplay.attach(self.surface):
                log("software framebuffer active: %s; SDL %s" %
                    (fbdisplay.info(), pygame.get_sdl_version()))
                return
            reason = fbdisplay.last_error() or "unknown framebuffer error"
            log("direct framebuffer unavailable: " + reason)

        # Desktop/fallback path for environments with a working SDL backend.
        preferred = os.environ.get("RINTROFLIX_SDL_DRIVERS", "")
        drivers = [item.strip() for item in preferred.split(",") if item.strip()]
        if not drivers:
            drivers = ["kmsdrm", "fbcon", "wayland", "x11", "dummy"]
        errors = []
        self.surface = None
        active_driver = None
        for driver in drivers:
            try:
                pygame.display.quit()
                os.environ["SDL_VIDEODRIVER"] = driver
                pygame.display.init()
                flags = pygame.FULLSCREEN if driver != "dummy" and os.environ.get("RINTROFLIX_DESKTOP") != "1" else 0
                try:
                    self.surface = pygame.display.set_mode((W, H), flags)
                except pygame.error:
                    self.surface = pygame.display.set_mode((W, H))
                active_driver = driver
                break
            except pygame.error as exc:
                detail = str(exc) or "(SDL returned an empty error message)"
                errors.append("%s: %s" % (driver, detail))
                log("SDL video driver %s failed: %s" % (driver, detail))
        if self.surface is None:
            raise RuntimeError("Unable to initialize video. framebuffer=%s; SDL=%s" %
                               (fbdisplay.last_error() if use_fb else "not requested", " | ".join(errors)))
        log("SDL video driver active: %s; SDL %s" % (active_driver, pygame.get_sdl_version()))
        pygame.display.set_caption("RintrofliX")
        pygame.mouse.set_visible(False)
    def init_joysticks(self):
        pygame.joystick.init()
        self.joysticks = []
        try:
            for index in range(pygame.joystick.get_count()):
                joy = pygame.joystick.Joystick(index)
                joy.init()
                self.joysticks.append(joy)
                log("joystick %d: %s" % (index, joy.get_name()))
        except pygame.error as exc:
            log("joystick init: " + str(exc))

    def suspend_display(self):
        try:
            from rintroflix import fbdisplay
            fbdisplay.detach()
        except Exception:
            pass
        pygame.display.quit()

    def resume_display(self):
        self.init_display()
        self.init_joysticks()

    def push(self, screen):
        self.stack.append(screen)

    def pop(self):
        if len(self.stack) > 1:
            self.stack.pop()

    def top(self):
        return self.stack[-1]

    def toast(self, message, ok=True):
        self.toast_ui.show(message, ok)
        log(("OK " if ok else "ERR ") + str(message))

    def log_addon(self, addon_id, message):
        log("ADDON %s: %s" % (addon_id, str(message)[:300]))

    def boot_animation(self):
        """Short skippable brand animation; entirely local and safe to disable."""
        if not self.cfg.get("boot_animation", True):
            return
        clock = pygame.time.Clock()
        started = time.monotonic()
        duration = 1.65
        logo = None
        try:
            logo = pygame.image.load(str(C.ROOT_DIR / "resources" / "rintroflix.png")).convert_alpha()
        except (pygame.error, OSError):
            logo = self.theme.logo
        while self.running and time.monotonic() - started < duration:
            for event in pygame.event.get():
                if event.type in (pygame.KEYDOWN, pygame.JOYBUTTONDOWN, pygame.QUIT):
                    return
            if self.input.active() and self.input.poll():
                return
            elapsed = time.monotonic() - started
            progress = min(1.0, elapsed / duration)
            self.theme.background(self.surface)
            center = (W // 2, 172)
            pulse = 1.0 + 0.035 * (1.0 - abs(0.5 - progress) * 2)
            radius = int(58 * pulse)
            pygame.draw.circle(self.surface, (18, 42, 57), center, radius + 15, 2)
            pygame.draw.circle(self.surface, self.theme.accent, center, radius + 7, 2)
            if logo:
                mark = pygame.transform.smoothscale(logo, (110, 110))
                self.surface.blit(mark, mark.get_rect(center=center))
            self.theme.text(self.surface, "Rintro", (W//2 - 88, 258), self.theme.f_brand, FG)
            self.theme.text(self.surface, "fliX", (W//2 - 88 + self.theme.f_brand.size("Rintro")[0], 258),
                            self.theme.f_brand, self.theme.accent)
            tagline = "YOUR HANDHELD MEDIA CENTRE"
            self.theme.text(self.surface, tagline,
                            (W//2 - self.theme.f_tiny.size(tagline)[0]//2, 307),
                            self.theme.f_tiny, DIM)
            track = pygame.Rect(190, 350, 260, 5)
            pygame.draw.rect(self.surface, (36, 53, 70), track, border_radius=3)
            pygame.draw.rect(self.surface, self.theme.accent,
                             (track.x, track.y, int(track.w * progress), track.h), border_radius=3)
            self.theme.text(self.surface, "PRESS ANY BUTTON TO SKIP",
                            (W//2 - self.theme.f_tiny.size("PRESS ANY BUTTON TO SKIP")[0]//2, 383),
                            self.theme.f_tiny, FAINT)
            pygame.display.flip()
            clock.tick(30)

    def busy(self, label, function):
        self.surface.fill(BG)
        self.theme.header(self.surface, "RINTROFLIX", "WORKING")
        self.theme.text(self.surface, label, (26, 200), self.theme.f_big, self.theme.accent, W - 50)
        self.theme.text(self.surface, "This may take a moment depending on your connection.", (28, 250), self.theme.f_small, DIM)
        pygame.display.flip()
        try:
            return function()
        except Exception as exc:
            log("busy error: " + traceback.format_exc(limit=4))
            self.toast(str(exc)[:90], ok=False)
            return None

    def available_channels(self):
        """Core playlist plus explicitly enabled API-v2 add-on sources."""
        channels = list(self.playlist.channels) if self.playlist else []
        try:
            channels.extend(self.addons.channels())
        except Exception as exc:
            log("addon source aggregation failed: %s" % exc)
        return channels

    def reload_playlist(self, force=False):
        entry = self.cfg.active_playlist()
        if not entry:
            self.playlist = None
            self.epg = epg_mod.EPG()
            return
        result = self.busy("Loading: " + entry.get("name", "playlist"),
                           lambda: m3u.load_playlist(entry, self.cfg.get("user_agent")))
        if result is not None:
            self.playlist = result
            self.logos.user_agent = self.cfg.get("user_agent", "")
            if self.cfg.get("show_logos", True):
                self.logos.prefetch(result.channels)
            self.toast("Playlist loaded · %d channels" % len(result.channels))
            self.reload_epg(force=force)

    def reload_epg(self, force=False):
        urls = epg_mod.collect_epg_urls(self.cfg, self.playlist)
        if not urls:
            self.epg = epg_mod.EPG()
            return
        age = 0 if force else self.cfg.get("epg_max_age_hours", 12)
        result = self.busy("Loading TV guide · %d sources" % len(urls), lambda: self._load_epg(urls, age))
        if result is not None:
            self.epg = result
            self.toast("TV guide · %d sources OK · %d errors" % (len(result.sources_ok), len(result.sources_err)), bool(result.sources_ok))

    def _load_epg(self, urls, age):
        result = epg_mod.EPG()
        result.load(urls, self.cfg.get("user_agent"), age)
        return result

    def open_channels(self, favorites=False):
        if not self.playlist or not self.playlist.channels:
            self.toast("Add an M3U playlist first.", ok=False)
            self.push(PlaylistScreen(self))
            return
        self.push(WatchTVScreen(self, tab=1 if favorites else 0))

    def play_channel(self, channels, index):
        if not channels:
            return
        position = max(0, min(index, len(channels) - 1))
        while self.running:
            channel = channels[position]
            log("play: " + channel.name)
            # API v2 source hook: an add-on may own playback for its channels.
            # Returning True means handled; otherwise use the normal MPV/FFplay adapter.
            if self.addons.play_channel(channel):
                break
            self.suspend_display()
            result = self.player.play(channel, self.epg)
            self.resume_display()
            if result == RESULT_NEXT:
                position = (position + 1) % len(channels)
            elif result == RESULT_PREV:
                position = (position - 1) % len(channels)
            elif result == RESULT_FAV:
                added = self.cfg.toggle_favorite(channel.url)
                self.toast(("Added to favourites: " if added else "Removed from favourites: ") + channel.name)
            elif result == RESULT_ERROR:
                self.toast(self.player.last_error or "Playback error", ok=False)
                break
            else:
                break

    def dispatch(self, button):
        if button:
            self.top().on_button(button)

    def logical_button(self, raw):
        saved = self.cfg.get("button_map", {})
        if _ENV_BUTTONS and saved == C.DEFAULTS.get("button_map"):
            return _ENV_BUTTONS.get(raw)
        return saved.get(str(raw))

    def poll_dpad(self):
        hx, hy = self.input.hat() if self.input.active() else (0, 0)
        for joystick in ([] if self.input.active() else self.joysticks):
            try:
                if joystick.get_numhats():
                    x, y = joystick.get_hat(0)
                    hx, hy = hx or x, hy or y
                if joystick.get_numaxes() >= 2:
                    x, y = joystick.get_axis(0), joystick.get_axis(1)
                    if abs(x) > 0.6:
                        hx = hx or (1 if x > 0 else -1)
                    if abs(y) > 0.6:
                        hy = hy or (1 if y < 0 else -1)
            except pygame.error:
                continue
        current = (hx, hy)
        now = time.monotonic()
        if current == (0, 0):
            self._dpad_last = current
            return
        if current != self._dpad_last or now - self._dpad_time > 0.17:
            self._dpad_time = now
            self._dpad_last = current
            if hy > 0:
                self.dispatch("UP")
            elif hy < 0:
                self.dispatch("DOWN")
            if hx < 0:
                self.dispatch("LEFT")
            elif hx > 0:
                self.dispatch("RIGHT")

    def run(self):
        self.init_display()
        self.init_joysticks()
        if os.environ.get("RINTROFLIX_FB") == "1":
            self.input.start()
        self.boot_animation()
        self.push(HomeScreen(self))
        if self.cfg.migrated:
            self.toast("VoidCast settings imported into RintrofliX")
        if self.cfg.active_playlist():
            self.reload_playlist()
        clock = pygame.time.Clock()
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.JOYBUTTONDOWN and not self.input.active():
                    self.dispatch(self.logical_button(event.button))
                elif event.type == pygame.KEYDOWN:
                    self.dispatch(KEYBOARD_MAP.get(event.key))
                elif event.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
                    self.init_joysticks()
            if self.input.active():
                for button in self.input.poll():
                    if button == "MENU":
                        continue
                    self.dispatch(button)
            self.poll_dpad()
            self.theme.background(self.surface)
            try:
                self.top().draw(self.surface)
            except Exception:
                log("draw error: " + traceback.format_exc(limit=4))
                self.pop()
            self.toast_ui.draw(self.surface)
            pygame.display.flip()
            clock.tick(FPS)
        self.input.close()
        self.logos.close()
        try:
            from rintroflix import fbdisplay
            fbdisplay.detach()
        except Exception:
            pass
        pygame.quit()


def main():
    if os.environ.get("RINTROFLIX_FB") == "1":
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", "1")
    log("=== RintrofliX %s boot ===" % C.APP_VERSION)
    App().run()


if __name__ == "__main__":
    main()
