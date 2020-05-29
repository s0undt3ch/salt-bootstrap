import pathlib
import sys

import setuptools

if __name__ == "__main__":
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "src"))
    print(sys.path)
    setuptools.setup()
