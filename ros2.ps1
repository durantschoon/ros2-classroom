<#
.SYNOPSIS
    Windows stand-in for the Makefile: every student-facing `make TARGET` is
    `.\ros2.ps1 TARGET`, with the same arguments.

.DESCRIPTION
    Arguments can be written the make way or the PowerShell way:
        .\ros2.ps1 run PKG=my_robot NODE=talker
        .\ros2.ps1 run -Pkg my_robot -Node talker
    Any other NAME=value (NOVNC_PORT=6081, ROS_DOMAIN_ID=7, ...) is set in the
    environment for this run, as make does with command-line variables.

    Like make, each command prints the docker command it runs before running
    it, so nothing here is a black box.  .\ros2.ps1 help lists them all.

    Windows PowerShell 5.1 compatible, ASCII only: 5.1 reads a file without a
    byte-order mark in the system code page.
#>
param(
    [Parameter(Position = 0)] [string]$Command = "desktop",
    [string]$NativeRecipeRequest = "",
    [string]$Pkg = "",
    [string]$Node = "",
    [string]$Template = "",
    [switch]$Python,
    [switch]$Interfaces,
    [switch]$Yes,
    # make-style NAME=value words, `help` / `examples`, or bare PKG NODE.
    [Parameter(Position = 1, ValueFromRemainingArguments = $true)] [string[]]$Rest = @()
)

$ErrorActionPreference = "Stop"

# Ensure working directory is the repository root
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Definition }
if ($scriptDir) {
    Set-Location $scriptDir
}

# --- make-style arguments ------------------------------------------------------
# Sorted into: NAME=value assignments, help/examples words, and bare words,
# which fill -Pkg then -Node as the positional parameters used to.

# Keep the boundary value before an older environment provider can erase an
# explicitly empty assignment. Null alone means that no override was supplied.
$ExplainOverrideValue = [Environment]::GetEnvironmentVariable("EXPLAIN")
$RosDistroOverrideValue = [Environment]::GetEnvironmentVariable("ROS_DISTRO")
$HelpWords = @()
$BareWords = @()
foreach ($word in $Rest) {
    if ($word -match '^([A-Z][A-Z0-9_]*)=(.*)$') {
        if ($Matches[1] -ceq "EXPLAIN") { $ExplainOverrideValue = $Matches[2] }
        if ($Matches[1] -ceq "ROS_DISTRO") { $RosDistroOverrideValue = $Matches[2] }
        Set-Item -Path "env:$($Matches[1])" -Value $Matches[2]
    } elseif ($word -eq "help" -or $word -eq "examples") {
        $HelpWords += $word
    } else {
        $BareWords += $word
    }
}
if (-not $Pkg -and $env:PKG) { $Pkg = $env:PKG }
if (-not $Node -and $env:NODE) { $Node = $env:NODE }
if (-not $Template -and $env:TEMPLATE) { $Template = $env:TEMPLATE }
if ($env:PYTHON -eq "1") { $Python = $true }
if ($env:INTERFACES -eq "1") { $Interfaces = $true }
if ($env:YES -eq "1") { $Yes = $true }
if ($BareWords.Count -gt 0 -and -not $Pkg) { $Pkg = $BareWords[0]; $BareWords = @($BareWords | Select-Object -Skip 1) }
if ($BareWords.Count -gt 0 -and -not $Node) { $Node = $BareWords[0]; $BareWords = @($BareWords | Select-Object -Skip 1) }
if ($BareWords.Count -gt 0) {
    Write-Host "Unexpected argument(s): $($BareWords -join ' ')" -ForegroundColor Red
    Write-Host "Arguments look like PKG=name or -Pkg name.  See: .\ros2.ps1 help"
    exit 2
}

$NovncPort = if ($env:NOVNC_PORT) { $env:NOVNC_PORT } else { 6080 }
$Url = "http://127.0.0.1:$NovncPort"
$DesktopUrl = "$Url/vnc.html?autoconnect=1&resize=remote&reconnect=true"
$Service = "desktop"

# The student's compose project (the `name:` in compose.yaml) and the self-test's.
$Projects = @(
    $(if ($env:COMPOSE_PROJECT_NAME) { $env:COMPOSE_PROJECT_NAME } else { "ros2-tutorials" }),
    $(if ($env:SELFTEST_PROJECT) { $env:SELFTEST_PROJECT } else { "ros2-tutorials-selftest" })
)
$ProjectLabel = "com.docker.compose.project"

# --- helpers -------------------------------------------------------------------

function Format-Argv([string[]]$Argv) {
    <# A command line as the student would type it: words with spaces quoted. #>
    ($Argv | ForEach-Object { if ($_ -match '\s') { "'$_'" } else { $_ } }) -join ' '
}

function Invoke-Native {
    <# Print a command, run it, and stop with its exit code if it fails, as make does. #>
    param([string[]]$Argv)
    Write-Host (Format-Argv $Argv) -ForegroundColor DarkGray
    $exe = $Argv[0]
    $arguments = @($Argv | Select-Object -Skip 1)
    & $exe @arguments
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

function Get-NativeOutput {
    <# A command's stdout lines, or $null if it could not run or failed.  Silent. #>
    param([string[]]$Argv)
    $prevEAP = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    try {
        $exe = $Argv[0]
        $arguments = @($Argv | Select-Object -Skip 1)
        $output = & $exe @arguments 2>$null
        if ($LASTEXITCODE -ne 0) { return $null }
        # The comma keeps a one-line answer an array; PowerShell would unroll it.
        return ,@($output | Where-Object { $_ -ne $null -and "$_".Trim() -ne "" } | ForEach-Object { "$_" })
    } catch {
        return $null
    } finally {
        $ErrorActionPreference = $prevEAP
    }
}

function Test-NativeSucceeds {
    param([string[]]$Argv)
    return ($null -ne (Get-NativeOutput $Argv))
}

function Read-Confirmation([string]$Word) {
    <# True only when the student types $Word.  No terminal to ask means no. #>
    if ($Yes) { return $true }
    if ([Console]::IsInputRedirected) {
        Write-Host "Not asking without a terminal; rerun with YES=1 to go ahead." -ForegroundColor Red
        exit 1
    }
    $answer = Read-Host "Type `"$Word`" to confirm"
    return ($answer.Trim() -eq $Word)
}

function Format-Size([long]$Bytes) {
    <# Bytes in the decimal units docker itself prints. #>
    if ($Bytes -lt 1000) { return "$Bytes B" }
    $value = $Bytes / 1000.0
    foreach ($unit in @("kB", "MB")) {
        if ($value -lt 1000) { return ("{0:N1} {1}" -f $value, $unit) }
        $value = $value / 1000
    }
    return ("{0:N1} GB" -f $value)
}

function Check-Docker {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Host "Docker is not installed or not in PATH." -ForegroundColor Red
        Write-Host "Prerequisite: Please download and install Docker Desktop for Windows from:" -ForegroundColor Yellow
        Write-Host "  https://docs.docker.com/desktop/install/windows-install/"
        Write-Host "After installation, open Docker Desktop, wait for it to start, and run this again." -ForegroundColor Yellow
        exit 1
    }

    if (-not (Test-NativeSucceeds @("docker", "info"))) {
        Write-Host "Docker Desktop is installed, but the Docker engine is not running." -ForegroundColor Red
        Write-Host "Please start Docker Desktop from your Windows Start Menu, wait until it starts, and try again." -ForegroundColor Yellow
        exit 1
    }
}

# Package commands exec into the desktop; say plainly when it is not running
# rather than surfacing docker's "service is not running" error.
function Require-Desktop {
    Check-Docker
    if (-not (Test-NativeSucceeds @("docker", "compose", "exec", "-T", $Service, "true"))) {
        Write-Host "The desktop is not running. Start it first:  .\ros2.ps1 up" -ForegroundColor Red
        exit 1
    }
}

function Wait-For-Desktop {
    Write-Host "Waiting for the desktop to start..."
    $maxAttempts = 30
    $attempt = 0
    while ($attempt -lt $maxAttempts) {
        try {
            $response = Invoke-WebRequest -Uri "$Url/vnc.html" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-Host "`nDesktop is ready!"
                return
            }
        } catch {
            Write-Host -NoNewline "."
            Start-Sleep -Seconds 2
        }
        $attempt++
    }
    Write-Host "`nThe desktop did not answer after 60s. Is it running? Details: .\ros2.ps1 logs" -ForegroundColor Red
    exit 1
}

