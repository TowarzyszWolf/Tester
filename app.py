"""Local Cinebench results manager. Python 3.12+, no external dependencies."""
import argparse
import csv
import io
import json
import math
import sqlite3
from contextlib import contextmanager
from datetime import date
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from importers import parse_report
from metadata import cinebench_edition, operating_system

ROOT = Path(__file__).resolve().parent
OLD_FIELDS = ('edition', 'test', 'score', 'unit', 'cpu', 'gpu', 'threads', 'os', 'measured_at', 'notes')
FIELDS = OLD_FIELDS + ('cores', 'clock_mhz', 'benchmark_version', 'system_name', 'architecture', 'source_file', 'os_name', 'os_version', 'os_build')
TESTS = ('CPU Single Core', 'CPU Multi Core', 'GPU', 'OpenGL', 'Shading (CINEMA 4D)', 'OpenGL Software Lighting', 'OpenGL Hardware Lighting', 'OpenGL Standard')
UNITS = ('pts', 'cb', 'fps', 'CB-CPU', 'CB-GFX')
MAX_BODY = 2 * 1024 * 1024


def validate(raw):
    if not isinstance(raw, dict):
        raise ValueError('Wynik musi być obiektem.')
    result = {}
    for key in FIELDS:
        value = raw.get(key, '')
        if value is None:
            value = ''
        result[key] = str(value).strip()
        if len(result[key]) > (4000 if key == 'notes' else 255):
            raise ValueError(f'Pole {key} jest za długie.')
    detected = cinebench_edition(result['benchmark_version'])
    if not result['edition'] and detected:
        result['edition'] = detected
    entered = cinebench_edition(result['edition'])
    if detected and entered and detected != entered:
        raise ValueError('Edycja Cinebench nie zgadza się z pełną wersją programu.')
    if entered:
        if not result['benchmark_version'] and result['edition'].upper().removeprefix('R') != entered.upper().removeprefix('R'):
            result['benchmark_version'] = result['edition']
        result['edition'] = entered
    if result['os']:
        result.update(operating_system(result['os']))
    if not result['edition'] or not result['cpu']:
        raise ValueError('Podaj wersję Cinebench i procesor.')
    if result['test'] not in TESTS or result['unit'] not in UNITS:
        raise ValueError('Nieprawidłowy tryb testu lub jednostka.')
    try:
        result['score'] = float(result['score'].replace(',', '.'))
    except ValueError:
        raise ValueError('Wynik musi być liczbą.') from None
    if not math.isfinite(result['score']) or result['score'] <= 0:
        raise ValueError('Wynik musi być skończoną liczbą większą od zera.')
    try:
        result['threads'] = int(result['threads']) if result['threads'] else None
        if result['threads'] is not None and not 1 <= result['threads'] <= 65536:
            raise ValueError
    except ValueError:
        raise ValueError('Liczba wątków musi być liczbą całkowitą od 1 do 65536.') from None
    try:
        result['cores'] = int(result['cores']) if result['cores'] else None
        if result['cores'] is not None and not 1 <= result['cores'] <= 65536:
            raise ValueError
        result['clock_mhz'] = float(result['clock_mhz']) if result['clock_mhz'] else None
        if result['clock_mhz'] is not None and (not math.isfinite(result['clock_mhz']) or result['clock_mhz'] <= 0):
            raise ValueError
    except ValueError:
        raise ValueError('Nieprawidłowa liczba rdzeni lub częstotliwość MHz.') from None
    try:
        if result['measured_at']:
            date.fromisoformat(result['measured_at'])
    except ValueError:
        raise ValueError('Podaj datę pomiaru w formacie RRRR-MM-DD.') from None
    return result


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            old_columns = {row['name'] for row in conn.execute('PRAGMA table_info(results)')}
            migrate = bool(old_columns) and 'source_file' not in old_columns
            conn.execute('BEGIN')
            if migrate:
                conn.execute('ALTER TABLE results RENAME TO results_legacy')
            statements = (ROOT / 'schema.sql').read_text().split(';')
            for statement in statements:
                if statement.strip():
                    conn.execute(statement)
            if migrate:
                shared = ','.join(('id',) + OLD_FIELDS + ('created_at',))
                conn.execute(f'INSERT INTO results ({shared}) SELECT {shared} FROM results_legacy')
                conn.execute('DROP TABLE results_legacy')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_results_group ON results(edition, test, unit)')
            columns = {row['name'] for row in conn.execute('PRAGMA table_info(results)')}
            backfill_os = migrate or any(column not in columns for column in ('os_name', 'os_version', 'os_build'))
            for column in ('os_name', 'os_version', 'os_build'):
                if column not in columns:
                    conn.execute(f"ALTER TABLE results ADD COLUMN {column} TEXT NOT NULL DEFAULT ''")
            if backfill_os:
                for row in conn.execute('SELECT id, os FROM results').fetchall():
                    detected_os = operating_system(row['os'])
                    conn.execute('UPDATE results SET os_name=?, os_version=?, os_build=? WHERE id=?',
                                 (*detected_os.values(), row['id']))
            conn.execute('PRAGMA user_version = 3')

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def add(self, rows):
        validated = [validate(row) for row in rows]
        sql = f"INSERT INTO results ({','.join(FIELDS)}) VALUES ({','.join('?' for _ in FIELDS)})"
        with self.connect() as conn:
            for row in validated:
                conn.execute(sql, [row[key] for key in FIELDS])
        return len(validated)

    def list(self, filters):
        clauses, values = [], []
        for key in ('edition', 'test', 'unit'):
            if filters.get(key):
                clauses.append(f'{key} = ?')
                values.append(filters[key])
        if filters.get('q'):
            clauses.append('(instr(lower(cpu), lower(?)) > 0 OR instr(lower(gpu), lower(?)) > 0 OR instr(lower(notes), lower(?)) > 0)')
            values.extend([filters['q']] * 3)
        sql = 'SELECT * FROM results'
        if clauses:
            sql += ' WHERE ' + ' AND '.join(clauses)
        sql += ' ORDER BY measured_at DESC, id DESC'
        with self.connect() as conn:
            return [dict(row) for row in conn.execute(sql, values)]

    def delete(self, result_id):
        with self.connect() as conn:
            return conn.execute('DELETE FROM results WHERE id = ?', (result_id,)).rowcount

    def snapshot(self):
        with self.connect() as source, sqlite3.connect(':memory:') as target:
            source.backup(target)
            return target.serialize()


