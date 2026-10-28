"""Publish the current submission decision pages (delegates to build_k3c_site, literal gate)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_k3c_site import build  # noqa: E402


def main():
    build()


if __name__ == '__main__':
    main()
