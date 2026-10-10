import hashlib
import importlib.util
from pathlib import Path
import zipfile


def test_release_keeps_bundled_datasets_and_excludes_runtime_data(tmp_path, monkeypatch):
    source = tmp_path / 'Daffo-Botz-Ultimate'
    fixtures = {
        'main.py': 'print("test")',
        'legacy/data/anya/kbbi.json': '["kata"]',
        '.env.example': 'ADMIN_PASSWORD_HASH=',
        '.env': 'private-test-fixture',
        'data/control.db': 'private-test-fixture',
        'tests/ui/node_modules/pkg/index.js': 'dependency',
        '.artifacts/screenshot.png': 'generated',
    }
    for name, contents in fixtures.items():
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents)
    spec = importlib.util.spec_from_file_location('release', Path('scripts/package_release.py'))
    release = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(release)
    output = tmp_path / 'release.zip'
    monkeypatch.setattr(release, 'ROOT', source)
    monkeypatch.setattr(release, 'OUTPUT', output)
    release.main()
    with zipfile.ZipFile(output) as archive:
        assert set(archive.namelist()) == {
            'Daffo-Botz-Ultimate/main.py',
            'Daffo-Botz-Ultimate/legacy/data/anya/kbbi.json',
            'Daffo-Botz-Ultimate/.env.example',
        }
        assert archive.testzip() is None
    assert output.with_suffix('.zip.sha256').read_text().split()[0] == hashlib.sha256(output.read_bytes()).hexdigest()
