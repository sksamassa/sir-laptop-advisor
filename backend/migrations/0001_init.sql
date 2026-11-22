-- SIR laptop selection service: initial schema.
-- Applied by laptop_dss.shared.adapters.db.migrate(); never edited after release.

CREATE TABLE IF NOT EXISTS users (
    id uuid PRIMARY KEY,
    email text NOT NULL,
    password_hash text NOT NULL,
    role text NOT NULL DEFAULT 'shopper' CHECK (role IN ('shopper', 'maintainer')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS users_email_lower_idx ON users (lower(email));

CREATE TABLE IF NOT EXISTS sessions (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    token_hash bytea NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    absolute_expires_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_user_idx ON sessions (user_id);
CREATE INDEX IF NOT EXISTS sessions_expiry_idx ON sessions (expires_at);

CREATE TABLE IF NOT EXISTS profiles (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL UNIQUE REFERENCES users (id) ON DELETE CASCADE,
    goals text[] NOT NULL,
    budget_minor bigint NOT NULL CHECK (budget_minor > 0 AND budget_minor <= 100000000),
    preferred_brand text,
    preferred_os text CHECK (preferred_os IN ('windows', 'macos', 'linux')),
    form_factor text CHECK (form_factor IN ('ultrabook', 'laptop', 'gaming', 'convertible')),
    w_price numeric(9, 6) NOT NULL CHECK (w_price >= 0),
    w_performance numeric(9, 6) NOT NULL CHECK (w_performance >= 0),
    w_memory numeric(9, 6) NOT NULL CHECK (w_memory >= 0),
    w_weight numeric(9, 6) NOT NULL CHECK (w_weight >= 0),
    w_battery numeric(9, 6) NOT NULL CHECK (w_battery >= 0),
    w_screen numeric(9, 6) NOT NULL CHECK (w_screen >= 0),
    w_warranty numeric(9, 6) NOT NULL CHECK (w_warranty >= 0),
    revision integer NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT profiles_weight_sum CHECK (
        w_price + w_performance + w_memory + w_weight + w_battery + w_screen + w_warranty
        BETWEEN 0.999999 AND 1.000001
    )
);

CREATE TABLE IF NOT EXISTS device_models (
    id uuid PRIMARY KEY,
    brand text NOT NULL CHECK (char_length(brand) BETWEEN 1 AND 60),
    model_name text NOT NULL CHECK (char_length(model_name) BETWEEN 1 AND 120),
    slug text NOT NULL UNIQUE,
    os text NOT NULL CHECK (os IN ('windows', 'macos', 'linux')),
    form_factor text NOT NULL CHECK (form_factor IN ('ultrabook', 'laptop', 'gaming', 'convertible')),
    price_minor bigint NOT NULL CHECK (price_minor > 0),
    cpu_score integer NOT NULL CHECK (cpu_score > 0),
    ram_gb integer NOT NULL CHECK (ram_gb BETWEEN 4 AND 256),
    weight_g integer NOT NULL CHECK (weight_g BETWEEN 500 AND 5000),
    battery_minutes integer NOT NULL CHECK (battery_minutes BETWEEN 60 AND 2000),
    screen_score numeric(4, 2) NOT NULL CHECK (screen_score BETWEEN 0 AND 10),
    warranty_months integer NOT NULL CHECK (warranty_months BETWEEN 0 AND 60),
    status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'retired')),
    published_at timestamptz,
    retired_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (brand, model_name)
);
CREATE INDEX IF NOT EXISTS device_models_status_price_idx ON device_models (status, price_minor);
CREATE INDEX IF NOT EXISTS device_models_brand_idx ON device_models (brand);
CREATE INDEX IF NOT EXISTS device_models_os_idx ON device_models (os);
CREATE INDEX IF NOT EXISTS device_models_form_idx ON device_models (form_factor);

CREATE TABLE IF NOT EXISTS rankings (
    id uuid PRIMARY KEY,
    user_id uuid REFERENCES users (id) ON DELETE SET NULL,
    preferences jsonb NOT NULL,
    catalog_snapshot jsonb NOT NULL,
    algorithm_version text NOT NULL,
    criteria_version text NOT NULL,
    candidate_count integer NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS rankings_user_created_idx ON rankings (user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS ranking_items (
    ranking_id uuid NOT NULL REFERENCES rankings (id) ON DELETE CASCADE,
    rank integer NOT NULL,
    model_id uuid NOT NULL,
    model_snapshot jsonb NOT NULL,
    phi_plus numeric(12, 9) NOT NULL,
    phi_minus numeric(12, 9) NOT NULL,
    net_score numeric(12, 9) NOT NULL,
    contributions jsonb NOT NULL,
    reason text NOT NULL,
    PRIMARY KEY (ranking_id, rank),
    UNIQUE (ranking_id, model_id)
);

CREATE TABLE IF NOT EXISTS processed_events (
    event_id uuid NOT NULL,
    handler text NOT NULL,
    processed_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (event_id, handler)
);