def parse_csv(body):
    try:
        content = body.decode('utf-8-sig')
        dialect = csv.Sniffer().sniff(content[:8192], delimiters=',;\t')
        reader = csv.DictReader(io.StringIO(content, newline=''), dialect=dialect)
        if not reader.fieldnames or not set(OLD_FIELDS).issubset(reader.fieldnames) or not set(reader.fieldnames).issubset(FIELDS) or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError('Nieprawidłowe kolumny CSV. Pobierz wzór pliku.')
        rows = []
        for index, row in enumerate(reader, 2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f'Wiersz {index}: nieprawidłowa liczba kolumn.')
            try:
                rows.append(validate(row))
            except ValueError as exc:
                raise ValueError(f'Wiersz {index}: {exc}') from None
        if not rows:
            raise ValueError('Plik CSV nie zawiera wyników.')
        return rows
    except (UnicodeError, csv.Error) as exc:
        raise ValueError('Nie można odczytać CSV. Użyj UTF-8 oraz separatora przecinek, średnik lub tabulator.') from exc


def handler_for(store):
    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, body, content_type='application/json; charset=utf-8', filename=None):
            if not isinstance(body, bytes):
                body = json.dumps(body, ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; form-action 'self'")
            if filename:
                self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(body)

        def body(self):
            # Mutations require a custom header: cross-origin forms cannot write.
            if self.headers.get('X-Cinebench-Client') != '1':
                raise ValueError('Brak nagłówka aplikacji.')
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= MAX_BODY:
                raise ValueError('Plik lub żądanie jest puste albo przekracza limit 2 MB.')
            return self.rfile.read(size)

        def do_GET(self):
            url = urlsplit(self.path)
            if url.path in ('/', '/app.js', '/style.css'):
                name, mime = {'/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'text/javascript; charset=utf-8'), '/style.css': ('style.css', 'text/css; charset=utf-8')}[url.path]
                self.reply(200, (ROOT / 'static' / name).read_bytes(), mime)
            elif url.path in ('/api/results', '/api/export.csv'):
                filters = {key: value[0] for key, value in parse_qs(url.query).items()}
                rows = store.list(filters)
                if url.path.endswith('.csv'):
                    output = io.StringIO(newline='')
                    writer = csv.DictWriter(output, fieldnames=FIELDS, extrasaction='ignore')
                    writer.writeheader()
                    writer.writerows(rows)
                    self.reply(200, output.getvalue().encode('utf-8-sig'), 'text/csv; charset=utf-8', 'cinebench.csv')
                else:
                    self.reply(200, rows)
            elif url.path == '/api/database':
                self.reply(200, store.snapshot(), 'application/vnd.sqlite3', 'cinebench.sqlite3')
            elif url.path == '/api/template.csv':
                self.reply(200, (','.join(FIELDS) + '\r\n').encode(), 'text/csv; charset=utf-8', 'szablon.csv')
            else:
                self.reply(404, {'error': 'Nie znaleziono.'})

        def do_POST(self):
            try:
                path = urlsplit(self.path).path
                if path == '/api/results':
                    count = store.add([json.loads(self.body())])
                elif path == '/api/parse':
                    rows = parse_report(self.body())
                    self.reply(200, rows)
                    return
                elif path == '/api/import-results':
                    rows = json.loads(self.body())
                    if not isinstance(rows, list) or not rows:
                        raise ValueError('Brak wyników do zapisania.')
                    count = store.add(rows)
                elif path == '/api/import':
                    count = store.add(parse_csv(self.body()))
                else:
                    self.reply(404, {'error': 'Nie znaleziono.'})
                    return
                self.reply(201, {'added': count})
            except (ValueError, UnicodeError) as exc:
                self.reply(400, {'error': str(exc)})

        def do_DELETE(self):
            try:
                if self.headers.get('X-Cinebench-Client') != '1':
                    raise ValueError('Brak nagłówka aplikacji.')
                parts = urlsplit(self.path).path.split('/')
                if len(parts) != 4 or parts[1:3] != ['api', 'results']:
                    self.reply(404, {'error': 'Nie znaleziono.'})
                    return
                deleted = store.delete(int(parts[3]))
                self.reply(200 if deleted else 404, {'deleted': deleted})
            except ValueError as exc:
                self.reply(400, {'error': str(exc)})

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--db', type=Path, default=ROOT / 'data' / 'cinebench.sqlite3')
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), handler_for(Store(args.db)))
    print(f'Cinebench: http://{args.host}:{server.server_port} | baza: {args.db}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
