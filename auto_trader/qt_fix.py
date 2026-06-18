"""Fix PyQt5 platform plugin path on Windows."""

from __future__ import annotations

import os
import sys


def setup_qt_plugins() -> None:
    try:
        import PyQt5
    except ImportError:
        return

    base = os.path.dirname(PyQt5.__file__)
    plugins = os.path.join(base, "Qt5", "plugins")
    platforms = os.path.join(plugins, "platforms")
    qt_bin = os.path.join(base, "Qt5", "bin")

    if os.path.isdir(platforms):
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = platforms
    if os.path.isdir(plugins):
        os.environ["QT_PLUGIN_PATH"] = plugins
    if os.path.isdir(qt_bin):
        os.environ["PATH"] = qt_bin + os.pathsep + os.environ.get("PATH", "")

    if hasattr(os, "add_dll_directory") and os.path.isdir(qt_bin):
        os.add_dll_directory(qt_bin)


setup_qt_plugins()
