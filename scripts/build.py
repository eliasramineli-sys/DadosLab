"""Build the C++ C ABI library and Java 17 class, without CMake or a server."""
from pathlib import Path
import argparse
import os
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parent.parent


def compiler_environment(cxx):
    # GCC's helper executables must also find the DLLs in its bin directory.
    environment=os.environ.copy()
    environment["PATH"]=str(Path(cxx).resolve().parent)+os.pathsep+environment.get("PATH","")
    return environment


def build(compiler=None, windows=None):
    windows=sys.platform=="win32" if windows is None else windows
    candidates=[compiler,os.environ.get("CXX"),shutil.which("g++")]
    if windows:candidates += ["C:/msys64/ucrt64/bin/g++.exe"]
    cxx=next((str(c) for c in candidates if c and Path(c).is_file()),None)
    if not cxx:raise RuntimeError("G++ não encontrado. Instale o GCC do MSYS2 UCRT64 e use --compiler se necessário.")
    java=shutil.which("java")
    if not java:raise RuntimeError("Instale um JDK 17+ e disponibilize java no PATH.")
    output=ROOT/"bin";output.mkdir(exist_ok=True)
    filename="dice.dll" if windows else "libdice.so"
    command=[cxx,"-std=c++20","-O2","-Wall","-Wextra","-Werror","-shared"]
    command+= ["-static"] if windows else ["-fPIC","-pthread"]
    command += [str(ROOT/"native"/"dice.cpp"),"-o",str(output/filename)]
    subprocess.run(command,check=True,env=compiler_environment(cxx))
    classes=output/"java";classes.mkdir(exist_ok=True)
    subprocess.run([java,"-m","jdk.compiler/com.sun.tools.javac.Main","--release","17","-encoding","UTF-8",
        "-d",str(classes),str(ROOT/"java"/"SequenceAudit.java")],check=True)
    print("Motores C++ e Java compilados:",output)
    return cxx


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--compiler");parser.add_argument("--windows",action="store_true")
    args=parser.parse_args()
    build(args.compiler,True if args.windows else None)
