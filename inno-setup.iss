; Inno Setup Script for generating Windows Installer of Local Console.

#define MyAppName "Local Console"
#define MyAppPublisher "Sony Semiconductor Solutions Corporation"
#define MyAppExeName "local-console.exe"
#define MyAppAssocName MyAppName + " File"
#define MyAppAssocExt ".myp"
#define MyAppCanonical StringChange(MyAppName, " ", "")
#define MyAppAssocKey MyAppCanonical + MyAppAssocExt
; Define the path to the version file
#define FileHandle = FileOpen("VERSION")
#define VersionString = FileRead(FileHandle)
#if FileHandle
  #expr FileClose(FileHandle)
#endif
; Python Wheel of local-console follows a structured naming
#define WheelFile "local_console-" + VersionString + "-py3-none-any.whl"

[Setup]
AppId={{63A38119-1103-4ED1-AD9B-0D873FB090B5}}
AppName={#MyAppName}
AppVersion={#VersionString}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppCanonical}
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
OutputBaseFilename=local-console-setup-{#VersionString}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
AlwaysRestart=no
ArchitecturesInstallIn64BitMode=x64
SetupIconFile=local-console\windows\installer.ico
UninstallDisplayIcon=local-console\windows\installer.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "{#WheelFile}"; Flags: dontcopy;
Source: "local-console\windows\*"; Flags: recursesubdirs dontcopy;
Source: "local-console-ui\dist\win-unpacked\*"; DestDir: "{app}\UI"; Flags: recursesubdirs;

[UninstallDelete]
Type: files; Name: "{userdesktop}\Local Console.lnk"
Type: filesandordirs; Name: "{app}"
Type: filesandordirs; Name: "{userappdata}\local-console"

[Code]
var
  InstallationSucceeded: Boolean;

function RunThenCheckIfFailed(Command: string): Integer;
var
  ResultCode: Integer;
 begin
    Exec('powershell.exe', Command, '', SW_SHOW, ewWaitUntilTerminated, ResultCode);
    //if not (ResultCode = 0) then
    //begin
    //  MsgBox('Command failed with exit code ' + IntToStr(ResultCode) + ':' + #13#13 + Command + #13#13 + SysErrorMessage(ResultCode), mbError, MB_OK);
    //end;
    Result := ResultCode;
end;

function DeployLocalConsole(): Integer;
var
    ResultCode: Integer;
    UnpackRoot, AppRoot, Command, ShellWaitAfterError: String;
begin
    ShellWaitAfterError := '; $exitCode = $LASTEXITCODE; if ($exitCode -ne 0) { . ' + ExpandConstant('{tmp}') + '\utils.ps1; Wait-UserInput 40; }; exit $exitCode';
    UnpackRoot := ExpandConstant('{tmp}');
    AppRoot := ExpandConstant('{app}');

    Command := 'Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser';
    ResultCode := RunThenCheckIfFailed(Command);
    if not (ResultCode = 0) then
    begin
        MsgBox('Error during preparation script!', mbCriticalError, MB_OK);
        Result := ResultCode;
        Exit
    end;
    Log('Preparation succeeded!');

    Command := UnpackRoot + '\install.ps1 -AppInstallPath "' + AppRoot + '" -WheelPath $((Get-ChildItem ' + UnpackRoot + '\local_console*.whl).FullName)' + ShellWaitAfterError;
    ResultCode := RunThenCheckIfFailed(Command);
    if not (ResultCode = 0) then
    begin
        MsgBox('Error during main script!', mbCriticalError, MB_OK);
        Result := ResultCode;
        Exit
    end;

    Result := 0;
end;


function IsAppRunning(const FileName : string): Boolean;
var
    FSWbemLocator: Variant;
    FWMIService   : Variant;
    FWbemObjectSet: Variant;
begin
    Result := false;
    FSWbemLocator := CreateOleObject('WBEMScripting.SWBEMLocator');
    FWMIService := FSWbemLocator.ConnectServer('', 'root\CIMV2', '', '');
    FWbemObjectSet :=
      FWMIService.ExecQuery(
        Format('SELECT Name FROM Win32_Process Where Name="%s"', [FileName]));
    Result := (FWbemObjectSet.Count > 0);
    FWbemObjectSet := Unassigned;
    FWMIService := Unassigned;
    FSWbemLocator := Unassigned;
end;

function CheckIfLocalConsoleIsRunning(): Boolean;
var
  Answer: Integer;
begin
  Result := True;
  while IsAppRunning('LocalConsole-win-x64.exe') do
  begin
    Answer := MsgBox('Local Console is currently running. Please close it in order to continue.', mbError, MB_OKCANCEL);
    if Answer = IDCANCEL then
    begin
      Result := False;
      Exit;
    end;
  end;
end;

function InitializeSetup(): Boolean;
begin
  InstallationSucceeded := false;
  Result := CheckIfLocalConsoleIsRunning();
end;

function InitializeUninstall(): Boolean;
begin
  Result := CheckIfLocalConsoleIsRunning();
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  ExtractTemporaryFile(ExpandConstant('{#WheelFile}'));
  ExtractTemporaryFiles('*.ps1');

  ResultCode := DeployLocalConsole();
  InstallationSucceeded := ResultCode = 0;
  if not InstallationSucceeded then
  begin
    Result := 'Installation failed. Setup will now close.';
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Command, ShellWaitAfterError: String;
  ResultCode: Integer;
begin

  ShellWaitAfterError := '; $exitCode = $LASTEXITCODE; if ($exitCode -ne 0) { . ' + ExpandConstant('{tmp}') + '\utils.ps1; Wait-UserInput 40; }; exit $exitCode';

  if CurStep = ssPostInstall then
  begin

    // First, create desktop icon
    Command := ExpandConstant('{tmp}\steps\desktopicon.ps1') + ' ' + ExpandConstant('{app}\UI\LocalConsole.exe') + ShellWaitAfterError;
    RunThenCheckIfFailed(Command);

    // Then, punch a whole in the Firewall for the local console's webserver
    Command := ExpandConstant('{tmp}\steps\firewall.ps1') + ' ' + ExpandConstant('{app}\virtualenv\Scripts\local-console.exe');
    Log('Command: ' + Command);
    ResultCode := RunThenCheckIfFailed(Command);
    if not (ResultCode = 0) then
    begin
        MsgBox('Error during main script!', mbCriticalError, MB_OK);
        Exit
    end;

    // Finally, restore execution policy of PowerShell
    Command := 'Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser';
    ResultCode := RunThenCheckIfFailed(Command);
    if not (ResultCode = 0) then
    begin
        MsgBox('Error during preparation script!', mbCriticalError, MB_OK);
        Exit
    end;
    Log('Preparation succeeded!');
  end;
end;
