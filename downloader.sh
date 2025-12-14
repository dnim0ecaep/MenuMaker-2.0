#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="./bin/backup"
mkdir -p "$BASE_DIR"

declare -A tools

# Dashboards
tools[btop]="https://github.com/aristocratos/btop/releases/latest/download/btop-x86_64-linux-musl.tbz"
tools[bottom]="https://github.com/ClementTsang/bottom/releases/latest/download/bottom_x86_64-unknown-linux-gnu.tar.gz"
tools[bandwhich]="https://github.com/imsnif/bandwhich/releases/latest/download/bandwhich-x86_64-unknown-linux-musl.tar.gz"
tools[gping]="https://github.com/orf/gping/releases/latest/download/gping-x86_64-unknown-linux-musl.tar.gz"
tools[gotop]="https://github.com/xxxserxxx/gotop/releases/latest/download/gotop_linux_amd64.tgz"
tools[glances]="https://github.com/nicolargo/glances/releases/latest/download/glances-x86_64.AppImage"
tools[cointop]="https://github.com/miguelmota/cointop/releases/latest/download/cointop_Linux_x86_64.tar.gz"
tools[trippy]="https://github.com/a8m/trippy/releases/latest/download/trippy_linux_amd64.tar.gz"
tools[taskwarrior-tui]="https://github.com/kdheepak/taskwarrior-tui/releases/latest/download/taskwarrior-tui-x86_64-unknown-linux-gnu.tar.gz"

# File Managers
tools[nnn]="https://github.com/jarun/nnn/releases/latest/download/nnn-linux-amd64.zip"
tools[lf]="https://github.com/gokcehan/lf/releases/latest/download/lf-linux-amd64.tar.gz"
tools[broot]="https://dystroy.org/broot/download/x86_64-linux/broot"
tools[yazi]="https://github.com/sxyazi/yazi/releases/latest/download/yazi-x86_64-unknown-linux-musl.zip"
tools[superfile]="https://github.com/ruffle-rs/superfile/releases/latest/download/superfile-linux-amd64.tar.gz"

# Docker / Kubernetes
tools[lazydocker]="https://github.com/jesseduffield/lazydocker/releases/latest/download/lazydocker_Linux_x86_64.tar.gz"
tools[k9s]="https://github.com/derailed/k9s/releases/latest/download/k9s_Linux_amd64.tar.gz"
tools[dry]="https://github.com/moncho/dry/releases/latest/download/dry-linux-amd64"

# Development tools
tools[lazygit]="https://github.com/jesseduffield/lazygit/releases/latest/download/lazygit_Linux_x86_64.tar.gz"
tools[gitui]="https://github.com/extrawurst/gitui/releases/latest/download/gitui-linux-musl.tar.gz"
tools[oha]="https://github.com/hatoo/oha/releases/latest/download/oha-linux-amd64.tar.gz"
tools[bagels]="https://github.com/sharkdp/bagels/releases/latest/download/bagels-x86_64-unknown-linux-musl.tar.gz"
tools[delta]="https://github.com/dandavison/delta/releases/latest/download/git-delta-x86_64-unknown-linux-musl.tar.gz"
tools[diskonaut]="https://github.com/imsnif/diskonaut/releases/latest/download/diskonaut-x86_64-unknown-linux-musl.tar.gz"
tools[duf]="https://github.com/muesli/duf/releases/latest/download/duf_linux_amd64.tar.gz"

# Extra stable
tools[bat]="https://github.com/sharkdp/bat/releases/latest/download/bat-x86_64-unknown-linux-gnu.tar.gz"
tools[fd]="https://github.com/sharkdp/fd/releases/latest/download/fd-x86_64-unknown-linux-gnu.tar.gz"
tools[ripgrep]="https://github.com/BurntSushi/ripgrep/releases/latest/download/ripgrep-x86_64-unknown-linux-musl.tar.gz"

# Main downloader loop
for tool in "${!tools[@]}"; do
  url="${tools[$tool]}"
  filename="${tool}_$(basename "$url")"
  dest="${BASE_DIR}/${filename}"

  echo "→ Downloading $tool..."
  if curl -sL "$url" -o "$dest"; then
    echo "✅ $tool downloaded successfully."
  else
    echo "⚠️ Failed to download $tool" | tee -a download_errors.log
  fi
done

echo "🎯 All downloads complete."

