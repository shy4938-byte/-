#define MyAppName "SpecCompare"
#define MyAppVersion "1.0.0"
[Setup]
AppId={{A589BB21-6E47-45D0-8487-482A0B382D15}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\SpecCompare
DefaultGroupName=SpecCompare
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist
OutputBaseFilename=SpecCompare_Setup
SetupIconFile=..\assets\icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupArchitecture=x64
[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
[Files]
Source: "..\dist\SpecCompare\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\SpecCompare"; Filename: "{app}\SpecCompare.exe"
Name: "{autodesktop}\SpecCompare"; Filename: "{app}\SpecCompare.exe"
[Run]
Filename: "{app}\SpecCompare.exe"; Description: "Launch SpecCompare"; Flags: nowait postinstall skipifsilent
