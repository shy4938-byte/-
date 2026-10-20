"""Resource lookup after extraction/installation, independent of cwd."""
import sys
from pathlib import Path
ROOT=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent.parent))
def template_path():
    if getattr(sys,'frozen',False):
        bundled=Path(sys.executable).resolve().parent/'templates'/'스펙비교 양식(1).xlsx'
        if bundled.exists():
            return bundled
    return ROOT/'assets'/'template.xlsx'
