#!/usr/bin/env bash
#
# setup_system.sh
#
# Automates the system configuration described in the Walker README:
#
#   "Requirements" / "Phidget22" (apt dependencies)
#     - installs the apt build dependencies (build-essential cmake git clang
#       libeigen3-dev) and, if needed, registers the Phidgets apt repository
#       and installs libphidget22. MADS is NOT installed by this script - it
#       is a separate GitHub release, see the README.
#
#   "Configure USB Power Delivery via Software"
#     - sets usb_max_current_enable=1 in the Raspberry Pi firmware config
#       (/boot/firmware/config.txt, or /boot/config.txt on older images);
#
#   "Remove root permission to files for serial communication"
#     - adds the target user to the "dialout" group;
#     - installs the udev rule for Phidget devices
#       (/etc/udev/rules.d/99-libphidget22.rules);
#     - installs the udev rules for the Driver and Portenta boards
#       (/etc/udev/rules.d/99-usb-serial.rules), providing the /dev/drivers
#       and /dev/portenta symlinks;
#     - reloads and re-triggers udev.
#
# The script is idempotent: every change is applied only when it is missing or
# different from what is expected, so a second run on an already configured
# machine does nothing.  Existing settings are updated in place instead of
# being duplicated.  Each file that is actually modified is first backed up to
# "<file>.bak" (the first backup is kept, so it always holds the pristine
# original).
#
# Usage:
#   sudo ./setup_system.sh [options]
#
# Options:
#   -o, --only TASK   run only one task: "deps", "usb-power" or "serial"
#                     (default: all, in that order)
#   -u, --user USER   user to add to the dialout group
#                     (default: $SUDO_USER, or the invoking user)
#   -s, --serial SN   serial number of the Portenta board
#                     (default: 004200473033510A34323437, env PORTENTA_SERIAL)
#   -f, --file PATH   firmware config file to edit
#                     (default: /boot/firmware/config.txt, then /boot/config.txt)
#   -v, --value VAL   value for usb_max_current_enable (default: 1)
#   -n, --dry-run     report what would be done, change nothing (no root needed)
#   -h, --help        show this help and exit

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
SCRIPT_PATH="$(cd "$(dirname "$0")" 2>/dev/null && pwd)/${SCRIPT_NAME}"
[[ -f $SCRIPT_PATH ]] || SCRIPT_PATH="$(command -v -- "$0" 2>/dev/null || echo "$0")"

# --- apt dependencies -----------------------------------------------------
APT_PACKAGES=(build-essential cmake git clang libeigen3-dev)
PHIDGET_PACKAGE="libphidget22"
PHIDGET_SETUP_URL="https://www.phidgets.com/downloads/setup_linux"

# --- USB power delivery -------------------------------------------------------
USB_KEY="usb_max_current_enable"
USB_VALUE="${USB_VALUE:-1}"
CONFIG_FILE="${CONFIG_FILE:-}"

# --- serial permissions -------------------------------------------------------
PHIDGET_RULES="${PHIDGET_RULES:-/etc/udev/rules.d/99-libphidget22.rules}"
SERIAL_RULES="${SERIAL_RULES:-/etc/udev/rules.d/99-usb-serial.rules}"
PORTENTA_SERIAL="${PORTENTA_SERIAL:-004200473033510A34323437}"
TARGET_USER=""

BEGIN_MARK="# >>> Walker serial permissions - managed by setup_system.sh, do not edit >>>"
END_MARK="# <<< Walker serial permissions <<<"

TASKS="all"
DRY_RUN=0
CHANGES=0
DEPS_CHANGED=0
BOOT_CHANGED=0
UDEV_CHANGED=0
GROUP_CHANGED=0

# ---------------------------------------------------------------- logging ---
if [[ -t 1 ]]; then
  C_RESET=$'\033[0m'; C_INFO=$'\033[36m'; C_OK=$'\033[32m'
  C_WARN=$'\033[33m'; C_ERR=$'\033[31m'
else
  C_RESET=""; C_INFO=""; C_OK=""; C_WARN=""; C_ERR=""
