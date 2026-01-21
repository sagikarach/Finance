[Setup]
AppName=Finance
AppVersion=1.0.0
AppPublisher=Finance
DefaultDirName={pf}\Finance
DefaultGroupName=Finance
OutputDir=.\Output
OutputBaseFilename=Finance-Setup
Compression=lzma2
SolidCompression=yes

[Files]
Source: "..\dist\Finance\*"; DestDir: "{app}"; Flags: recursesubdirs

[Icons]
Name: "{group}\Finance"; Filename: "{app}\Finance.exe"
Name: "{commondesktop}\Finance"; Filename: "{app}\Finance.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\Finance.exe"; Description: "Launch Finance"; Flags: nowait postinstall skipifsilent