# Run a command in the running desktop as the workstation user, with a login
# shell so the ROS environment is sourced exactly as documented.
function Invoke-InDesktop([string]$Script, [switch]$Interactive) {
    $argv = @("docker", "compose", "exec")
    # A TTY only when there is one to give, so Ctrl-C reaches `run`'s node.
    if (-not $Interactive -or [Console]::IsInputRedirected) { $argv += "-T" }
    $argv += @("-u", "ros", "-e", "DISPLAY=:1", "-e", "PKG_VIA_MAKE=1", $Service, "bash", "-lc", $Script)
    Invoke-Native $argv
}

# --- the first-run question ----------------------------------------------------
# The same contract as scripts/explain-choice, written out here because Windows
# may have no Python: the same question, the same answers, the same file
# (.workstation/preferences.json next to this script) and the same JSON, so a
# student using both make and this script on one checkout is asked once.
# EXPLAIN=0, EXPLAIN=1 or EXPLAIN=only, in the environment or as an argument,
# overrides the saved answer for one command.  With no terminal to ask on,
# nothing is asked and nothing is saved.  Change one script, change both.

$PreferencesPath = Join-Path (Join-Path $scriptDir ".workstation") "preferences.json"
$ChooseCommand = ".\ros2.ps1 choose"
# The commands that ask first: the same student commands as the Makefile's,
# plus desktop, the default, which is up then open and asks once.
$AskOnceCommands = @("desktop", "up", "open", "shell", "turtlesim", "turtlesim-teleop", "package", "build", "run", "test")

function Test-Terminal {
    return (-not [Console]::IsInputRedirected -and -not [Console]::IsOutputRedirected)
}

function Get-ExplainOverride {
    <# EXPLAIN as off/on/only, "" only when unset; stops on anything else. #>
    $raw = $ExplainOverrideValue
    if ($null -eq $raw) { return "" }
    if ($raw -ceq "0") { return "off" }
    if ($raw -ceq "1") { return "on" }
    if ($raw -ceq "only") { return "only" }
    Write-Host "EXPLAIN=$raw is not understood. Use EXPLAIN=0, EXPLAIN=1 or EXPLAIN=only."
    exit 2
}

function Get-SavedProblem([string]$Text) {
    <# What is wrong with the saved file's text, in explain-choice's words, or "". #>
    if ([string]::IsNullOrWhiteSpace($Text)) { return "it is not JSON" }
    try {
        $data = $Text | ConvertFrom-Json
    } catch {
        return "it is not JSON"
    }
    if ($data -isnot [System.Management.Automation.PSCustomObject]) { return 'it is not an object with "version" and "explain"' }
    $names = @($data.PSObject.Properties | ForEach-Object { $_.Name })
    $version = $data.version
    if ($names -cnotcontains "version" -or ($version -isnot [int] -and $version -isnot [long]) -or $version -ne 1) { return 'its "version" is not 1' }
    if ($names -cnotcontains "explain") { return 'it has no "explain"' }
    if ($data.explain -isnot [string] -or ($data.explain -cne "off" -and $data.explain -cne "on")) { return 'its "explain" is neither "off" nor "on"' }
    return ""
}

function Read-SavedAnswer {
    <# The saved answer, off or on, or "".  An unreadable file is said, never dropped. #>
    if (-not (Test-Path -LiteralPath $PreferencesPath)) { return "" }
    try {
        $text = [System.IO.File]::ReadAllText($PreferencesPath, (New-Object System.Text.UTF8Encoding $false, $true))
    } catch {
        Write-Host "${PreferencesPath}: the saved answer could not be read: it cannot be opened; treating it as not saved."
        return ""
    }
    $problem = Get-SavedProblem $text
    if ($problem) {
        Write-Host "${PreferencesPath}: the saved answer could not be read: $problem; treating it as not saved."
        return ""
    }
    return "$(($text | ConvertFrom-Json).explain)"
}

