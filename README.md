# FOR ALLTID · GO DEO

A one-page keepsake describing the inscriptions inside Shauneen and David's Tiffany & Co. wedding bands.

- **Shauneen's ring:** FOR ALLTID, Norwegian for forever.
- **David's ring:** GO DEO, Irish for forever.

Both are hand engraved in capitals by Tiffany & Co. engravers in New York City.

![Preview](preview.png)

**View it:** [estim8d.github.io/for-alltid-go-deo](https://estim8d.github.io/for-alltid-go-deo/) · [Download the PDF](Wedding-Band-Inscriptions.pdf)

## Build it

The page is drawn with Python and ReportLab. Spacing is set from measured ink, not font boxes: every gap between visible marks inside a group is 11 pt, and the gaps between groups are calculated so the content fills a US Letter page between 54 pt margins.

Requirements: Python 3, npm, and `pdftoppm` (from poppler).

```sh
pip install -r requirements.txt
python3 setup_fonts.py    # downloads Cormorant Garamond and Cinzel into ./fonts
python3 make_pdf.py       # writes Wedding-Band-Inscriptions.pdf
```

## Publish the web page

The page is password protected. Edit `src/index.html` (plain text), then build the published `index.html` and `keepsake.bin` (the encrypted PDF):

```sh
pip install cryptography
python3 encrypt_page.py    # asks for the page password
```

The published page holds only AES-256-GCM ciphertext; the browser decrypts it once the right password is entered. `_config.yml` keeps this README, the scripts, `src/`, the plain PDF and `preview.png` off the site. Rebuild after changing the PDF too.

## Type and color

- Text: Cormorant Garamond. Inscriptions: Cinzel, standing in for an engraver's Roman capital.
- Ink #00563B on Tiffany Blue #81D8D0.

Both fonts are under the SIL Open Font License; the web page serves them from `webfonts/`, with their licenses. The Tiffany & Co. wordmark is a trademark of Tiffany & Co.
