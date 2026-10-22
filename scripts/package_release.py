"""Allowlisted source distribution: never package local sessions or credentials."""
from pathlib import Path
import hashlib
import json
import zipfile


def main():
    root=Path(__file__).resolve().parent.parent
    version=json.loads((root/'.codex-plugin/plugin.json').read_text(encoding='utf-8'))['version'].split('+')[0]
    files=[p for p in root.iterdir() if p.suffix in ('.md','.ps1','.cmd')]
    files += list((root/'scripts').glob('*.py'))
    files += [root/'LICENSE',root/'.codex-plugin/plugin.json',root/'.gitignore',root/'.gitattributes']
    target=root/'dist'/f'codex-token-meter-{version}-windows-source.zip'
    target.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.write(path, 'codex-token-meter/'+path.relative_to(root).as_posix())
    digest=hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix('.zip.sha256').write_text(digest+'  '+target.name+'\n',encoding='ascii')
    print(target)
    print('SHA256 '+digest)


if __name__=='__main__':
    main()
