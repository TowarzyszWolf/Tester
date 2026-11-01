PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY,
    edition TEXT NOT NULL,
    test TEXT NOT NULL CHECK(test IN ('CPU Single Core', 'CPU Multi Core', 'GPU', 'OpenGL', 'Shading (CINEMA 4D)', 'OpenGL Software Lighting', 'OpenGL Hardware Lighting', 'OpenGL Standard')),
    score REAL NOT NULL CHECK(score > 0),
    unit TEXT NOT NULL CHECK(unit IN ('pts', 'cb', 'fps', 'CB-CPU', 'CB-GFX')),
    cpu TEXT NOT NULL,
    gpu TEXT NOT NULL DEFAULT '',
    threads INTEGER CHECK(threads > 0),
    os TEXT NOT NULL DEFAULT '',
    measured_at TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    cores INTEGER CHECK(cores > 0),
    clock_mhz REAL CHECK(clock_mhz > 0),
    benchmark_version TEXT NOT NULL DEFAULT '',
    system_name TEXT NOT NULL DEFAULT '',
    architecture TEXT NOT NULL DEFAULT '',
    source_file TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_results_group ON results(edition, test, unit);
