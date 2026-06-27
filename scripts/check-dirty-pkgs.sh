#!/bin/bash
# Report which git-backed debpkgs are behind their configured remote branch.
# Packages whose remote HEAD differs from the SHA recorded at last build time
# need ./scripts/bump-version.sh <pkg> "..." before being rebuilt.
#
# Skipped: tag-pinned (jack2-pistomp, lg-pistomp, sfizz-pistomp),
#          commit-pinned (jack-capture), tarball/local (ffmpeg, fluidsynth, lcd-splash, libfluidsynth2-compat).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../config.sh
source "${ROOT_DIR}/config.sh"

CACHE_DIR="${ROOT_DIR}/cache/debpkgs"

declare -A PKG_REPO PKG_REF
PKG_REPO[amidithru]="${AMIDITHRU_REPO}";                PKG_REF[amidithru]="${AMIDITHRU_REF}"
PKG_REPO[browsepy]="${BROWSEPY_REPO}";                  PKG_REF[browsepy]="${BROWSEPY_REF}"
PKG_REPO[cabsim-lv2]="${CABSIM_LV2_REPO}";             PKG_REF[cabsim-lv2]="${CABSIM_LV2_REF}"
PKG_REPO[hylia]="${HYLIA_REPO}";                        PKG_REF[hylia]="${HYLIA_REF}"
PKG_REPO[jackbridge]="${JACKROUTER_REPO}";              PKG_REF[jackbridge]="${JACKROUTER_REF}"
PKG_REPO[mod-host-pistomp]="${MOD_HOST_REPO}";         PKG_REF[mod-host-pistomp]="${MOD_HOST_BRANCH}"
PKG_REPO[mod-midi-merger]="${MOD_MIDI_MERGER_REPO}";   PKG_REF[mod-midi-merger]="${MOD_MIDI_MERGER_REF}"
PKG_REPO[mod-ttymidi]="${MOD_TTYMIDI_REPO}";           PKG_REF[mod-ttymidi]="${MOD_TTYMIDI_REF}"
PKG_REPO[mod-ui]="${MODUI_REPO}";                       PKG_REF[mod-ui]="${MODUI_BRANCH}"
PKG_REPO[pi-stomp]="${PISTOMP_REPO}";                   PKG_REF[pi-stomp]="${PISTOMP_BRANCH}"
PKG_REPO[pistomp-recovery]="${PISTOMP_RECOVERY_REPO}"; PKG_REF[pistomp-recovery]="${PISTOMP_RECOVERY_BRANCH}"

dirty=()
unknown=()
clean=()
errors=()

for pkg in $(echo "${!PKG_REPO[@]}" | tr ' ' '\n' | sort); do
    repo="${PKG_REPO[$pkg]}"
    ref="${PKG_REF[$pkg]}"
    sha_file="${CACHE_DIR}/${pkg}.built-sha"

    remote_sha=$(git ls-remote "$repo" "refs/heads/${ref}" 2>/dev/null | awk '{print $1}')
    if [ -z "$remote_sha" ]; then
        remote_sha=$(git ls-remote "$repo" "refs/tags/${ref}" 2>/dev/null | awk '{print $1}')
    fi
    if [ -z "$remote_sha" ]; then
        errors+=("${pkg}: could not resolve '${ref}' on ${repo}")
        continue
    fi

    if [ ! -f "$sha_file" ]; then
        unknown+=("${pkg}  remote=${remote_sha:0:12}  ref=${ref}")
        continue
    fi

    built_sha=$(cat "$sha_file")
    if [ "$built_sha" = "$remote_sha" ]; then
        clean+=("${pkg}  ${built_sha:0:12}  ref=${ref}")
    else
        dirty+=("${pkg}  built=${built_sha:0:12}  remote=${remote_sha:0:12}  ref=${ref}")
    fi
done

echo ""
if [ ${#dirty[@]} -gt 0 ]; then
    echo "DIRTY — upstream moved since last build (needs bump-version):"
    for d in "${dirty[@]}"; do echo "  $d"; done
else
    echo "DIRTY — none"
fi

echo ""
if [ ${#unknown[@]} -gt 0 ]; then
    echo "UNKNOWN — no .built-sha recorded (build once to establish baseline):"
    for u in "${unknown[@]}"; do echo "  $u"; done
fi

if [ ${#errors[@]} -gt 0 ]; then
    echo ""
    echo "ERRORS:"
    for e in "${errors[@]}"; do echo "  $e"; done
fi

echo ""
if [ ${#clean[@]} -gt 0 ]; then
    echo "CLEAN:"
    for c in "${clean[@]}"; do echo "  $c"; done
fi
echo ""
