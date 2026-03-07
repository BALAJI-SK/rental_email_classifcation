import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "lette.db")


async def get_db():
    """Return a raw connection (for use outside FastAPI request context)."""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def db_dependency():
    """FastAPI dependency — yields connection, closes on teardown."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            -- ============================================
            -- CORE TABLES
            -- ============================================

            CREATE TABLE IF NOT EXISTS properties (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                units INTEGER NOT NULL,
                manager TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                type TEXT NOT NULL,
                role TEXT,
                unit TEXT,
                property_id TEXT,
                lease_start TEXT,
                lease_end TEXT,
                is_known BOOLEAN DEFAULT TRUE,
                notes TEXT,
                total_messages INTEGER DEFAULT 0,
                total_threads INTEGER DEFAULT 0,
                first_seen TEXT,
                last_seen TEXT,
                sentiment_avg TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (property_id) REFERENCES properties(id)
            );

            CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email);
            CREATE INDEX IF NOT EXISTS idx_contacts_type ON contacts(type);
            CREATE INDEX IF NOT EXISTS idx_contacts_property ON contacts(property_id);

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                thread_id TEXT NOT NULL,
                thread_position INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                sender_name TEXT NOT NULL,
                sender_email TEXT,
                sender_type TEXT NOT NULL,
                sender_unit TEXT,
                sender_role TEXT,
                property_id TEXT,
                contact_id INTEGER,
                recipient TEXT,
                cc TEXT,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                attachments TEXT,
                is_read BOOLEAN DEFAULT FALSE,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (property_id) REFERENCES properties(id),
                FOREIGN KEY (contact_id) REFERENCES contacts(id)
            );

            CREATE INDEX IF NOT EXISTS idx_messages_thread ON messages(thread_id);
            CREATE INDEX IF NOT EXISTS idx_messages_property ON messages(property_id);
            CREATE INDEX IF NOT EXISTS idx_messages_sender_type ON messages(sender_type);
            CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);

            CREATE TABLE IF NOT EXISTS threads (
                id TEXT PRIMARY KEY,
                subject TEXT NOT NULL,
                property_id TEXT,
                property_name TEXT,
                category TEXT,
                urgency_level TEXT,
                urgency_score INTEGER,
                urgency_reasons TEXT,
                previous_urgency_score INTEGER,
                status TEXT DEFAULT 'open',
                ai_summary TEXT,
                recommended_actions TEXT,
                draft_response TEXT,
                sentiment TEXT,
                sentiment_trend TEXT,
                risk_flags TEXT,
                message_count INTEGER DEFAULT 0,
                follow_up_count INTEGER DEFAULT 0,
                days_open INTEGER DEFAULT 0,
                participant_names TEXT,
                participant_types TEXT,
                primary_contact_id INTEGER,
                first_message_at TEXT,
                last_message_at TEXT,
                is_read BOOLEAN DEFAULT FALSE,
                analysed_at TEXT,
                escalated_at TEXT,
                resolved_at TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (property_id) REFERENCES properties(id),
                FOREIGN KEY (primary_contact_id) REFERENCES contacts(id)
            );

            CREATE INDEX IF NOT EXISTS idx_threads_urgency ON threads(urgency_score DESC);
            CREATE INDEX IF NOT EXISTS idx_threads_property ON threads(property_id);
            CREATE INDEX IF NOT EXISTS idx_threads_category ON threads(category);
            CREATE INDEX IF NOT EXISTS idx_threads_status ON threads(status);

            CREATE TABLE IF NOT EXISTS escalation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT NOT NULL,
                old_score INTEGER,
                new_score INTEGER,
                old_level TEXT,
                new_level TEXT,
                reason TEXT NOT NULL,
                triggered_by TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (thread_id) REFERENCES threads(id)
            );

            CREATE TABLE IF NOT EXISTS pattern_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                severity TEXT NOT NULL,
                property_id TEXT,
                related_thread_ids TEXT,
                is_dismissed BOOLEAN DEFAULT FALSE,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (property_id) REFERENCES properties(id)
            );

            CREATE TABLE IF NOT EXISTS dashboard_cache (
                id INTEGER PRIMARY KEY DEFAULT 1,
                total_messages INTEGER,
                unread_messages INTEGER,
                total_threads INTEGER,
                critical_count INTEGER,
                high_count INTEGER,
                medium_count INTEGER,
                low_count INTEGER,
                morning_brief TEXT,
                voice_script TEXT,
                portfolio_health TEXT,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS export_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                export_type TEXT NOT NULL,
                filename TEXT NOT NULL,
                filters TEXT,
                row_count INTEGER,
                created_at TEXT DEFAULT (datetime('now'))
            );

            -- ============================================
            -- CONTRACTOR PROCUREMENT TABLES
            -- ============================================

            CREATE TABLE IF NOT EXISTS contractors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id INTEGER,
                company_name TEXT NOT NULL,
                contact_person TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT,
                specialties TEXT NOT NULL,
                service_areas TEXT,
                avg_rating REAL DEFAULT 0,
                total_jobs INTEGER DEFAULT 0,
                avg_response_time_hours REAL,
                avg_price_rating TEXT,
                is_emergency_available BOOLEAN DEFAULT FALSE,
                notes TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (contact_id) REFERENCES contacts(id)
            );

            CREATE INDEX IF NOT EXISTS idx_contractors_specialty ON contractors(specialties);
            CREATE INDEX IF NOT EXISTS idx_contractors_active ON contractors(is_active);

            CREATE TABLE IF NOT EXISTS procurement_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT NOT NULL,
                property_id TEXT NOT NULL,
                unit TEXT,
                work_type TEXT NOT NULL,
                work_description TEXT NOT NULL,
                urgency TEXT NOT NULL,
                status TEXT DEFAULT 'requesting_quotes',
                contractors_contacted TEXT,
                quote_deadline TEXT,
                auto_negotiate BOOLEAN DEFAULT TRUE,
                selected_contractor_id INTEGER,
                selected_price REAL,
                selected_date TEXT,
                tenant_notified BOOLEAN DEFAULT FALSE,
                pm_approved BOOLEAN DEFAULT FALSE,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (thread_id) REFERENCES threads(id),
                FOREIGN KEY (property_id) REFERENCES properties(id),
                FOREIGN KEY (selected_contractor_id) REFERENCES contractors(id)
            );

            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                procurement_job_id INTEGER NOT NULL,
                contractor_id INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                quoted_price REAL,
                quoted_currency TEXT DEFAULT 'EUR',
                availability_date TEXT,
                availability_notes TEXT,
                estimated_duration TEXT,
                terms_notes TEXT,
                raw_response TEXT,
                ai_extracted_data TEXT,
                negotiation_draft TEXT,
                negotiation_sent BOOLEAN DEFAULT FALSE,
                request_sent_at TEXT,
                response_received_at TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (procurement_job_id) REFERENCES procurement_jobs(id),
                FOREIGN KEY (contractor_id) REFERENCES contractors(id)
            );

            CREATE INDEX IF NOT EXISTS idx_quotes_job ON quotes(procurement_job_id);
            CREATE INDEX IF NOT EXISTS idx_quotes_status ON quotes(status);

            CREATE TABLE IF NOT EXISTS contractor_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contractor_id INTEGER NOT NULL,
                procurement_job_id INTEGER NOT NULL,
                property_id TEXT,
                work_type TEXT,
                quoted_price REAL,
                final_price REAL,
                promised_date TEXT,
                actual_date TEXT,
                quality_rating INTEGER,
                on_time BOOLEAN,
                on_budget BOOLEAN,
                tenant_feedback TEXT,
                notes TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (contractor_id) REFERENCES contractors(id),
                FOREIGN KEY (procurement_job_id) REFERENCES procurement_jobs(id)
            );
        """)
        await db.commit()