fi

info() { printf '%s==>%s %s\n' "$C_INFO" "$C_RESET" "$*"; }
ok()   { printf '%s  ok%s %s\n' "$C_OK" "$C_RESET" "$*"; }
chg()  { printf '%s mod%s %s\n' "$C_WARN" "$C_RESET" "$*"; CHANGES=$((CHANGES + 1)); }
warn() { printf '%swarn%s %s\n' "$C_WARN" "$C_RESET" "$*" >&2; }
die()  { printf '%serr %s %s\n' "$C_ERR" "$C_RESET" "$*" >&2; exit 1; }
head1() { printf '\n%s--- %s ---%s\n' "$C_INFO" "$*" "$C_RESET"; }

usage() { awk 'NR==1 {next} /^#/ {sub(/^# ?/, ""); print; next} {exit}' "$SCRIPT_PATH"; }

# ------------------------------------------------------------ CLI parsing ---
CONFIG_FILE_GIVEN=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    -o|--only)    TASKS="${2:-}"; shift 2 ;;
    -u|--user)    TARGET_USER="${2:-}"; [[ -n $TARGET_USER ]] || die "--user needs an argument"; shift 2 ;;
    -s|--serial)  PORTENTA_SERIAL="${2:-}"; [[ -n $PORTENTA_SERIAL ]] || die "--serial needs an argument"; shift 2 ;;
    -f|--file)    CONFIG_FILE="${2:-}"; CONFIG_FILE_GIVEN=1; [[ -n $CONFIG_FILE ]] || die "--file needs an argument"; shift 2 ;;
    -v|--value)   USB_VALUE="${2:-}"; [[ -n $USB_VALUE ]] || die "--value needs an argument"; shift 2 ;;
    -n|--dry-run) DRY_RUN=1; shift ;;
    -h|--help)    usage; exit 0 ;;
    *)            die "unknown option: $1 (try --help)" ;;
  esac
done

case "$TASKS" in
  all|deps|usb-power|serial) ;;
  *) die "unknown task '$TASKS' (expected: all, deps, usb-power, serial)" ;;
esac
DO_DEPS=0; DO_USB_POWER=0; DO_SERIAL=0
[[ $TASKS == all || $TASKS == deps      ]] && DO_DEPS=1
[[ $TASKS == all || $TASKS == usb-power ]] && DO_USB_POWER=1
[[ $TASKS == all || $TASKS == serial    ]] && DO_SERIAL=1

# ------------------------------------------------------ environment checks ---
[[ "$(uname -s)" == "Linux" ]] || die "this script only makes sense on Linux (found $(uname -s))"

if [[ -z $TARGET_USER ]]; then
  TARGET_USER="${SUDO_USER:-}"
  [[ -n $TARGET_USER ]] || TARGET_USER="$(logname 2>/dev/null || id -un)"
fi
id -u "$TARGET_USER" >/dev/null 2>&1 || die "user '$TARGET_USER' does not exist"

if [[ $DO_USB_POWER -eq 1 && -z $CONFIG_FILE ]]; then
  for candidate in /boot/firmware/config.txt /boot/config.txt; do
    [[ -f $candidate ]] && { CONFIG_FILE="$candidate"; break; }
  done
fi

# Re-exec through sudo when we actually have to write something.
if [[ $DRY_RUN -eq 0 && $EUID -ne 0 ]]; then
  command -v sudo >/dev/null 2>&1 || die "root privileges required (run as root or install sudo)"
  info "elevating privileges with sudo..."
  sudo_args=(--only "$TASKS" --user "$TARGET_USER" --serial "$PORTENTA_SERIAL" --value "$USB_VALUE")
  [[ -n $CONFIG_FILE ]] && sudo_args+=(--file "$CONFIG_FILE")
  exec sudo -- "$SCRIPT_PATH" "${sudo_args[@]}"
fi

[[ $DRY_RUN -eq 1 ]] && info "dry run: no file will be modified"

# ------------------------------------------------------------------ common ---

