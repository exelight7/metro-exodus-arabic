"""Arabic desktop installer. Local assets only; no telemetry or game execution."""
from __future__ import annotations
import argparse, html, math, os, random, sys
from pathlib import Path
from PySide6.QtCore import Qt, QObject, QThread, Signal, QTimer, QRectF, QPointF
from PySide6.QtGui import QColor,QPainter,QPen,QFont,QFontDatabase,QLinearGradient,QRadialGradient,QIcon,QPolygonF
from PySide6.QtWidgets import QApplication,QMainWindow,QWidget,QHBoxLayout,QVBoxLayout,QLabel,QPushButton,QLineEdit,QFileDialog,QFrame,QCheckBox,QProgressBar,QMessageBox,QBoxLayout
from core import Installer,InstallError,detect_games

BASE=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
ASSETS=Path(os.environ.get('METRO_AR_ASSETS',BASE/'assets'))
RESOURCES=Path(os.environ.get('METRO_AR_RESOURCES',BASE/'resources'))
FONT='Noto Sans Arabic'

class ArabicLabel(QLabel):
    def setText(self,text):super().setText('\n'.join('\u202b'+line+'\u202c' for line in text.split('\n')))

def label(text,size=14,color='#adb2ae',bold=False):
    w=ArabicLabel();w.setLayoutDirection(Qt.LeftToRight);w.setTextFormat(Qt.PlainText);w.setText(text);w.setAlignment(Qt.AlignRight|Qt.AlignAbsolute|Qt.AlignVCenter);w.setWordWrap(True);w.setStyleSheet(f'color:{color};font-size:{size}px;font-weight:{700 if bold else 400};background:transparent;');return w

class Hero(QWidget):
    def __init__(self):super().__init__();self.setMinimumWidth(365);self.setMaximumWidth(395)
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);w=self.width();h=self.height()
        g=QLinearGradient(0,0,w,h);g.setColorAt(0,QColor('#242b29'));g.setColorAt(1,QColor('#0a0f10'));p.fillRect(self.rect(),g)
        glow=QRadialGradient(w*.2,h*.76,w*.8);glow.setColorAt(0,QColor(182,85,21,40));glow.setColorAt(1,QColor(0,0,0,0));p.fillRect(self.rect(),glow)
        r=random.Random(73)
        for i in range(1700):
            p.setPen(QColor(225,225,196,r.randrange(4,20)));p.drawPoint(r.randrange(w),r.randrange(h))
        p.setPen(QPen(QColor(115,129,120,24),1))
        for x in range(0,w,28):p.drawLine(x,0,x,h)
        for y in range(0,h,28):p.drawLine(0,y,w,y)
        # Original rail/locomotive geometry, not game artwork.
        van=QPointF(w*.50,h*.63)
        p.setPen(QPen(QColor(147,148,121,65),2))
        for x in [-w*.30,w*.14,w*.84,w*1.30]:p.drawLine(van,QPointF(x,h))
        for i in range(1,12):
            t=(i/12)**1.7;y=van.y()+(h-van.y())*t;dx=w*.58*t
            p.drawLine(QPointF(van.x()-dx,y),QPointF(van.x()+dx,y))
        p.setPen(QPen(QColor('#50584f'),1));p.setBrush(QColor('#121b1a'))
        p.drawPolygon(QPolygonF([QPointF(w*.32,h*.64),QPointF(w*.35,h*.46),QPointF(w*.65,h*.46),QPointF(w*.68,h*.64)]))
        p.setBrush(QColor('#2c3833'));p.drawRoundedRect(QRectF(w*.39,h*.49,w*.22,h*.065),4,4)
        p.setPen(QPen(QColor('#778275'),2));p.drawLine(QPointF(w*.39,h*.56),QPointF(w*.61,h*.56))
        p.setBrush(QColor('#ffb866'));p.setPen(Qt.NoPen);p.drawEllipse(QPointF(w*.5,h*.595),3.5,3.5)
        p.setPen(QColor('#dddcd0'));f=QFont(FONT);f.setPixelSize(61);f.setWeight(QFont.Black);f.setStretch(80);p.setFont(f)
        p.drawText(QRectF(34,34,w-68,85),Qt.AlignHCenter|Qt.AlignVCenter,'METRO')
        f.setPixelSize(18);f.setLetterSpacing(QFont.AbsoluteSpacing,8);f.setWeight(QFont.Medium);p.setFont(f)
        p.setPen(QColor('#b5b9a9'));p.drawText(QRectF(37,112,w-70,40),Qt.AlignHCenter,'EXODUS')
        p.setPen(QColor('#f19036'));p.drawLine(36,174,w-36,174)
        f=QFont(FONT);f.setPixelSize(40);f.setWeight(QFont.Bold);p.setFont(f);p.setPen(QColor('#f2f1e8'))
        p.drawText(QRectF(30,205,w-60,90),Qt.AlignRight|Qt.AlignAbsolute|Qt.AlignVCenter,'رحلتك.')
        p.setPen(QColor('#ee8b32'));p.drawText(QRectF(30,275,w-60,85),Qt.AlignRight|Qt.AlignAbsolute|Qt.AlignVCenter,'بلغتك.')
        f.setPixelSize(15);f.setWeight(QFont.Normal);p.setFont(f);p.setPen(QColor('#b6b9ae'))
        p.drawText(QRectF(36,h-156,w-72,56),Qt.AlignRight|Qt.AlignAbsolute|Qt.TextWordWrap,'من أنفاق موسكو إلى الأفق.\nعش الرحلة بالعربية.')
        p.setBrush(QColor('#e68b36'));p.setPen(Qt.NoPen);p.drawRect(0,h-46,w,3)
        f.setPixelSize(11);f.setLetterSpacing(QFont.AbsoluteSpacing,1);p.setFont(f);p.setPen(QColor('#8c958b'))
        p.drawText(QRectF(36,h-32,w-72,24),Qt.AlignLeft,'WINDOWS  /  PROTON  ·  x86_64')
        p.end()

