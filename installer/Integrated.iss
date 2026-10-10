#define MyAppName "Integrated"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Integrated"
#define MyAppExeName "Integrated.exe"

[Setup]
AppId={{B79F3103-946C-4FC7-8CE0-2E38BF343317}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Integrated
DefaultGroupName=Integrated
OutputDir=..\dist
OutputBaseFilename=Integrated-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#MyAppExeName}

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked

[Files]
Source: "..\dist\Integrated\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Integrated"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Integrated"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir Integrated"; Flags: postinstall nowait skipifsilent
