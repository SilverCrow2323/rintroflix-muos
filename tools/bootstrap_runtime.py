#!/usr/bin/env python3
# RintrofliX first-run runtime bootstrap. No rootfs/chroot required.
# Downloads a CPython/PyPy-compatible ARM wheel from PyPI into app-local runtime.
from __future__ import print_function
import hashlib, json, os, platform, shutil, ssl, subprocess, sys, tempfile, urllib.request, zipfile

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(APP, "data")
RUNTIME = os.path.join(APP, "runtime")
MARKER = os.path.join(DATA, ".pygame_ready")
LOG = os.path.join(DATA, "rintroflix-bootstrap.log")
PYPI = "https://pypi.org/pypi/"

def log(message):
    line = message
    try:
        with open(LOG, "a") as stream:
            stream.write(line + "\n")
    except IOError:
        pass
    print(line, flush=True)

def machine_tags():
    machine = platform.machine().lower()
    if machine in ("aarch64", "arm64"):
        return ("aarch64", "arm64")
    if machine.startswith("armv7") or machine.startswith("armv6"):
        return ("armv7l", "armv6l", "armhf")
    return (machine,)

def wheel_score(filename, py_tag, arch_tags):
    # Accept only CPython ABI wheels for this interpreter and Linux ARM.
    parts = filename[:-4].split("-")
    if len(parts) < 5:
        return -1
    python_tag, abi_tag, platform_tag = parts[-3:]
    if python_tag != py_tag or abi_tag not in (py_tag, "abi3"):
        return -1
    if not ("linux" in platform_tag or "manylinux" in platform_tag):
        return -1
    if not any(tag in platform_tag for tag in arch_tags):
        return -1
    return 2 if "manylinux" in platform_tag else 1

def main():
    os.makedirs(DATA, exist_ok=True)
    log("=== RintrofliX runtime bootstrap ===")
    if sys.version_info < (3, 8):
        log("FATAL: Python 3.8+ required; found " + sys.version.split()[0])
        return 1
    machine = platform.machine()
    py_tag = "cp%d%d" % sys.version_info[:2]
    arch_tags = machine_tags()
    log("Python: %s / %s / %s" % (sys.version.split()[0], py_tag, machine))

    # A wheel contains native code: select only an exact interpreter ABI and CPU.
    context = ssl.create_default_context()
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=context))
    opener.addheaders = [("User-Agent", "RintrofliX-muOS-runtime/2.6.1")]
    selected = None
    for package in ("pygame-ce", "pygame"):
        try:
            with opener.open(PYPI + package + "/json", timeout=25) as response:
                metadata = json.load(response)
            candidates = []
            for item in metadata.get("urls", []):
                filename = item.get("filename", "")
                score = wheel_score(filename, py_tag, arch_tags)
                if score >= 0:
                    candidates.append((score, item))
            if candidates:
                candidates.sort(key=lambda pair: pair[0], reverse=True)
                selected = candidates[0][1]
                log("Selected %s %s" % (package, selected["filename"]))
                break
        except Exception as error:
            log("PyPI lookup for %s failed: %s" % (package, error))
    if not selected:
        log("FATAL: no compatible ARM wheel for %s/%s" % (py_tag, machine))
        return 2

    archive = os.path.join(DATA, "pygame-runtime.whl.part")
    try:
        with opener.open(selected["url"], timeout=60) as response, open(archive, "wb") as output:
            digest = hashlib.sha256()
            while True:
                chunk = response.read(256 * 1024)
                if not chunk:
                    break
                output.write(chunk)
                digest.update(chunk)
        expected = selected.get("digests", {}).get("sha256")
        if not expected or digest.hexdigest().lower() != expected.lower():
            raise ValueError("wheel SHA256 mismatch")
        log("Wheel download and SHA256 verification OK")
        staging = RUNTIME + ".staging"
        shutil.rmtree(staging, ignore_errors=True)
        os.makedirs(staging)
        with zipfile.ZipFile(archive) as wheel:
            for member in wheel.infolist():
                target = os.path.realpath(os.path.join(staging, member.filename))
                if not (target == os.path.realpath(staging) or target.startswith(os.path.realpath(staging) + os.sep)):
                    raise ValueError("unsafe path in wheel")
                wheel.extract(member, staging)
        env = os.environ.copy()
        env["PYTHONPATH"] = staging
        env["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
        check = subprocess.run([sys.executable, "-c", "import pygame; print(pygame.version.ver)"],
                               env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               universal_newlines=True, timeout=45)
        if check.returncode:
            raise RuntimeError("pygame import test failed: " + check.stderr[-1200:])
        shutil.rmtree(RUNTIME, ignore_errors=True)
        os.rename(staging, RUNTIME)
        with open(MARKER, "w") as marker:
            marker.write("pygame %s; %s; %s\n" % (check.stdout.strip(), py_tag, machine))
        log("Bootstrap complete: " + check.stdout.strip())
        return 0
    except Exception as error:
        log("FATAL: bootstrap failed: " + str(error))
        shutil.rmtree(RUNTIME + ".staging", ignore_errors=True)
        return 3
    finally:
        try:
            os.remove(archive)
        except OSError:
            pass

if __name__ == "__main__":
    sys.exit(main())
