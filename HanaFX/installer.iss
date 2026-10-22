#define AppVersion "1.0.0"
#ifndef AppSource
#define AppSource "dist\windows-v1.0.0\HanaFX"
#endif
#ifndef InstallerOutput
#define InstallerOutput "dist\windows-v1.0.0"
#endif
[Setup]
AppId={{DEAC245F-4F33-4795-86AA-65AE085AD3C2}
AppName=HanaFX
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\HanaFX
DefaultGroupName=HanaFX
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#InstallerOutput}
OutputBaseFilename=HanaFX_Setup_v1.0.0
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
[Files]
Source: "{#AppSource}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\HanaFX"; Filename: "{app}\HanaFX.exe"
Name: "{autodesktop}\HanaFX"; Filename: "{app}\HanaFX.exe"
[Run]
Filename: "{app}\HanaFX.exe"; Description: "HanaFX"; Flags: nowait postinstall skipifsilent