class Worker(QObject):
    progress=Signal(int,str);done=Signal(object);failed=Signal(str);state_after_failure=Signal(object);finished=Signal()
    def __init__(self,action,path,configure):super().__init__();self.action=action;self.path=path;self.configure=configure
    def run(self):
        engine=None;failure=False
        try:
            engine=Installer(RESOURCES,lambda n,t:self.progress.emit(n,t))
            if self.action=='install':r=engine.install(self.path,self.configure)
            elif self.action=='restore':r=engine.restore(self.path)
            elif self.action=='inspect':r=engine.inspect(self.path)
            else:r=engine.verify(self.path)
            self.done.emit(r)
        except PermissionError:failure=True;self.failed.emit('لا يمكن الكتابة في مجلد اللعبة. في Windows، شغل التطبيق كمسؤول عند التثبيت. لا حاجة لذلك لمعاينة الواجهة.')
        except InstallError as e:failure=True;self.failed.emit(str(e))
        except Exception as e:failure=True;self.failed.emit('تعذر إكمال العملية. راجع صلاحية الكتابة والمساحة، ثم أعد فحص المجلد.\n'+str(e))
        finally:
            if failure and engine and self.action in ('install','restore'):
                try:self.state_after_failure.emit(engine.inspect(self.path))
                except Exception:pass
            self.finished.emit()

