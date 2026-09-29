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

$HelpWords = @()
$BareWords = @()
foreach ($word in $Rest) {
    if ($word -match '^([A-Z][A-Z0-9_]*)=(.*)$') {
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

# --- the ROS distribution ------------------------------------------------------
# The same resolution as the Makefile's scripts/distros, written out here
# because Windows may have no Python.  ROS_DISTRO comes from the environment
# (a ROS_DISTRO=name argument has just been put there), else .env, else the
# default in distros.json.  It resolves to the base digest, the image tag and
# a compose project of its own, hence its own /workspace.  The default's tag
# and project are `latest` and `ros2-tutorials`, what students already have.
# Explicit ROS_BASE_DIGEST, IMAGE_TAG and COMPOSE_PROJECT_NAME are kept.

$DistrosPath = Join-Path $scriptDir "distros.json"
$DotEnvPath = Join-Path $scriptDir ".env"

function Read-DotEnv([string]$Path) {
    <# NAME=value pairs as compose reads .env: blank lines and comments skipped,
       one pair of matching quotes stripped, a later line winning. #>
    $values = New-Object System.Collections.Hashtable ([StringComparer]::Ordinal)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $values }
    foreach ($raw in @(Get-Content -LiteralPath $Path)) {
        $line = "$raw".Trim()
        # [string] because .NET Framework, under 5.1, has no Contains(char).
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains([string]"=")) { continue }
        # -split, because .NET Framework has no String.Split(string, int).
        $parts = $line -split '=', 2
        $value = $parts[1].Trim()
        if ($value.Length -ge 2 -and $value[0] -eq $value[$value.Length - 1] -and ('"', "'") -contains [string]$value[0]) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        $values[$parts[0].Trim()] = $value
    }
    return $values
}

try {
    $DistroTable = Get-Content -Raw -LiteralPath $DistrosPath | ConvertFrom-Json
} catch {
    Write-Host "${DistrosPath}: cannot read it ($($_.Exception.Message))" -ForegroundColor Red
    exit 1
}
$DistroNames = @()
if ($DistroTable -and $DistroTable.distros) {
    $DistroNames = @($DistroTable.distros.PSObject.Properties | ForEach-Object { $_.Name } | Sort-Object)
}
$DefaultDistro = if ($DistroTable) { "$($DistroTable.default)" } else { "" }
if ($DistroNames.Count -eq 0 -or $DistroNames -cnotcontains $DefaultDistro) {
    Write-Host "${DistrosPath}: no ""distros"", or the default is not among them" -ForegroundColor Red
    exit 1
}

$DotEnv = Read-DotEnv $DotEnvPath
$RosDistro = if ($env:ROS_DISTRO) { $env:ROS_DISTRO } elseif ($DotEnv["ROS_DISTRO"]) { $DotEnv["ROS_DISTRO"] } else { $DefaultDistro }
if ($DistroNames -cnotcontains $RosDistro) {
    Write-Host "ROS_DISTRO=$RosDistro is not supported. Choose one of: $($DistroNames -join ' ')" -ForegroundColor Red
    exit 2
}

function Get-DistroTag([string]$Name) {
    if ($Name -ceq $DefaultDistro) { return "latest" } else { return $Name }
}

function Get-DistroProject([string]$Name) {
    if ($Name -ceq $DefaultDistro) { return "ros2-tutorials" } else { return "ros2-tutorials-$Name" }
}

$env:ROS_DISTRO = $RosDistro
if (-not $env:ROS_BASE_DIGEST) { $env:ROS_BASE_DIGEST = $DistroTable.distros.$RosDistro.digest }
if (-not $env:IMAGE_TAG) { $env:IMAGE_TAG = Get-DistroTag $RosDistro }
if (-not $env:COMPOSE_PROJECT_NAME) { $env:COMPOSE_PROJECT_NAME = Get-DistroProject $RosDistro }

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
    Write-Host "This removes the $env:COMPOSE_PROJECT_NAME containers ($env:ROS_DISTRO) and these volumes:"
    Write-Host "  $($env:COMPOSE_PROJECT_NAME)_ros-workspace   (src/, build/, install/, log/)"
    Write-Host "  $($env:COMPOSE_PROJECT_NAME)_ros-home        (shell history, rosdep cache, settings)"
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

# The same table and hint as `make distros`.
function Show-Distros {
    # An ArrayList, so each row stays one array; PowerShell would flatten them.
    $rows = New-Object System.Collections.ArrayList
    [void]$rows.Add([string[]]@("DISTRO", "UBUNTU", "IMAGE TAG", "COMPOSE PROJECT"))
    foreach ($name in $DistroNames) {
        [void]$rows.Add([string[]]@($name, "$($DistroTable.distros.$name.ubuntu)", (Get-DistroTag $name), (Get-DistroProject $name)))
    }
    $widths = @(0, 0, 0, 0)
    foreach ($row in $rows) {
        foreach ($i in 0..3) { if ($row[$i].Length -gt $widths[$i]) { $widths[$i] = $row[$i].Length } }
    }
    foreach ($row in $rows) {
        $cells = (@(foreach ($i in 0..3) { $row[$i].PadRight($widths[$i]) })) -join "  "
        if ($row[0] -ceq $DefaultDistro) { Write-Host "$cells  (default)" } else { Write-Host $cells.TrimEnd() }
    }
    Write-Host ""
    Write-Host "Choose one with ROS_DISTRO=<name>, e.g.  .\ros2.ps1 up ROS_DISTRO=jazzy"
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
        @{ Usage = "distros";                                  About = "List the ROS 2 distributions; pick one with ROS_DISTRO=name"; Native = "" }
        @{ Usage = "engine";                                   About = "Show which compose command is used";                        Native = "docker compose version" }
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
    Write-Host "Distribution: $env:ROS_DISTRO (compose project $env:COMPOSE_PROJECT_NAME); others: .\ros2.ps1 distros"
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

# --- dispatch ------------------------------------------------------------------

$Dispatch = [ordered]@{
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
    "distros"          = { Show-Distros }
    "help"             = { Show-Help }
    "examples"         = { Show-TopicHelp @("examples") }
}

if (-not $Dispatch.Contains($Command)) {
    Write-Host "Unknown command: $Command" -ForegroundColor Red
    Write-Host ""
    Show-Help
    exit 1
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

& $Dispatch[$Command]
