# Cinebase — baza wyników Cinebench

Lokalna aplikacja po polsku do archiwizacji wyników w SQLite. Python 3.12+, bez dodatkowych bibliotek. Wersja benchmarku jest polem tekstowym: można zapisywać edycje od 2003 do 2026 i własne nazwy. Podpowiedzi nie są katalogiem oficjalnych wydań ani gwarancją obsługi ich plików.

## Pobieranie

Gotowy program z bazą 62 wyników: [pobierz Cinebase ZIP](https://github.com/TowarzyszWolf/Tester/raw/refs/heads/main/downloads/cinebase-v2.zip). Rozpakuj do nowego folderu i przeczytaj `START.txt`. Wymagany Python 3.12+.

Osobno: [baza SQLite](downloads/cinebase-wyniki.sqlite3) i [eksport SQL](downloads/cinebase-wyniki.sql). Pliki w `downloads` są migawką danych z przesłanych raportów.

## Uruchomienie

W katalogu projektu:

```sh
python app.py
```

Na własnym komputerze otwórz `http://127.0.0.1:8000`. Zatrzymanie: Ctrl+C. Parametry: `--port 8001`, `--db /ścieżka/wyniki.sqlite3`. Baza `data/cinebench.sqlite3` powstaje automatycznie. Zachowaj ją przy aktualizacji. Aplikacja nasłuchuje lokalnie i nie ma logowania; nie jest przeznaczona do publicznego udostępniania. Podgląd localhost w interfejsie onboarding nie jest dostępny; serwer można sprawdzać żądaniami HTTP wewnątrz środowiska.

## Import plików wynikowych

Wybierz jeden lub wiele plików (do 100), sprawdź podgląd i zapisz. Wersja, CPU, GPU, system i parametry sprzętu są odczytywane z treści plików. Nazwa pliku trafia do bazy jako źródło. Dane obecne w pliku mają pierwszeństwo przed polami uzupełniającymi. Raporty nie zawierają dat pomiarów: pozostają nieznane, dopóki sam ich nie podasz. Data importu jest zapisywana osobno jako `created_at`.

Importer jest zweryfikowany na **25 przesłanych raportach**, zawierających łącznie **62 wykonane pomiary** z Cinebench 2003, 9.5, R10, R11.5, R15, R20, R23 i 2026. Dostarczony raport 2024 jest rozpoznawany, ale zawiera wyłącznie zera i brak pola CBCPUX — nie wnosi wyniku do bazy. Obsługa dodatniego CBGPU jest testowana na zmodyfikowanej próbce, nie na rzeczywistym pomiarze GPU z 2024/2026.

- Raporty 2003 / 9.5 / R10: Rendering Single/Multiple CPU i odrębne testy Shading CINEMA 4D, OpenGL Software Lighting, Hardware Lighting oraz Standard. Jednostki `CB-CPU` i `CB-GFX` pozostają bez przeliczania.
- Raporty R11.5 / R15 / R20 / R23 / 2024 / 2026: pola `CBCPU1`, `CBCPUX`, `CBOPENGL`, `CBGPU`. Zera i `---` oznaczają brak wyniku i są pomijane. Wartości PEAK i ARRAY są metadanymi istniejącego pomiaru, a nie dodatkowymi wynikami. `MHZ_ESTIMATE=inf` nie jest wynikiem testu.
- Fizyczne rdzenie są odczytywane z `CORES`. Dla R11.5/R15 liczba wątków to CORES × LOGICALCORES; nowsze raporty mają `THREADS`. Starsze `Number of CPUs` jest liczbą wątków renderujących, a nie dowodem na liczbę fizycznych rdzeni.
- Zachowywane są pełna wersja programu, MHz, architektura, nazwa komputera, system, sterowniki i inne dostępne szczegóły w notatkach. Częstotliwości w GHz są przeliczane na MHz.
- Obsługiwane są także proste raporty `CPU (Multi Core): 12345 pts`, nazwane pola `cb_cpu1`, `cb_cpux`, `cb_ogl`, `cpu_single_core`, `cpu_multi_core`, `gpu_score` i JSON: obiekt wyniku, lista lub `{"results": [...]}`.

Kodowanie: UTF-8 (opcjonalny BOM), UTF-16 z BOM. Końce linii Windows, Unix i klasycznego Mac OS. Limit 2 MB na plik; żądanie zapisu całej partii również ma limit 2 MB. Pliki błędne i pliki bez wyników są wyszczególniane w podsumowaniu; pozostałe można zapisać po sprawdzeniu podglądu. Nieznane formaty są odrzucane. Ponowny import tworzy nowe pomiary — bez automatycznego usuwania duplikatów.

Oryginalne próbki znajdują się w `tests/fixtures`; `examples/report.txt` to syntetyczny przykład formatu uproszczonego. Obsługa innych odmian raportów wymaga osobnej weryfikacji.

## Dane i eksport

Pola: edycja i pełna wersja benchmarku, rodzaj testu, wynik, jednostka, procesor, karta graficzna, rdzenie, wątki, MHz, architektura, nazwa komputera, system, data, plik źródłowy i notatki. Dla testu GPU wymagana jest karta graficzna. Testy OpenGL i Shading są oddzielnymi rodzajami testów.

Porównuj wyłącznie tę samą wersję, tryb, jednostkę i zgodne ustawienia testu. Wyniki nie są przeliczane między wersjami ani łączone w ranking.

CSV przyjmuje także starszy układ kolumn:

```csv
edition,test,score,unit,cpu,gpu,threads,os,measured_at,notes
R23,CPU Multi Core,12345.5,pts,Example CPU,,16,Linux,2026-11-01,Przykład
```

Eksport zawiera dodatkowo kolumny `cores,clock_mhz,benchmark_version,system_name,architecture,source_file`. Import akceptuje oba układy. Import: UTF-8, separator przecinek/średnik/tabulator; liczby z kropką lub przecinkiem i data ISO. Błąd jednego rekordu anuluje cały import. Eksport CSV uwzględnia filtry. CSV zachowuje teksty; przy otwieraniu niezaufanych danych w arkuszu importuj kolumny jako tekst, aby nie interpretować formuł.

Przycisk **Pobierz bazę SQLite** tworzy spójną kopię całej bazy do otwarcia np. w DB Browser for SQLite. Nie jest to eksport dla MySQL/MSSQL. Schemat: `schema.sql`. Starsza baza aplikacji jest automatycznie migrowana transakcyjnie przy starcie, z zachowaniem rekordów i ich identyfikatorów.

```sql
SELECT edition, test, score, unit, cpu, gpu, measured_at
FROM results
WHERE edition = 'R23' AND test = 'CPU Multi Core' AND unit = 'pts'
ORDER BY score DESC;
```

## Testy

```sh
python -m unittest discover -s tests -v
```

Testy używają tymczasowych baz i lokalnego serwera na losowym porcie. Sprawdzają trwałość, filtry, walidację, atomowość importu, parsery, kopię bazy i przepływ HTTP: odczyt raportu, zapis, eksport, usunięcie. Nie zmieniają danych użytkownika. Testy porównują dokładne wartości wyników wszystkich 25 próbek oraz sprawdzają migrację starszej bazy.
