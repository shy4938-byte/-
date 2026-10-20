"""Synthetic, license-free PDFs for build/packaged runtime verification."""
from pathlib import Path
import fitz

def create_fixtures(folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    cases={
        'MEMORY': ['Manufacturer: Test Memory Co','Model: TEST-RAM-16','Capacity: 16 GB','Memory Type: DDR5 UDIMM','Data Rate: 5600 MT/s','CAS Latency: CL46'],
        'SSD': ['Brand: Test Storage Co','Model Number: TEST-SSD-1','Storage Capacity: 1 TB','Sequential Read Speed: 7.4 GB/s','Sequential Write Speed: 6000 MB/s','Random Read IOPS: 500K IOPS','TBW: 600 TB'],
        'VGA': ['Vendor: Test Graphics Co','Product Model: TEST-GPU-1','Memory Size: 16 GB','VRAM Type: GDDR6','Memory Bandwidth: 512 GB/s','TGP: 200 W'],
    }
    paths={}
    for category,lines in cases.items():
        path=folder/(category+' 검증.pdf')
        with fitz.open() as doc:
            page=doc.new_page();page.insert_text((40,50),'\n'.join(lines));doc.save(path)
        paths[category]=path
    return paths
