#!/usr/bin/env python3
"""Build the published, password-protected index.html from src/index.html.

The <main> content of src/index.html and the PDF are encrypted with AES-256-GCM,
using a key derived from the password with PBKDF2-SHA256. The published
index.html holds only ciphertext; the browser decrypts it once the right
password is entered. The password itself is never written to the repo.

    PAGE_PASSWORD=... python3 encrypt_page.py     # or omit it and type it

Writes index.html and keepsake.bin (the encrypted PDF).
"""
import base64
import getpass
import json
import os
import re

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src", "index.html")
PDF = os.path.join(HERE, "Wedding-Band-Inscriptions.pdf")
OUT = os.path.join(HERE, "index.html")
OUT_PDF = os.path.join(HERE, "keepsake.bin")
ITERATIONS = 600_000

SCRIPT = r"""<script>
(function () {
  var P = __PAYLOAD__;
  var STORE = "for-alltid-go-deo-key";
  var enc = new TextEncoder(), dec = new TextDecoder();
  var b64 = function (s) { return Uint8Array.from(atob(s), function (c) { return c.charCodeAt(0); }); };
  var toB64 = function (buf) { return btoa(String.fromCharCode.apply(null, new Uint8Array(buf))); };
  var gate = document.querySelector(".gate");
  var input = document.getElementById("pw");
  var busy = false;

  try { localStorage.removeItem("for-alltid-go-deo"); } catch (e) {}

  function derive(pw) {
    return crypto.subtle.importKey("raw", enc.encode(pw), "PBKDF2", false, ["deriveKey"]).then(function (base) {
      return crypto.subtle.deriveKey(
        { name: "PBKDF2", salt: b64(P.salt), iterations: P.iter, hash: "SHA-256" },
        base, { name: "AES-GCM", length: 256 }, true, ["decrypt"]);
    });
  }

  function open(key) {
    return crypto.subtle.decrypt({ name: "AES-GCM", iv: b64(P.iv) }, key, b64(P.ct)).then(function (buf) {
      document.querySelector("main").innerHTML = dec.decode(buf);
      document.body.classList.remove("locked");
      var link = document.querySelector("a.pdf");
      if (link) link.addEventListener("click", function (e) { e.preventDefault(); download(key); });
      return key;
    });
  }

  function download(key) {
    fetch(P.pdf.file).then(function (r) { return r.arrayBuffer(); }).then(function (data) {
      return crypto.subtle.decrypt({ name: "AES-GCM", iv: b64(P.pdf.iv) }, key, data);
    }).then(function (buf) {
      var url = URL.createObjectURL(new Blob([buf], { type: "application/pdf" }));
      var a = document.createElement("a");
      a.href = url; a.download = P.pdf.name;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 10000);
    });
  }

  function remember(key) {
    return crypto.subtle.exportKey("raw", key).then(function (raw) {
      try { localStorage.setItem(STORE, toB64(raw)); } catch (e) {}
    });
  }

  function wrong() {
    gate.classList.remove("wrong"); void gate.offsetWidth; gate.classList.add("wrong");
    input.select();
  }

  var saved = null;
  try { saved = localStorage.getItem(STORE); } catch (e) {}
  if (saved) {
    crypto.subtle.importKey("raw", b64(saved), "AES-GCM", true, ["decrypt"]).then(open).catch(function () {
      try { localStorage.removeItem(STORE); } catch (e) {}
    });
  }

  gate.querySelector("form").addEventListener("submit", function (e) {
    e.preventDefault();
    if (busy) return;
    busy = true;
    derive(input.value.trim().toLowerCase()).then(open).then(remember).catch(wrong)
      .then(function () { busy = false; });
  });
})();
</script>
"""


def main():
    password = os.environ.get("PAGE_PASSWORD") or getpass.getpass("Page password: ")
    password = password.strip().lower()
    if not password:
        raise SystemExit("No password given.")

    src = open(SRC, encoding="utf-8").read()
    m = re.search(r"<main>(.*?)</main>", src, flags=re.S)
    if not m:
        raise SystemExit("src/index.html has no <main> element.")

    salt = os.urandom(16)
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt,
                     iterations=ITERATIONS).derive(password.encode("utf-8"))
    aes = AESGCM(key)

    iv = os.urandom(12)
    ct = aes.encrypt(iv, m.group(1).encode("utf-8"), None)

    pdf_iv = os.urandom(12)
    with open(PDF, "rb") as f:
        pdf_ct = aes.encrypt(pdf_iv, f.read(), None)
    with open(OUT_PDF, "wb") as f:
        f.write(pdf_ct)

    b = lambda x: base64.b64encode(x).decode("ascii")
    payload = {
        "iter": ITERATIONS, "salt": b(salt), "iv": b(iv), "ct": b(ct),
        "pdf": {"file": "keepsake.bin", "iv": b(pdf_iv), "name": "Wedding-Band-Inscriptions.pdf"},
    }
    out = src[:m.start()] + "<main></main>\n" + SCRIPT.replace("__PAYLOAD__", json.dumps(payload)) \
        + src[m.end():].lstrip("\n")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"Wrote {os.path.relpath(OUT, HERE)} and {os.path.relpath(OUT_PDF, HERE)}")


if __name__ == "__main__":
    main()
