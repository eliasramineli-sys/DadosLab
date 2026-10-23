from __future__ import annotations
from pathlib import Path
import csv
import sys
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QHBoxLayout,QVBoxLayout,
    QLabel,QPushButton,QComboBox,QSpinBox,QFrame,QCheckBox,QStackedWidget,QTextEdit,
    QFileDialog,QMessageBox,QScrollArea,QGridLayout)
from .bridge import NativeDice, MAX_ROLLS
from .analysis import analyze, conclusion, report_text
from .die_widget import DieWidget
from .plots import Charts
from .storage import Store

STYLE = """
QWidget { color:#e9f1ff; font-family:'Segoe UI'; font-size:13px; }
QMainWindow, QWidget#root { background:#0a1220; }
QWidget#sidebar { background:#0e192b; border-right:1px solid #22324b; }
QWidget#experiment { background:transparent; }
QFrame#card { background:#111e32; border:1px solid #273851; border-radius:16px; }
QLabel { background:transparent; border:none; }
QLabel#muted { color:#9aafca; }
QLabel#eyebrow { color:#65dcc7; font-size:11px; font-weight:700; }
QLabel#title { font-size:29px; font-weight:700; }
QLabel#metric { font-size:27px; font-weight:700; }
QLabel#brand { font-size:21px; font-weight:700; }
QPushButton { background:#1c2d46; border:1px solid #354d6b; border-radius:9px; padding:10px 14px; font-weight:600; }
QPushButton:hover { background:#2b4261; }
QPushButton:disabled { color:#71839b; background:#18263a; }
QPushButton#primary { background:#64dcc7; color:#082a29; border:none; padding:14px; font-size:15px; }
QPushButton#primary:hover { background:#83efdc; }
QPushButton#nav { text-align:left; border:none; background:transparent; padding:12px; }
QPushButton#nav:checked { background:#203650; color:#72e7d0; }
QComboBox,QSpinBox { background:#0b1526; border:1px solid #38506e; border-radius:7px; padding:7px; min-height:21px; }
QComboBox QAbstractItemView { background:#14253b; selection-background-color:#2a496a; }
QTextEdit { background:#111e32; border:1px solid #273851; border-radius:12px; padding:15px; font-size:14px; }
QScrollArea { border:none; background:transparent; }
QCheckBox { color:#b6c8df; padding:4px 0; }
QToolTip { background:#203650; color:white; border:1px solid #496786; }
"""


def label(text, name=None, wrap=False):
    item=QLabel(text)
    if name: item.setObjectName(name)
    item.setWordWrap(wrap)
    return item


def card():
    frame=QFrame()
    frame.setObjectName("card")
    layout=QVBoxLayout(frame)
    layout.setContentsMargins(20,18,20,18)
    layout.setSpacing(12)
    return frame,layout


class AnalysisWorker(QThread):
    ready=Signal(object,object,object)
    error=Signal(str)

    def __init__(self,native,values,selected,count=0,manual=None):
        super().__init__()
        self.native,self.values,self.selected=native,values[:],selected
        self.count,self.manual=count,manual

    def run(self):
        try:
            additions=self.native.roll(self.count) if self.count else (self.manual or [])
            values=self.values+additions
            result=analyze(values,self.selected,self.native)
            self.ready.emit(additions,values,result)
        except Exception as exc:
            self.error.emit(str(exc))


