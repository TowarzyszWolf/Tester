"""Local Cinebench report database, Python 3.12+, standard library only."""
import argparse
import csv
import io
import json
import hashlib
import re
import sqlite3
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from importers import parse_report
from records import FIELDS, META, METRICS, BY_TEST, UNITS, validate, combine_measurements, aggregate, normalized

ROOT = Path(__file__).resolve().parent
MAX_BODY = 2 * 1024 * 1024
TESTS = tuple(BY_TEST)
OLD_FIELDS = ('edition','test','score','unit','cpu','gpu','threads','os','measured_at','notes')


def merge_legacy(rows):
    groups, active = [], {}
    for old in rows:
        if not old.get('source_file'):
            groups.append([old])
            continue
        key = tuple(str(old.get(k) or '') for k in META if k!='notes') + (str(old.get('created_at') or '')[:19],)
        current = active.get(key)
        if current is None or any(r['test']==old['test'] for r in current):
            current = []
            active[key] = current
            groups.append(current)
        current.append(old)
    return [(group[0]['id'], group[0].get('created_at'), validate(combine_measurements(group)[0])) for group in groups]


class Store:
    def __init__(self,path):
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.created = not self.path.exists() or self.path.stat().st_size == 0
        self.backup_path=None
        with self.connect() as conn:
            columns={row['name'] for row in conn.execute('PRAGMA table_info(results)')}
            migrate='test' in columns
            if migrate:
                # Snapshot before touching the original schema or measurements.
                backup=self.path.with_name(self.path.name+'.before-v4.sqlite3')
                counter=1
                while backup.exists():
                    backup=self.path.with_name(self.path.name+f'.before-v4-{counter}.sqlite3')
                    counter+=1
                with sqlite3.connect(backup) as destination:
                    conn.backup(destination)
                self.backup_path=backup
                legacy=[dict(r) for r in conn.execute('SELECT * FROM results ORDER BY id')]
                combined=merge_legacy(legacy)
            conn.execute('BEGIN')
            if migrate:
                conn.execute('ALTER TABLE results RENAME TO results_legacy')
            for statement in (ROOT/'schema.sql').read_text().split(';'):
                if statement.strip():
                    conn.execute(statement)
            if migrate:
                columns=('id','created_at')+FIELDS
                sql=f"INSERT INTO results ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})"
                for old_id,created,row in combined:
                    conn.execute(sql,[old_id,created or '']+[row[key] for key in FIELDS])
                conn.execute('DROP TABLE results_legacy')
            conn.execute('PRAGMA user_version = 5')

    @contextmanager
    def connect(self):
        conn=sqlite3.connect(self.path,timeout=10)
        conn.row_factory=sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def add(self,rows):
        validated=[validate(row) for row in rows]
        sql=f"INSERT INTO results ({','.join(FIELDS)}) VALUES ({','.join('?' for _ in FIELDS)})"
        with self.connect() as conn:
            for row in validated:
                conn.execute(sql,[row[key] for key in FIELDS])
        return len(validated)

    def list(self,filters):
        clauses,values=[],[]
        if filters.get('edition'):
            clauses.append('edition=?');values.append(filters['edition'])
        if filters.get('test'):
            metric=BY_TEST.get(filters['test'])
            if not metric:
                return []
            clauses.append(f'{metric} IS NOT NULL')
        if filters.get('unit'):
            clauses.append('('+' OR '.join(key+'_unit=?' for key in METRICS)+')')
            values.extend([filters['unit']]*len(METRICS))
        if filters.get('q'):
            clauses.append('('+' OR '.join('instr(lower('+key+'),lower(?))>0' for key in ('cpu','gpu','notes','source_file'))+')')
            values.extend([filters['q']]*4)
        sql='SELECT * FROM results'+(' WHERE '+' AND '.join(clauses) if clauses else '')+' ORDER BY id'
        with self.connect() as conn:
            rows=[dict(row) for row in conn.execute(sql,values)]
        if filters.get('group_by') in ('cpu','gpu','hardware'):
            rows=aggregate(rows,filters['group_by'])
        allowed=('cpu','gpu','edition','measured_at','id',*METRICS)
        sort=filters.get('sort','cpu')
        if sort not in allowed:
            sort='cpu'
        # Unknown values remain last in either direction.
        known=[row for row in rows if row.get(sort) not in ('',None)]
        missing=[row for row in rows if row.get(sort) in ('',None)]
        def key(row):
            value=row[sort]
            return normalized(value) if isinstance(value,str) else value
        return sorted(known,key=key,reverse=filters.get('direction')=='desc')+missing

    def status(self):
        with self.connect() as conn:
            return {'record_count': conn.execute('SELECT count(*) FROM results').fetchone()[0],
                    'database_created': self.created}

    def import_batch(self,items):
        if not isinstance(items,list) or not 1 <= len(items) <= 100:
            raise ValueError('Partia musi zawierać od 1 do 100 raportów.')
        outcomes=[]
        with self.connect() as conn:
            # Acquire the write lock before checking receipts, including concurrent retries.
            conn.execute('BEGIN IMMEDIATE')
            for item in items:
                token=item.get('token','') if isinstance(item,dict) else ''
                try:
                    if not isinstance(token,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',token):
                        raise ValueError('Nieprawidłowy identyfikator importu.')
                    row=validate(item.get('record'))
                    digest=hashlib.sha256(json.dumps(row,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
                    receipt=conn.execute('SELECT * FROM import_receipts WHERE token=?',(token,)).fetchone()
                    if receipt:
                        if receipt['payload_hash'] != digest:
                            raise ValueError('Identyfikator importu został już użyty dla innych danych.')
                        outcomes.append({'token':token,'status':'already_saved','id':receipt['result_id']})
                        continue
                    sql=f"INSERT INTO results ({','.join(FIELDS)}) VALUES ({','.join('?' for _ in FIELDS)})"
                    result_id=conn.execute(sql,[row[key] for key in FIELDS]).lastrowid
                    conn.execute('INSERT INTO import_receipts VALUES(?,?,?)',(token,digest,result_id))
                    outcomes.append({'token':token,'status':'saved','id':result_id})
                except ValueError as exc:
                    outcomes.append({'token':token if isinstance(token,str) else '', 'status':'error','error':str(exc)})
        return {'added':sum(r['status']=='saved' for r in outcomes),
                'already_saved':sum(r['status']=='already_saved' for r in outcomes),
                'failed':sum(r['status']=='error' for r in outcomes),'items':outcomes}

    def delete(self,result_id):
        with self.connect() as conn:
            return conn.execute('DELETE FROM results WHERE id=?',(result_id,)).rowcount

    def snapshot(self):
        with self.connect() as source,sqlite3.connect(':memory:') as target:
            source.backup(target)
            return target.serialize()


def parse_csv(body):
    try:
        content=body.decode('utf-8-sig')
        dialect=csv.Sniffer().sniff(content[:8192],delimiters=',;\t')
        reader=csv.DictReader(io.StringIO(content,newline=''),dialect=dialect)
        headers=reader.fieldnames or []
        if len(set(headers))!=len(headers) or not {'edition','cpu'}.issubset(headers) or not set(headers).issubset(FIELDS):
            raise ValueError('Nieprawidłowe kolumny CSV. Pobierz nowy szablon: jeden wiersz to jeden raport.')
        rows=[]
        for index,row in enumerate(reader,2):
            try:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError('Nieprawidłowa liczba kolumn.')
                rows.append(validate(row))
            except ValueError as exc:
                raise ValueError(f'Wiersz {index}: {exc}') from None
        if not rows:
            raise ValueError('Plik CSV nie zawiera rekordów.')
        return rows
    except (UnicodeError,csv.Error) as exc:
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
                    columns = FIELDS + (('report_count',) + tuple(key+'_count' for key in METRICS) if filters.get('group_by') in ('cpu','gpu','hardware') else ())
                    writer = csv.DictWriter(output, fieldnames=columns, extrasaction='ignore')
                    writer.writeheader()
                    for row in rows:
                        exported = dict(row)
                        for key in METRICS:
                            if exported[key] is not None:
                                exported[key] = format(exported[key], '.2f')
                            exported[key+'_count'] = row.get('counts',{}).get(key,'')
                        writer.writerow(exported)
                    self.reply(200, output.getvalue().encode('utf-8-sig'), 'text/csv; charset=utf-8', 'cinebench.csv')
                else:
                    self.reply(200, rows)
            elif url.path == '/api/database':
                self.reply(200, store.snapshot(), 'application/vnd.sqlite3', 'cinebench.sqlite3')
            elif url.path == '/api/status':
                self.reply(200, store.status())
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
                elif path == '/api/import-batch':
                    outcome = store.import_batch(json.loads(self.body()))
                    self.reply(200, outcome)
                    return
                elif path == '/api/import':
                    count = store.add(parse_csv(self.body()))
                else:
                    self.reply(404, {'error': 'Nie znaleziono.'})
                    return
                self.reply(201, {'added': count})
            except (ValueError, UnicodeError) as exc:
                self.reply(400, {'error': str(exc)})
            except sqlite3.Error:
                self.reply(503, {'error': 'Nie udało się zapisać partii. Ponów import — już zapisane pliki nie zostaną dodane ponownie.'})

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
    try:
        store = Store(args.db)
    except (OSError, sqlite3.Error, ValueError) as exc:
        parser.exit(1, f'Nie udało się otworzyć lub przygotować bazy {args.db}: {exc}\n')
    if store.created:
        print(f'Utworzono nową, pustą bazę: {args.db}', flush=True)
    server = ThreadingHTTPServer((args.host, args.port), handler_for(store))
    print(f'Cinebench: http://{args.host}:{server.server_port} | baza: {args.db}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
