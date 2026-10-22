"""Free local model setup. No API key input or billable cloud provider."""
from PySide6.QtCore import QSettings,QThread,Signal,QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog,QVBoxLayout,QFormLayout,QComboBox,QLineEdit,QLabel,QPushButton,QHBoxLayout
from .ai import AIConfig,request_json,validate_local_model


class SetupTask(QThread):
    done=Signal(str)
    def __init__(self,config,pull=False):super().__init__();self.config=config;self.pull=pull
    def run(self):
        try:
            self.config.validate();base=self.config.endpoint.rstrip('/')
            if self.pull:
                result=request_json(base+'/api/pull',{'model':self.config.model,'stream':False},timeout=1800)
                if result.get('error'):raise ValueError('모델을 다운로드하지 못했습니다. 모델명과 디스크 공간을 확인하세요.')
                details=request_json(base+'/api/show',{'model':self.config.model},timeout=20);validate_local_model(details)
                text='무료 로컬 비전 모델 다운로드 완료. 설정 적용 후 분석하세요.'
            else:
                result=request_json(base+'/api/tags',timeout=10);names=[v.get('name','') for v in result.get('models',[])]
                if self.config.model in names:
                    details=request_json(base+'/api/show',{'model':self.config.model},timeout=20);validate_local_model(details)
                    text='무료 로컬 비전 모델 연결 성공. PDF는 이 PC에서 처리합니다.'
                else:text='Ollama 연결 성공. 선택 모델은 아직 없습니다. 무료 모델 받기를 누르세요.'
            self.done.emit(text)
        except Exception as exc:self.done.emit(str(exc))


class AISettingsDialog(QDialog):
    def __init__(self,config,parent=None):
        super().__init__(parent);self.setWindowTitle('무료 AI 연결 설정');self.resize(640,400);self.task=None
        box=QVBoxLayout(self)
        intro=QLabel('API 이용 요금 없이 이 PC에서 PDF를 해석합니다.\n처음 한 번 무료 Ollama 설치와 수 GB의 비전 모델 다운로드가 필요합니다.\nPDF를 유료 온라인 API로 전송하지 않으며 API 키도 필요하지 않습니다.');intro.setWordWrap(True);box.addWidget(intro)
        form=QFormLayout();box.addLayout(form)
        self.endpoint=QLineEdit(config.endpoint);form.addRow('이 PC의 AI 주소',self.endpoint)
        self.model=QComboBox();self.model.setEditable(True);self.model.addItems(['qwen2.5vl:3b','qwen2.5vl:7b']);self.model.setCurrentText(config.model);form.addRow('무료 로컬 비전 모델',self.model)
        self.status=QLabel('3b는 가벼운 시작 모델, 7b는 더 높은 성능의 PC용입니다.\nRAM 16GB 이상을 권장하며 RAM·GPU에 따라 속도와 해석 품질이 달라집니다.\nAI가 읽은 값도 원문 근거를 확인해야 합니다.');self.status.setWordWrap(True);box.addWidget(self.status)
        row=QHBoxLayout();box.addLayout(row)
        self.install=QPushButton('무료 Ollama 설치');self.install.clicked.connect(lambda:QDesktopServices.openUrl(QUrl('https://ollama.com/download/windows')));row.addWidget(self.install)
        self.check=QPushButton('연결 확인');self.check.clicked.connect(lambda:self.run_task(False));row.addWidget(self.check)
        self.pull=QPushButton('무료 모델 받기');self.pull.clicked.connect(lambda:self.run_task(True));row.addWidget(self.pull)
        buttons=QHBoxLayout();box.addLayout(buttons);self.apply=QPushButton('설정 적용');self.apply.clicked.connect(self.accept_checked);buttons.addWidget(self.apply);cancel=QPushButton('닫기');cancel.clicked.connect(self.reject);buttons.addWidget(cancel)
    def config(self):return AIConfig(model=self.model.currentText().strip(),endpoint=self.endpoint.text().strip())
    def run_task(self,pull):
        if self.task and self.task.isRunning():return
        try:self.config().validate()
        except Exception as exc:self.status.setText(str(exc));return
        self.status.setText('무료 모델 다운로드 중입니다. 최초 수 GB를 내려받으며 시간이 걸릴 수 있습니다.' if pull else '로컬 AI를 확인하고 있습니다. PDF는 전송하지 않습니다.')
        self.task=SetupTask(self.config(),pull);self.task.done.connect(self.status.setText);self.task.finished.connect(self.unblock)
        for w in [self.check,self.pull,self.apply,self.model]:w.setEnabled(False)
        self.task.start()
    def unblock(self):
        for w in [self.check,self.pull,self.apply,self.model]:w.setEnabled(True)
    def accept_checked(self):
        try:self.config().validate()
        except Exception as exc:self.status.setText(str(exc));return
        c=self.config();settings=QSettings('SpecCompare','SpecCompare')
        for k in ['provider','model','endpoint']:settings.setValue('ai/'+k,getattr(c,k))
        self.accept()
    def reject(self):
        if self.task and self.task.isRunning():self.status.setText('연결·다운로드가 끝난 후 닫으세요.');return
        super().reject()
    def closeEvent(self,event):
        if self.task and self.task.isRunning():event.ignore()
        else:event.accept()


def load_config():
    settings=QSettings('SpecCompare','SpecCompare');default=AIConfig()
    if settings.value('ai/provider','ollama')!='ollama':return default
    return AIConfig(model=str(settings.value('ai/model',default.model)),endpoint=str(settings.value('ai/endpoint',default.endpoint)))
