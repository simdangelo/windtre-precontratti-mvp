-- ============================================================================
-- Google Cloud Spanner (PostgreSQL Dialect) Database Schema
-- Project: Automazione Creazione Sintesi Contrattuali e Trasparenze Tariffarie
-- ============================================================================
-- Note on Spanner Best Practices:
-- 1. Primary keys are UUIDs. Generation is handled at the application layer (FastAPI) 
--    using cryptographically secure UUIDv4 to guarantee uniform key distribution and 
--    prevent database hotspots.
-- 2. Foreign keys are supported and enforced with CASCADE delete behaviors.
-- 3. Dynamic layout elements are mapped to the native Spanner "JSON" data type.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Table: segments
-- Enforces data isolation between the 9 corporate segments (e.g. Consumer, Very Mobile)
-- ----------------------------------------------------------------------------
CREATE TABLE segments (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 2. Table: users
-- Synced accounts from Google Workspace / Google Identity Platform
-- ----------------------------------------------------------------------------
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(150) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index to optimize login/authentication queries
CREATE UNIQUE INDEX idx_users_email ON users(email);

-- ----------------------------------------------------------------------------
-- 3. Table: user_segment_roles
-- Maps user Google Group associations to specific segments for strict RBAC
-- ----------------------------------------------------------------------------
CREATE TABLE user_segment_roles (
    user_id UUID NOT NULL,
    segment_id VARCHAR(50) NOT NULL,
    role VARCHAR(50) NOT NULL,
    PRIMARY KEY (user_id, segment_id),
    CONSTRAINT fk_roles_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_roles_segment FOREIGN KEY (segment_id) REFERENCES segments(id) ON DELETE CASCADE,
    CONSTRAINT chk_role_type CHECK (role IN ('editor', 'viewer', 'admin'))
);

-- ----------------------------------------------------------------------------
-- 4. Table: offers
-- Master table for commercial and technical offer parameters
-- ----------------------------------------------------------------------------
CREATE TABLE offers (
    id UUID PRIMARY KEY,
    segment_id VARCHAR(50) NOT NULL,
    commercial_name VARCHAR(255) NOT NULL,
    technology_type VARCHAR(50) NOT NULL, -- 'FTTH', 'FTTC', 'FWA', '5G', '4G'
    base_price DECIMAL(10, 2) NOT NULL,
    po_code VARCHAR(50), -- Mandatory unique code for Very Mobile offers
    current_agcom_code VARCHAR(50), -- Alphanumeric 10-char or 36-char (UUID) code from AGCOM
    status VARCHAR(20) NOT NULL, -- 'NUOVA', 'APERTA', 'CHIUSA'
    date_start DATE NOT NULL,
    date_end DATE,
    custom_filename_sintesi VARCHAR(255), -- User defined filename for Sintesi document
    custom_filename_trasparenza VARCHAR(255), -- User defined filename for Trasparenza document
    payment_method VARCHAR(50) NOT NULL DEFAULT 'credito_residuo', -- 'credito_residuo' or 'abbonamento'
    activation_price_gia_clienti DECIMAL(10, 2),
    activation_price_nuovi_nativi DECIMAL(10, 2),
    activation_price_nuovi_portabilita DECIMAL(10, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_offers_segment FOREIGN KEY (segment_id) REFERENCES segments(id) ON DELETE RESTRICT,
    CONSTRAINT chk_offer_status CHECK (status IN ('NUOVA', 'APERTA', 'CHIUSA')),
    CONSTRAINT chk_agcom_len CHECK (current_agcom_code IS NULL OR length(current_agcom_code) IN (10, 36)),
    CONSTRAINT chk_payment_method CHECK (payment_method IN ('credito_residuo', 'abbonamento'))
);

-- Index to accelerate offer queries by commercial segment
CREATE INDEX idx_offers_segment ON offers(segment_id);
-- Index to optimize Very Mobile queries via unique PO identifier
CREATE INDEX idx_offers_po ON offers(po_code);

-- ----------------------------------------------------------------------------
-- 5. Table: offer_state_history
-- Audit log tracks offer lifecycle and references historical, immutable documents
-- ----------------------------------------------------------------------------
CREATE TABLE offer_state_history (
    id UUID PRIMARY KEY,
    offer_id UUID NOT NULL,
    old_status VARCHAR(20),
    new_status VARCHAR(20) NOT NULL,
    agcom_code_used VARCHAR(10),
         UUID,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    docx_gcs_uri VARCHAR(512),
    xlsx_gcs_uri VARCHAR(512),
    sintesi_pdf_gcs_uri VARCHAR(512),
    trasparenza_pdf_gcs_uri VARCHAR(512),
    CONSTRAINT fk_history_offer FOREIGN KEY (offer_id) REFERENCES offers(id) ON DELETE CASCADE,
    CONSTRAINT fk_history_user FOREIGN KEY (changed_by) REFERENCES users(id) ON DELETE SET NULL
);

-- ----------------------------------------------------------------------------
-- 6. Table: dynamic_tables
-- Dynamically scaling Padre-Figlio structures stored in native Spanner JSON format
-- ----------------------------------------------------------------------------
CREATE TABLE dynamic_tables (
    id UUID PRIMARY KEY,
    offer_id UUID NOT NULL,
    table_identifier VARCHAR(100) NOT NULL, -- e.g. 'PREZZO', 'SERVIZI', 'COSTI'
    sequence_order INT NOT NULL,
    title VARCHAR(255),
    structural_content JSON NOT NULL, -- Contains dynamic Padre/Figlio array
    note_links JSON, -- Footnote strings and links compiled at table end
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tables_offer FOREIGN KEY (offer_id) REFERENCES offers(id) ON DELETE CASCADE
);

-- Index to query dynamic components belonging to specific offers in sequence
CREATE INDEX idx_dynamic_tables_offer ON dynamic_tables(offer_id, sequence_order);

-- ----------------------------------------------------------------------------
-- 7. Table: global_configs
-- Stores centralized system metadata (e.g. annual RDA Constant)
-- ----------------------------------------------------------------------------
CREATE TABLE global_configs (
    config_key VARCHAR(100) PRIMARY KEY,
    config_value VARCHAR(500) NOT NULL,
    description VARCHAR(500),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Initial Data Seed (Bootstrap Segments & Global RDA Constant)
-- ============================================================================
INSERT INTO segments (id, name, description) VALUES 
('W3_MOB_GA_CNS', 'WINDTRE Mobile GA Consumer', 'Windtre Mobile Generazione Attiva Consumer'),
('W3_MOB_CB_CNS', 'WINDTRE Mobile CB Consumer', 'Windtre Mobile Customer Base Consumer'),
('W3_MOB_GA_MB', 'WINDTRE Mobile GA Microbusiness', 'Windtre Mobile Generazione Attiva Microbusiness'),
('W3_FIX_GA_CNS', 'WINDTRE Fisso GA Consumer', 'Windtre Fisso Generazione Attiva Consumer'),
('W3_FIX_CB_CNS', 'WINDTRE Fisso CB Consumer', 'Windtre Fisso Customer Base Consumer'),
('W3_FIX_GA_MB', 'WINDTRE Fisso GA Microbusiness', 'Windtre Fisso Generazione Attiva Microbusiness'),
('W3_FIX_CB_MB', 'WINDTRE Fisso CB Microbusiness', 'Windtre Fisso Customer Base Microbusiness'),
('W3_ETN_CNS', 'WINDTRE Etnico Consumer', 'Windtre Etnico Consumer GA/CB'),
('VERY_MOBILE', 'Very Mobile', 'Very Mobile GA/CB Segment');

INSERT INTO global_configs (config_key, config_value, description) VALUES
('RDA_COEFFICIENT_2026', '2.0', 'Annual RDA coefficient for EU Roaming calculation'),
('CONVERGENCE_TERMS_2026', 'Mobile+Luce+Gas', 'Active convergence standard name');