# Back up a file to <file>.bak, keeping the first (pristine) backup.
backup_file() {
  local file="$1" bak="$1.bak"
  [[ -f $file ]] || return 0
  if [[ -f $bak ]]; then
    info "backup $bak already exists, keeping the original one"
    return 0
  fi
  if [[ $DRY_RUN -eq 1 ]]; then
    info "would back up $file to $bak"
  else
    cp -p -- "$file" "$bak" 2>/dev/null || cp -- "$file" "$bak"
    info "backed up $file to $bak"
  fi
}

# ============================================================================
#  Task 1: apt dependencies  (build tools + Phidget22 driver)
# ============================================================================

# True (0) if the given dpkg package is installed.
pkg_installed() {
  dpkg-query -W -f='${Status}' "$1" 2>/dev/null | grep -q '^install ok installed'
}

# True (0) if an apt source for the Phidgets repository is already registered.
phidget_repo_present() {
  grep -r -l -i 'phidgets\.com' /etc/apt/sources.list /etc/apt/sources.list.d/ 2>/dev/null | grep -q .
}

task_deps() {
  head1 "apt dependencies"

  if ! command -v dpkg-query >/dev/null 2>&1 || ! command -v apt-get >/dev/null 2>&1; then
    warn "apt/dpkg not found on this system: skipping dependency installation"
    return 0
  fi

  local missing=() pkg
  for pkg in "${APT_PACKAGES[@]}"; do
    pkg_installed "$pkg" || missing+=("$pkg")
  done

  local need_repo=0
  if ! pkg_installed "$PHIDGET_PACKAGE"; then
    missing+=("$PHIDGET_PACKAGE")
    if ! phidget_repo_present; then
      need_repo=1
    fi
  fi

  if [[ ${#missing[@]} -eq 0 ]]; then
    ok "all required apt packages already installed (${APT_PACKAGES[*]} $PHIDGET_PACKAGE)"
    return 0
  fi

  DEPS_CHANGED=1

  if [[ $need_repo -eq 1 ]]; then
    chg "registering the Phidgets apt repository ($PHIDGET_SETUP_URL)"
    if [[ $DRY_RUN -eq 0 ]]; then
      command -v curl >/dev/null 2>&1 || die "curl is required to register the Phidgets apt repository"
      curl -fsSL "$PHIDGET_SETUP_URL" | bash -
    fi
  fi

  chg "installing missing apt package(s): ${missing[*]}"
  if [[ $DRY_RUN -eq 0 ]]; then
    apt-get update -qq
    apt-get install -y "${missing[@]}"
    ok "installed: ${missing[*]}"
  fi
}

# ============================================================================
#  Task 2: USB power delivery  (config.txt)
# ============================================================================

# List every occurrence of the key as "<line>\t<section>\t<active|commented>\t<value>".
scan_occurrences() {
  awk -v K="$USB_KEY" '
    BEGIN { sec = "(global)" }
    {
      L = $0; sub(/\r$/, "", L)          # tolerate CRLF files
      if (L ~ /^[ \t]*\[[^]]*\][ \t]*$/) {
        s = L; gsub(/^[ \t]+|[ \t]+$/, "", s); sec = s; next
      }
      if (match(L, "^[ \t]*" K "[ \t]*=")) {
        v = substr(L, RSTART + RLENGTH); gsub(/^[ \t]+|[ \t]+$/, "", v)
        print NR "\t" sec "\tactive\t" v; next
      }
      if (match(L, "^[ \t]*#+[ \t]*" K "[ \t]*=")) {
        v = substr(L, RSTART + RLENGTH); gsub(/^[ \t]+|[ \t]+$/, "", v)
        print NR "\t" sec "\tcommented\t" v
      }
    }' "$CONFIG_FILE"
}

# Last section header of the file, "(global)" if the file has none.
last_section() {
  awk '{ L = $0; sub(/\r$/, "", L)
         if (L ~ /^[ \t]*\[[^]]*\][ \t]*$/) { s = L; gsub(/^[ \t]+|[ \t]+$/, "", s) } }
       END { print (s == "" ? "(global)" : s) }' "$CONFIG_FILE"
}

