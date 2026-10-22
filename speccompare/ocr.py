"""Tesseract's C file reader may not accept Unicode tessdata paths on Windows."""
import ctypes
import hashlib
import os
from pathlib import Path
import sys
import tempfile


def data_path(source):
    source=Path(source)
    if sys.platform!='win32' or str(source).isascii():return str(source)
    # Read Unicode bundled paths through Python; cache in the user's TEMP folder.
    files=['eng.traineddata','kor.traineddata']
    contents={name:(source/name).read_bytes() for name in files}
    digest=hashlib.sha256(b''.join(contents.values())).hexdigest()[:20]
    cache=Path(tempfile.gettempdir())/'SpecCompare-OCR'/digest;cache.mkdir(parents=True,exist_ok=True)
    for name,data in contents.items():
        target=cache/name
        if target.is_file() and hashlib.sha256(target.read_bytes()).digest()==hashlib.sha256(data).digest():continue
        temporary=None
        try:
            with tempfile.NamedTemporaryFile(dir=cache,delete=False) as f:temporary=f.name;f.write(data)
            os.replace(temporary,target);temporary=None
        finally:
            if temporary:Path(temporary).unlink(missing_ok=True)
    resolved=str(cache)
    if not resolved.isascii():
        # Korean Windows account names can also make TEMP a Unicode path.
        get_short=ctypes.windll.kernel32.GetShortPathNameW
        get_short.argtypes=[ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_uint32];get_short.restype=ctypes.c_uint32
        length=get_short(resolved,None,0)
        if length:
            buffer=ctypes.create_unicode_buffer(length+1)
            if get_short(resolved,buffer,len(buffer)):resolved=buffer.value
    if not resolved.isascii():raise RuntimeError('OCR 언어 경로를 읽지 못했습니다. 영어 경로의 TEMP 폴더가 필요합니다.')
    return resolved
