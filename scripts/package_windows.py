"""Assemble an offline portable Windows x64 folder with a native EXE launcher.

Run on Windows for a native build, or pass a MinGW-w64 cross compiler on Linux.
Binary packages are downloaded from official Python/Azul servers and PyPI.
The result must be smoke-tested on Windows (Wine is supplementary only).
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import urllib.request
import zipfile

from build import ROOT,build,compiler_environment

PYTHON_VERSION="3.12.10"
AZUL_API=("https://api.azul.com/metadata/v1/zulu/packages/?java_version=17&os=windows&arch=x86&hw_bitness=64"
    "&archive_type=zip&java_package_type=jre&release_status=ga&availability_types=CA&latest=true")


def download(url,path):
    if not path.exists():
        with urllib.request.urlopen(url,timeout=120) as response,path.open("wb") as output:
            shutil.copyfileobj(response,output)
    return path


def package(compiler=None,offline_cache=None):
    cxx=build(compiler,windows=True)
    cache=Path(offline_cache or ROOT/"build"/"downloads");cache.mkdir(parents=True,exist_ok=True)
    target=ROOT/"dist"/"DadosLab"
    if target.exists():shutil.rmtree(target)
    app=target/"app";app.mkdir(parents=True)
    for directory in ["dadoslab","bin"]:
        shutil.copytree(ROOT/directory,app/directory,ignore=shutil.ignore_patterns("__pycache__","*.so"))
    shutil.copy2(ROOT/"main.py",app)
    shutil.copy2(ROOT/"README.md",target/"LEIA-ME.md")
    shutil.copytree(ROOT/"docs",target/"docs")
    python=target/"runtime-python";python.mkdir()
    archive=download(f"https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-amd64.zip",cache/"python-embed.zip")
    with zipfile.ZipFile(archive) as bundle:bundle.extractall(python)
    wheels=cache/"wheels";wheels.mkdir(exist_ok=True)
    subprocess.run([sys.executable,"-m","pip","download","--only-binary=:all:","--platform","win_amd64",
        "--python-version","312","--implementation","cp","--abi","cp312","--dest",str(wheels),"-r",str(ROOT/"requirements.txt")],check=True)
    site=python/"Lib"/"site-packages";site.mkdir(parents=True)
    for wheel in sorted(wheels.glob("*.whl")):
        with zipfile.ZipFile(wheel) as bundle:
            for name in bundle.namelist():
                if ".data/" in name:
                    # Wheels used here have no scripts needed by the application.
                    continue
                bundle.extract(name,site)
    (python/"python312._pth").write_text("python312.zip\n.\nLib/site-packages\n../app\nimport site\n",encoding="utf-8")
    metadata=cache/"java-metadata.json"
    if not metadata.exists():
        with urllib.request.urlopen(AZUL_API,timeout=60) as response:
            choices=json.load(response)
        chosen=next(p for p in choices if p["name"].endswith("win_x64.zip") and "-fx-" not in p["name"])
        metadata.write_text(json.dumps(chosen,indent=2),encoding="utf-8")
    chosen=json.loads(metadata.read_text())
    java_zip=download(chosen["download_url"],cache/"java-runtime.zip")
    temp=cache/"java-expanded"
    if temp.exists():shutil.rmtree(temp)
    with zipfile.ZipFile(java_zip) as bundle:bundle.extractall(temp)
    shutil.copytree(next(p for p in temp.iterdir() if p.is_dir()),target/"app"/"runtime-java")
    subprocess.run([cxx,"-std=c++20","-O2","-Wall","-Wextra","-Werror","-municode","-mwindows","-static",
        str(ROOT/"native"/"launcher.cpp"),"-o",str(target/"DadosLab.exe")],check=True,env=compiler_environment(cxx))
    (target/"Diagnosticar.cmd").write_bytes(b'@echo off\r\ncd /d "%~dp0"\r\n"runtime-python\\python.exe" "app\\main.py"\r\npause\r\n')
    (target/"TERCEIROS.txt").write_text("DadosLab inclui Python (PSF), Qt/PySide/Shiboken (LGPL/GPL/comercial), NumPy, pandas, SciPy, Matplotlib e dependências com suas licenças originais nas pastas de pacotes e metadados *.dist-info. Java Zulu OpenJDK: GPLv2 com Classpath Exception; veja app/runtime-java/legal e LICENSE/DISCLAIMER. As bibliotecas permanecem substituíveis. Fontes e termos: https://www.python.org/ https://code.qt.io/pyside/pyside-setup.git/ https://github.com/numpy/numpy https://github.com/pandas-dev/pandas https://github.com/scipy/scipy https://github.com/matplotlib/matplotlib https://www.azul.com/downloads/?package=jre\n",encoding="utf-8")
    hashes={str(p.relative_to(cache)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [archive,java_zip,*sorted(wheels.glob("*.whl"))]}
    (target/"docs"/"DEPENDENCIAS-BINARIAS.json").write_text(json.dumps({"python":PYTHON_VERSION,"java":chosen,"sha256":hashes},indent=2),encoding="utf-8")
    print("Pacote montado em",target)
    return target


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--compiler");parser.add_argument("--cache")
    args=parser.parse_args();package(args.compiler,args.cache)
