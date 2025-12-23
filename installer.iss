; Inno Setup Script for PDF Harvester
; Created by ONUR THE CELEBI Solutions

#define MyAppName "PDF Harvester"
#define MyAppVersion "1.0"
#define MyAppPublisher "ONUR THE CELEBI Solutions"
#define MyAppExeName "PDFHarvester_OnurTheCelebi.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppCopyright=Copyright (C) 2025 ONUR THE CELEBI Solutions
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=installer_output
OutputBaseFilename=PDFHarvester_Setup_OnurTheCelebi
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=
LicenseFile=
; Show publisher name prominently
AppPublisherURL=https://onurthecelebi.com
AppSupportURL=https://onurthecelebi.com
AppUpdatesURL=https://onurthecelebi.com

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
WelcomeLabel1=Welcome to PDF Harvester Setup
WelcomeLabel2=Created by ONUR THE CELEBI Solutions%n%nThis will install PDF Harvester on your computer.%n%nIt is recommended that you close all other applications before continuing.
FinishedHeadingLabel=PDF Harvester Installation Complete
FinishedLabel=PDF Harvester has been installed on your computer.%n%nThank you for using software by ONUR THE CELEBI Solutions!

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\PDFHarvester_OnurTheCelebi.exe"; DestDir: "{app}"; Flags: ignoreversion
; Add Playwright browsers - user must install separately or bundle them

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
procedure InitializeWizard;
begin
  WizardForm.WelcomeLabel1.Caption := 'PDF Harvester';
  WizardForm.WelcomeLabel2.Caption := 'Created by ONUR THE CELEBI Solutions' + #13#10 + #13#10 +
    'This wizard will guide you through the installation of PDF Harvester.' + #13#10 + #13#10 +
    'PDF Harvester is a powerful browser automation tool for downloading PDF reports from financial institutions.' + #13#10 + #13#10 +
    'Click Next to continue.';
end;
