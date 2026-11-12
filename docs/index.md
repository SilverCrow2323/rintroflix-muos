---
title: RintrofliX — Your handheld media hub
---

<div class="hero" markdown>
  <div class="hero-copy">
    <div class="eyebrow">MUOS · HANDHELD MEDIA CENTRE</div>
    # Your media. Your handheld. Your rules. ✨
    A controller-first, Kodi-inspired media experience designed for the compact screen and buttons of the Anbernic H700 family.

    <div class="hero-actions">
      <a class="md-button md-button--primary" href="installation/">Get started →</a>
      <a class="md-button" href="architecture/">Explore the architecture</a>
    </div>
    <div class="hero-meta"><span>🟣 Modular</span><span>🔵 Controller-first</span><span>🟠 Open to extensions</span></div>
  </div>
  <div class="hero-orbit">
    <div class="orbit orbit-a"></div><div class="orbit orbit-b"></div>
    <div class="screen-card"><div class="screen-top"><i></i><i></i><i></i><b>RINTROFLIX</b></div><div class="screen-art">▶</div><div class="screen-lines"><i></i><i></i><i></i></div><div class="screen-footer">LIVE · LIBRARY · ADD-ONS</div></div>
    <div class="orbit-dot dot-a"></div><div class="orbit-dot dot-b"></div><div class="orbit-dot dot-c"></div>
  </div>
</div>

<div class="stat-grid" markdown>
<div class="stat"><strong>2.6.0</strong><span>Documented app baseline</span></div>
<div class="stat"><strong>640×480</strong><span>Handheld UI target</span></div>
<div class="stat"><strong>2 APIs</strong><span>Add-on compatibility</span></div>
<div class="stat"><strong>22/22</strong><span>Baseline unit tests passing*</span></div>
</div>
<small>* Reported by the 2.6.0 working source baseline; the repository's own CI has not yet run the application suite.</small>

## 🎬 One home for the whole experience

RintrofliX brings the essentials together without turning a handheld into a desktop UI squeezed onto a tiny display.

<div class="feature-grid" markdown>
<div class="feature-card"><span class="feature-icon">📡</span><h3>Watch TV</h3><p>Browse channels, groups, favourites, search and the electronic programme guide.</p><a href="features/#watch-tv">Explore TV →</a></div>
<div class="feature-card"><span class="feature-icon">🎞️</span><h3>Local Library</h3><p>Browse folders on demand and play local video without scanning the entire SD card.</p><a href="features/#local-library">Explore library →</a></div>
<div class="feature-card"><span class="feature-icon">🧩</span><h3>Add-ons</h3><p>Extend the app with explicit, versioned APIs and dependency checks.</p><a href="addons/">Explore the SDK →</a></div>
<div class="feature-card"><span class="feature-icon">🛠️</span><h3>Sources & Settings</h3><p>Keep playlist and guide configuration separate from general extension management.</p><a href="features/#sources-and-settings">Explore settings →</a></div>
</div>

## 🧭 How the experience fits together

```mermaid
flowchart LR
    A[Home] --> B[Watch TV]
    A --> C[Local Library]
    A --> D[Add-ons]
    A --> E[Sources]
    A --> F[Settings]
    B --> G[M3U + XMLTV]
    C --> H[Local folders]
    D --> I[API v1 / API v2]
    G --> J[Playback engine]
    H --> J
    I --> J
```

## 📊 Product focus

The following chart is a qualitative prioritisation snapshot, not telemetry or measured usage.

<canvas id="focusChart" height="120" aria-label="Qualitative product focus chart"></canvas>
<div class="chart-note">Design priorities: readability, reliable playback, modularity and safe extension management.</div>

## 🚦 Project status

| Area | Status | Notes |
|---|---|---|
| Core media experience | <span class="status status-progress">Baseline documented</span> | Current application baseline: 2.6.0 |
| Add-on API v1/v2 | <span class="status status-progress">Implemented in baseline</span> | v1 actions; v2 source registration and playback hook |
| Repository index service | <span class="status status-progress">Foundation implemented</span> | HTTPS + SHA-256 integrity; no publisher signatures |
| Dynamic repository UI | <span class="status status-planned">Planned</span> | Not part of the 2.6.0 baseline |
| Physical device validation | <span class="status status-planned">Pending</span> | Requires RG35XX H / muOS testing |

!!! info "A living handbook"
    This site is designed to evolve alongside the application. Features, API contracts, known limitations and release notes should be updated with every meaningful code change.

!!! warning "No bundled TV subscription"
    RintrofliX does not ship a personal playlist URL or a paid content service. Users must configure sources they are authorised to access.
