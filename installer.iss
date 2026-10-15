; Inno Setup 6 script  ->  installer\ERP_Setup.exe  (single file for customers)
[Setup]
AppName=ERP Project Management
AppVersion=2.3
DefaultDirName={localappdata}\Programs\ERP Project Management
DefaultGroupName=ERP Project Management
PrivilegesRequired=lowest
OutputDir=installer
OutputBaseFilename=ERP_Setup
SetupIconFile=icons\app.ico
UninstallDisplayIcon={app}\ERP.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "dist\ERP\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion createallsubdirs

[Icons]
Name: "{group}\ERP Project Management"; Filename: "{app}\ERP.exe"
Name: "{autodesktop}\ERP Project Management"; Filename: "{app}\ERP.exe"

[Run]
Filename: "{app}\ERP.exe"; Description: "Launch ERP"; Flags: nowait postinstall skipifsilent