function Save-Answer([string]$Explain) {
    <# Write the answer atomically: a temporary file beside it, then a rename. #>
    $dir = Split-Path -Parent $PreferencesPath
    $temp = Join-Path $dir ".preferences.$PID.tmp"
    try {
        if (-not (Test-Path -LiteralPath $dir -PathType Container)) { [void](New-Item -ItemType Directory -Path $dir) }
        # The same bytes explain-choice writes: LF, and UTF-8 with no BOM.
        $text = '{"version": 1, "explain": "' + $Explain + '"}' + "`n"
        [System.IO.File]::WriteAllText($temp, $text, (New-Object System.Text.UTF8Encoding $false))
        if (Test-Path -LiteralPath $PreferencesPath) {
            # [NullString]: PowerShell would pass $null as "", which Replace refuses.
            [System.IO.File]::Replace($temp, $PreferencesPath, [NullString]::Value)
        } else {
            [System.IO.File]::Move($temp, $PreferencesPath)
        }
    } catch {
        if (Test-Path -LiteralPath $temp) { Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue }
        Write-Host "Could not save the answer in ${PreferencesPath}: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}

function Get-OptionNumber([string]$Explain) {
    if ($Explain -ceq "on") { return "2" } else { return "1" }
}

function Read-ChoiceLine {
    # ReadLine can swallow Ctrl-C on Unix PowerShell. Read keys explicitly so
    # cancellation and EOF never turn into a saved default answer.
    $previous = [Console]::TreatControlCAsInput
    try {
        [Console]::TreatControlCAsInput = $true
        Write-Host -NoNewline "Choose 1 or 2 [1]: "
        $line = ""
        while ($true) {
            $key = [Console]::ReadKey($true)
            $code = [int]$key.KeyChar
            if ($code -eq 3) { Write-Host ""; exit 130 }
            if ($code -eq 4 -or $code -eq 26) { Write-Host ""; return $null }
            if ($key.Key -eq [ConsoleKey]::Enter) { Write-Host ""; return $line }
            if ($key.Key -eq [ConsoleKey]::Backspace) {
                if ($line.Length -gt 0) {
                    $line = $line.Substring(0, $line.Length - 1)
                    Write-Host -NoNewline "`b `b"
                }
            } elseif (-not [char]::IsControl($key.KeyChar)) {
                $line += $key.KeyChar
                Write-Host -NoNewline $key.KeyChar
            }
        }
    } finally {
        [Console]::TreatControlCAsInput = $previous
    }
}

function Read-Answer {
    <# Ask until a usable answer, at most three times: off, on, or "" for option 1 for now. #>
    Write-Host "One question before we start. You will only be asked once."
    Write-Host ""
    Write-Host "  1. Just run things for me in the browser workstation."
    Write-Host "  2. Do that, AND show me the commands that should do the same thing directly"
    Write-Host "     on my own system - no container involved."
    Write-Host ""
    Write-Host "Option 2 shows commands we think work on your system, each marked with how"
    Write-Host "well it has been checked. It is not a promise."
    Write-Host "You can change your answer at any time with: $ChooseCommand"
    Write-Host ""
    for ($try = 0; $try -lt 3; $try++) {
        $line = Read-ChoiceLine
        if ($null -eq $line) {
            Write-Host ""
            return ""
        }
        $answer = $line.Trim()
        if ($answer -eq "" -or $answer -eq "1") { return "off" }
        if ($answer -eq "2") { return "on" }
        Write-Host """$answer"" is not 1 or 2."
    }
    return ""
}

function Invoke-AskAndSave {
    $answer = Read-Answer
    if (-not $answer) {
        Write-Host "Using option 1 for now. Nothing was saved, so you will be asked again."
        return
    }
    Save-Answer $answer
    Write-Host "Saved: option $(Get-OptionNumber $answer). You can change it at any time with: $ChooseCommand"
}

# Before the student commands: ask only when EXPLAIN has not decided, nothing
# is saved, and there is a terminal to ask on.
function Invoke-AskOnce {
    if (Get-ExplainOverride) { return }
    if (Read-SavedAnswer) { return }
    if (-not (Test-Terminal)) { return }
    Invoke-AskAndSave
}

function Run-Choose {
    [void](Get-ExplainOverride)
    if (-not (Test-Terminal)) {
        Write-Host "$ChooseCommand asks a question, so it needs a terminal. Nothing was changed." -ForegroundColor Red
        exit 1
    }
    $saved = Read-SavedAnswer
    if ($saved) {
        Write-Host "Your current answer: option $(Get-OptionNumber $saved)."
    } else {
        Write-Host "Nothing is saved yet."
    }
    Write-Host ""
    Invoke-AskAndSave
}

# --- commands ------------------------------------------------------------------

function Run-Up {
    Check-Docker
    Write-Host "Pulling the latest prebuilt workstation image (this only takes a moment)..."
    Invoke-Native @("docker", "compose", "pull", "--ignore-pull-failures")
    Write-Host "Starting the ROS 2 workstation..."
    Invoke-Native @("docker", "compose", "up", "-d")
}

function Run-Open {
    Wait-For-Desktop
    Write-Host "Opening the browser to $DesktopUrl"
    Start-Process $DesktopUrl
    Write-Host ""
    Write-Host "Two terminals, two jobs:" -ForegroundColor Cyan
    Write-Host "  - THIS terminal, on your computer: every script command."
    Write-Host "      .\ros2.ps1 turtlesim   then   .\ros2.ps1 turtlesim-teleop"
    Write-Host "  - The terminal INSIDE the browser desktop: ROS commands"
    Write-Host "    (ros2, colcon, pkg). .\ros2.ps1 does not work in there."
}

# No --pull: the base image is pinned by digest, so there is nothing newer to
# fetch for a given ROS_BASE_DIGEST.  Most students never need this: `up`
# pulls the prebuilt image instead.
function Run-Image {
    Check-Docker
    Invoke-Native @("docker", "compose", "build")
}

# A one-off container, so it works whether or not the desktop is running.
function Run-Shell {
    Check-Docker
    Write-Host "Entering a ROS shell. Type exit to come back."
    Write-Host "Not sure what to type? exit, then:  .\ros2.ps1 shell examples"
    Invoke-Native @("docker", "compose", "run", "--rm", "shell")
}

function Run-Turtlesim {
    Check-Docker
    Invoke-InDesktop 'nohup ros2 run turtlesim turtlesim_node >/tmp/turtlesim.log 2>&1 &'
    Write-Host "turtlesim started on the browser desktop ($Url)."
    Write-Host "Next, to drive the turtle:  .\ros2.ps1 turtlesim-teleop"
}

function Run-TurtlesimTeleop {
    Check-Docker
    Invoke-InDesktop "nohup xterm -title 'turtlesim teleop (arrow keys)' -bg white -fg black -u8 -fa 'DejaVu Sans Mono' -fs 11 -e bash -lc turtlesim-teleop >/tmp/teleop.log 2>&1 &"
    Write-Host "turtlesim teleop opened on the browser desktop."
    Write-Host "Click inside the WHITE window titled 'turtlesim teleop' to use arrow keys."
}

function Run-Package {
    if (-not $Pkg) {
        Write-Host "usage: .\ros2.ps1 package PKG=name [TEMPLATE=pubsub|param] [PYTHON=1] [INTERFACES=1]" -ForegroundColor Red
        Write-Host "e.g.   .\ros2.ps1 package PKG=my_robot TEMPLATE=pubsub"
        exit 2
    }
    Require-Desktop
    $options = ""
    if ($Python) { $options += " --python" }
    if ($Template) { $options += " --template $Template" }
    if ($Interfaces) { $options += " --interfaces" }
    Invoke-InDesktop "pkg new $Pkg$options"
}

function Run-Build {
    Require-Desktop
    Invoke-InDesktop "pkg build $Pkg"
}

# Foreground, so Ctrl-C stops the node.
function Run-RunNode {
    if (-not $Pkg -or -not $Node) {
        Write-Host "usage: .\ros2.ps1 run PKG=name NODE=executable" -ForegroundColor Red
        Write-Host ".\ros2.ps1 build PKG=name  lists the executables it built."
        exit 2
    }
    Require-Desktop
    Invoke-InDesktop "pkg run $Pkg $Node" -Interactive
}

function Run-Test {
    Require-Desktop
    Invoke-InDesktop "pkg test $Pkg"
}

function Run-Logs {
    Check-Docker
    Invoke-Native @("docker", "compose", "logs", "-f")
}

function Run-Ps {
    Check-Docker
    Invoke-Native @("docker", "compose", "ps")
}

function Run-Down {
    Check-Docker
    Invoke-Native @("docker", "compose", "down")
}

# Destructive: prints exactly what will be removed and requires confirmation.
function Run-Reset {
    Check-Docker
    Write-Host "This removes the ros2-tutorials containers and these volumes:"
    Write-Host "  ros2-tutorials_ros-workspace   (src/, build/, install/, log/)"
    Write-Host "  ros2-tutorials_ros-home        (shell history, rosdep cache, settings)"
    if (-not (Read-Confirmation "delete")) {
        Write-Host "aborted; nothing was removed"
        exit 1
    }
    Invoke-Native @("docker", "compose", "down", "-v", "--remove-orphans")
}

# Which compose command is in use.  On Windows it is always Docker Desktop's.
function Run-Engine {
    Check-Docker
    $version = Get-NativeOutput @("docker", "compose", "version", "--short")
    if ($null -eq $version) {
        Write-Host "docker is running but has no compose plugin; update Docker Desktop." -ForegroundColor Red
        exit 1
    }
    Write-Host "docker compose $($version[0])  (Docker Desktop)"
}

# Everything reset removes, plus the images, for both the student's project and
# the self-test's.  Talks to docker directly rather than through compose, so it
# works whatever state compose left behind, and never touches anything outside
# those projects' labels and this repo's image names.  The build cache is
# shared with every other project on the machine, so it is reported, not removed.
function Run-Uninstall {
    Check-Docker

    $items = @()
    foreach ($project in $Projects) {
        $filter = "label=$ProjectLabel=$project"
        foreach ($name in (Get-NativeOutput @("docker", "ps", "-a", "--filter", $filter, "--format", "{{.Names}}"))) {
            if ($name) { $items += [pscustomobject]@{ Kind = "container"; Ref = $name; Size = 0 } }
        }
    }
    foreach ($kind in @("volume", "network")) {
        foreach ($project in $Projects) {
            $filter = "label=$ProjectLabel=$project"
            foreach ($name in (Get-NativeOutput @("docker", $kind, "ls", "--filter", $filter, "--format", "{{.Name}}"))) {
                if ($name) { $items += [pscustomobject]@{ Kind = $kind; Ref = $name; Size = 0 } }
            }
        }
    }

    # The image compose.yaml names (pulled or built), the name the self-test
    # builds under, and the digest-pinned ROS base, present after a local build.
    $images = @()
    $composeImages = Get-NativeOutput @("docker", "compose", "config", "--images")
    if ($composeImages) { $images += $composeImages }
    $imageName = if ($env:IMAGE_NAME) { $env:IMAGE_NAME } else { "ros2-tutorials" }
    $rosDistro = if ($env:ROS_DISTRO) { $env:ROS_DISTRO } else { "lyrical" }
    $images += "${imageName}:$rosDistro"
    $digestLine = Select-String -Path (Join-Path $scriptDir "Dockerfile") -Pattern '^ARG ROS_BASE_DIGEST=(\S+)' | Select-Object -First 1
    $digest = if ($env:ROS_BASE_DIGEST) { $env:ROS_BASE_DIGEST } elseif ($digestLine) { $digestLine.Matches[0].Groups[1].Value } else { "" }
    if ($digest) {
        $registry = if ($env:ROS_REGISTRY) { $env:ROS_REGISTRY.TrimEnd("/") } else { "docker.io/library" }
        $images += "$registry/ros@$digest"
    }
    foreach ($image in ($images | Where-Object { $_ } | Select-Object -Unique)) {
        $size = Get-NativeOutput @("docker", "image", "inspect", "--format", "{{.Size}}", $image)
        if ($null -ne $size) { $items += [pscustomobject]@{ Kind = "image"; Ref = $image; Size = [long]$size[0] } }
    }

    $cacheHint = "Not removed: docker's build cache, which other projects share. To clear it too:  docker builder prune"
    if ($items.Count -eq 0) {
        Write-Host "Nothing of the workstation's is on this machine; nothing to remove."
        Write-Host $cacheHint
        return
    }

    Write-Host "This removes, from this machine:"
    foreach ($item in $items) {
        $size = if ($item.Size) { "  ($(Format-Size $item.Size))" } else { "" }
        Write-Host ("  {0,-9} {1}{2}" -f $item.Kind, $item.Ref, $size)
    }
    $total = ($items | Measure-Object -Property Size -Sum).Sum
    if ($total) { Write-Host "Frees at least $(Format-Size $total)." }
    Write-Host ""

    if (-not (Read-Confirmation "uninstall")) {
        Write-Host "aborted; nothing was removed"
        exit 1
    }

    # One docker call per kind, in the order they must go.
    $failed = $false
    foreach ($kind in @("container", "volume", "network", "image")) {
        $refs = @($items | Where-Object { $_.Kind -eq $kind } | ForEach-Object { $_.Ref })
        if ($refs.Count -eq 0) { continue }
        $argv = if ($kind -eq "container") { @("docker", "rm", "-f") + $refs } else { @("docker", $kind, "rm") + $refs }
        Write-Host (Format-Argv $argv) -ForegroundColor DarkGray
        & $argv[0] @($argv | Select-Object -Skip 1) | Out-Null
        if ($LASTEXITCODE -ne 0) { $failed = $true }
    }
    Write-Host ""
    Write-Host $cacheHint
    Write-Host "This checkout is still at $scriptDir; delete it yourself when you are done."
    if ($failed) { exit 1 }
}

# Whether this machine can run the workstation, with the fix for anything
# missing.  Changes nothing.  Windows means Docker Desktop, so this checks
# Docker alone; `make doctor` also knows about Podman.
function Run-Doctor {
    $diskGbWanted = 15
    $memoryGbWanted = 4
    function Ok([string]$Text) { Write-Host -NoNewline "  "; Write-Host -NoNewline "ok  " -ForegroundColor Green; Write-Host "  $Text" }
    function Warn([string]$Text) { Write-Host -NoNewline "  "; Write-Host -NoNewline "warn" -ForegroundColor Yellow; Write-Host "  $Text" }
    function Miss([string]$Text) { Write-Host -NoNewline "  "; Write-Host -NoNewline "miss" -ForegroundColor Red; Write-Host "  $Text" }
    function Fix([string]$Text) { Write-Host "        -> $Text" }
    function Resource([string]$Label, [long]$Gb, [int]$Wanted) {
        if ($Gb -ge $Wanted) { Ok "${Label}: $Gb GB" } else { Warn "${Label}: $Gb GB ($Wanted GB recommended)" }
    }

    $ready = $true
    Write-Host "Container engine"
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Miss "docker is not installed"
        Fix "install Docker Desktop: https://docs.docker.com/desktop/install/windows-install/"
        $ready = $false
    } elseif (-not (Test-NativeSucceeds @("docker", "info"))) {
        Miss "Docker Desktop is installed, but its engine is not running"
        Fix "start Docker Desktop from the Start Menu and wait for it to finish starting"
        $ready = $false
    } else {
        $compose = Get-NativeOutput @("docker", "compose", "version", "--short")
        if ($null -eq $compose) {
            Miss "docker has no compose plugin"
            Fix "update Docker Desktop"
            $ready = $false
        } else {
            Ok "compose: docker compose $($compose[0])"
        }
        $version = Get-NativeOutput @("docker", "version", "--format", "{{.Client.Version}}")
        if ($null -ne $version) { Ok "engine:  docker $($version[0])" }
    }

    Write-Host ""
    Write-Host "Resources"
    # Docker Desktop keeps its images on the drive holding %LOCALAPPDATA%.
    $dockerDrive = if ($env:LOCALAPPDATA) { Split-Path -Qualifier $env:LOCALAPPDATA } else { Split-Path -Qualifier $scriptDir }
    $drive = Get-PSDrive -Name $dockerDrive.TrimEnd(":") -ErrorAction SilentlyContinue
    if ($drive -and $drive.Free) { Resource "disk free ($dockerDrive)" ([long][math]::Floor($drive.Free / 1GB)) $diskGbWanted }
    if ($ready) {
        $memory = Get-NativeOutput @("docker", "info", "--format", "{{.MemTotal}}")
        if ($null -ne $memory) { Resource "memory (docker's VM)" ([long][math]::Floor([long]$memory[0] / 1GB)) $memoryGbWanted }
    }

    Write-Host ""
    if ($ready) {
        Write-Host "Ready: run .\ros2.ps1 desktop"
    } else {
        Write-Host "Not ready; see docs/host-requirements.md."
        exit 1
    }
}

# The old name, kept only to point at the new one.
function Run-Teleop {
    Write-Host "'.\ros2.ps1 teleop' is now '.\ros2.ps1 turtlesim-teleop' -- it only drives turtlesim."
    exit 2
}

# --- help ----------------------------------------------------------------------

# Each entry pairs a command with the native command it stands in for, so the
# help teaches what actually runs rather than hiding it.
function Show-Help {
    $exec = "docker compose exec -u ros desktop"
    $commands = @(
        @{ Usage = "desktop";                                  About = "Start the desktop and open it in the browser (the default)"; Native = "docker compose up -d, then open $Url" }
        @{ Usage = "up";                                       About = "Start the desktop";                                         Native = "docker compose pull; docker compose up -d" }
        @{ Usage = "open";                                     About = "Open the desktop in the browser";                           Native = "Start-Process $DesktopUrl" }
        @{ Usage = "shell";                                    About = "Open a ROS shell in this terminal";                         Native = "docker compose run --rm shell" }
        @{ Usage = "turtlesim";                                About = "Start turtlesim on the browser desktop";                    Native = "$exec ros2 run turtlesim turtlesim_node" }
        @{ Usage = "turtlesim-teleop";                         About = "Open the arrow-key controller on the desktop";              Native = "$exec turtlesim-teleop" }
        @{ Usage = "package PKG=name [TEMPLATE=pubsub|param]"; About = "Create a package in /workspace/src (also PYTHON=1, INTERFACES=1)"; Native = "$exec pkg new name [--template pubsub]" }
        @{ Usage = "build [PKG=name]";                         About = "Build one package, or all of them";                         Native = "$exec pkg build [name]" }
        @{ Usage = "run PKG=name NODE=executable";             About = "Run a node from your package";                              Native = "$exec pkg run name executable" }
        @{ Usage = "test [PKG=name]";                          About = "Test one package, or all of them";                          Native = "$exec pkg test [name]" }
        @{ Usage = "logs";                                     About = "Follow the desktop's logs (Ctrl-C to stop)";                Native = "docker compose logs -f" }
        @{ Usage = "ps";                                       About = "List the workstation's containers";                         Native = "docker compose ps" }
        @{ Usage = "down";                                     About = "Stop the containers (your work is kept)";                   Native = "docker compose down" }
        @{ Usage = "reset";                                    About = "Delete your workspace and settings (asks first)";           Native = "docker compose down -v --remove-orphans" }
        @{ Usage = "uninstall";                                About = "Delete all of that and the images (asks first)";            Native = "docker rm / volume rm / network rm / image rm" }
        @{ Usage = "doctor";                                   About = "Check this machine can run the workstation";                Native = "docker info; docker compose version" }
        @{ Usage = "image";                                    About = "Build the image locally instead of pulling it";             Native = "docker compose build" }
        @{ Usage = "engine";                                   About = "Show which compose command is used";                        Native = "docker compose version" }
        @{ Usage = "choose"; About = "Change the saved native explanation preference"; Native = "" }
        @{ Usage = "help";                                     About = "Show this help";                                            Native = "" }
        @{ Usage = "COMMAND help | COMMAND examples";          About = "More on shell, package, build, run, test";                  Native = "" }
    )

    Write-Host "Usage: .\ros2.ps1 COMMAND [NAME=value ...]    (or .\ros2.bat COMMAND ...)" -ForegroundColor Cyan
    Write-Host "Every 'make COMMAND' in the docs is '.\ros2.ps1 COMMAND' here, same arguments."
    Write-Host ""
    foreach ($entry in $commands) {
        Write-Host ("  {0,-42} {1}" -f $entry.Usage, $entry.About)
        if ($entry.Native) {
            Write-Host ("  {0,-42} runs: {1}" -f "", $entry.Native) -ForegroundColor DarkGray
        }
    }
    Write-Host ""
    Write-Host "Example:" -ForegroundColor Cyan
    Write-Host "  .\ros2.ps1 package PKG=my_robot TEMPLATE=pubsub"
    Write-Host "  .\ros2.ps1 build PKG=my_robot"
    Write-Host "  .\ros2.ps1 run PKG=my_robot NODE=talker"
    Write-Host ""
    Write-Host "Desktop: $Url"
}

# `COMMAND help`, `COMMAND examples` and `examples` print the same text as
# `make COMMAND help`: scripts/workstation-help, run by the image's python3
# since Windows may have none, with `make` swapped for `.\ros2.ps1`.  The
# arguments it shows (PKG=name) work unchanged here.
function Show-TopicHelp([string[]]$Words) {
    Check-Docker
    $helpScript = Join-Path $scriptDir "scripts\workstation-help"
    $argv = @("docker", "compose", "run", "--rm", "-T", "--no-deps", "shell", "python3", "-") + $Words
    # stderr is merged so a refusal (`up help`) gets the same rewording; 5.1
    # turns merged stderr into error records, which "Stop" would throw on.
    $prevEAP = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $text = Get-Content -Raw $helpScript | & $argv[0] @($argv | Select-Object -Skip 1) 2>&1
    $status = $LASTEXITCODE
    $ErrorActionPreference = $prevEAP
    foreach ($item in $text) {
        $line = if ($item -is [System.Management.Automation.ErrorRecord]) { $item.Exception.Message } else { "$item" }
        # A blank stderr line arrives as an error record with no message.
        if ($line -eq "System.Management.Automation.RemoteException") { $line = "" }
        # Compose's container progress and the entrypoint's log are not help.
        if ($line -match '^\s*Container \S+ (Creating|Created|Starting|Started)\s*$' -or $line -match '^\[entrypoint\]') { continue }
        Write-Host ($line -replace '\bmake (?=[a-z<])', '.\ros2.ps1 ')
    }
    if ($status -ne 0) {
        Write-Host "(from: $(Format-Argv $argv) < scripts\workstation-help)" -ForegroundColor DarkGray
        exit $status
    }
}

# Native explanations use the same strict schema and exact platform policy as
# scripts/native-recipes. This boundary uses .NET only, including on Windows 5.1.
$NativeParameters = @{
    'install' = @(); 'session' = @('workspace'); 'shell' = @('workspace')
    'turtlesim' = @('workspace'); 'teleop' = @('workspace')
    'package' = @('workspace','package','build_type')
    'package-template' = @('workspace','package','build_type','template')
    'package-interfaces' = @('workspace','package')
    'build-workspace' = @('workspace'); 'test-workspace' = @('workspace')
    'build' = @('workspace','package'); 'run' = @('workspace','package','node')
    'test' = @('workspace','package'); 'container-maintenance' = @()
}
function Test-NativeFields($Value, [string[]]$Names) {
    if ($Value -isnot [System.Management.Automation.PSCustomObject]) { return $false }
    $actual = @($Value.PSObject.Properties | ForEach-Object { $_.Name })
    return ($actual.Count -eq $Names.Count -and @($Names | Where-Object { $actual -cnotcontains $_ }).Count -eq 0)
}
function Test-NativeText($Value) {
    return ($Value -is [string] -and $Value.Trim().Length -gt 0 -and $Value -notmatch '[\x00-\x1f\x7f-\x9f]')
}
function Test-NativeWord($Value) {
    return ($Value -is [string] -and $Value -cmatch '^[a-zA-Z0-9][a-zA-Z0-9_.-]*\z')
}
function Read-NativeJson([string]$Text) {
    # ConvertFrom-Json 5.1 silently discards duplicate keys. Check lexical JSON
    # first, retaining an ordinal key set for every object, including nested ones.
    $tokens = New-Object 'System.Collections.Generic.List[string]'
    $offset = 0
    $pattern = '\G[ \t\r\n]*("(?:[^"\\\x00-\x1f]|\\(?:["\\/bfnrt]|u[0-9a-fA-F]{4}))*"|-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?|true|false|null|[{}\[\],:])'
    while ($offset -lt $Text.Length) {
        if ($Text.Substring($offset) -cmatch '\A[ \t\r\n]*\z') { break }
        # \G anchors at zero in Match(string); use a suffix so each token starts here.
        $match = [regex]::Match($Text.Substring($offset), $pattern)
        if (-not $match.Success) { return @{ outcome='error'; message='invalid JSON token' } }
        $tokens.Add($match.Groups[1].Value)
        $offset += $match.Length
    }
    $stack = New-Object System.Collections.Stack
    $previous = ''
    try {
        foreach ($token in $tokens) {
            if ($token -eq '{') { $stack.Push(@{ kind='object'; keys=(New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::Ordinal)) }) }
            elseif ($token -eq '[') { $stack.Push(@{ kind='array' }) }
            elseif ($token -eq '}' -or $token -eq ']') {
                if ($previous -eq ',') { return @{ outcome='error'; message='trailing JSON comma' } }
                if ($stack.Count -gt 0) { [void]$stack.Pop() }
            }
            elseif ($token.StartsWith('"') -and $stack.Count -gt 0 -and $stack.Peek().kind -eq 'object' -and $previous -in @('{',',')) {
                $key = $token | ConvertFrom-Json
                if (-not $stack.Peek().keys.Add($key)) { return @{ outcome='error'; message='duplicate JSON object key' } }
            }
            $previous = $token
        }
        $value = $Text | ConvertFrom-Json
        return @{ outcome='ok'; value=$value }
    } catch { return @{ outcome='error'; message='invalid JSON' } }
}
function Test-NativeCatalog($Catalog) {
    if (-not (Test-NativeFields $Catalog @('schema_version','recipes')) -or $Catalog.schema_version -is [bool] -or ($Catalog.schema_version -isnot [int] -and $Catalog.schema_version -isnot [long]) -or $Catalog.schema_version -ne 1 -or $Catalog.recipes -isnot [array]) { return 'invalid catalog' }
    $identities = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::Ordinal)
    foreach ($r in $Catalog.recipes) {
        if (-not (Test-NativeFields $r @('id','platform','operation','verification','commands','guidance')) -or -not (Test-NativeWord $r.id) -or -not $identities.Add($r.id)) { return 'invalid recipe identity or fields' }
        $p = $r.platform
        if (-not (Test-NativeFields $p @('os','version','architecture','route','ros_distro','context'))) { return 'invalid platform fields' }
        foreach ($property in $p.PSObject.Properties) { if (-not (Test-NativeWord $property.Value)) { return 'invalid platform identifier' } }
        $routes = @{ ubuntu='apt'; macos='pixi'; windows='wsl2' }
        if (@('ubuntu','macos','windows') -cnotcontains $p.os -or @('amd64','arm64') -cnotcontains $p.architecture -or $routes[$p.os] -cne $p.route -or @('native','wsl') -cnotcontains $p.context -or ($p.context -ceq 'wsl' -and $p.os -cne 'ubuntu')) { return 'invalid platform' }
        if ($NativeParameters.Keys -cnotcontains $r.operation -or $r.operation -ceq 'container-maintenance') { return 'invalid operation' }
        $e = $r.verification
        if (-not (Test-NativeFields $e @('status','reference','date','procedure','subject','provenance'))) { return 'invalid evidence fields' }
        foreach ($key in @('reference','date','procedure','subject')) { if (-not (Test-NativeText $e.$key)) { return 'invalid evidence text' } }
        $provenance = @{ 'verified-in-ci'='ci_run'; 'verified-by-hand'='environment'; 'community-reported'='report' }
        if ($provenance.Keys -cnotcontains $e.status) { return 'invalid evidence status' }
        $key = $provenance[$e.status]
        $date = [datetime]::MinValue
        if (-not (Test-NativeFields $e.provenance @($key)) -or -not (Test-NativeText $e.provenance.$key) -or $e.subject -cne $r.id -or -not $e.reference.StartsWith('https://') -or $e.reference.Length -le 8 -or $e.date -cnotmatch '^\d{4}-\d{2}-\d{2}$' -or -not [datetime]::TryParseExact($e.date, 'yyyy-MM-dd', [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::None, [ref]$date)) { return 'invalid evidence' }
        if ($r.guidance -isnot [array] -or $r.commands -isnot [array] -or $r.commands.Count -eq 0) { return 'invalid command or guidance list' }
        foreach ($line in $r.guidance) { if (-not (Test-NativeText $line)) { return 'invalid guidance' } }
        $used = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::Ordinal)
        foreach ($c in $r.commands) {
            if (-not (Test-NativeFields $c @('argv')) -or $c.argv -isnot [array] -or $c.argv.Count -eq 0) { return 'invalid argv' }
            $index = 0
            foreach ($t in $c.argv) {
                if ((Test-NativeFields $t @('literal')) -and (Test-NativeText $t.literal)) { }
                elseif ($index -gt 0 -and (Test-NativeFields $t @('parameter')) -and $t.parameter -is [string] -and $NativeParameters[$r.operation] -ccontains $t.parameter) { [void]$used.Add($t.parameter) }
                else { return 'invalid command token' }
                $index++
            }
        }
        if ($used.Count -ne $NativeParameters[$r.operation].Count) { return 'missing operation parameters' }
    }
    return ''
}
function Test-NativeRequest($Request) {
    if (-not (Test-NativeFields $Request @('operation','parameters')) -or $NativeParameters.Keys -cnotcontains $Request.operation -or -not (Test-NativeFields $Request.parameters $NativeParameters[$Request.operation])) { return 'invalid request' }
    foreach ($property in $Request.parameters.PSObject.Properties) { if (-not (Test-NativeText $property.Value)) { return 'invalid parameter' } }
    if ($Request.parameters.PSObject.Properties.Name -ccontains 'build_type' -and @('ament_cmake','ament_python') -cnotcontains $Request.parameters.build_type) { return 'invalid build type' }
    if ($Request.parameters.PSObject.Properties.Name -ccontains 'template' -and @('pubsub','param') -cnotcontains $Request.parameters.template) { return 'invalid template' }
    return ''
}
function ConvertTo-NativeCanonical($Value) {
    if ($Value -is [string]) { return '"' + $Value.Replace('\','\\').Replace('"','\"') + '"' }
    if ($Value -is [array]) {
        $parts=@($Value | ForEach-Object { ConvertTo-NativeCanonical $_ })
        return '[' + ($parts -join ',') + ']'
    }
    $keys=[string[]]@($Value.PSObject.Properties | ForEach-Object { $_.Name })
    [array]::Sort($keys, [StringComparer]::Ordinal)
    $parts=@()
    foreach ($key in $keys) { $parts += (ConvertTo-NativeCanonical $key) + ':' + (ConvertTo-NativeCanonical $Value.$key) }
    return '{' + ($parts -join ',') + '}'
}
function Get-NativeFingerprint($Recipe) {
    $data=[pscustomobject]@{id=$Recipe.id;platform=$Recipe.platform;operation=$Recipe.operation;commands=$Recipe.commands;guidance=$Recipe.guidance}
    $canonical=ConvertTo-NativeCanonical $data
    $sha=[Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($canonical)))).Replace('-','').ToLowerInvariant() }
    finally { $sha.Dispose() }
}
function Test-NativeAdmission($Recipe) {
    $e=$Recipe.verification
    if ($e.status -cne 'verified-in-ci') { return -not $e.reference.StartsWith('https://example.invalid/') }
    if ($e.reference -cnotmatch '^https://github.com/[^/]+/[^/]+/actions/runs/([1-9][0-9]*)\z') { return $false }
    $runId=$Matches[1]
    return ($e.provenance.ci_run -ceq $runId -and $e.procedure.Contains('Recipe SHA-256: ' + (Get-NativeFingerprint $Recipe)))
}

function Test-NativeRenderParameters($Recipe, $Parameters) {
    if ($Recipe.platform.os -ceq 'ubuntu' -and $Parameters.PSObject.Properties.Name -ccontains 'workspace' -and -not $Parameters.workspace.StartsWith('/')) { return 'Ubuntu native workspace must be an absolute POSIX path' }
    return ''
}
function Format-NativeRecipe($Recipe, $Parameters) {
    $e = $Recipe.verification
    $lines = @(('# Native Bash commands: ' + $Recipe.id), ('# ' + $e.status + ': ' + $e.reference), ('# ' + $e.date + '; ' + $e.procedure))
    foreach ($line in $Recipe.guidance) { $lines += '# ' + $line }
    $escape = "'" + '"' + "'" + '"' + "'"
    foreach ($c in $Recipe.commands) {
        $words = @()
        foreach ($t in $c.argv) {
            $value = if ($t.PSObject.Properties.Name -ccontains 'literal') { $t.literal } else { $Parameters.($t.parameter) }
            $words += "'" + $value.Replace("'", $escape) + "'"
        }
        $lines += $words -join ' '
    }
    return ($lines -join "`n") + "`n"
}
function Select-NativeRecipe($Catalog, $Platform, $Request) {
    $problem = Test-NativeCatalog $Catalog
    if (-not $problem) { $problem = Test-NativeRequest $Request }
    if ($problem) { return @{ outcome='error'; message=$problem } }
    if ($Request.operation -ceq 'container-maintenance') { return @{ outcome='unsupported'; message='container maintenance has no native equivalent' } }
    $names = @('os','version','architecture','route','ros_distro','context')
    foreach ($name in $names) { if (-not (Test-NativeText $Platform.$name)) { return @{ outcome='unsupported'; message='unknown platform' } } }
    $matches = @($Catalog.recipes | Where-Object {
        $r = $_
        $r.operation -ceq $Request.operation -and @($names | Where-Object { $r.platform.$_ -cne $Platform.$_ }).Count -eq 0
    })
    if ($matches.Count -ne 1) { return @{ outcome='unsupported'; message='no unique evidenced recipe for this exact platform and operation' } }
    return @{ outcome='ok'; recipe=$matches[0] }
}
function Get-NativePlatform([string]$Distro) {
    $system = [Environment]::OSVersion.Platform
    $platform = @{ os='windows'; version=[Environment]::OSVersion.Version.ToString(); architecture=''; route='wsl2'; ros_distro=$Distro; context='native' }
    $machine = if ($env:PROCESSOR_ARCHITEW6432) { $env:PROCESSOR_ARCHITEW6432 } else { $env:PROCESSOR_ARCHITECTURE }
    if ($system -eq [PlatformID]::Unix) {
        $platform.os = ''; $platform.version = ''; $platform.route = ''; $platform.context = ''
        if (Test-Path -LiteralPath '/etc/os-release') {
            foreach ($line in [IO.File]::ReadAllLines('/etc/os-release')) {
                if ($line -cmatch '^ID=(.*)$') { $platform.os = $Matches[1].Trim('"',"'") }
                if ($line -cmatch '^VERSION_ID=(.*)$') { $platform.version = $Matches[1].Trim('"',"'") }
            }
            if ($platform.os -ceq 'ubuntu') { $platform.route = 'apt' }
        }
        if (Test-Path -LiteralPath '/proc/sys/kernel/osrelease') {
            $release = [IO.File]::ReadAllText('/proc/sys/kernel/osrelease').Trim()
            if ($release) { $platform.context = if ($release -match 'microsoft') { 'wsl' } else { 'native' } }
        }
        $machine = [Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString()
    }
    if ($machine -match '^(AMD64|x86_64|X64)$') { $platform.architecture='amd64' }
    elseif ($machine -match '^(ARM64|aarch64)$') { $platform.architecture='arm64' }
    return $platform
}
function Get-NativeDistro {
    $value = $RosDistroOverrideValue
    if ($null -eq $value) {
        $path = Join-Path $scriptDir '.env'
        if (Test-Path -LiteralPath $path) {
            foreach ($line in [IO.File]::ReadAllLines($path)) {
                if ($line -cmatch '^\s*(?:export\s+)?ROS_DISTRO\s*=\s*(.*?)\s*$') {
                    $value=$Matches[1]
                    if ($value.Length -ge 2 -and ($value[0] -eq '"' -or $value[0] -eq "'") -and $value[-1] -eq $value[0]) { $value=$value.Substring(1,$value.Length-2) }
                    else { $value=($value -split '\s+#',2)[0].Trim() }
                }
            }
        }
        if ($null -eq $value) { $value='lyrical' }
    }
    return $value
}
function Show-NativeExplanation([string]$Mode) {
    $distro=Get-NativeDistro
    if (-not (Test-NativeWord $distro)) { Write-Host 'configured ROS_DISTRO must be a literal identifier'; return 2 }
    foreach ($value in @($Pkg,$Node)) {
        if ($value -and $value -cnotmatch '^[a-zA-Z_][a-zA-Z0-9_]*\z') { Write-Host 'package and node must be single ROS identifiers'; return 2 }
    }
    $workspace = if ($env:NATIVE_WORKSPACE) { $env:NATIVE_WORKSPACE } else { Join-Path ([Environment]::GetFolderPath('UserProfile')) 'ros2_ws' }
    if ($workspace -notmatch '^(?:/|[A-Za-z]:[\\/]|\\\\)') { Write-Host 'NATIVE_WORKSPACE must be an absolute path'; return 2 }
    $parameters = @{ workspace=$workspace }
    $operations = @{ image='install'; up='install'; desktop='install'; open='session'; shell='shell'; turtlesim='turtlesim'; 'turtlesim-teleop'='teleop'; package='package'; run='run' }
    $operation = if ($operations.ContainsKey($Command)) { $operations[$Command] } else { 'container-maintenance' }
    if ($Command -in @('build','test')) { $operation=if ($Pkg) { $Command } else { $Command+'-workspace' } }
    if ($operation -in @('install','container-maintenance')) { $parameters=@{} }
    if ($operation -in @('package','build','test','run')) { $parameters.package=$Pkg }
    if ($operation -eq 'run') { $parameters.node=$Node }
    if ($operation -eq 'package' -and $Interfaces -and ($Python -or $Template)) { Write-Host 'interfaces require CMake and cannot be combined with a template'; return 2 }
    if ($operation -eq 'package') {
        $parameters.build_type=if ($Python) { 'ament_python' } else { 'ament_cmake' }
        if ($Interfaces) { $operation='package-interfaces'; $parameters.Remove('build_type') }
        elseif ($Template) { $operation='package-template'; $parameters.template=$Template }
    }
    $request=[pscustomobject]@{ operation=$operation; parameters=[pscustomobject]$parameters }
    $problem=Test-NativeRequest $request
    if ($problem) { Write-Host $problem; return 2 }
    $path=Join-Path (Join-Path (Join-Path $scriptDir 'recipes') 'native') 'ubuntu-apt.json'
    if (Test-Path -LiteralPath $path) { $loaded=Read-NativeJson ([IO.File]::ReadAllText($path)) }
    else { $loaded=@{ outcome='ok'; value=[pscustomobject]@{schema_version=1;recipes=@()} } }
    if ($loaded.outcome -ne 'ok') { Write-Host $loaded.message; return 2 }
    $selected=Select-NativeRecipe $loaded.value (Get-NativePlatform $distro) $request
    if ($selected.outcome -eq 'error') { Write-Host $selected.message; return 2 }
    if ($selected.outcome -eq 'ok') {
        $problem=Test-NativeRenderParameters $selected.recipe $request.parameters
        if ($problem) { Write-Host $problem; return 2 }
    }
    if ($selected.outcome -eq 'ok' -and -not (Test-NativeAdmission $selected.recipe)) { $selected=@{ outcome='unsupported'; message='candidate awaits an actual successful CI run' } }
    if ($selected.outcome -eq 'ok') { Write-Host -NoNewline (Format-NativeRecipe $selected.recipe $request.parameters); return 0 }
    Write-Host "Native commands unavailable for ${Command}: $($selected.message)."
    if ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT) { Write-Host 'Windows native installation uses WSL 2; no Windows bootstrap recipe is verified yet.' }
    if ($Mode -eq 'only') { return 2 }
    return 0
}

function Get-NativeFactsPlatform($Raw) {
    $keys = @('system','version','machine','os_id','os_version','kernel_release','ssh','vm','tools','display','gpu','network','ros_distro')
    if (-not (Test-NativeFields $Raw @('schema_version','facts')) -or $Raw.schema_version -is [bool] -or ($Raw.schema_version -isnot [int] -and $Raw.schema_version -isnot [long]) -or $Raw.schema_version -ne 1 -or -not (Test-NativeFields $Raw.facts $keys)) { return @{ outcome='error'; message='invalid facts' } }
    $values = @{}
    foreach ($key in $keys) {
        $fact=$Raw.facts.$key
        if (-not (Test-NativeFields $fact @('state','values')) -or @('known','unknown','none','not-observed') -cnotcontains $fact.state -or $fact.values -isnot [array] -or (($fact.state -ceq 'known') -ne ($fact.values.Count -gt 0)) -or ($key -cne 'tools' -and $fact.values.Count -gt 1)) { return @{ outcome='error'; message='invalid fact' } }
        $seen = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::Ordinal)
        foreach ($value in $fact.values) {
            if (-not (Test-NativeText $value) -or -not $seen.Add($value) -or ($key -ceq 'tools' -and @('apt-get','dnf','brew','pixi','docker','podman','wsl') -cnotcontains $value)) { return @{ outcome='error'; message='invalid observation' } }
        }
        $values[$key]=if ($fact.state -ceq 'known') { $fact.values[0] } else { '' }
    }
    $platform=@{os='';version=$values.version;architecture='';route='';ros_distro=$values.ros_distro;context=''}
    switch -CaseSensitive ($values.system) {
        'Linux' {
            $platform.os=$values.os_id; $platform.version=$values.os_version
            if ($values.kernel_release) { $platform.context=if ($values.kernel_release -match 'microsoft') { 'wsl' } else { 'native' } }
        }
        'Darwin' { $platform.os='macos';$platform.context='native' }
        'Windows' { $platform.os='windows';$platform.context='native' }
    }
    $machine=$values.machine.ToLowerInvariant()
    if (@('amd64','x86_64') -ccontains $machine) { $platform.architecture='amd64' }
    elseif (@('arm64','aarch64') -ccontains $machine) { $platform.architecture='arm64' }
    if ($platform.os -ceq 'ubuntu') { $platform.route='apt' }
    elseif ($platform.os -ceq 'macos') { $platform.route='pixi' }
    elseif ($platform.os -ceq 'windows') { $platform.route='wsl2' }
    return @{outcome='ok';value=$platform}
}
function Invoke-NativeRecipeProtocol([string]$Path) {
    try { $loaded=Read-NativeJson ([IO.File]::ReadAllText($Path)) }
    catch { $loaded=@{outcome='error';message='cannot read JSON file'} }
    $result=$loaded
    if ($loaded.outcome -eq 'ok') {
        $raw=$loaded.value
        if (-not (Test-NativeFields $raw @('schema_version','catalog','facts','request')) -or $raw.schema_version -is [bool] -or ($raw.schema_version -isnot [int] -and $raw.schema_version -isnot [long]) -or $raw.schema_version -ne 1) { $result=@{outcome='error';message='invalid protocol'} }
        else {
            $facts=Get-NativeFactsPlatform $raw.facts
            if ($facts.outcome -ne 'ok') { $result=$facts }
            else {
                $result=Select-NativeRecipe $raw.catalog $facts.value $raw.request
                if ($result.outcome -eq 'ok') {
                    $problem=Test-NativeRenderParameters $result.recipe $raw.request.parameters
                    if ($problem) { $result=@{outcome='error';message=$problem} }
                }
                if ($result.outcome -eq 'ok') {
                    $result=@{outcome='ok';schema_version=1;recipe=$result.recipe;parameters=$raw.request.parameters;rendered=(Format-NativeRecipe $result.recipe $raw.request.parameters);fingerprint=(Get-NativeFingerprint $result.recipe);admitted=(Test-NativeAdmission $result.recipe)}
                }
            }
        }
    }
    $result | ConvertTo-Json -Depth 40 -Compress
    if ($result.outcome -eq 'error') { return 2 }
    if ($result.outcome -eq 'unsupported') { return 1 }
    return 0
}

# --- dispatch ------------------------------------------------------------------

if ($NativeRecipeRequest) {
    $protocolOutput = @(Invoke-NativeRecipeProtocol $NativeRecipeRequest)
    $status = $protocolOutput[-1]
    $protocolOutput | Select-Object -SkipLast 1 | Write-Output
    exit $status
}

$Dispatch = [ordered]@{
    "choose"           = { Run-Choose }
    "desktop"          = { Run-Up; Run-Open }
    "up"               = { Run-Up }
    "open"             = { Run-Open }
    "image"            = { Run-Image }
    "shell"            = { Run-Shell }
    "turtlesim"        = { Run-Turtlesim }
    "turtlesim-teleop" = { Run-TurtlesimTeleop }
    "teleop"           = { Run-Teleop }
    "package"          = { Run-Package }
    "build"            = { Run-Build }
    "run"              = { Run-RunNode }
    "test"             = { Run-Test }
    "logs"             = { Run-Logs }
    "ps"               = { Run-Ps }
    "down"             = { Run-Down }
    "reset"            = { Run-Reset }
    "uninstall"        = { Run-Uninstall }
    "doctor"           = { Run-Doctor }
    "engine"           = { Run-Engine }
    "help"             = { Show-Help }
    "examples"         = { Show-TopicHelp @("examples") }
}

if (-not $Dispatch.Contains($Command)) {
    Write-Host "Unknown command: $Command" -ForegroundColor Red
    Write-Host ""
    Show-Help
    exit 1
}

# Validate before help interception, whose topic renderer normally uses Docker.
$override = Get-ExplainOverride
if ($override -ceq "only" -and ($HelpWords.Count -gt 0 -or $Command -in @("help", "examples"))) {
    Show-Help
    exit 0
}

# Like `make build help`: when help or examples is named with a command, in
# either order, only the help runs, never the command itself.
if ($Command -eq "help" -or $Command -eq "examples") {
    if ($Pkg) {
        Show-TopicHelp (@($Pkg, $Command) + $HelpWords)
        exit 0
    }
} elseif ($HelpWords.Count -gt 0) {
    Show-TopicHelp (@($Command) + $HelpWords)
    exit 0
}

if ($AskOnceCommands -contains $Command) { Invoke-AskOnce }
$mode = Get-ExplainOverride
if (-not $mode) { $mode = Read-SavedAnswer }
if ($mode -in @("on","only") -and $Command -notin @("help","examples","choose")) {
    $status = Show-NativeExplanation $mode
    if ($status -ne 0 -or $mode -eq "only") { exit $status }
}
& $Dispatch[$Command]
