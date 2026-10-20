"""Generate synthetic test PDFs (requires PyMuPDF). Not manufacturer documents."""
from pathlib import Path
import fitz
root = Path(__file__).parent / 'samples'
root.mkdir(exist_ok=True)
cases = {
    'memory': ['Manufacturer: Samsung','Model: SAMPLE-RAM5','Capacity: 16GB','Memory Type: DDR5 UDIMM','Data Rate: 5600 MT/s','CAS Latency: CL46'],
    'vga': ['Manufacturer: NVIDIA','Model: SAMPLE-GPU1','Memory Size: 16GB','Memory Type: GDDR6','Memory Bandwidth: 512 GB/s','TGP: 200 W'],
    'mixed': ['Model: SAMPLE-A1','Capacity: 1TB','Model: SAMPLE-B2','Capacity: 2TB'],
}
for name,lines in cases.items():
    with fitz.open() as doc:
        page=doc.new_page();page.insert_text((40,50),'\n'.join(lines));doc.save(root/(name+'.pdf'))
with fitz.open() as doc:
    doc.new_page();doc.save(root/'scan.pdf')
with fitz.open() as doc:
    doc.new_page();doc.save(root/'locked.pdf',encryption=fitz.PDF_ENCRYPT_AES_256,owner_pw='owner',user_pw='secret')
(root/'bad.pdf').write_text('not PDF')
