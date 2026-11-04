#!/usr/bin/env python3
"""Repository entrypoint for the self-contained foura-dialogue skill toolkit."""
from pathlib import Path
import runpy
if __name__=='__main__':
    runpy.run_path(str(Path(__file__).resolve().parents[1]/'skills/foura-dialogue/scripts/foura_dialogue.py'),run_name='__main__')