# Replace the given (comma separated) line numbers with "KEY=VALUE".
rewrite_lines() {
  awk -v K="$USB_KEY" -v V="$USB_VALUE" -v LINES="$1" '
    BEGIN { n = split(LINES, a, ","); for (i = 1; i <= n; i++) target[a[i] + 0] = 1 }
    { if (NR in target) print K "=" V; else print }' "$CONFIG_FILE"
}

task_usb_power() {
  head1 "USB power delivery"

  if [[ -z $CONFIG_FILE ]]; then
    warn "no Raspberry Pi firmware config found (looked for /boot/firmware/config.txt"
    warn "and /boot/config.txt): skipping the USB power configuration, use --file to force one"
    return 0
  fi
  if [[ ! -f $CONFIG_FILE ]]; then
    [[ $CONFIG_FILE_GIVEN -eq 1 ]] && die "$CONFIG_FILE does not exist (this script does not create a firmware config from scratch)"
    warn "$CONFIG_FILE does not exist, skipping the USB power configuration"
    return 0
  fi

  info "checking $USB_KEY in $CONFIG_FILE"

  local occurrences active commented wrong dupes lines sec new_content action line val
  occurrences="$(scan_occurrences)"
  active="$(printf '%s\n' "$occurrences" | awk -F'\t' '$3 == "active"')"
  commented="$(printf '%s\n' "$occurrences" | awk -F'\t' '$3 == "commented"')"
  new_content=""; action=""

  if [[ -n $active ]]; then
    # One or more active settings: fix the ones that do not already hold USB_VALUE.
    wrong="$(printf '%s\n' "$active" | awk -F'\t' -v V="$USB_VALUE" '$4 != V')"
    dupes="$(printf '%s\n' "$active" | grep -c '' || true)"
    if [[ -z $wrong ]]; then
      [[ $dupes -gt 1 ]] && warn "$USB_KEY is set to $USB_VALUE in $dupes places, leaving them alone"
      ok "$USB_KEY=$USB_VALUE already set in $CONFIG_FILE"
    else
      while IFS=$'\t' read -r line sec _ val; do
        [[ -n $line ]] || continue
        chg "updating line $line of section $sec: $USB_KEY=$val -> $USB_KEY=$USB_VALUE"
      done <<< "$wrong"
      new_content="$(rewrite_lines "$(printf '%s\n' "$wrong" | cut -f1 | paste -sd, -)")"
      action="update"
    fi
  elif [[ -n $commented ]]; then
    # No active setting, but the key is commented out: enable that occurrence.
    IFS=$'\t' read -r line sec _ val <<< "$(printf '%s\n' "$commented" | tail -1)"
    chg "enabling the commented $USB_KEY at line $line of section $sec (was: $val)"
    new_content="$(rewrite_lines "$line")"
    action="update"
  else
    # Not there at all: append it, under [all] when the file uses sections.
    sec="$(last_section)"
    new_content="$(cat "$CONFIG_FILE")"
    if [[ $sec == "(global)" || $sec == "[all]" ]]; then
      chg "appending $USB_KEY=$USB_VALUE to $CONFIG_FILE (section $sec)"
      new_content+=$'\n'"$USB_KEY=$USB_VALUE"
    else
      chg "appending an [all] section with $USB_KEY=$USB_VALUE to $CONFIG_FILE (last section was $sec)"
      new_content+=$'\n\n[all]\n'"$USB_KEY=$USB_VALUE"
    fi
    action="append"
  fi

  [[ -n $action ]] || return 0
  BOOT_CHANGED=1

  if [[ $DRY_RUN -eq 1 ]]; then
    info "would write $CONFIG_FILE:"
    if command -v diff >/dev/null 2>&1; then
      diff -u "$CONFIG_FILE" <(printf '%s\n' "$new_content") | sed 's/^/      /' || true
    else
      printf '%s\n' "$new_content" | sed 's/^/      /'
    fi
    return 0
  fi

  backup_file "$CONFIG_FILE"
  local tmp; tmp="$(mktemp "${CONFIG_FILE}.XXXXXX")"
  printf '%s\n' "$new_content" > "$tmp"
  chmod --reference="$CONFIG_FILE" "$tmp" 2>/dev/null || chmod 0755 "$tmp" 2>/dev/null || true
  chown --reference="$CONFIG_FILE" "$tmp" 2>/dev/null || true
  mv -f -- "$tmp" "$CONFIG_FILE"
  ok "written $CONFIG_FILE"
}

