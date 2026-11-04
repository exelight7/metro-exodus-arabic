"""Rebuild the native single-control UI and restore clean loader timing."""
import shutil
from pathlib import Path
from build_subtitle_colors import main as build_colors
ROOT=Path(__file__).resolve().parents[1]
def main():
    build_colors()
    source=ROOT/'02_extracted/steam_local/patch_04/content/scripts/loader_data.bin'
    target=ROOT/'06_build/stage/content/scripts/loader_data.bin'
    shutil.copyfile(source,target);assert source.read_bytes()==target.read_bytes()
    print('Clean loader timing restored; no overlay or invisible spacing')
if __name__=='__main__':main()
