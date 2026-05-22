#!/usr/bin/env python
"""
Task:
    CLI executable script wrapper for the PDF text extraction utility.
    Resolves dependencies and invokes the core pdf extractor runner.

Input_Params:
    cli_arguments (via sys.argv):
        CommandLine arguments parsed by the underlying module (e.g. pdf_path, --ocr, --output).

Output_Params:
    None

Returns:
    None
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.utils.pdf_extractor import main

if __name__ == "__main__":
    main()
