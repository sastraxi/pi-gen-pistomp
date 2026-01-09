# pi-Stomp Builder

A Python-based deployment tool for pi-Stomp components.

## Usage

Use the wrapper script `deploy.sh`:

```bash
# Deploy to local directory
./deploy.sh <target>

# Deploy to remote device (defaults to pistomp@pistomp.local)
./deploy.sh <target> --ssh [user@host]
```

**Targets:**
- Component name: `mod-ui`
- Git URL: `https://github.com/TreeFallSound/mod-ui.git` (HTTPS only)
- Tarball: `http://download.drobilla.net/lilv-0.24.12.tar.bz2`
- GitHub shorthand: `TreeFallSound/mod-ui` (HTTPS; supports `#branch`)
- Local path: `.`

## Development

Managed via `uv`.

### Checks

```bash
# Type Check
uv run ty .

# Lint
uv run ruff check .
```
