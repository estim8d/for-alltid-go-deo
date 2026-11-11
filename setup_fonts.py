"""Download the open-source fonts the page uses and convert them to TTF in ./fonts.

Cormorant Garamond and Cinzel are both under the SIL Open Font License and come from
the Fontsource packages on npm. Needs `npm` and `pip install fonttools brotli`.
"""
import subprocess
import tarfile
from pathlib import Path

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent
FONT_DIR = ROOT / "fonts"
BUILD = ROOT / "build"

PACKAGES = {
    "@fontsource/cormorant-garamond@5.3.0": {
        "cormorant-garamond-latin-300-italic.woff2": "CG-300-italic",
        "cormorant-garamond-latin-400-normal.woff2": "CG-400-normal",
        "cormorant-garamond-latin-400-italic.woff2": "CG-400-italic",
        "cormorant-garamond-latin-500-normal.woff2": "CG-500-normal",
        "cormorant-garamond-latin-700-normal.woff2": "CG-700-normal",
    },
    "@fontsource/cinzel@5.3.0": {
        "cinzel-latin-400-normal.woff2": "Cinzel-400",
    },
}


def main():
    FONT_DIR.mkdir(exist_ok=True)
    BUILD.mkdir(exist_ok=True)
    for pkg, files in PACKAGES.items():
        name = subprocess.run(["npm", "pack", pkg, "--silent"], cwd=BUILD, check=True,
                              capture_output=True, text=True).stdout.strip().splitlines()[-1]
        with tarfile.open(BUILD / name) as tar:
            for src, dst in files.items():
                member = tar.extractfile(f"package/files/{src}")
                out = BUILD / src
                out.write_bytes(member.read())
                font = TTFont(out)
                font.flavor = None
                font.save(FONT_DIR / f"{dst}.ttf")
                print(f"fonts/{dst}.ttf")


if __name__ == "__main__":
    main()
