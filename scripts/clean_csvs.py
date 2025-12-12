import sys
from pathlib import Path
import re

HEADER = "NO;KECAMATAN;KODE;NAMA MAJELIS TA'LIM;NO. STATISTIK MT;TGL TAHUN BERDIRI;ALAMAT;NO. TGL SURAT KELUAR;STATUS TANAH;TTD SK;No. URUT AGENDA BBSK"


def is_noise_line(parts):
    # line like ';TAHUN 2024;;;;;;;;;' or a single year marker
    joined = ";".join(parts).upper()
    if 'TAHUN' in joined:
        return True
    # match lines that only contain a year or year with semicolons
    if re.search(r";?\s*\d{4}\s*;?", joined):
        # make sure it's not part of an address (conservative)
        tokens = [p.strip() for p in parts if p.strip()]
        if len(tokens) == 1 and re.fullmatch(r"\d{4}", tokens[0]):
            return True
    return False


def clean_file(path: Path):
    text = path.read_text(encoding='utf-8')
    lines = [l.rstrip('\n') for l in text.splitlines()]
    if not lines:
        return

    # find header (first line that contains 'NO;KECAMATAN')
    header_idx = None
    for i, l in enumerate(lines):
        if l.strip().upper().startswith('NO;') and 'KECAMATAN' in l.upper():
            header_idx = i
            break
    if header_idx is None:
        # assume first line is header
        header_idx = 0

    raw_rows = lines[header_idx+1:]

    records = []
    last = None
    for ln in raw_rows:
        if not ln.strip():
            continue
        parts = ln.split(';')
        # pad to 11
        if len(parts) < 11:
            parts += [''] * (11 - len(parts))
        # normalize parts
        parts = [p.strip() for p in parts[:11]]

        if is_noise_line(parts):
            continue

        if parts[0]:
            # new record
            last = parts[:]
            records.append(last)
        else:
            # continuation line: append non-empty fields to last record
            if last is None:
                # stray continuation without previous record -> skip
                continue
            for i, p in enumerate(parts):
                if p:
                    if last[i]:
                        last[i] = last[i] + ' ' + p
                    else:
                        last[i] = p

    # renumber NO sequentially
    for idx, rec in enumerate(records, start=1):
        rec[0] = str(idx)

    # write backup
    bak = path.with_suffix(path.suffix + '.bak')
    path.rename(bak)

    # write cleaned file
    out_lines = [HEADER]
    for rec in records:
        # ensure 11 columns
        row = ';'.join(rec)
        out_lines.append(row)

    path.write_text('\n'.join(out_lines) + '\n', encoding='utf-8')


def main(folder):
    p = Path(folder)
    if not p.exists():
        print('Path not found:', folder)
        return 1

    csvs = list(p.glob('*.csv'))
    if not csvs:
        print('No CSV files found in', folder)
        return 0

    for f in csvs:
        print('Cleaning', f.name)
        try:
            clean_file(f)
        except Exception as e:
            print('Failed', f.name, e)

    print('Done')
    return 0


if __name__ == '__main__':
    folder = sys.argv[1] if len(sys.argv) > 1 else '.'
    raise SystemExit(main(folder))
