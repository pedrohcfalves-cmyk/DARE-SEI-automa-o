; Instalador do DARE Automação (Inno Setup 6.3 ou superior).
; Gerado por construir_aplicativo.bat. Para compilar à mão:
;   ISCC.exe /DVersao=3.0.0 empacotamento\instalador.iss
;
; - Instala SEM precisar de administrador, na pasta do usuário (%LOCALAPPDATA%\Programs).
; - Leva tudo o que o programa precisa: o computador NÃO precisa ter Python.
; - Ao atualizar, mantém os dados do usuário (PDFs, histórico e logs ficam em Documentos).

#ifndef Versao
  #define Versao "3.0.0"
#endif
#define Nome "DARE Automação"
#define Exe "DARE Automacao.exe"

[Setup]
AppId={{8C5D2F4A-6B1E-4E0B-9C3A-DA7E0A11C0DE}
AppName={#Nome}
AppVersion={#Versao}
AppVerName={#Nome} {#Versao}
AppPublisher={#Nome}
VersionInfoVersion={#Versao}
VersionInfoDescription=Instalador do {#Nome}
DefaultDirName={localappdata}\Programs\DARE Automacao
DefaultGroupName={#Nome}
DisableProgramGroupPage=yes
DisableDirPage=auto
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist\instalador
OutputBaseFilename=DARE_Automacao_Instalador_{#Versao}
SetupIconFile=..\dare_auto\gui\recursos\icone.ico
UninstallDisplayIcon={app}\{#Exe}
UninstallDisplayName={#Nome} {#Versao}
LicenseFile=..\LICENCA.txt
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "ptbr"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "atalho"; Description: "Criar atalho na Área de Trabalho"; GroupDescription: "Atalhos:"

[InstallDelete]
; Remove as bibliotecas da versão anterior antes de copiar as novas (atualização limpa)
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "..\dist\DARE Automacao\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#Nome}"; Filename: "{app}\{#Exe}"
Name: "{autoprograms}\Diagnóstico do {#Nome}"; Filename: "{app}\{#Exe}"; Parameters: "--diagnostico"
Name: "{autodesktop}\{#Nome}"; Filename: "{app}\{#Exe}"; Tasks: atalho

[Run]
Filename: "{app}\{#Exe}"; Description: "Abrir o {#Nome} agora"; Flags: nowait postinstall skipifsilent

[Code]
function NavegadorInstalado(): Boolean;
begin
  Result :=
    FileExists(ExpandConstant('{commonpf32}\Google\Chrome\Application\chrome.exe')) or
    FileExists(ExpandConstant('{commonpf64}\Google\Chrome\Application\chrome.exe')) or
    FileExists(ExpandConstant('{localappdata}\Google\Chrome\Application\chrome.exe')) or
    FileExists(ExpandConstant('{commonpf32}\Microsoft\Edge\Application\msedge.exe')) or
    FileExists(ExpandConstant('{commonpf64}\Microsoft\Edge\Application\msedge.exe'));
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Codigo: Integer;
begin
  if (CurStep = ssPostInstall) and (not NavegadorInstalado()) and (not WizardSilent()) then
    if MsgBox('O DARE Automação usa o Google Chrome (ou o Microsoft Edge), e nenhum dos dois foi ' +
              'encontrado neste computador.' + #13#10#13#10 +
              'Deseja abrir a página de download do Google Chrome agora?',
              mbConfirmation, MB_YESNO) = IDYES then
      ShellExec('open', 'https://www.google.com/chrome/', '', '', SW_SHOWNORMAL, ewNoWait, Codigo);
end;
