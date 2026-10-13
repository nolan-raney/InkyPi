# Wi-Fi recovery and access-point migration

The Pi uses NetworkManager. It can save multiple Wi-Fi profiles and automatically select
an available one when reconnecting. A larger `connection.autoconnect-priority` is preferred;
changing that priority does not force a healthy active connection to switch immediately.
Keep the existing network available while staging/testing a replacement.

The Pi Zero 2 W supports **2.4 GHz Wi-Fi**, so the new access points must provide 2.4 GHz
service with compatible security. A 5/6 GHz-only SSID will not work. See the
[Raspberry Pi specification](https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/) and
[NetworkManager CLI reference](https://networkmanager.pages.freedesktop.org/NetworkManager/NetworkManager/nmcli.html).

## Inspect connections without showing passwords

Run on the Pi:

```bash
nmcli -f NAME,UUID,AUTOCONNECT,AUTOCONNECT-PRIORITY connection show
nmcli -f GENERAL.CONNECTION,IP4.ADDRESS,IP4.GATEWAY device show wlan0
nmcli -f SSID,SIGNAL,SECURITY device wifi list ifname wlan0
```

NetworkManager stores credentials in root-protected profiles. Never put real passwords
into Git, command-line arguments, or a public recovery guide.

## New APs keeping the same SSID/password

An existing profile can connect to different APs advertising the same SSID with compatible
security and the same password, provided it is not pinned to a BSSID. No new profile is
needed solely because the access-point hardware changed. Keep 2.4 GHz enabled and preserve
the intended LAN access to TrueNAS.

## Stage a new SSID with the same password

Replace `CURRENT PROFILE` and `NEW SSID` with the actual profile name and new network name:

```bash
sudo nmcli connection clone 'CURRENT PROFILE' 'InkyPi - New WiFi'
sudo nmcli connection modify 'InkyPi - New WiFi' \
  802-11-wireless.ssid 'NEW SSID' \
  802-11-wireless.bssid '' \
  connection.autoconnect yes \
  connection.autoconnect-priority 30
```

Cloning reuses the existing credentials without displaying them. These commands save the
new profile without disconnecting the current Wi-Fi. When the new AP is ready and visible:

```bash
sudo nmcli connection up 'InkyPi - New WiFi' ifname wlan0
```

SSH may disconnect during activation or if the IP changes. Reconnect by hostname/IP and
verify `nmcli device status`, TrueNAS reachability, and `inkypi-photo-sync.service`. Do not
remove the old profiles until the new connection works. NetworkManager also provides a
checkpoint command for remote changes with timeout rollback; use it when making more
complex network changes rather than removing the only working connection.

## New SSID/password

Use an interactive terminal on the Pi (or an interactive SSH session):

```bash
sudo nmcli --ask device wifi connect 'NEW SSID' ifname wlan0 name 'InkyPi - New WiFi'
sudo nmcli connection modify 'InkyPi - New WiFi' connection.autoconnect yes connection.autoconnect-priority 30
```

Enter the password at the prompt; this connects immediately. Keep the old network available
and reconnect if SSH drops. For remote staging when the password changes, arrange secure
credential entry before switching the active connection.

## Router/LAN changes

The photo NFS share is restricted to the Pi's LAN IP; the mount also contains the NAS IP.
Reserve the Pi's address in the new router. If addresses change, update the photo NFS
authorized host through the TrueNAS UI/API and update only the photo mount's server address
in `/etc/fstab`. Restart the sync job and confirm successful cache updates. Existing media
exports are independent and should not be edited as part of the Pi Wi-Fi change.

Cached photos keep rotating while the Pi is offline or the NAS is unreachable. This does
not provide remote administration or delivery of new photos until connectivity returns.

## Recover saved profiles after an SD-card replacement

First connect the fresh Pi to Wi-Fi through Raspberry Pi Imager or interactive `nmcli`;
network access is required to read a backup from the NAS. The private snapshot is at
`InkyPhotos/.recovery/inkypi-wifi-profiles-latest.tar.gz`, excluded from photo sync and Git.
It contains real Wi-Fi credentials and is not an automatic recurring backup. Restore only
profiles for networks that are still valid; it cannot contain a future network configured
after the snapshot.

After mounting the NAS using the [photo-frame recovery guide](folder-photos-recovery.md):

```bash
sudo install -d -m 700 ~/inky-recovery-backups
sudo tar -xzf /mnt/inkypi-photos/.recovery/inkypi-wifi-profiles-latest.tar.gz -C ~/inky-recovery-backups
```

Select a recovered profile, then copy it under a **new filename** so the fresh Pi's working
profile is not overwritten:

```bash
sudo install -m 600 -o root -g root \
  '/path/to/recovered/profile.nmconnection' \
  '/etc/NetworkManager/system-connections/recovered-home.nmconnection'
sudo nmcli connection reload
nmcli connection show
```

Use a distinct destination filename for each profile. Check for UUID/name conflicts before
loading a profile over an existing installation. Refresh the private NAS snapshot after
changing Wi-Fi configuration; do not copy the keyfiles into the source repository.
