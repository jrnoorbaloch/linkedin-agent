# PyInstaller spec for the LinkedIn Agent desktop app.
#   pyinstaller packaging/linkedin-agent.spec --noconfirm
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

ROOT = Path(SPECPATH).parent
icon = str(ROOT / "packaging" / "assets" / ("icon.ico" if sys.platform == "win32" else "icon.png"))
hidden = collect_submodules("linkedin_agent") + collect_submodules("uvicorn") + collect_submodules("apscheduler") + ["webview"]
datas = [(str(ROOT / "linkedin_agent" / "static"), "linkedin_agent/static")] + collect_data_files("reportlab") + collect_data_files("docx")

a = Analysis([str(ROOT / "packaging" / "launch.py")], pathex=[str(ROOT)], datas=datas, hiddenimports=hidden, noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="LinkedIn Agent", console=False, icon=icon)
coll = COLLECT(exe, a.binaries, a.datas, name="LinkedIn Agent")
if sys.platform == "darwin":
    app = BUNDLE(coll, name="LinkedIn Agent.app", icon=str(ROOT / "packaging" / "assets" / "icon.png"),
                 bundle_identifier="io.github.jrnoorbaloch.linkedinagent",
                 info_plist={"CFBundleShortVersionString": "2.0.0", "NSHighResolutionCapable": True})
