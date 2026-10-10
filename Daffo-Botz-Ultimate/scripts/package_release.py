"""Create a source release, excluding credentials, session data and caches."""
import hashlib
from pathlib import Path
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT.parent / 'Daffo-Botz-Ultimate-v3.2.zip'
EXCLUDED = {'.venv', 'node_modules', '__pycache__', '.pytest_cache', '.artifacts', '.git'}


def main():
    paths = sorted(p for p in ROOT.rglob('*') if p.is_file() and not p.is_symlink()
                   and not EXCLUDED.intersection(p.relative_to(ROOT).parts)
                   and p.relative_to(ROOT).parts[0] != 'data'
                   and (not p.name.startswith('.env') or p.name == '.env.example')
                   and p.suffix not in ('.pyc', '.pyo'))
    with tempfile.TemporaryDirectory(prefix='daffo-release-') as tmp:
        archive = Path(tmp) / OUTPUT.name
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
            for path in paths:
                z.write(path, Path(ROOT.name) / path.relative_to(ROOT))
        with zipfile.ZipFile(archive) as z:
            if z.testzip() is not None:
                raise SystemExit('ZIP integrity check failed')
        OUTPUT.write_bytes(archive.read_bytes())
    digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    OUTPUT.with_suffix('.zip.sha256').write_text(digest + '  ' + OUTPUT.name + '\n')
    print(f'Packaged {len(paths)} source files: {OUTPUT.name}')


if __name__ == '__main__':
    main()
