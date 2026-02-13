-- Database Migrations for Wormhole Bridge

-- Bridges Table (Wormhole cross-chain transactions)
CREATE TABLE IF NOT EXISTS bridges (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    source_chain TEXT NOT NULL,  -- 'solana' or 'polygon'
    dest_chain TEXT NOT NULL,    -- 'polygon' or 'solana'
    amount_sol REAL NOT NULL,
    amount_dest REAL,            -- Amount received on destination
    status TEXT NOT NULL DEFAULT 'pending_signature',
    -- Statuses: pending_signature → submitted → attesting → attested → completing → completed → failed
    tx_hash TEXT,                -- Source chain transaction hash
    vaa_hash TEXT,               -- Wormhole VAA hash
    destination_tx TEXT,         -- Destination chain transaction hash
    error_msg TEXT,
    retries INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,    -- ISO timestamp
    updated_at TEXT NOT NULL,    -- ISO timestamp
    completed_at TEXT,           -- ISO timestamp when completed
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Bridge Status Index (for efficient polling)
CREATE INDEX IF NOT EXISTS idx_bridges_user_status 
ON bridges(user_id, status);

CREATE INDEX IF NOT EXISTS idx_bridges_created_at 
ON bridges(created_at DESC);

-- Bridge Logs Table (detailed event tracking)
CREATE TABLE IF NOT EXISTS bridge_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bridge_id TEXT NOT NULL,
    event_type TEXT NOT NULL,  -- 'signature_created', 'submitted', 'guardian_#_signed', 'vaa_complete', 'submitted_to_dest', 'completed', 'failed'
    event_data TEXT,           -- JSON details
    created_at TEXT NOT NULL,
    FOREIGN KEY (bridge_id) REFERENCES bridges(id)
);

CREATE INDEX IF NOT EXISTS idx_bridge_events_bridge_id 
ON bridge_events(bridge_id);

-- Fees Cache Table (for optimization)
CREATE TABLE IF NOT EXISTS fee_cache (
    id INTEGER PRIMARY KEY,
    last_updated TEXT NOT NULL,
    base_relayer_fee_sol REAL,
    solana_priority_fee_sol REAL,
    polygon_gas_gwei REAL,
    total_estimated_cost_sol REAL
);
