# pi-Stomp Builder

A Python-based deployment tool for pi-Stomp components.

## Development

This project uses `uv` for dependency management.

### Linting and Type Checking

To run the linter (Ruff):
```bash
uv run ruff check .
```

To run the type checker (Ty):
```bash
uv run ty .
```

### Adding dependencies

```bash
uv add <package>
uv add --dev <dev-package>
```
