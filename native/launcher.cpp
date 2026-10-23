#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#include <windows.h>
#include <string>
#include <vector>

// A small native entry point. The Python/Qt and Java runtimes live beside it.
int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR, int) {
    std::vector<wchar_t> buffer(32768);
    DWORD length = GetModuleFileNameW(nullptr, buffer.data(), static_cast<DWORD>(buffer.size()));
    if (length == 0 || length >= buffer.size()) return 1;
    std::wstring root(buffer.data(), length);
    root = root.substr(0, root.find_last_of(L"\\/"));
    std::wstring python = root + L"\\runtime-python\\pythonw.exe";
    std::wstring command = L"\"" + python + L"\" \"" + root + L"\\app\\main.py\"";
    STARTUPINFOW startup{}; startup.cb = sizeof(startup);
    PROCESS_INFORMATION process{};
    if (!CreateProcessW(python.c_str(), command.data(), nullptr, nullptr, FALSE, 0,
                        nullptr, root.c_str(), &startup, &process)) {
        MessageBoxW(nullptr,L"Nao foi possivel iniciar. Extraia todo o ZIP antes de abrir DadosLab.exe.",
                    L"DadosLab",MB_OK | MB_ICONERROR);
        return 1;
    }
    CloseHandle(process.hThread);
    WaitForSingleObject(process.hProcess, INFINITE);
    DWORD code = 1; GetExitCodeProcess(process.hProcess, &code);
    CloseHandle(process.hProcess);
    if (code != 0) MessageBoxW(nullptr,L"O aplicativo encerrou com erro. Use Diagnosticar.cmd para ver os detalhes.",L"DadosLab",MB_OK|MB_ICONERROR);
    return static_cast<int>(code);
}
