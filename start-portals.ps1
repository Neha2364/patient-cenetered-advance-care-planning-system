# ACP Care - Start All Three Portals
# -------------------------------------------------------------------
# Portal layout:
#   Patient Portal  ->  http://localhost:8080   (Vite dev server)
#   Doctor Portal   ->  http://localhost:8081   (reverse proxy -> 8080/doctor-login)
#   Admin Portal    ->  http://localhost:8082   (reverse proxy -> 8080/admin-login)
#
# Backend (Flask) must be started separately in its own terminal:
#   cd C:\ACP_System\backend; python app.py
#
# Usage:
#   cd C:\ACP_System
#   .\start-portals.ps1
# -------------------------------------------------------------------

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "  ACP Care - Starting all portals" -ForegroundColor Cyan
Write-Host ""

# 0. Clean up stale processes on ports 8080, 8081, 8082
$stalePorts = @(8080, 8081, 8082)
foreach ($port in $stalePorts) {
    try {
        $conns = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
        if ($conns) {
            foreach ($c in $conns) {
                if ($c.OwningProcess -and $c.OwningProcess -gt 0) {
                    Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
                }
            }
        }
    } catch {
        # Ignore errors during cleanup
    }
}

# 1. Patient Portal (Vite dev server on 8080)
$frontendDir = Join-Path -Path $root -ChildPath "frontend"
Write-Host "  [1/3] Starting Patient Portal (Vite dev server) on port 8080..." -ForegroundColor Green
$patientJob = Start-Process -FilePath "cmd.exe" `
  -ArgumentList "/c npm run dev -- --port 8080 --host 127.0.0.1 --strictPort" `
  -WorkingDirectory $frontendDir `
  -PassThru `
  -WindowStyle Normal

# Wait until port 8080 is listening or timeout after 15 seconds
$port8080Ready = $false
for ($i = 0; $i -lt 15; $i++) {
    Start-Sleep -Seconds 1
    $conn = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue
    if ($conn) {
        $port8080Ready = $true
        break
    }
}
if (-not $port8080Ready) {
    Write-Host "  Note: Port 8080 not yet detected as Listen, proceeding with proxy launch..." -ForegroundColor Yellow
}

# 2. Doctor Portal (proxy on 8081)
$doctorProxy = Join-Path -Path $root -ChildPath "dev-proxy-doctor.cjs"
Write-Host "  [2/3] Starting Doctor Portal proxy on port 8081..." -ForegroundColor Green
$doctorJob = Start-Process -FilePath "node" `
  -ArgumentList "`"$doctorProxy`"" `
  -WorkingDirectory $root `
  -PassThru `
  -WindowStyle Normal

# 3. Admin Portal (proxy on 8082)
$adminProxy = Join-Path -Path $root -ChildPath "dev-proxy-admin.cjs"
Write-Host "  [3/3] Starting Admin Portal proxy on port 8082..." -ForegroundColor Green
$adminJob = Start-Process -FilePath "node" `
  -ArgumentList "`"$adminProxy`"" `
  -WorkingDirectory $root `
  -PassThru `
  -WindowStyle Normal

Start-Sleep -Seconds 2

Write-Host ""
Write-Host "  -----------------------------------------------------" -ForegroundColor DarkGray
Write-Host "  Patient Portal  ->  http://localhost:8080" -ForegroundColor White
Write-Host "  Doctor Portal   ->  http://localhost:8081" -ForegroundColor White
Write-Host "  Admin Portal    ->  http://localhost:8082" -ForegroundColor White
Write-Host "  -----------------------------------------------------" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Backend must be running separately:" -ForegroundColor Yellow
Write-Host "    cd C:\ACP_System\backend; python app.py" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Press Ctrl+C to stop all portals." -ForegroundColor DarkGray
Write-Host ""

# Keep script alive, cleanup on exit
try {
  Wait-Process -Id $patientJob.Id
} catch {
  # Patient process ended or interrupted
} finally {
  if ($doctorJob -and -not $doctorJob.HasExited) {
    Stop-Process -Id $doctorJob.Id -Force -ErrorAction SilentlyContinue
  }
  if ($adminJob -and -not $adminJob.HasExited) {
    Stop-Process -Id $adminJob.Id -Force -ErrorAction SilentlyContinue
  }
  if ($patientJob -and -not $patientJob.HasExited) {
    Stop-Process -Id $patientJob.Id -Force -ErrorAction SilentlyContinue
  }
}