class Window(QMainWindow):
    def __init__(self, store=None):
        super().__init__()
        self.setWindowTitle("DadosLab — Laboratório de Probabilidade")
        self.resize(1440,980)
        self.setMinimumSize(1060,800)
        self.native=NativeDice()
        self.store=store or Store()
        self.mode="virtual"
        self.session,self.values=self.store.load(self.mode)
        self.result=None
        self.busy=False
        self.worker=None
        self.pending=None
        self.build_ui()
        QTimer.singleShot(0,self.reanalyze)

    def build_ui(self):
        root=QWidget();root.setObjectName("root")
        self.setCentralWidget(root)
        layout=QHBoxLayout(root);layout.setContentsMargins(0,0,0,0);layout.setSpacing(0)
        sidebar=QWidget();sidebar.setObjectName("sidebar");sidebar.setFixedWidth(210)
        side=QVBoxLayout(sidebar);side.setContentsMargins(22,30,20,25);side.setSpacing(8)
        side.addWidget(label("◆ DadosLab","brand"))
        side.addWidget(label("LABORATÓRIO DO ACASO","eyebrow"))
        side.addSpacing(35)
        self.stack=QStackedWidget()
        self.nav=[]
        for i,text in enumerate(["◈  Experimento","▤  Relatório","?  Como funciona"]):
            button=QPushButton(text);button.setObjectName("nav");button.setCheckable(True)
            button.clicked.connect(lambda checked=False,index=i:self.navigate(index))
            self.nav.append(button);side.addWidget(button)
        self.nav[0].setChecked(True)
        side.addStretch()
        side.addWidget(label("100% local\nSem conta ou nuvem","muted",True))
        side.addSpacing(15)
        side.addWidget(label("Python · C++ · Java\nVersão 0.1.0","muted",True))
        layout.addWidget(sidebar)
        content=QWidget();body=QVBoxLayout(content);body.setContentsMargins(28,25,28,20);body.setSpacing(17)
        header=QHBoxLayout()
        titles=QVBoxLayout();titles.addWidget(label("PROBABILIDADE EM MOVIMENTO","eyebrow"))
        titles.addWidget(label("O acaso, em perspectiva.","title"))
        titles.addWidget(label("Lance, observe e compare os dados com a teoria.","muted"))
        header.addLayout(titles);header.addStretch()
        self.status=label("Iniciando os motores…","muted");header.addWidget(self.status)
        body.addLayout(header)
        body.addWidget(self.stack,1)
        layout.addWidget(content,1)
        scroll=QScrollArea();scroll.setWidgetResizable(True)
        experiment=QWidget();experiment.setObjectName("experiment")
        page=QVBoxLayout(experiment);page.setContentsMargins(0,0,0,0);page.setSpacing(16)
        scroll.setWidget(experiment);self.stack.addWidget(scroll)
        main=QHBoxLayout();main.setSpacing(18)
        left=QVBoxLayout();left.setSpacing(14)
        stage,stage_l=card();stage.setFixedWidth(310)
        stage_l.addWidget(label("01 / LANÇAMENTO","eyebrow"))
        self.mode_box=QComboBox();self.mode_box.addItems(["Dado virtual","Dado físico · registro manual"])
        self.mode_box.currentIndexChanged.connect(self.change_mode);stage_l.addWidget(self.mode_box)
        self.die=DieWidget();self.die.setMinimumSize(265,215)
        self.die.landed.connect(self.animation_done);stage_l.addWidget(self.die)
        self.last=label("Pronto para o primeiro lançamento","muted",True)
        self.last.setAlignment(Qt.AlignmentFlag.AlignCenter);stage_l.addWidget(self.last)
        self.animate=QCheckBox("Animar lançamento virtual");self.animate.setChecked(True);stage_l.addWidget(self.animate)
        self.roll_button=QPushButton("Jogar dado");self.roll_button.setObjectName("primary")
        self.roll_button.clicked.connect(self.roll_one);stage_l.addWidget(self.roll_button)
        self.manual_box=QWidget();manual_l=QHBoxLayout(self.manual_box);manual_l.setContentsMargins(0,0,0,0)
        self.manual_face=QSpinBox();self.manual_face.setRange(1,6);self.manual_face.setPrefix("Face: ")
        self.record_button=QPushButton("Registrar");self.record_button.clicked.connect(self.record)
        manual_l.addWidget(self.manual_face);manual_l.addWidget(self.record_button)
        self.manual_box.hide();stage_l.addWidget(self.manual_box)
        left.addWidget(stage)
        settings,settings_l=card();settings.setFixedWidth(310)
        settings_l.addWidget(label("02 / EXPERIMENTO","eyebrow"))
        self.face=QSpinBox();self.face.setRange(1,6);self.face.setPrefix("Face em foco: ")
        self.face.valueChanged.connect(self.reanalyze);settings_l.addWidget(self.face)
        self.batch=QSpinBox();self.batch.setRange(1,100000);self.batch.setValue(1000);self.batch.setPrefix("Lote: ")
        settings_l.addWidget(self.batch)
        self.batch_button=QPushButton("Simular lote");self.batch_button.clicked.connect(self.roll_batch);settings_l.addWidget(self.batch_button)
        self.new_button=QPushButton("Nova sessão");self.new_button.clicked.connect(self.new_session);settings_l.addWidget(self.new_button)
        settings_l.addWidget(label("Sessões virtual e física separadas. Até 100.000 lançamentos por sessão.","muted",True))
        left.addWidget(settings);left.addStretch();main.addLayout(left)
        right=QVBoxLayout();right.setSpacing(14)
        metrics=QHBoxLayout();metrics.setSpacing(10)
        self.metrics=[]
        for title in ["LANÇAMENTOS","CHANCE TEÓRICA","FREQ. DA FACE"]:
            metric,ml=card();ml.setContentsMargins(15,13,15,13)
            ml.addWidget(label(title,"eyebrow"));value=label("—","metric");ml.addWidget(value)
            self.metrics.append(value);metrics.addWidget(metric)
        right.addLayout(metrics)
        plot_card,plot_l=card();plot_l.setContentsMargins(10,12,10,8)
        self.charts=Charts();plot_l.addWidget(self.charts,1)
        plot_l.addWidget(label("Barras: frequência observada · hastes: IC individual de 95% · tracejado: dado justo","muted",True))
        right.addWidget(plot_card,1)
        actions=QHBoxLayout()
        for text,callback in [("Exportar CSV",self.export_csv),("Salvar gráficos",self.export_plot),("Salvar relatório",self.export_report)]:
            button=QPushButton(text);button.clicked.connect(callback);actions.addWidget(button)
        right.addLayout(actions);main.addLayout(right,1);page.addLayout(main)
        summary,summary_l=card();summary_l.addWidget(label("03 / LEITURA DOS RESULTADOS","eyebrow"))
        self.summary=label("Aguardando a análise…",None,True);self.summary.setTextFormat(Qt.TextFormat.PlainText)
        self.summary.setMinimumHeight(65);summary_l.addWidget(self.summary);page.addWidget(summary)
        self.report=QTextEdit();self.report.setReadOnly(True);self.stack.addWidget(self.report)
        help_text=QTextEdit();help_text.setReadOnly(True)
        help_text.setHtml("""<h1>Um laboratório para aprender com o acaso</h1>
        <h2>1. Escolha a origem</h2><p>O dado virtual usa um gerador C++ uniforme. No modo físico, lance seu próprio dado e registre a face superior. As sessões não se misturam.</p>
        <h2>2. Lance ou simule</h2><p>A animação representa o resultado previamente sorteado; não é uma simulação física certificada e não usa câmera. Lotes geram todos os resultados, mas só mostram o último dado, sem animar cada lançamento.</p>
        <h2>3. Compare com a teoria</h2><p>Para um dado justo e lançamentos independentes, P(face)=1/6=16,67%. Isso não muda porque uma face está atrasada. Frequência é o que foi observado na amostra.</p>
        <h2>4. Leia os intervalos</h2><p>O intervalo exato de Clopper–Pearson de 95% estima a proporção de uma face em repetições do procedimento. Os seis intervalos são individuais, não simultâneos; não representam 95% de chance de o próximo lançamento cair no intervalo.</p>
        <h2>5. Interprete o teste com cuidado</h2><p>O teste compara as seis contagens com uniformidade. Em amostras esparsas, usa Monte Carlo multinomial com 10.000 réplicas e semente fixa; nos demais casos usa a aproximação qui-quadrado. p &lt; 0,05 indica discrepância exploratória, não prova de trapaça. p alto não prova justiça. Repetir testes até encontrar significância aumenta falsos alarmes.</p>
        <h2>As três linguagens têm trabalho real</h2><p><b>C++:</b> geração pseudoaleatória e contagens. <b>Java:</b> auditoria, entropia, sequências, correlação e estatística de Pearson. <b>Python:</b> NumPy, pandas, SciPy, Matplotlib, interface e persistência SQLite.</p>
        <p>A média teórica é 3,5 e a variância teórica é 35/12. A variância amostral usa denominador n−1. Correlação e entropia são descritivas e não certificam independência.</p>
        <p>Os dados são salvos apenas neste computador. Não há telemetria, contas, acesso à câmera ou comunicação externa.</p>""")
        self.stack.addWidget(help_text)
        self.busy_controls=[self.mode_box,self.face,self.batch,self.roll_button,self.batch_button,self.record_button,self.new_button,self.animate,self.manual_face]

    def navigate(self,index):
        self.stack.setCurrentIndex(index)
        for i,button in enumerate(self.nav): button.setChecked(i==index)

    def set_busy(self,value):
        self.busy=value
        for control in self.busy_controls: control.setEnabled(not value)
        if not value:
            self.batch_button.setEnabled(self.mode=="virtual")
            self.batch.setEnabled(self.mode=="virtual")
            self.animate.setEnabled(self.mode=="virtual")
        self.status.setText("Calculando em Python + C++ + Java…" if value else "●  Motores conectados")

    def start(self,count=0,manual=None,animation=False):
        if self.busy: return
        if len(self.values)+count+len(manual or [])>MAX_ROLLS:
            QMessageBox.information(self,"Limite da sessão","A sessão comporta até 100.000 lançamentos. Inicie uma nova sessão.")
            return
        self.set_busy(True)
        self.pending=None
        worker=AnalysisWorker(self.native,self.values,self.face.value(),count,manual)
        self.worker=worker
        worker.ready.connect(lambda additions,values,result:self.analysis_ready(additions,values,result,animation))
        worker.error.connect(self.failed)
        # Keep the worker alive until finished, even if a queued result is already delivered.
        worker.finished.connect(lambda current=worker:self.worker_finished(current))
        worker.start()

    def worker_finished(self,current):
        if self.worker is current: self.worker=None
        current.deleteLater()

    def analysis_ready(self,additions,values,result,animation):
        try:
            if additions: self.store.append(self.session,additions)
            self.values,self.result=values,result
            self.pending=(values,result)
            if additions:
                self.last.setText(("Última face do lote: " if len(additions)>1 else "Resultado: ")+str(additions[-1]))
                self.die.roll(additions[-1],animate=animation and self.animate.isChecked() and self.mode=="virtual")
            else: self.animation_done(0)
        except Exception as exc: self.failed(str(exc))

    def animation_done(self,face):
        if self.pending is None: return
        values,result=self.pending;self.pending=None
        self.metrics[0].setText(f"{len(values):,}")
        self.metrics[1].setText("16,67%")
        self.metrics[2].setText(f"{result['selected_row']['frequencia']:.2%}" if values else "—")
        self.charts.refresh(values,result)
        self.summary.setText(conclusion(result,self.mode))
        self.report.setPlainText(report_text(result,self.mode))
        self.set_busy(False)

    def failed(self,message):
        self.pending=None;self.set_busy(False);self.status.setText("Falha na operação")
        QMessageBox.critical(self,"Não foi possível concluir",message)

    def reanalyze(self,*args): self.start()
    def roll_one(self): self.start(count=1,animation=True)
    def roll_batch(self): self.start(count=self.batch.value())
    def record(self): self.start(manual=[self.manual_face.value()])

    def change_mode(self,index):
        self.mode="virtual" if index==0 else "fisico"
        self.session,self.values=self.store.load(self.mode)
        self.roll_button.setVisible(index==0);self.manual_box.setVisible(index==1)
        self.last.setText("Pronto para o próximo lançamento")
        self.reanalyze()

    def new_session(self):
        if QMessageBox.question(self,"Nova sessão","Iniciar uma nova sessão desta origem? A anterior permanece arquivada no banco local.")!=QMessageBox.StandardButton.Yes: return
        self.session=self.store.new(self.mode);self.values=[];self.last.setText("Nova sessão iniciada");self.reanalyze()

    def export_csv(self):
        if self.busy or not self.result: return
        path,_=QFileDialog.getSaveFileName(self,"Exportar lançamentos","dadoslab-lancamentos.csv","CSV (*.csv)")
        if not path:return
        try:
            with open(path,"w",newline="",encoding="utf-8-sig") as output:
                writer=csv.writer(output);writer.writerow(["sessao","origem","lancamento","face"])
                writer.writerows((self.session,self.mode,i,face) for i,face in enumerate(self.values,1))
        except OSError as exc: self.failed(str(exc))

    def export_report(self):
        if self.busy or not self.result:return
        path,_=QFileDialog.getSaveFileName(self,"Salvar relatório","dadoslab-relatorio.txt","Texto (*.txt)")
        if path:
            try:Path(path).write_text(report_text(self.result,self.mode),encoding="utf-8")
            except OSError as exc:self.failed(str(exc))

    def export_plot(self):
        if self.busy or not self.result:return
        path,_=QFileDialog.getSaveFileName(self,"Salvar gráficos","dadoslab-graficos.png","PNG (*.png)")
        if path:
            try:self.charts.figure.savefig(path,dpi=180,facecolor=self.charts.figure.get_facecolor())
            except OSError as exc:self.failed(str(exc))

    def closeEvent(self,event):
        if self.busy or self.worker is not None:
            QMessageBox.information(self,"Análise em andamento","Aguarde a operação atual terminar antes de fechar.")
            event.ignore();return
        self.store.close();event.accept()


def main():
    app=QApplication(sys.argv)
    app.setApplicationName("DadosLab")
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    app.setFont(QFont("Segoe UI",10))
    try: window=Window()
    except Exception as exc:
        QMessageBox.critical(None,"DadosLab — inicialização",str(exc));return 1
    window.show()
    return app.exec()
