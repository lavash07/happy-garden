CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS zones (
    id TEXT PRIMARY KEY,
    data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pots (
    id TEXT PRIMARY KEY,
    zone_id TEXT NOT NULL,
    data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS groups_ (
    id TEXT PRIMARY KEY,
    zone_id TEXT NOT NULL,
    data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    pot_id TEXT NOT NULL,
    zone_id TEXT NOT NULL,
    data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reminders (
    id TEXT PRIMARY KEY,
    zone_id TEXT NOT NULL,
    fire_at TEXT NOT NULL,
    done INTEGER NOT NULL,
    data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS friends (
    id TEXT PRIMARY KEY,
    data TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pots_zone ON pots(zone_id);
CREATE INDEX IF NOT EXISTS idx_groups_zone ON groups_(zone_id);
CREATE INDEX IF NOT EXISTS idx_events_pot ON events(pot_id);
CREATE INDEX IF NOT EXISTS idx_events_zone ON events(zone_id);
CREATE INDEX IF NOT EXISTS idx_reminders_zone ON reminders(zone_id);
