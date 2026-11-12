#!/bin/sh
# HELP: RintrofliX - handheld media centre: Live TV, local library, add-ons and TV guide
# ICON: rintroflix
# GRID: RintrofliX

[ -f /opt/muos/script/var/func.sh ] && . /opt/muos/script/var/func.sh
if command -v SETUP_APP >/dev/null 2>&1; then
    SETUP_APP "python3" ""
fi

DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$DIR" || exit 1
mkdir -p "$DIR/data"
LOG="$DIR/data/rintroflix-launch.log"
echo "$(date) === RintrofliX 2.1.0 start ===" >>"$LOG"
[ -f "$DIR/lib/glyph_install.sh" ] && . "$DIR/lib/glyph_install.sh" && \
    INSTALL_GLYPH "$DIR/resources/rintroflix.png" "rintroflix"

# Runtime 1: Python + pygame already installed in muOS.
PY_SYS=""
if command -v python3 >/dev/null 2>&1 && python3 -c 'import pygame' >/dev/null 2>&1; then
    PY_SYS="$(command -v python3)"
fi

# Runtime 2: the pygame wheel installed by VoidDesk.
VD_RT=""
VD_SDL=""
for CAND in \
    "$DIR/../VoidDesk" \
    /run/muos/storage/application/VoidDesk \
    /mnt/mmc/MUOS/application/VoidDesk \
    /mnt/sdcard/MUOS/application/VoidDesk; do
    if [ -f "$CAND/data/.pygame_ready" ] && [ -d "$CAND/runtime" ]; then
        VD_RT="$(CDPATH= cd -- "$CAND/runtime" && pwd)"
        [ -f "$CAND/data/sdl_path.txt" ] && VD_SDL="$(head -1 "$CAND/data/sdl_path.txt")"
        break
    fi
done

# Runtime 3: legacy VoidDesk chroot (kept as a compatibility fallback).
ROOTFS=""
for CAND in \
    "$DIR/../VoidDesk/data/rootfs" \
    /run/muos/storage/application/VoidDesk/data/rootfs \
    /mnt/mmc/MUOS/application/VoidDesk/data/rootfs \
    /mnt/sdcard/MUOS/application/VoidDesk/data/rootfs; do
    if [ -f "$CAND/.voiddesk_ready" ] || { [ -d "$CAND" ] && [ -f "$CAND/../.bootstrap_ok" ]; }; then
        ROOTFS="$(CDPATH= cd -- "$CAND" && pwd)"
        break
    fi
done

run_system() {
    echo "$(date) runtime: system python ($PY_SYS)" >>"$LOG"
    "$PY_SYS" "$DIR/rintroflix/main.py" >>"$DIR/data/rintroflix.log" 2>&1
    return $?
}
run_wheel() {
    export PYTHONPATH="$VD_RT${PYTHONPATH:+:$PYTHONPATH}"
    export PYGAME_HIDE_SUPPORT_PROMPT=1
    echo "$(date) runtime: VoidDesk pygame wheel ($VD_RT)" >>"$LOG"
    RINTROFLIX_FB=1 python3 "$DIR/rintroflix/main.py" >>"$DIR/data/rintroflix.log" 2>&1
    EXIT=$?
    if [ "$EXIT" -ne 0 ] && [ -n "$VD_SDL" ] && [ -f "$VD_SDL" ]; then
        echo "$(date) retry with system SDL preload" >>"$LOG"
        LD_PRELOAD="$VD_SDL" python3 "$DIR/rintroflix/main.py" >>"$DIR/data/rintroflix.log" 2>&1
        EXIT=$?
    fi
    if [ "$EXIT" -ne 0 ]; then
        echo "$(date) retry with SDL automatic driver" >>"$LOG"
        python3 "$DIR/rintroflix/main.py" >>"$DIR/data/rintroflix.log" 2>&1
        EXIT=$?
    fi
    return "$EXIT"
}

if [ -n "$PY_SYS" ]; then
    run_system
    EXIT=$?
elif [ -n "$VD_RT" ]; then
    run_wheel
    EXIT=$?
elif [ -n "$ROOTFS" ]; then
    for M in proc sys dev; do mkdir -p "$ROOTFS/$M"; done
    mountpoint -q "$ROOTFS/proc" || mount -t proc proc "$ROOTFS/proc"
    mountpoint -q "$ROOTFS/sys" || mount -t sysfs sysfs "$ROOTFS/sys"
    mountpoint -q "$ROOTFS/dev" || mount --bind /dev "$ROOTFS/dev"
    mkdir -p "$ROOTFS/rintroflix_app"
    mountpoint -q "$ROOTFS/rintroflix_app" || mount --bind "$DIR" "$ROOTFS/rintroflix_app"
    [ -f /etc/resolv.conf ] && cat /etc/resolv.conf >"$ROOTFS/etc/resolv.conf" 2>/dev/null
    chroot "$ROOTFS" /bin/bash -c 'export HOME=/root TERM=linux SDL_VIDEODRIVER=kmsdrm SDL_RENDER_DRIVER=software; cd /rintroflix_app && python3 rintroflix/main.py' >>"$DIR/data/rintroflix.log" 2>&1
    EXIT=$?
    if [ "$EXIT" -ne 0 ]; then
        chroot "$ROOTFS" /bin/bash -c 'export HOME=/root TERM=linux; unset SDL_VIDEODRIVER; cd /rintroflix_app && python3 rintroflix/main.py' >>"$DIR/data/rintroflix.log" 2>&1
        EXIT=$?
    fi
    for M in rintroflix_app dev proc sys; do mountpoint -q "$ROOTFS/$M" && umount -l "$ROOTFS/$M" 2>/dev/null; done
else
    EXIT=42
    echo "$(date) ERRORE: runtime Python3 + pygame non disponibile" >>"$LOG"
fi

echo "$(date) === RintrofliX exit $EXIT ===" >>"$LOG"
if [ "$EXIT" -ne 0 ] && command -v python3 >/dev/null 2>&1 && [ -f "$DIR/lib/fbmsg.py" ]; then
    if [ "$EXIT" -eq 42 ]; then
        python3 "$DIR/lib/fbmsg.py" "RintrofliX - runtime mancante" 12 \
            "Python3 + pygame non sono disponibili." "" \
            "Avvia VoidDesk e completa il setup del runtime." </dev/null
    else
        tail -14 "$DIR/data/rintroflix.log" | python3 "$DIR/lib/fbmsg.py" "RintrofliX - errore" 14
    fi
fi
exit "$EXIT"
