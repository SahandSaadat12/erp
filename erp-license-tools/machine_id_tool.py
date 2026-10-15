#!/usr/bin/env python3
"""
Customer-side Machine ID utility (standalone; no private key, no network,
no persistence).  READ-ONLY: it only reads MachineGuid / BIOS / baseboard /
system-volume info, hashes them, shows the result and can copy it to the
clipboard.  Never writes the registry, never installs anything.

Build (optional):  pyinstaller --onefile --windowed machine_id_tool.py
"""

import hashlib
import os
import re
import subprocess
import sys

SLOTS = ("machine_guid", "bios_uuid", "baseboard_serial", "bios_serial", "system_volume_serial")
_JUNK = {
    "", "NONE", "NULL", "N/A", "NA", "UNKNOWN", "DEFAULT STRING",
    "TO BE FILLED BY O.E.M.", "TO BE FILLED BY OEM", "NOT SPECIFIED",
    "NOT APPLICABLE", "SYSTEM SERIAL NUMBER", "SYSTEM PRODUCT NAME",
    "BASE BOARD SERIAL NUMBER", "O.E.M.", "OEM", "SERIAL NUMBER",
    "123456789", "1234567890", "0", "000000000", "INVALID",
}


class MachineIdError(RuntimeError):
    pass


def normalize(value):
    if value is None:
        return ""
    text = re.sub(r"\s+", " ", str(value)).strip().strip("{}").strip().upper()
    if text in _JUNK:
        return ""
    if re.fullmatch(r"[0\-]+", text) or re.fullmatch(r"[F\-]+", text):
        return ""
    return text


def compute_machine_id(identifiers):
    values = {s: normalize(identifiers.get(s)) for s in SLOTS}
    if not values["machine_guid"]:
        raise MachineIdError("MachineGuid is not available")
    if sum(1 for v in values.values() if v) < 2:
        raise MachineIdError("not enough hardware identifiers available")
    blob = "ERP-MACHINE-ID-V1\n" + "\n".join(f"{s}={values[s]}" for s in SLOTS)
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest().upper()[:32]
    return "M1-" + "-".join(digest[i:i + 4] for i in range(0, 32, 4))


def _run(args, timeout=20):
    out = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=False)
    return out.stdout or ""


_PS = ("$ErrorActionPreference='SilentlyContinue';"
       "'uuid='+(Get-CimInstance Win32_ComputerSystemProduct).UUID;"
       "'board='+(Get-CimInstance Win32_BaseBoard).SerialNumber;"
       "'bios='+(Get-CimInstance Win32_BIOS).SerialNumber")


def _wmi_values():
    result = {}
    for _ in range(2):
        try:
            text = _run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _PS])
        except Exception:
            text = ""
        for line in text.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                result[k.strip()] = v.strip()
        if result.get("uuid") or result.get("board") or result.get("bios"):
            return result
    try:
        for key, cmd in (("uuid", "csproduct get uuid"), ("board", "baseboard get serialnumber"),
                         ("bios", "bios get serialnumber")):
            for line in _run(["wmic"] + cmd.split() + ["/value"]).splitlines():
                if "=" in line:
                    result[key] = line.split("=", 1)[1].strip()
    except Exception:
        pass
    return result


def collect_identifiers():
    if not sys.platform.startswith("win"):
        raise MachineIdError("Machine ID is only supported on Windows")
    import ctypes
    import winreg
    ids = {}
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0,
                            winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
            ids["machine_guid"] = winreg.QueryValueEx(key, "MachineGuid")[0]
    except Exception as error:
        raise MachineIdError(f"cannot read MachineGuid: {error}")
    wmi = _wmi_values()
    ids["bios_uuid"], ids["baseboard_serial"], ids["bios_serial"] = (
        wmi.get("uuid", ""), wmi.get("board", ""), wmi.get("bios", ""))
    try:
        root = os.environ.get("SystemDrive", "C:").rstrip("\\") + "\\"
        serial = ctypes.c_uint32(0)
        ok = ctypes.windll.kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(root), None, 0, ctypes.byref(serial), None, None, None, 0)
        ids["system_volume_serial"] = f"{serial.value:08X}" if ok else ""
    except Exception:
        ids["system_volume_serial"] = ""
    return ids


def get_machine_id():
    return compute_machine_id(collect_identifiers())


def main():
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.title("شناسه دستگاه (Machine ID)")
    root.geometry("520x210")
    root.resizable(False, False)
    try:
        machine_id = get_machine_id()
        error = ""
    except Exception as exc:
        machine_id, error = "", str(exc)

    tk.Label(root, text="شناسه دستگاه شما:", font=("Tahoma", 12)).pack(pady=(18, 6))
    var = tk.StringVar(value=machine_id or "—")
    entry = tk.Entry(root, textvariable=var, font=("Consolas", 14), justify="center",
                     state="readonly", width=44)
    entry.pack(pady=6)
    if error:
        tk.Label(root, text=error, fg="red", wraplength=480).pack()

    def copy():
        if machine_id:
            root.clipboard_clear()
            root.clipboard_append(machine_id)
            root.update()
            messagebox.showinfo("کپی شد", "شناسه دستگاه در کلیپ‌بورد کپی شد.")

    tk.Button(root, text="کپی", width=14, command=copy,
              state="normal" if machine_id else "disabled").pack(pady=14)
    tk.Label(root, text="این شناسه را برای دریافت لایسنس ارسال کنید.", font=("Tahoma", 10)).pack()
    root.mainloop()


if __name__ == "__main__":
    main()
