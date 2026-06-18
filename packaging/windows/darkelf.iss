; Inno Setup script for Darkelf Shadow (Windows installer)
; Compile from repo root:
;   iscc /DMyAppVersion=1.2.3 packaging\windows\darkelf.iss
; Expects the PyInstaller one-dir bundle at dist\DarkelfShadow\

#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif

#define MyAppName "Darkelf Shadow"
#define MyAppPublisher "Darkelf Project"
#define MyAppExeName "DarkelfShadow.exe"

; Inno resolves relative paths against THIS script's directory, not the CWD.
; Anchor everything to the repo root (two levels up from packaging/windows).
#define ROOT SourcePath + "..\.."

[Setup]
AppId={{8E2F6A4C-1D3B-4E9A-9C77-DA2KELF5HADOW}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\DarkelfShadow
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir={#ROOT}\dist\installer
OutputBaseFilename=DarkelfShadow-Setup-{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
WizardStyle=modern
SetupIconFile={#ROOT}\app\frontend\assets\darkelf-mark.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#ROOT}\dist\DarkelfShadow\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