# ============================================================================
#  Task 3: serial permissions  (dialout group + udev rules)
# ============================================================================

# Extract "vendor:product" from a udev rule line, so that an older, manually
# written rule for the same device can be replaced instead of duplicated.
rule_key() {
  local line="$1" vendor product
  vendor="$(sed -n 's/.*idVendor}=="\([^"]*\)".*/\1/p' <<<"$line")"
  product="$(sed -n 's/.*idProduct}=="\([^"]*\)".*/\1/p' <<<"$line")"
  [[ -n $vendor && -n $product ]] || return 1
  printf '%s:%s' "$vendor" "$product"
}

# ensure_block <file> <description> <rule line> [<rule line> ...]
#
# Makes sure <file> contains exactly the given rules inside the managed block.
# Content outside the block is preserved, except stale rules matching the same
# vendor/product pair, which are dropped (updated, not duplicated).
ensure_block() {
  local file="$1" desc="$2"; shift 2
  local rules=("$@")
  local desired current tmp line key k stale in_block content
  local keys=() kept=() dropped=()

  desired="$(printf '%s\n' "${rules[@]}")"

  for line in "${rules[@]}"; do
    [[ $line == \#* || -z $line ]] && continue
    if key="$(rule_key "$line")"; then keys+=("$key"); fi
  done

  # Split the existing file into "managed block" and "everything else".
  current=""
  if [[ -f $file ]]; then
    in_block=0
    while IFS= read -r line || [[ -n $line ]]; do
      if [[ $line == "$BEGIN_MARK" ]]; then in_block=1; continue; fi
      if [[ $line == "$END_MARK"   ]]; then in_block=0; continue; fi
      if [[ $in_block -eq 1 ]]; then
        current+="$line"$'\n'
        continue
      fi
      # Outside the block: drop stale rules for the same devices.
      if key="$(rule_key "$line" 2>/dev/null)"; then
        stale=0
        for k in "${keys[@]}"; do [[ $k == "$key" ]] && stale=1; done
        if [[ $stale -eq 1 ]]; then dropped+=("$line"); continue; fi
      fi
      kept+=("$line")
    done < "$file"
  fi

  if [[ ${#dropped[@]} -eq 0 && "${current%$'\n'}" == "$desired" ]]; then
    ok "$desc: $file already up to date"
    return 0
  fi

  if [[ -f $file ]]; then
    if [[ -z $current ]]; then
      chg "$desc: adding the Walker rules to the existing $file"
    else
      chg "$desc: updating the Walker rules in $file"
    fi
  else
    chg "$desc: creating $file"
  fi
  for line in "${dropped[@]:-}"; do
    [[ -n $line ]] && info "  superseding pre-existing rule: $line"
  done
  UDEV_CHANGED=1

  # Rebuild the file: preserved content first, managed block last.
  content=""
  if [[ ${#kept[@]} -gt 0 ]]; then
    content="$(printf '%s\n' "${kept[@]}")"
    content="${content%$'\n'}"
    # Drop trailing blank lines left over by the removals.
    while [[ $content == *$'\n' || $content == *' ' ]]; do content="${content%[$' \n']}"; done
    [[ -n $content ]] && content+=$'\n\n'
  fi
  content+="$BEGIN_MARK"$'\n'"$desired"$'\n'"$END_MARK"$'\n'

  if [[ $DRY_RUN -eq 1 ]]; then
    info "would write $file:"
    printf '%s\n' "$content" | sed 's/^/      /'
    return 0
  fi

  backup_file "$file"
  tmp="$(mktemp "${file}.XXXXXX")"
  printf '%s' "$content" > "$tmp"
  chmod 0644 "$tmp"
  chown root:root "$tmp" 2>/dev/null || true
  mv -f -- "$tmp" "$file"
  ok "$desc: written $file"
}

task_serial() {
  head1 "serial communication permissions"

  # --- dialout group ---
  info "checking group membership for user '$TARGET_USER'"
  if ! getent group dialout >/dev/null 2>&1; then
    warn "group 'dialout' does not exist on this system, skipping"
  elif id -nG "$TARGET_USER" | tr ' ' '\n' | grep -qx dialout; then
    ok "user '$TARGET_USER' is already in the 'dialout' group"
  else
    chg "adding user '$TARGET_USER' to the 'dialout' group"
    GROUP_CHANGED=1
    if [[ $DRY_RUN -eq 0 ]]; then
      usermod -aG dialout "$TARGET_USER"
      ok "user '$TARGET_USER' added to 'dialout'"
    fi
  fi

  # --- udev rules ---
  local rules_dir; rules_dir="$(dirname "$PHIDGET_RULES")"
  if [[ ! -d $rules_dir ]]; then
    if [[ $DRY_RUN -eq 1 ]]; then
      info "would create $rules_dir"
    else
      mkdir -p "$rules_dir"
      info "created $rules_dir"
    fi
  fi

  info "checking Phidget udev rule"
  ensure_block "$PHIDGET_RULES" "Phidget" \
    '# All current and future Phidgets - Vendor = 0x06c2, Product = 0x0030 - 0x00af' \
    'SUBSYSTEMS=="usb", ACTION=="add", ATTRS{idVendor}=="06c2", ATTRS{idProduct}=="00[3-a][0-f]", MODE="666"'

  info "checking Driver/Portenta udev rules"
  ensure_block "$SERIAL_RULES" "USB serial" \
    '# Motor driver board -> /dev/drivers' \
    'SUBSYSTEM=="tty", ATTRS{idVendor}=="20d2", ATTRS{idProduct}=="5740", SYMLINK+="drivers", MODE="0666"' \
    '# Portenta board -> /dev/portenta' \
    "SUBSYSTEM==\"tty\", ATTRS{idVendor}==\"2341\", ATTRS{idProduct}==\"025b\", ATTRS{serial}==\"${PORTENTA_SERIAL}\", SYMLINK+=\"portenta\", MODE=\"0666\""
}

# ============================================================================
#  Main
# ============================================================================
[[ $DO_DEPS      -eq 1 ]] && task_deps
[[ $DO_USB_POWER -eq 1 ]] && task_usb_power
[[ $DO_SERIAL    -eq 1 ]] && task_serial

head1 "summary"
if [[ $CHANGES -eq 0 ]]; then
  info "nothing to do, the system is already configured"
  exit 0
fi

if [[ $DRY_RUN -eq 1 ]]; then
  info "dry run finished: $CHANGES change(s) would be applied"
  exit 0
fi

if [[ $UDEV_CHANGED -eq 1 ]]; then
  if command -v udevadm >/dev/null 2>&1; then
    info "reloading udev rules"
    udevadm control --reload-rules
    udevadm trigger --subsystem-match=usb --subsystem-match=tty || true
    ok "udev rules reloaded"
  else
    warn "udevadm not found: reboot to apply the new rules"
  fi
fi

info "$CHANGES change(s) applied"
[[ $DEPS_CHANGED  -eq 1 ]] && info "apt packages installed/updated"
[[ $UDEV_CHANGED  -eq 1 ]] && info "unplug/replug the boards so that the new udev rules are applied"
[[ $GROUP_CHANGED -eq 1 ]] && info "open a new login session so that the 'dialout' membership of '$TARGET_USER' takes effect"
[[ $BOOT_CHANGED  -eq 1 ]] && info "reboot for the new USB power setting to take effect"
exit 0
