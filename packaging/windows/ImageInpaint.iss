#define AppName "Image Inpaint"
#ifndef AppVersion
#define AppVersion "0.1.0"
#endif
#ifndef SourceDir
#define SourceDir "..\..\dist\ImageInpaint"
#endif
#ifndef OutputDir
#define OutputDir "..\..\release"
#endif
#define AppExeName "ImageInpaint.exe"
#define AppSmokeExeName "ImageInpaintSmoke.exe"

[Setup]
AppId={{8A0B74AD-853C-4B49-B789-0A49F07E7A58}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Image Inpaint contributors
AppPublisherURL=https://github.com/jackbook-open/image-inpaint
AppSupportURL=https://github.com/jackbook-open/image-inpaint/issues
AppUpdatesURL=https://github.com/jackbook-open/image-inpaint/releases
DefaultDirName={localappdata}\ImageInpaint\app
DefaultGroupName=Image Inpaint
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#OutputDir}
OutputBaseFilename=ImageInpaint-Setup-x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExeName}
SetupLogging=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: checkedonce

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Image Inpaint"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\Image Inpaint"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch Image Inpaint"; Flags: nowait postinstall skipifsilent unchecked
