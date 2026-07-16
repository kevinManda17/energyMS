# Rend joignables depuis le telephone, sur le reseau du partage de connexion
# uniquement : l'API Django (8000), le frontend Vite (5173) et le bundler
# Metro/Expo (8081 — sans lui, Expo Go ne peut pas telecharger le bundle JS).
#
# A LANCER DANS UN POWERSHELL ADMINISTRATEUR :
#   powershell -ExecutionPolicy Bypass -File .\open-lan-ports.ps1
#
# Pour tout annuler :
#   Remove-NetFirewallRule -DisplayName "EMS dev - *"

$ErrorActionPreference = "Stop"

$principal = New-Object Security.Principal.WindowsPrincipal(
    [Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Ce script doit etre lance depuis un PowerShell ADMINISTRATEUR."
}

# 1. Reclasser le reseau du partage de connexion en Prive.
#    Windows le marque Public par defaut, ce qui empeche toute regle Prive
#    de s'appliquer. C'est le hotspot du telephone : reseau de confiance.
# L'IP du partage de connexion change a chaque reseau : on ne la code pas en
# dur, on reclasse tout profil Public qui n'est pas le tunnel VPN.
$profiles = Get-NetConnectionProfile | Where-Object {
    $_.NetworkCategory -eq "Public" -and $_.InterfaceAlias -notmatch "WireGuard|Proton|TAP|VPN"
}
if (-not $profiles) {
    Write-Output "Aucun reseau Public a reclasser (deja Prive, ou seul le VPN est Public)."
} else {
    foreach ($p in $profiles) {
        Set-NetConnectionProfile -InterfaceIndex $p.InterfaceIndex -NetworkCategory Private
        Write-Output "Reseau '$($p.Name)' reclasse : Public -> Private"
    }
}

# 2. Ouvrir les deux ports, profil Prive uniquement.
$rules = @(
    @{ Name = "EMS dev - API Django 8000"; Port = 8000 },
    @{ Name = "EMS dev - Frontend Vite 5173"; Port = 5173 },
    @{ Name = "EMS dev - Metro Expo 8081"; Port = 8081 }
)
foreach ($r in $rules) {
    $existing = Get-NetFirewallRule -DisplayName $r.Name -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Output "Regle deja presente : $($r.Name)"
        continue
    }
    New-NetFirewallRule -DisplayName $r.Name -Direction Inbound -Action Allow `
        -Protocol TCP -LocalPort $r.Port -Profile Private | Out-Null
    Write-Output "Regle creee : $($r.Name) (TCP $($r.Port), profil Prive)"
}

Write-Output ""
Write-Output "Termine. Depuis le telephone, ouvrir http://<IP-de-cette-machine>:5173"
Write-Output "(l'IP est donnee par 'ipconfig' sur l'interface Wi-Fi)."
Write-Output "Si ca ne passe toujours pas, couper ProtonVPN (il peut router/bloquer le LAN)."
