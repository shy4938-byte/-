"""One-time provider setup. Keys remain in process memory, never QSettings."""
from PySide6.QtCore import QSettings, QThread, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog,QVBoxLayout,QFormLayout,QComboBox,QLineEdit,QLabel,QPushButton,QHBoxLayout,QCheckBox
from .ai import AIConfig, request_json


class SetupTask(QThread):
    done=Signal(str)
    def __init__(self,config,pull=False):super().__init__();self.config=config;self.pull=pull
    def run(self):
        try:
            self.config.validate()
            if self.config.provider=='ollama':
                base=self.config.endpoint.rstrip('/')
                if self.pull:
                    result=request_json(base+'/api/pull',{'name':self.config.model,'stream':False},timeout=1800)
                    if result.get('error'):raise ValueError('모델을 다운로드하지 못했습니다. 모델명과 디스크 공간을 확인하세요.')
                    text='모델 다운로드 완료. AI 설정을 적용하고 분석하세요.'
                else:
                    result=request_json(base+'/api/tags',timeout=10)
                    names=[v.get('name','') for v in result.get('models',[])]
                    text='로컬 AI 연결 성공. 설치 모델: '+(', '.join(names) or '없음 — 모델 받기를 누르세요.')
                    if self.config.model not in names:text+='\n선택 모델은 아직 설치되어 있지 않습니다.'
            else:
                result=request_json('https://api.openai.com/v1/models/'+self.config.model,headers={'Authorization':'Bearer '+self.config.api_key},timeout=20)
                text='온라인 AI 모델 조회 성공. 실제 PDF 해석은 분석 버튼에서 수행합니다.'
            self.done.emit(text)
        except Exception as exc:self.done.emit(str(exc))


class AISettingsDialog(QDialog):
    def __init__(self,config,parent=None):
        super().__init__(parent);self.setWindowTitle('AI 연결 설정');self.resize(640,440);self.task=None
        box=QVBoxLayout(self);intro=QLabel('다양한 양식은 AI가 글자·표·페이지 이미지를 읽어 해석합니다.\nAI 결과도 오류가 있을 수 있으므로 원문 근거를 확인하세요.');intro.setWordWrap(True);box.addWidget(intro)
        form=QFormLayout();box.addLayout(form)
        self.provider=QComboBox();self.provider.addItem('로컬 AI · 이 PC의 Ollama','ollama');self.provider.addItem('온라인 AI · OpenAI API','openai');form.addRow('분석 방식',self.provider)
        self.endpoint=QLineEdit(config.endpoint);form.addRow('로컬 AI 주소',self.endpoint)
        self.model=QLineEdit(config.model);form.addRow('모델 이름',self.model)
        self.key=QLineEdit(config.api_key);self.key.setEchoMode(QLineEdit.EchoMode.Password);self.key.setPlaceholderText('API 키는 이번 실행에서만 사용하며 파일에 저장하지 않습니다.');form.addRow('온라인 API 키',self.key)
        self.consent=QCheckBox('온라인 AI 사용 시 선택 PDF의 글자·페이지 이미지를 OpenAI로 전송하는 데 동의합니다. 이용 요금이 발생할 수 있습니다.');self.consent.setChecked(config.online_consent);box.addWidget(self.consent)
        self.status=QLabel('로컬 AI는 처음 한 번 Ollama 설치와 비전 모델 다운로드가 필요합니다.\n권장 시작 모델: qwen2.5vl:7b. RAM 약 16GB 이상을 권장하며 CPU에서는 느릴 수 있습니다.');self.status.setWordWrap(True);box.addWidget(self.status)
        row=QHBoxLayout();box.addLayout(row)
        self.install=QPushButton('Ollama 설치 페이지');self.install.clicked.connect(lambda:QDesktopServices.openUrl(QUrl('https://ollama.com/download/windows')));row.addWidget(self.install)
        self.check=QPushButton('연결 확인');self.check.clicked.connect(lambda:self.run_task(False));row.addWidget(self.check)
        self.pull=QPushButton('로컬 모델 받기');self.pull.clicked.connect(lambda:self.run_task(True));row.addWidget(self.pull)
        buttons=QHBoxLayout();box.addLayout(buttons);self.apply=QPushButton('설정 적용');self.apply.clicked.connect(self.accept_checked);buttons.addWidget(self.apply);cancel=QPushButton('닫기');cancel.clicked.connect(self.reject);buttons.addWidget(cancel)
        self.provider.setCurrentIndex(0 if config.provider=='ollama' else 1);self.provider.currentIndexChanged.connect(self.changed);self.changed(False)
    def changed(self,change_model=True):
        local=self.provider.currentData()=='ollama'
        self.endpoint.setEnabled(local);self.key.setEnabled(not local);self.consent.setEnabled(not local);self.pull.setEnabled(local);self.install.setEnabled(local)
        if change_model:self.model.setText('qwen2.5vl:7b' if local else 'gpt-4.1-mini')
    def config(self):
        return AIConfig(self.provider.currentData(),self.model.text().strip(),self.endpoint.text().strip(),self.key.text().strip(),self.consent.isChecked())
    def run_task(self,pull):
        if self.task and self.task.isRunning():return
        try:self.config().validate()
        except Exception as exc:self.status.setText(str(exc));return
        self.status.setText('모델 다운로드 중입니다. 최초 수 GB를 내려받으며 시간이 걸릴 수 있습니다.' if pull else 'AI 연결을 확인하고 있습니다. PDF는 전송하지 않습니다.')
        self.task=SetupTask(self.config(),pull);self.task.done.connect(self.status.setText);self.task.finished.connect(self.unblock)
        for w in [self.check,self.pull,self.apply,self.provider]:w.setEnabled(False)
        self.task.start()
    def unblock(self):
        for w in [self.check,self.apply,self.provider]:w.setEnabled(True)
        self.changed(False)
    def accept_checked(self):
        try:self.config().validate()
        except Exception as exc:self.status.setText(str(exc));return
        c=self.config();settings=QSettings('SpecCompare','SpecCompare')
        for k in ['provider','model','endpoint']:settings.setValue('ai/'+k,getattr(c,k))
        # Consent is session-specific; no API key or document data is persisted.
        self.accept()
    def reject(self):
        if self.task and self.task.isRunning():self.status.setText('연결·다운로드 작업이 끝난 후 닫으세요.');return
        super().reject()
    def closeEvent(self,event):
        if self.task and self.task.isRunning():event.ignore()
        else:event.accept()


def load_config():
    settings=QSettings('SpecCompare','SpecCompare');default=AIConfig()
    return AIConfig(**{k:str(settings.value('ai/'+k,getattr(default,k))) for k in ['provider','model','endpoint']})
