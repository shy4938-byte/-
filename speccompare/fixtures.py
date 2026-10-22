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


def create_capacity_fixture(path):
    """License-free merged-label matrix and vertically merged SKU catalogue."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with fitz.open() as doc:
        page=doc.new_page()
        def line(y,values):
            for x,text in values:page.insert_text((x,y),text,fontsize=10)
        line(35,[(30,'SSD Technical Specifications')])
        line(65,[(150,'Capacity1)'),(330,'1TB'),(480,'2TB')])
        for y,label,a,b in [(95,'DRAM Cache Memory','1GB LPDDR4','2GB LPDDR4'),(125,'Sequential Read','7,100 MB/s','7,200 MB/s'),(155,'Sequential Write','6,100 MB/s','6,200 MB/s')]:
            line(y,[(150,label),(315,a),(465,b)])
        line(185,[(110,'QD 1'),(220,'Ran. Read'),(315,'20K IOPS'),(465,'21K IOPS')])
        line(210,[(110,'Thread 1'),(220,'Ran. Write'),(315,'70K IOPS'),(465,'71K IOPS')])
        line(240,[(110,'QD 32'),(220,'Ran. Read'),(315,'1,100K IOPS'),(465,'1300K IOPS')])
        line(265,[(110,'Thread 16'),(220,'Ran. Write'),(315,'1,500K IOPS'),(465,'1,600K IOPS')])
        line(300,[(150,'TBW'),(330,'600TB'),(480,'1,200TB')])
        # A partial border recreates a table extractor missing the rightmost column.
        for x in [140,290,420]:page.draw_line((x,50),(x,315))
        for y in [50,80,110,140,170,220,275,315]:page.draw_line((140,y),(420,y))
        page=doc.new_page()
        line(40,[(30,'PRODUCT LINEUP')])
        line(70,[(35,'Density'),(125,'Model Name'),(280,'Box Contents'),(465,'Model Code')])
        for y,cap,part in [(100,'1TB','ACME-X1'),(150,'2TB','ACME-X2')]:
            line(y,[(40,cap),(280,'Acme SSD '+cap),(465,part+'BW')])
            line(y+12,[(125,part)])
            line(y+24,[(40,'(nominal)'),(280,'Warranty Statement'),(465,part+'B/AM')])
        line(200,[(30,'* Notes: synthetic fixture')])
        doc.save(path)
    return path