class Window(QMainWindow):
    def __init__(self,review=False):
        super().__init__();self.review=review;self.busy=False;self.current_info=None;self.action=None
        self.setWindowTitle('Metro Exodus — مثبت التعريب');self.resize(1160,750);self.setMinimumSize(1080,720)
        if (ASSETS/'icon.png').exists():self.setWindowIcon(QIcon(str(ASSETS/'icon.png')))
        self.setStyleSheet('''
QMainWindow,QWidget {background:#111819;color:#edece3;font-family:"Noto Sans Arabic";font-size:14px;}
QPushButton {border:1px solid #46504b;border-radius:5px;background:#202a29;padding:10px 18px;color:#e6e7de;font-weight:600;min-height:26px;}
QPushButton:hover {background:#2c3935;border-color:#7d8b77;} QPushButton:pressed {background:#35473e;}
QPushButton:disabled {color:#65736b;border-color:#2b3933;background:#182321;}
QPushButton#primary {background:#ea8c35;color:#151b17;border:1px solid #f3ad62;font-weight:800;}
QPushButton#primary:hover {background:#ffac54;} QPushButton#primary:disabled {background:#674727;color:#a1947b;border-color:#6c543a;}
QPushButton#text {background:transparent;border:none;color:#c5c7b9;padding:4px 0;min-height:22px;font-weight:400;}
QPushButton#text:hover {color:#f4a455;}
QLineEdit {background:#0c1314;border:1px solid #46524b;border-radius:5px;padding:13px 12px;color:#e1e6da;font-family:"Segoe UI";font-size:13px;min-height:24px;}
QLineEdit:focus {border:1px solid #ea8c35;} QCheckBox {spacing:9px;color:#c0c6b9;font-size:13px;}
QCheckBox::indicator {width:18px;height:18px;border:1px solid #66735e;border-radius:3px;background:#17201d;}
QCheckBox::indicator:checked {background:#df8734;border:1px solid #efa75b;}
QProgressBar {border:0;background:#2b3730;border-radius:2px;height:4px;} QProgressBar::chunk {background:#ed953f;border-radius:2px;}
QFrame#card {background:#182321;border:1px solid #36473a;border-radius:6px;}
QLabel {background:transparent;} QMessageBox {background:#182321;} QToolTip {background:#242f28;color:#eee;}
''')
        root=QWidget();self.setCentralWidget(root);outer=QHBoxLayout(root);outer.setContentsMargins(0,0,0,0);outer.setSpacing(0);outer.setDirection(QBoxLayout.LeftToRight)
        outer.addWidget(Hero())
        panel=QWidget();outer.addWidget(panel,1);layout=QVBoxLayout(panel);layout.setContentsMargins(38,24,38,24);layout.setSpacing(9)
        top=QHBoxLayout();top.setDirection(QBoxLayout.LeftToRight)
        self.badge=label('معاينة التصميم' if review else 'مثبت التعريب',12,'#e8a45e',True);top.addWidget(self.badge);top.addStretch()
        info=QPushButton('معلومات الإصدار');info.setObjectName('text');info.clicked.connect(self.about);top.addWidget(info);layout.addLayout(top)
        step=QHBoxLayout();step.setDirection(QBoxLayout.LeftToRight)
        for i,text in enumerate(['اختيار اللعبة','التحقق','التثبيت']):
            step.addWidget(label(f'{i+1:02}  {text}',12,'#e5a15d' if i==0 else '#748378',i==0))
            if i<2:
                separator=QFrame();separator.setFrameShape(QFrame.HLine);separator.setStyleSheet('color:#38483c;');step.addWidget(separator)
        layout.addLayout(step);layout.addSpacing(9)
        layout.addWidget(label('هيئ رحلتك بالعربية.',29,'#f1f0e6',True))
        layout.addWidget(label('تثبيت واضح، ونسخة احتياطية تبقي طريق العودة مفتوحا.',14,'#acb7a7'))
        layout.addSpacing(7);layout.addWidget(label('مجلد اللعبة',14,'#d6dbcc',True))
        pathrow=QHBoxLayout();pathrow.setDirection(QBoxLayout.LeftToRight)
        self.path=QLineEdit();self.path.setLayoutDirection(Qt.LeftToRight);self.path.setAlignment(Qt.AlignLeft);self.path.setPlaceholderText('…/steamapps/common/Metro Exodus')
        self.path.editingFinished.connect(self.inspect);pathrow.addWidget(self.path,1)
        self.browse=QPushButton('استعراض');self.browse.clicked.connect(self.choose);pathrow.addWidget(self.browse);layout.addLayout(pathrow)
        layout.addWidget(label('اختر المجلد الذي يحتوي على MetroExodus.exe.',12,'#829584'))
        self.card=QFrame();self.card.setObjectName('card');self.card.setMinimumHeight(85);cl=QVBoxLayout(self.card);cl.setContentsMargins(18,10,18,10);cl.setSpacing(3)
        self.status_title=label('اختر مجلد اللعبة للبدء',16,'#e5e6d7',True);self.status_body=label('سنتحقق من الإصدار قبل إجراء أي تغيير.',12,'#9faf99')
        cl.addWidget(self.status_title);cl.addWidget(self.status_body);layout.addWidget(self.card)
        self.configure=QCheckBox('تفعيل التعريب في إعدادات لغة النصوص');self.configure.setChecked(True);layout.addWidget(self.configure)
        layout.addWidget(label('تحفظ الملفات الأصلية تلقائيا داخل مجلد اللعبة.',12,'#9dac98'))
        self.progress=QProgressBar();self.progress.setFixedHeight(5);self.progress.setRange(0,100);self.progress.setValue(0);self.progress.setTextVisible(False);layout.addWidget(self.progress)
        self.progress_text=label('جاهز لاختيار المجلد',12,'#bfc6b4');layout.addWidget(self.progress_text)
        layout.addStretch(1)
        row=QHBoxLayout();row.setDirection(QBoxLayout.LeftToRight)
        self.install_btn=QPushButton('تثبيت التعريب');self.install_btn.setObjectName('primary');self.install_btn.setMinimumHeight(36);self.install_btn.clicked.connect(lambda:self.request('install'));row.addWidget(self.install_btn,1)
        self.verify_btn=QPushButton('فحص الملفات');self.verify_btn.clicked.connect(lambda:self.request('verify'));row.addWidget(self.verify_btn);layout.addLayout(row)
        lower=QHBoxLayout();lower.setDirection(QBoxLayout.LeftToRight)
        self.restore_btn=QPushButton('استرجاع الأصل');self.restore_btn.setObjectName('text');self.restore_btn.clicked.connect(lambda:self.request('restore'));lower.addWidget(self.restore_btn);lower.addStretch()
        release=label('تعريب غير رسمي · إصدار تجريبي',11,'#788d7a');release.setWordWrap(False);lower.addWidget(release);layout.addLayout(lower)
        line=QFrame();line.setFrameShape(QFrame.HLine);line.setStyleSheet('color:#354334;');layout.addWidget(line)
        layout.addWidget(label('نسخة AppImage مخصصة للعبة Windows عبر Proton فقط. نسخة Linux الأصلية غير مدعومة.',12,'#a4b093'))
        for b in [self.install_btn,self.verify_btn,self.restore_btn]:b.setEnabled(False)
        games=detect_games()
        if games:self.path.setText(str(games[0]));QTimer.singleShot(100,self.inspect)
    def choose(self):
        p=QFileDialog.getExistingDirectory(self,'اختر مجلد Metro Exodus',self.path.text() or str(Path.home()))
        if p:self.path.setText(p);self.inspect()
    def inspect(self):
        if not self.busy and self.path.text().strip():self.start('inspect')
    def start(self,action):
        if self.busy:return
        self.busy=True;self.action=action;self.progress.setValue(0)
        for w in [self.install_btn,self.verify_btn,self.restore_btn,self.browse,self.path,self.configure]:w.setEnabled(False)
        self.thread=QThread();self.worker=Worker(action,Path(self.path.text().strip()),self.configure.isChecked());self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run);self.worker.progress.connect(self.on_progress);self.worker.done.connect(self.done);self.worker.failed.connect(self.failed)
        self.worker.state_after_failure.connect(self.recover_controls)
        self.worker.finished.connect(self.thread.quit);self.worker.finished.connect(self.worker.deleteLater);self.thread.finished.connect(self.thread.deleteLater);self.thread.finished.connect(self.idle)
        self.progress_text.setText('جار التحقق من الإصدار...' if action=='inspect' else 'جار تجهيز العملية...');self.thread.start()
    def idle(self):
        self.busy=False
        for w in [self.browse,self.path,self.configure]:w.setEnabled(True)
        ok=bool(self.current_info)
        self.install_btn.setEnabled(ok and self.current_info.get('status')!='recovery');self.verify_btn.setEnabled(ok)
        self.restore_btn.setEnabled(ok and (self.current_info.get('owned') or self.current_info.get('status')=='recovery'))
    def on_progress(self,n,text):self.progress.setValue(n);self.progress_text.setText(text)
    def recover_controls(self,info):self.current_info=info
    def done(self,result):
        if self.action in ('inspect','verify'):
            self.current_info=result;s=result['status']
            titles={'ready':'إصدار مدعوم — جاهز للتثبيت','installed':'التعريب موجود بالفعل','partial':'يمكن إكمال تثبيت التعريب','recovery':'توجد عملية سابقة غير مكتملة'}
            self.status_title.setText(titles[s]);self.status_body.setText('نسخة Windows المتوافقة. يمكنك التثبيت أو فحص الملفات.' if s=='ready' else 'يمكنك فحص سلامة التعريب أو إعادة تثبيته مع حفظ الأصل.' if s=='installed' else 'استخدم استرجاع الأصل للعودة إلى حالة آمنة.' if s=='recovery' else 'ستحفظ نسخة احتياطية قبل إكمال التثبيت.')
            self.progress_text.setText('اكتمل فحص الملفات بنجاح' if self.action=='verify' else 'تم التعرف على اللعبة')
        else:
            self.status_title.setText('تم تثبيت التعريب بنجاح' if self.action=='install' else 'استعيدت الملفات الأصلية')
            self.status_body.setText('اختر English للغة النصوص داخل اللعبة إذا لم تظهر العربية. إعداد الصوت لا يتغير.' if self.action=='install' else 'أعيدت الملفات الأصلية، وبقيت ملفات الحفظ كما هي.')
            self.current_info={'status':'installed' if self.action=='install' else 'ready','owned':self.action=='install'}
        self.card.setStyleSheet('QFrame#card {background:#19271f;border:1px solid #526b46;border-radius:6px;}')
    def failed(self,message):
        self.current_info=None;self.status_title.setText('تعذر إكمال التحقق' if self.action=='inspect' else 'لم تكتمل العملية');self.status_body.setText(message)
        self.card.setStyleSheet('QFrame#card {background:#2b211c;border:1px solid #91613c;border-radius:6px;}');self.progress_text.setText('راجع الرسالة أعلاه ثم أعد المحاولة')
    def request(self,action):
        if self.review:
            QMessageBox.information(self,'معاينة التصميم','هذه معاينة للتصميم. لم يجر التطبيق أي تغيير على ملفات اللعبة.');return
        if action in ('install','restore'):
            text='سيحفظ التطبيق نسخة من الملفات الأصلية، ثم يثبت التعريب. أغلق اللعبة قبل المتابعة.' if action=='install' else 'سيعيد التطبيق الملفات الأصلية من نسخته الاحتياطية. لن يحذف ملفات الحفظ.'
            box=QMessageBox(self);box.setWindowTitle('تثبيت التعريب' if action=='install' else 'استرجاع الأصل');box.setText(text)
            yes=box.addButton('تثبيت' if action=='install' else 'استرجاع',QMessageBox.AcceptRole);box.addButton('رجوع',QMessageBox.RejectRole);box.exec()
            if box.clickedButton()!=yes:return
        self.start(action)
    def about(self):
        QMessageBox.information(self,'معلومات الإصدار','Metro Exodus — التعريب العربي\nالمثبت: 0.1.0 للمراجعة · الحزمة: final_review_r1\n\nWindows: إصدار Steam المطابق لملفات التعريب.\nLinux وSteam Deck: نسخة Windows عبر Proton فقط.\nنسخة Linux الأصلية غير مدعومة.\n\nالنصوص قيد المراجعة. اسم المتحدث أبيض مؤقتا.\nالتعريب غير رسمي، ولا يشغل التطبيق اللعبة.\nالخط: Noto Sans Arabic — OFL 1.1.\nالواجهة: Qt / PySide6 — LGPL v3. التراخيص مرفقة.')
    def closeEvent(self,event):
        if self.busy:self.progress_text.setText('انتظر اكتمال العملية قبل إغلاق التطبيق.');event.ignore()
        else:event.accept()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--review',action='store_true');ap.add_argument('--screenshot');ap.add_argument('--empty',action='store_true');args=ap.parse_args()
    if args.screenshot:os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    app=QApplication(sys.argv[:1]);app.setLayoutDirection(Qt.RightToLeft)
    if (ASSETS/'NotoSansArabic.ttf').exists():QFontDatabase.addApplicationFont(str(ASSETS/'NotoSansArabic.ttf'))
    app.setFont(QFont(FONT,10));w=Window(args.review or bool(args.screenshot))
    if args.empty:
        # Screenshot of the clean initial state, without a fixture or game write.
        w.path.clear()
    w.show()
    if args.screenshot:
        def capture():
            if w.busy:QTimer.singleShot(100,capture);return
            Path(args.screenshot).parent.mkdir(parents=True,exist_ok=True);w.grab().save(args.screenshot);app.quit()
        QTimer.singleShot(400,capture)
    return app.exec()
if __name__=='__main__':sys.exit(main())
