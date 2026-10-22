#define AppVersion "1.1.1"
#ifndef AppSource
#define AppSource "..\..\dist\windows-v1.1.1\SpecCompare"
#endif
#ifndef InstallerOutput
#define InstallerOutput "..\..\dist\windows-v1.1.1"
#endif
[Setup]
AppId={{BD5BB7FE-819A-4EA7-B333-B74C963D6C2F}
AppName=SpecCompare
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\SpecCompare
DefaultGroupName=SpecCompare
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#InstallerOutput}
OutputBaseFilename=SpecCompare_Setup_v1.1.1
SetupIconFile=..\..\assets\icon.ico
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
[Files]
Source: "{#AppSource}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\SpecCompare"; Filename: "{app}\SpecCompare.exe"
Name: "{autodesktop}\SpecCompare"; Filename: "{app}\SpecCompare.exe"
[Run]
Filename: "{app}\SpecCompare.exe"; Description: "Launch SpecCompare"; Flags: nowait postinstall skipifsilent
