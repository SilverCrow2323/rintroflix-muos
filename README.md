# RintrofliX for muOS

<p align="center">
  <img src="docs/assets/brand-mark.svg" alt="RintrofliX" width="180">
</p>

<h1 align="center">📺 RintrofliX</h1>
<p align="center"><strong>A controller-first handheld media centre for muOS.</strong></p>
<p align="center">
  <a href="https://github.com/SilverCrow2323/rintroflix-muos/actions"><img alt="Build" src="https://img.shields.io/github/actions/workflow/status/SilverCrow2323/rintroflix-muos/docs.yml?branch=main&label=docs"></a>
  <img alt="Version" src="https://img.shields.io/badge/version-2.6.0-8b5cf6">
  <img alt="Platform" src="https://img.shields.io/badge/platform-muOS%20%7C%20H700-06b6d4">
  <img alt="License" src="https://img.shields.io/badge/license-TBD-orange">
</p>

> [!IMPORTANT]
> This repository is being established as the canonical home for RintrofliX. The current documented application baseline is **2.6.0**. The initial commit focuses on the project handbook and automated documentation publishing; the application source mirror and release pipeline are the next repository-integration step.

## ✨ What is RintrofliX?

RintrofliX is a compact, Kodi-inspired media hub designed around handheld controls and the 640×480 display class of the Anbernic RG35XX H / H700 family running muOS. It brings live TV, a local video library, add-ons, source management and playback controls into one consistent interface.

## 🧭 Explore the handbook

The documentation is a living website, not a static wall of text:

- **[Project overview](https://silvercrow2323.github.io/rintroflix-muos/)** — vision, status and roadmap.
- **[Features](https://silvercrow2323.github.io/rintroflix-muos/features/)** — what each area does.
- **[Architecture](https://silvercrow2323.github.io/rintroflix-muos/architecture/)** — components and data flow.
- **[Add-on SDK](https://silvercrow2323.github.io/rintroflix-muos/addons/)** — API v1/v2 contracts and safety.
- **[Installation](https://silvercrow2323.github.io/rintroflix-muos/installation/)** — device setup and controls.
- **[Roadmap](https://silvercrow2323.github.io/rintroflix-muos/roadmap/)** — planned work and known limitations.

## 🎮 Product principles

| Principle | Meaning |
|---|---|
| Controller-first | Every primary workflow is reachable without a keyboard. |
| Readable at 640×480 | Large type, generous rows and clear focus states. |
| Modular | UI, playback and data services have explicit boundaries. |
| User-controlled | No personal playlist URL is shipped; users configure their own sources. |
| Honest security | Add-ons execute as Python code; archive checks are not a sandbox. |

## 🧪 Current baseline

| Area | Baseline |
|---|---|
| Application | 2.6.0 |
| Add-on API | v1 actions + v2 source providers/playback hook |
| Repository service | HTTPS index + SHA-256 package integrity |
| Publisher signatures | Not implemented |
| Automated tests | 22 passing in the 2.6.0 working source baseline |
| Device validation | Pending physical RG35XX H / muOS testing |

**Important:** SHA-256 verifies that downloaded bytes match the repository index. It does not prove who published that index. Do not treat unsigned repositories as authenticated publishers.

## 🌈 Documentation

Built with [MkDocs Material](https://squidfunk.github.io/mkdocs-material/), Mermaid diagrams, responsive tables, callouts, charts and a custom visual theme. All product documentation is written in English.

## 📜 License

No license has been selected yet. Until a license is added, normal copyright applies and reuse/redistribution permissions should not be assumed.
