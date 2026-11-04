# Backend

## Setup

### Initial Setup

First, add yourself to the authors in `pyproject.toml`.

You need to install Python 3.14.
These instructions are for users of `pip`.

Setup your python virtual environment as usual:

```bash
cd backend
python3 -m venv env
```

Then activate it:

- `bash`/`zsh`:

```bash
source env/bin/activate
```

- `fish`:

```bash
source env/bin/activate.fish
```

Finally, install the dependencies:

```bash
pip install -r requirements.txt
```

### IDE Setup

You should setup your IDE to use `basedpyright` (or the worse `pyright`) for static type-checking
and `ruff` for linting and formatting. Both can be installed via `pip`. Any further instructions heavily depend on the IDE.

If you do not want to integrate them into your IDE, you can also run them via the CLI:

To lint your code:

```bash
ruff check .
```

To format your code:

```bash
ruff format .
```

To type-check your code:

```bash
basedpyright . # or pyright .
```

## Running the server

Within the directory of this `README.md`, run:

```bash
uvicorn src.main:app --reload
```

This runs the server on `localhost:8000` with hot reloading, i.e. you can keep it running in the background and the server will update itself as soon as you modify its source code.

## Tests

Withing the directory of this `README.md`, run:

```bash
pytest
```
