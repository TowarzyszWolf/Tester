# Cinebase — baza raportów Cinebench

Lokalna aplikacja po polsku, Python 3.12+, SQLite, bez dodatkowych bibliotek. Jeden plik raportu tworzy **jeden rekord** z osobnymi kolumnami CPU Single Core, CPU Multi Core, GPU oraz starszych testów Shading i OpenGL. Wyniki na stronie i w CSV mają dokładnie dwa miejsca po przecinku. Baza SQLite zachowuje pełną precyzję.

## Pobieranie i start

[Pobierz program v6 — start z pustą bazą](https://github.com/TowarzyszWolf/Tester/raw/refs/heads/main/downloads/cinebase-v6.zip). Rozpakuj do nowego folderu. W katalogu programu uruchom:

```sh
python app.py
```

Na własnym komputerze otwórz `http://127.0.0.1:8000`. Zatrzymanie: Ctrl+C. Możesz użyć `--port 8001` i `--db /ścieżka/wyniki.sqlite3`. Domyślna baza to `data/cinebench.sqlite3`. Przy aktualizacji zachowaj własną bazę; nie zastępuj jej bazą przykładową z ZIP. Aplikacja działa lokalnie, bez logowania; nie jest przeznaczona do publicznego udostępniania. W interfejsie onboarding nie ma podglądu localhost; serwer sprawdza się lokalnymi żądaniami HTTP.

Osobno: [baza SQLite](downloads/cinebase-wyniki.sqlite3) i [eksport SQL](downloads/cinebase-wyniki.sql).

## Pierwszy start bez bazy

Paczka v6 nie zawiera pliku bazy. Przy starcie program sam tworzy katalog `data`, plik `cinebench.sqlite3`, tabele i indeksy. Nie trzeba uruchamiać SQL ani instalować SQLite osobno. Strona pokaże pustą bazę i przycisk wyboru pierwszych raportów. Tak samo działa nowa ścieżka podana przez `--db`, również z brakującymi katalogami. Ponowny start zachowuje zapisane rekordy.

Plik bazy o rozmiarze zero jest inicjalizowany. Uszkodzona istniejąca baza nie jest zastępowana nową — program kończy się z czytelnym błędem, zachowując plik. Gdy chcesz rozpocząć oddzielną bazę, wskaż nową nazwę przez `--db`.

Przykładowa baza 25 raportów / 62 pomiarów jest dostępna osobno w `downloads/cinebase-wyniki.sqlite3`. Można ją uruchomić poleceniem `python app.py --db downloads/cinebase-wyniki.sqlite3` po pobraniu całego repozytorium. Standardowa paczka v6 zaczyna bez przykładowych danych.

## Raporty i import

Wybierz do 500 plików naraz, sprawdź podgląd i zapisz. Pasek postępu pokazuje odczyt oraz zapis. Odczyt można anulować bez zapisywania danych. Wersja benchmarku, CPU, GPU, system, rdzenie, wątki i MHz są odczytywane z treści. Zera i `---` oznaczają brak pomiaru, zapisywany jako SQL `NULL`, bez wliczania do średnich. Rozpoznany plik bez wykonanych testów również tworzy jeden rekord (próbka 2024). Znajdziesz go w widoku **Oryginalne raporty**; nie wnosi wartości do widoków średnich. Ręczny formularz także zapisuje wszystkie podane wyniki jako jeden rekord.

Importer sprawdzono na 25 rzeczywistych raportach, obejmujących 62 wykonane pomiary z Cinebench 2003, 9.5, R10, R11.5, R15, R20, R23 i 2026 oraz pusty raport 2024. Dodatni wynik CBGPU jest testowany na zmodyfikowanej próbce, bez rzeczywistego pomiaru GPU 2024/2026.

- Starsze raporty: Rendering Single/Multiple CPU oraz osobne kolumny Shading CINEMA 4D, OpenGL Software Lighting, Hardware Lighting i Standard. Oryginalne jednostki `CB-CPU` i `CB-GFX` pozostają bez przeliczania.
- Raporty R11.5–2026: `CBCPU1`, `CBCPUX`, `CBOPENGL`, `CBGPU`; PEAK i ARRAY są szczegółami istniejących wyników. `MHZ_ESTIMATE=inf` nie jest wynikiem testu.
- W R11.5/R15 wątki obliczane są jako CORES × LOGICALCORES. Nowsze wersje mają THREADS. Starsze Number of CPUs wskazuje wątki renderujące, nie fizyczne rdzenie.
- Edycja jest rozpoznawana z nagłówka albo C4DVERSION, a pełna wersja, np. 2026.100, jest zachowywana oddzielnie. Niezgodność nagłówka z C4DVERSION przerywa import.
- System zachowuje oryginalny tekst `os` i rozpoznane `os_name`, `os_version`, `os_build`. Windows 10 z kompilacją 26100 nadal zapisuje się jako Windows 10, zgodnie z raportem. Starsze WINDOWS 64 BIT 6.2.9200 nie jest zamieniane na domniemaną wersję handlową. Obsługiwane są także macOS / Mac OS X / OS X i ich numery kompilacji.
- Modele GPU są opcjonalne również przy pomiarze GPU. W ręcznym formularzu można włączyć pole modelu karty.
- Data pomiaru nie jest odgadywana. Pozostaw puste, jeśli nieznana. Czas importu jest osobnym polem `created_at`.

Tekst UTF-8 / UTF-16 z BOM, końce linii Windows/Unix/klasyczny Mac OS. Limit 2 MB na pojedynczy plik. Łączny rozmiar wielu plików może być większy: strona dzieli zapis na partie do 25 raportów i około 500 KB, zamiast wysyłać wszystko jednym żądaniem. Nieznane i błędne pliki są opisane w podsumowaniu i nie są zapisywane. Poprawne raporty są zapisywane także wtedy, gdy inne mają błędy. Błędy odczytu i zapisu są przypisane do nazw plików. Po zapisie pozostają w podglądzie tylko błędne lub jeszcze niezapisane raporty: uzupełnij brakujące dane i ponów zapis. Ponowienie po utracie odpowiedzi w tej samej sesji strony nie dubluje już zapisanych raportów (identyfikatory potwierdzeń w tabeli import_receipts). Nie odświeżaj strony przed wznowieniem przerwanego importu, jeśli chcesz zachować jego identyfikatory. Ponowne wybranie tych samych plików rozpoczyna nowy import i może utworzyć kolejne rekordy; nie ma automatycznego usuwania duplikatów treści.

Obsługiwane są również uproszczone wiersze `CPU (Multi Core): 12345 pts` i JSON. Jeden plik JSON musi opisywać jedną konfigurację, bez powtórzonego rodzaju pomiaru. Przykłady i rzeczywiste próbki: `examples` i `tests/fixtures`.

## Rankingi CPU i GPU oraz historia modelu

Dwa niezależne panele pokazują rankingi procesorów i kart graficznych. W każdym wybierz edycję Cinebench, rodzaj testu, pełną wersję programu i jednostkę. Domyślnie wybierana jest najnowsza dostępna edycja oraz pełna wersja z pomiarem danego rodzaju. CPU domyślnie pokazuje Multi Core; GPU pokazuje test GPU, a gdy go nie ma — dostępny starszy test graficzny, np. OpenGL. Testy Single Core, Multi Core, renderowania GPU i historyczne testy graficzne mają osobne rankingi.

Nowy raport automatycznie zasila rankingi odpowiadające jego pomiarom. Rankingi są wyliczane z bazy na bieżąco, więc zapis z formularza, pliku lub CSV oraz usunięcie raportu od razu aktualizują zestawienia. Nie trzeba osobno przypisywać pomiarów do modeli ani odbudowywać rankingu. Jeden plik nadal jest jednym rekordem w bazie, nawet jeśli zasila więcej niż jeden ranking.

Modele są porządkowane malejąco według średniej arytmetycznej dostępnych wyników. Nazwy są porównywane bez wielkości liter i nadmiarowych spacji, z zachowaniem innych różnic. Obok wyniku jest liczba pomiarów. Średnia i kolejność używają pełnej precyzji, a wyświetlanie dwóch miejsc po przecinku. Dokładne remisy współdzielą miejsce (1, 1, 3). Wersje, jednostki i testy nie są łączone. Brak modelu GPU nie blokuje zapisu raportu, ale jego pomiar nie tworzy anonimowego wpisu w rankingu GPU.

Kliknij nazwę CPU lub GPU w rankingu albo archiwum, aby otworzyć historię tego modelu. Pokazuje ona **wszystkie zapisane raporty ze wszystkich edycji Cinebench**, podzielone na edycje, z pełnymi wersjami, pomiarami, systemem, datą, plikiem źródłowym i notatkami. Historia zawiera także częściowe raporty z nazwą tego modelu, w których nie wykonano odpowiedniego testu. Osobne podsumowania średnich zachowują rozdział wersji/testu/jednostki. Wyszukiwanie modelu jest dokładne po normalizacji nazwy — kliknięcie CPU A nie otwiera CPU A Plus. Filtry archiwum i aktualna wersja rankingu nie zawężają historii modelu.

Historia jest lokalnym oknem dialogowym; zamknij przyciskiem Zamknij lub klawiszem Escape. Pusta baza pokazuje puste rankingi, które uzupełnią się po pierwszym imporcie. Nie ma dodatkowej migracji danych z v5.

API: `GET /api/rankings?device=cpu&edition=R23&metric=cpu_multi&benchmark_version=23.200&unit=pts`, `GET /api/hardware?device=gpu&model=...`. Wyniki rankingów są widokami, bez osobnych kopii raportów w bazie.

## Sortowanie i średnie

Wybierz widok i sortowanie. Nagłówki CPU, GPU oraz wyników także zmieniają sortowanie rosnąco/malejąco. Brakujące wartości są na końcu.

- **Średnie CPU + GPU** (domyślnie): jedna grupa dla identycznej pary modeli CPU/GPU, edycji, pełnej wersji i zgodnych jednostek. Wszystkie kolumny wyników są uśredniane oddzielnie.
- **Średnie według CPU**: ten sam procesor, niezależnie od karty graficznej. Średnie obejmują tylko Single Core i Multi Core.
- **Średnie według GPU**: ta sama karta, niezależnie od procesora. Średnie obejmują tylko GPU, OpenGL i Shading. Raporty bez nazwy GPU nie tworzą anonimowej grupy GPU.
- **Oryginalne raporty**: każdy importowany plik w osobnym wierszu z kompletem wyników. Usunięcie usuwa cały raport.

Nazwy sprzętu są porównywane bez wielkości liter i nadmiarowych spacji; inne różnice w nazwach pozostają rozdzielone. Nie stosujemy przybliżonego dopasowywania modeli. Wersje, jednostki i rodzaje testów nie są mieszane. Grupy mogą obejmować różne systemy, taktowania i konfiguracje tego samego modelu sprzętu; średnia opisuje zapisane pomiary i nie jest kontrolowanym porównaniem tych konfiguracji. Filtry są stosowane przed uśrednianiem.

`n` przy każdej średniej oznacza rzeczywistą liczbę dostępnych pomiarów tej kolumny. Brak wyniku nie jest zerem. Liczba raportów grupy jest podawana oddzielnie. Średnie są wyliczane z pełnej precyzji, zaokrąglane dopiero przy wyświetlaniu. Oryginały w bazie nie są zastępowane średnimi. Nie ma przeliczania wyników między edycjami benchmarku.

## Baza i CSV

Tabela `results`: jeden rekord raportu z danymi sprzętu i polami `cpu_single`, `cpu_multi`, `gpu_score`, `opengl`, `shading`, `opengl_software`, `opengl_hardware`, `opengl_standard`. Każda kolumna ma własną jednostkę w polu z końcówką `_unit`. Schemat: `schema.sql`.

```sql
SELECT cpu, gpu, cpu_single, cpu_multi, gpu_score
FROM results
WHERE edition = 'R23' AND cpu_multi_unit = 'pts'
ORDER BY cpu_multi DESC;
```

CSV: jeden wiersz to jeden raport, UTF-8, separator przecinek/średnik/tabulator. Pobierz aktualny szablon z aplikacji. Kolumny nieobowiązkowe można pominąć. Przy podaniu wyniku wymagana jest jego jednostka. Przykład:

```csv
edition,cpu,gpu,cpu_single,cpu_single_unit,cpu_multi,cpu_multi_unit,benchmark_version,os
R23,Example CPU,,100.12,pts,12345.50,pts,23.200,Windows 10 (build 19045)
```

Eksport CSV dotyczy aktualnego widoku i ma dwa miejsca po przecinku. Eksport średnich zawiera także liczby raportów i liczebności pomiarów; jest zestawieniem, a nie plikiem do ponownego importu. Do ponownego importu CSV wybierz **Oryginalne raporty** (CSV zaokrągla wyniki; kopia SQLite i SQL zachowują pełną precyzję). Import jest transakcyjny: błąd jednego wiersza anuluje cały zapis. Stare CSV z osobnym wierszem na każdy test wymagają ponownego eksportu z nowej aplikacji; nie są przyjmowane jako nowe raporty.

Przycisk **Pobierz bazę SQLite** tworzy spójną kopię całej bazy. Można ją otworzyć np. w DB Browser for SQLite. Jest to SQLite, a nie format MySQL/MSSQL. CSV zachowuje oryginalne teksty; przy otwieraniu niezaufanych danych w arkuszu wybierz tekstowy typ kolumn, aby nie interpretować formuł.

## Aktualizacja starej bazy

Przy pierwszym uruchomieniu v4 program zapisuje kopię `cinebench.sqlite3.before-v4.sqlite3` obok bazy (jeśli nazwa jest zajęta, wybiera kolejny numer). Następnie transakcyjnie przebudowuje tabelę. Łączy stare wiersze z tą samą nazwą pliku, konfiguracją, wersją i czasem importu z dokładnością do sekundy, do momentu powtórzenia rodzaju testu. Osobne powtórne importy pozostają osobnymi raportami. Oryginalne wartości i notatki są zachowywane. Rekord bez pliku źródłowego pozostaje osobnym raportem, ponieważ nie można bezpiecznie odtworzyć jego pochodzenia. Zachowany jest identyfikator pierwszego wiersza każdej grupy; wszystkie stare identyfikatory są dostępne w kopii bazy.

Starsza baza nie zawiera wcześniej pominiętych pustych raportów — takie pliki trzeba ponownie zaimportować. Do osobnej bazy przykładowej dołączono także pustą próbkę 2024, dlatego ma ona 25 raportów i 62 pomiary. Aktualizacja v4 do v5 dodaje tylko tabelę potwierdzeń importu, bez zmiany rekordów raportów. Błąd migracji pozostawia starą tabelę bez zmian.

## Testy

```sh
python -m unittest discover -s tests -v
```

Testy korzystają z tymczasowych baz i lokalnego serwera. Sprawdzają dokładne wartości z 25 próbek, jeden plik/jeden rekord, komplet kolumn, sortowanie, średnie i ich liczebności, rozdzielanie wersji i jednostek, wartości brakujące, migrację z kopią bazy, zachowanie powtórnych importów, walidację i przepływ HTTP/CSV. Dodatkowe testy sprawdzają pierwszy start bez bazy i katalogu, pusty plik, ochronę uszkodzonej bazy, częściowo błędne partie oraz równoległe ponowienia bez dublowania rekordów. Testy rankingów sprawdzają średnie i remisy, rozdział wersji/testów/jednostek, brak nazwy GPU, historie dokładnie dopasowanych modeli oraz automatyczną aktualizację po imporcie i usunięciu. Dane użytkownika pozostają bez zmian.
