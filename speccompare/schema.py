from dataclasses import dataclass, field

FIELDS = {
 'MEMORY': ['제조사','모델명','용량','메모리 규격','동작속도','지연시간','가격'],
 'SSD': ['제조사','모델명','용량','인터페이스','순차읽기 속도','순차쓰기 속도','랜덤읽기 속도','랜덤쓰기 속도','내구성','가격'],
 'VGA': ['제조사','모델명','VRAM 용량','VRAM 종류','메모리 대역폭','소비전력','가격'],
}
ALIASES = {
 '제조사': ['manufacturer','vendor','제조사'], '모델명': ['model','part number','모델명'],
 '용량': ['capacity','density','용량'], '메모리 규격': ['memory type','module type','메모리 규격','규격'],
 '동작속도': ['data rate','memory speed','동작속도'], '지연시간': ['cas latency','latency','지연시간'],
 '가격': ['price','가격'], '인터페이스': ['interface','인터페이스'],
 '순차읽기 속도': ['sequential read','순차읽기'], '순차쓰기 속도': ['sequential write','순차쓰기'],
 '랜덤읽기 속도': ['random read','랜덤읽기'], '랜덤쓰기 속도': ['random write','랜덤쓰기'],
 '내구성': ['endurance','tbw','내구성'], 'VRAM 용량': ['memory size','frame buffer','vram capacity','VRAM 용량'],
 'VRAM 종류': ['memory type','vram type','VRAM 종류'], '메모리 대역폭': ['memory bandwidth','메모리 대역폭'],
 '소비전력': ['total graphics power','total board power','tdp','tgp','tbp','소비전력'],
 'DDR 세대':['ddr generation'], '폼팩터':['form factor'], 'ECC':['ecc'], '전압':['voltage'], 'Rank':['rank'],
 'PCIe 세대':['pcie generation'], 'NVMe':['nvme version'], 'DRAM':['dram'], 'NAND':['nand'],
 'TBW':['tbw'], 'MTBF':['mtbf'], 'GPU 모델':['gpu model'], 'GPU 아키텍처':['architecture'],
 '코어':['cuda cores','stream processors'], '부스트 클럭':['boost clock'], '메모리 버스':['memory bus'],
 '보조전원':['power connector'], '영상 출력':['display outputs','outputs'],
}
EXTRAS = {'MEMORY':['DDR 세대','폼팩터','ECC','전압','Rank'], 'SSD':['PCIe 세대','NVMe','DRAM','NAND','TBW','MTBF'], 'VGA':['GPU 모델','GPU 아키텍처','코어','부스트 클럭','메모리 버스','보조전원','영상 출력']}
@dataclass
class Value:
    text: str = '확인 필요'
    page: int | None = None
    evidence: str = ''
    status: str = '미확인'
@dataclass
class Product:
    source: str
    category: str
    values: dict[str, Value] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    @property
    def name(self):
        return self.values.get('모델명', Value()).text
