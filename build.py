#!/usr/bin/env python3
"""
Build script for The Minions Cursor Plugin.

Creates standalone executables:
- Windows: .exe file
- Linux: AppImage

Usage:
    python build.py          # Build for current platform
    python build.py --all    # Build for all platforms
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_NAME = "minions"
VERSION = "0.1.0"
MAIN_SCRIPT = "src/minions/cli.py"


def run_command(cmd, **kwargs):
    """Run a command and print output."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, **kwargs)
    return result.returncode == 0


def build_windows():
    """Build Windows .exe using PyInstaller."""
    print("\n=== Building Windows Executable ===\n")
    
    # PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", PROJECT_NAME,
        "--add-data", "configs;configs",
        "--hidden-import", "redis",
        "--hidden-import", "openai",
        "--hidden-import", "elevenlabs",
        "--hidden-import", "twilio",
        "--hidden-import", "yaml",
        "--console",
        MAIN_SCRIPT,
    ]
    
    if not run_command(cmd):
        print("ERROR: PyInstaller build failed")
        return False
    
    # Check output
    exe_path = Path("dist") / f"{PROJECT_NAME}.exe"
    if exe_path.exists():
        print(f"\nSUCCESS: Built {exe_path}")
        print(f"Size: {exe_path.stat().st_size / 1024 / 1024:.2f} MB")
        return True
    
    return False


def build_linux():
    """Build Linux executable using PyInstaller."""
    print("\n=== Building Linux Executable ===\n")
    
    # PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", PROJECT_NAME,
        "--add-data", "configs:configs",
        "--hidden-import", "redis",
        "--hidden-import", "openai",
        "--hidden-import", "elevenlabs",
        "--hidden-import", "twilio",
        "--hidden-import", "yaml",
        "--console",
        MAIN_SCRIPT,
    ]
    
    if not run_command(cmd):
        print("ERROR: PyInstaller build failed")
        return False
    
    # Check output
    exe_path = Path("dist") / PROJECT_NAME
    if exe_path.exists():
        print(f"\nSUCCESS: Built {exe_path}")
        print(f"Size: {exe_path.stat().st_size / 1024 / 1024:.2f} MB")
        return True
    
    return False


def create_appimage():
    """Create Linux AppImage (requires appimagetool)."""
    print("\n=== Creating AppImage ===\n")
    
    # First build the Linux executable
    if not build_linux():
        return False
    
    # Create AppDir structure
    appdir = Path("dist/AppDir")
    appdir.mkdir(parents=True, exist_ok=True)
    
    # Copy executable
    shutil.copy("dist/minions", appdir / "AppRun")
    (appdir / "AppRun").chmod(0o755)
    
    # Create desktop file
    desktop_content = f"""[Desktop Entry]
Type=Application
Name=The Minions
Comment=Monitor Cursor chats and get phone call summaries
Exec=minions
Icon=minions
Categories=Development;
Terminal=true
"""
    (appdir / "minions.desktop").write_text(desktop_content)
    
    # Create simple icon (placeholder)
    # In production, would use a proper icon file
    
    # Try to create AppImage using appimagetool
    appimage_tool = shutil.which("appimagetool")
    if appimage_tool:
        cmd = [appimage_tool, str(appdir), f"dist/{PROJECT_NAME}-{VERSION}.AppImage"]
        if run_command(cmd):
            print(f"\nSUCCESS: Created AppImage")
            return True
    else:
        print("NOTE: appimagetool not found. AppImage not created.")
        print("The Linux binary is available at: dist/minions")
    
    return True


def clean():
    """Clean build artifacts."""
    dirs_to_remove = ["build", "dist", "__pycache__", "*.egg-info"]
    files_to_remove = ["*.spec"]
    
    for pattern in dirs_to_remove:
        for path in Path(".").glob(pattern):
            if path.is_dir():
                print(f"Removing directory: {path}")
                shutil.rmtree(path)
    
    for pattern in files_to_remove:
        for path in Path(".").glob(pattern):
            if path.is_file():
                print(f"Removing file: {path}")
                path.unlink()
    
    print("Clean complete.")


def main():
    parser = argparse.ArgumentParser(description="Build The Minions Cursor Plugin")
    parser.add_argument("--clean", action="store_true", help="Clean build artifacts")
    parser.add_argument("--all", action="store_true", help="Build for all platforms (via Docker)")
    parser.add_argument("--appimage", action="store_true", help="Create AppImage (Linux only)")
    
    args = parser.parse_args()
    
    if args.clean:
        clean()
        return
    
    # Check for PyInstaller
    try:
        import PyInstaller
    except ImportError:
        print("ERROR: PyInstaller not installed. Run: pip install pyinstaller")
        sys.exit(1)
    
    system = platform.system()
    
    if args.all:
        print("Building for all platforms requires Docker.")
        print("Use: docker-compose run build")
        return
    
    if args.appimage:
        if system != "Linux":
            print("AppImage can only be created on Linux")
            sys.exit(1)
        create_appimage()
    elif system == "Windows":
        build_windows()
    elif system == "Linux":
        build_linux()
    elif system == "Darwin":
        print("macOS build uses same process as Linux")
        build_linux()
    else:
        print(f"Unsupported platform: {system}")
        sys.exit(1)


if __name__ == "__main__":
    main()
