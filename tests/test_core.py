import json
import math
import subprocess
import numpy as np
import pytest
from scipy import stats
from dadoslab.bridge import NativeDice, audit, validate, ROOT
from dadoslab.analysis import analyze, conclusion, report_text
from dadoslab.storage import Store


@pytest.fixture(scope="module")
def native():return NativeDice()


@pytest.mark.parametrize("values",[[],[1],[6]*30,list(range(1,7))*20,[1,2,2,3,6]])
def test_counts_across_three_languages(native,values):
    expected=[values.count(face) for face in range(1,7)]
    assert native.counts(values)==expected
    assert audit(values)["counts"]==expected
    assert np.bincount(np.asarray(values,dtype=int),minlength=7)[1:].tolist()==expected


def test_cpp_boundary_validation(native):
    import ctypes
    values=(ctypes.c_uint32*1)(7)
    counts=(ctypes.c_uint64*6)()
    assert native.lib.dice_counts(values,1,counts)==-1
    assert native.lib.dice_roll(values,100001)==-1


@pytest.mark.parametrize("value",[0,-1,100001,1.5,True])
def test_invalid_roll_size(native,value):
    with pytest.raises(ValueError):native.roll(value)


@pytest.mark.parametrize("values",[[0],[7],[1.0],[True],["2"]])
def test_invalid_observations(values):
    with pytest.raises(ValueError):validate(values)


def test_random_generation_invariants(native):
    # No stochastic p-value threshold: RNG tests should not fail on valid rare draws.
    values=native.roll(100000)
    assert len(values)==100000
    assert min(values)>=1 and max(values)<=6
    assert sum(native.counts(values))==100000


def test_balanced_reference(native):
    result=analyze(list(range(1,7))*100,3,native)
    assert result["pvalue"]==1
    assert result["java"]["chi2"]==0
    assert result["mean"]==3.5
    assert result["variance"]==pytest.approx(np.var(list(range(1,7))*100,ddof=1))
    assert result["java"]["entropy"]==pytest.approx(math.log2(6))
    assert result["java"]["lag1"]==pytest.approx(np.corrcoef((list(range(1,7))*100)[:-1],(list(range(1,7))*100)[1:])[0,1])
    assert "não prova" in conclusion(result,"fisico")


def test_sparse_monte_carlo_and_exact_interval(native):
    result=analyze([6]*20,6,native)
    assert result["method"].startswith("Monte Carlo")
    assert result["pvalue"] < .01
    expected=stats.binomtest(20,20,1/6).proportion_ci(method="exact")
    assert result["selected_row"]["ic95_inferior"]==pytest.approx(expected.low)
    assert result["java"]["longest_run"]==20
    assert result["java"]["lag1"] is None
    assert result["java"]["entropy"]==0


def test_empty_and_singleton(native):
    empty=analyze([],1,native)
    assert empty["pvalue"] is None and empty["mean"] is None
    one=analyze([3],3,native)
    assert one["variance"] is None and one["pvalue"]==1
    assert "não prevê" in report_text(one,"virtual")


def test_java_rejects_invalid_face():
    response=subprocess.run(["java","-cp",str(ROOT/"bin"/"java"),"SequenceAudit"],input="9\n",text=True,capture_output=True)
    assert response.returncode==2


def test_database_atomic_append_separate_sessions_and_reopen(tmp_path):
    path=tmp_path/"data.sqlite3"
    db=Store(path)
    virtual,values=db.load("virtual");assert values==[]
    db.append(virtual,[1,6,2])
    physical,values=db.load("fisico");assert values==[] and virtual!=physical
    db.append(physical,[5])
    with pytest.raises(ValueError):db.append(virtual,[2,7])
    assert db.load("virtual")== (virtual,[1,6,2])
    db.close()
    db=Store(path)
    assert db.load("fisico")== (physical,[5])
    new=db.new("virtual");assert db.load("virtual")== (new,[])
    assert db.connection.execute("SELECT COUNT(*) FROM rolls WHERE session=?",(virtual,)).fetchone()[0]==3
    db.close()
