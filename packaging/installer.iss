; Inno Setup script — builds "LinkedIn-Agent-Setup.exe" on the Windows release runner.
#define AppVersion GetEnv("APP_VERSION")
[Setup]
AppId={{6E1A3C4B-9B1E-4E55-A2F7-3B5BFD000002}
AppName=LinkedIn Agent
AppVersion={#AppVersion}
AppPublisher=jrnoorbaloch
AppPublisherURL=https://jrnoorbaloch.github.io/linkedin-agent/
DefaultDirName={autopf}\LinkedIn Agent
DefaultGroupName=LinkedIn Agent
OutputDir=..\dist
OutputBaseFilename=LinkedIn-Agent-Setup
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\LinkedIn Agent.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Files]
Source: "..\dist\LinkedIn Agent\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\LinkedIn Agent"; Filename: "{app}\LinkedIn Agent.exe"
Name: "{autodesktop}\LinkedIn Agent"; Filename: "{app}\LinkedIn Agent.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Run]
Filename: "{app}\LinkedIn Agent.exe"; Description: "Launch LinkedIn Agent"; Flags: nowait postinstall skipifsilent
