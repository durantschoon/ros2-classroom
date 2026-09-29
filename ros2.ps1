param(
    [string]$Command = "desktop",
    [string]$Pkg = "",
    [string]$Node = "",
    [string]$Template = ""
)

$ErrorActionPreference = "Stop"

# Ensure working directory is the repository root
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Definition }
if ($scriptDir) {
    Set-Location $scriptDir
}

$NovncPort = if ($env:NOVNC_PORT) { $env:NOVNC_PORT } else { 6080 }
$Url = "http://127.0.0.1:$NovncPort"
$DesktopUrl = "$Url/vnc.html?autoconnect=1&resize=remote&reconnect=true"
$Service = "desktop"

function Check-Docker {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Host "Docker is not installed or not in PATH." -ForegroundColor Red
        Write-Host "Prerequisite: Please download and install Docker Desktop for Windows from:" -ForegroundColor Yellow
        Write-Host "  https://docs.docker.com/desktop/install/windows-install/"
        Write-Host "After installation, open Docker Desktop, wait for it to start, and run this again." -ForegroundColor Yellow
        exit 1
    }

    $prevEAP = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    docker info > $null 2>&1
    $daemonExit = $LASTEXITCODE
    $ErrorActionPreference = $prevEAP

    if ($daemonExit -ne 0) {
        Write-Host "Docker Desktop is installed, but the Docker engine is not running." -ForegroundColor Red
        Write-Host "Please start Docker Desktop from your Windows Start Menu, wait until it starts, and try again." -ForegroundColor Yellow
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
    Write-Host "`nThe desktop did not answer after 60s. Is it running? Details: docker compose logs" -ForegroundColor Red
    exit 1
}

function Run-Up {
    Check-Docker
    Write-Host "Pulling the latest prebuilt workstation image (this only takes a moment)..."
    docker compose pull --ignore-pull-failures
    Write-Host "Starting the ROS 2 workstation..."
    docker compose up -d
}

function Run-Open {
    Wait-For-Desktop
    Write-Host "Opening the browser to $DesktopUrl"
    Start-Process $DesktopUrl
    Write-Host ""
    Write-Host "Two terminals, two jobs:" -ForegroundColor Cyan
    Write-Host "  - THIS terminal, on your computer: every script command."
    Write-Host "      .\ros2.bat turtlesim   then   .\ros2.bat turtlesim-teleop"
    Write-Host "  - The terminal INSIDE the browser desktop: ROS commands"
    Write-Host "    (ros2, colcon, pkg). .\ros2.bat does not work in there."
}

function Run-Shell {
    Check-Docker
    Write-Host "Entering a ROS shell. Type exit to come back."
    docker compose run --rm shell
}

function Run-Turtlesim {
    Check-Docker
    docker compose exec -d -u ros -e DISPLAY=:1 $Service bash -lc 'nohup ros2 run turtlesim turtlesim_node >/tmp/turtlesim.log 2>&1 &'
    Write-Host "turtlesim started on the browser desktop ($Url)."
    Write-Host "Next, to drive the turtle:  .\ros2.bat turtlesim-teleop"
}

function Run-TurtlesimTeleop {
    Check-Docker
    docker compose exec -d -u ros -e DISPLAY=:1 $Service bash -lc "nohup xterm -title 'turtlesim teleop (arrow keys)' -bg white -fg black -u8 -fa 'DejaVu Sans Mono' -fs 11 -e bash -lc turtlesim-teleop >/tmp/teleop.log 2>&1 &"
    Write-Host "turtlesim teleop opened on the browser desktop."
    Write-Host "Click inside the WHITE window titled 'turtlesim teleop' to use arrow keys."
}

function Run-Package {
    Check-Docker
    if (-not $Pkg) {
        Write-Host "usage: .\ros2.bat package -Pkg name [-Template pubsub]" -ForegroundColor Red
        exit 1
    }
    $templateArg = if ($Template) { "--template $Template" } else { "" }
    docker compose exec -u ros -e DISPLAY=:1 -e PKG_VIA_MAKE=1 $Service bash -lc "pkg new $Pkg $templateArg"
}

function Run-Build {
    Check-Docker
    $pkgArg = if ($Pkg) { $Pkg } else { "" }
    docker compose exec -u ros -e DISPLAY=:1 -e PKG_VIA_MAKE=1 $Service bash -lc "pkg build $pkgArg"
}

function Run-Test {
    Check-Docker
    $pkgArg = if ($Pkg) { $Pkg } else { "" }
    docker compose exec -u ros -e DISPLAY=:1 -e PKG_VIA_MAKE=1 $Service bash -lc "pkg test $pkgArg"
}

function Run-RunNode {
    Check-Docker
    if (-not $Pkg -or -not $Node) {
        Write-Host "usage: .\ros2.bat run -Pkg name -Node executable" -ForegroundColor Red
        exit 1
    }
    docker compose exec -u ros -e DISPLAY=:1 -e PKG_VIA_MAKE=1 $Service bash -lc "pkg run $Pkg $Node"
}

function Run-Down {
    Check-Docker
    docker compose down
}

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
        @{ Usage = "package -Pkg NAME [-Template pubsub]";     About = "Create a package in /workspace/src";                        Native = "$exec pkg new NAME [--template pubsub]" }
        @{ Usage = "build [-Pkg NAME]";                        About = "Build one package, or all of them";                         Native = "$exec pkg build [NAME]" }
        @{ Usage = "run -Pkg NAME -Node EXECUTABLE";           About = "Run a node from your package";                              Native = "$exec pkg run NAME EXECUTABLE" }
        @{ Usage = "test [-Pkg NAME]";                         About = "Test one package, or all of them";                          Native = "$exec pkg test [NAME]" }
        @{ Usage = "down";                                     About = "Stop the containers (your work is kept)";                   Native = "docker compose down" }
        @{ Usage = "help";                                     About = "Show this help";                                            Native = "" }
    )

    Write-Host "Usage: .\ros2.ps1 COMMAND [options]    (or .\ros2.bat COMMAND [options])" -ForegroundColor Cyan
    Write-Host ""
    foreach ($entry in $commands) {
        Write-Host ("  {0,-40} {1}" -f $entry.Usage, $entry.About)
        if ($entry.Native) {
            Write-Host ("  {0,-40} runs: {1}" -f "", $entry.Native) -ForegroundColor DarkGray
        }
    }
    Write-Host ""
    Write-Host "Example:" -ForegroundColor Cyan
    Write-Host "  .\ros2.ps1 package -Pkg my_robot -Template pubsub"
    Write-Host "  .\ros2.ps1 build -Pkg my_robot"
    Write-Host "  .\ros2.ps1 run -Pkg my_robot -Node talker"
    Write-Host ""
    Write-Host "Desktop: $Url"
}

switch ($Command) {
    "desktop" { Run-Up; Run-Open }
    "up" { Run-Up }
    "open" { Run-Open }
    "shell" { Run-Shell }
    "turtlesim" { Run-Turtlesim }
    "turtlesim-teleop" { Run-TurtlesimTeleop }
    "package" { Run-Package }
    "build" { Run-Build }
    "test" { Run-Test }
    "run" { Run-RunNode }
    "down" { Run-Down }
    "help" { Show-Help }
    default {
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Write-Host ""
        Show-Help
        exit 1
    }
}
