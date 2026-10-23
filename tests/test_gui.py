import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
import time
import numpy as np
import pytest
from PySide6.QtWidgets import QApplication, QFileDialog
from dadoslab.gui import Window,STYLE
from dadoslab.die_widget import NORMALS,face_orientation
from dadoslab.storage import Store


@pytest.fixture(scope="module")
def app():
    app=QApplication.instance() or QApplication([])
    app.setStyleSheet(STYLE)
    yield app


def idle(app,window):
    app.processEvents()
    end=time.monotonic()+30
    while window.busy or window.worker is not None:
        app.processEvents();time.sleep(.01)
        if time.monotonic()>end:pytest.fail("GUI did not become idle")
    app.processEvents()


@pytest.mark.parametrize("face",range(1,7))
def test_face_orientation_matches_result(face):
    visible={key:(face_orientation(face)@normal)[2] for key,normal in NORMALS.items()}
    assert max(visible,key=visible.get)==face


def test_gui_roll_animation_batch_physical_persistence_and_exports(app,tmp_path,monkeypatch):
    window=Window(Store(tmp_path/"session.sqlite3"));window.show();idle(app,window)
    assert window.result["n"]==0
    window.roll_one();idle(app,window)
    assert window.result["n"]==1
    assert window.die.running is False
    assert int(window.last.text().split()[-1])==window.values[-1]
    window.batch.setValue(120)
    window.roll_batch();idle(app,window)
    assert len(window.values)==121
    window.face.setValue(6);idle(app,window)
    assert window.result["selected"]==6
    for method,name in [("export_csv","rolls.csv"),("export_plot","plot.png"),("export_report","report.txt")]:
        target=tmp_path/name
        monkeypatch.setattr(QFileDialog,"getSaveFileName",lambda *a,path=str(target),**kw:(path,""))
        getattr(window,method)()
        assert target.stat().st_size>100
    window.mode_box.setCurrentIndex(1);idle(app,window)
    assert window.result["n"]==0
    assert not window.batch_button.isEnabled()
    window.manual_face.setValue(4);window.record();idle(app,window)
    assert window.values==[4]
    window.mode_box.setCurrentIndex(0);idle(app,window)
    assert len(window.values)==121
    window.close()
