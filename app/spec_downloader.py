"""
Auto-downloads telecom spec documents at startup if specs/ directory is empty.
Specs are hosted as GitHub release assets to keep them out of the main repo
while still being available for fresh deployments.
"""
import urllib.request
from pathlib import Path

# Specs hosted on GitHub Releases — update URLs after creating your release
SPECS_TO_FETCH = {
    "SIP.pdf": "https://github.com/ASH2090/TelecomRAG/releases/download/v1.0-specs/SIP.pdf",
    "MSRP.pdf": "https://github.com/ASH2090/TelecomRAG/releases/download/v1.0-specs/MSRP.pdf",
    "SIP_REG.pdf": "https://github.com/ASH2090/TelecomRAG/releases/download/v1.0-specs/SIP_REG.pdf",
}

SPECS_DIR = Path("data/specs")


def download_file(url: str, output_path: Path) -> bool:
    """Download a file from a URL. Returns True on success."""
    try:
        print(f"Downloading {output_path.name} from GitHub Releases...")
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "TelecomRAG/1.0"},
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            with open(output_path, "wb") as f:
                f.write(response.read())
        print(f"  Saved as {output_path.name}")
        return True
    except Exception as e:
        print(f"  Failed to download {output_path.name}: {e}")
        return False


def ensure_specs_available() -> int:
    """
    Check if specs directory has any PDFs. If not, download them.
    Returns the number of PDFs available after this runs.
    """
    SPECS_DIR.mkdir(parents=True, exist_ok=True)

    existing_pdfs = list(SPECS_DIR.glob("*.pdf"))
    if existing_pdfs:
        print(f"Found {len(existing_pdfs)} existing spec PDF(s), skipping download")
        return len(existing_pdfs)

    print("No specs found. Downloading from GitHub Releases...")
    downloaded = 0
    for filename, url in SPECS_TO_FETCH.items():
        output_path = SPECS_DIR / filename
        if download_file(url, output_path):
            downloaded += 1

    print(f"Downloaded {downloaded}/{len(SPECS_TO_FETCH)} specs")
    return downloaded


if __name__ == "__main__":
    ensure_specs_available()