# Releasing toolwall

The build and metadata are verified (`python -m build` + `twine check` both pass,
clean-install smoke test green). Publishing is a manual step **you** run with your
own PyPI token; nothing here uploads on your behalf.

## Before the first real publish

1. **Decide the version.** `pyproject.toml` is `0.2.0.dev0`. A `.dev0` release is
   installable but hidden from `pip install toolwall` by default (pre-release).
   - Keep `0.2.0.dev0` to publish a dev preview (opt-in via `pip install toolwall --pre`).
   - Or bump to `0.2.0` in `pyproject.toml` **and** `src/toolwall/__init__.py` for a
     normal first release.
2. **Confirm the name is yours.** `toolwall` was free on PyPI on 2026-08-28. Reserve it
   by publishing, or check https://pypi.org/project/toolwall/ first.
3. **Get a token.** PyPI account -> Account settings -> API tokens -> scope "Entire account"
   for the first upload (you can narrow it to the project afterwards).

## Publish (Test PyPI first, always)

```bash
cd toolwall
rm -rf dist
python -m build
python -m twine check dist/*

# 1) dry run on Test PyPI
python -m twine upload --repository testpypi dist/*
#    then verify a clean install:
python -m pip install --index-url https://test.pypi.org/simple/ --no-deps toolwall

# 2) real PyPI, only after Test PyPI looks right
python -m twine upload dist/*
```

You'll be prompted for the token (`__token__` as username, the `pypi-...` token as
password), or set `TWINE_USERNAME=__token__` and `TWINE_PASSWORD=pypi-...`.

## After publishing

- Tag the release: `git tag v0.2.0 && git push origin v0.2.0`
- Sanity check: `pip install toolwall` in a fresh venv, run `python -c "import toolwall"`
- Update the README install line from `pip install -e .` to `pip install toolwall`

## Do not

- Commit `dist/` (it's gitignored).
- Publish with real secrets anywhere in the tree (the shield fixtures are
  concatenation-built precisely so nothing real ships).
- Claim more than `gate-suite/results/REPORT.md` proves.
