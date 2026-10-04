# 🗄️ Scan Job Database Schema Template

This document provides a database schema template for implementing scan job functionality with two core tables: ScanJob and Results.

---

## 📋 Overview

The Scan Job database schema consists of two main tables:

1. **ScanJob** - Core scan job management and tracking
2. **[ResultTable]** - Storage for scan results and extracted data

---

## 🏗️ Table Schemas

### 1. ScanJob Table

**Purpose**: Core scan job management and status tracking

| **Column Name**         | **Type**    | **Constraints**           | **Description**                          |
|-------------------------|-------------|---------------------------|------------------------------------------|
| `id`                    | String      | PRIMARY KEY               | Unique internal identifier               |
| `scan_id`               | String      | UNIQUE, NOT NULL, INDEX   | External scan identifier                 |
| `status`                | String      | NOT NULL, INDEX           | pending, running, completed, failed, cancelled |
| `scan_type`             | String      | NOT NULL                  | Type of scan (user, project, calendar, etc.) |
| `config`                | JSON        | NOT NULL                  | Scan configuration and parameters        |
| `organization_id`       | String      | NULLABLE                  | Organization/tenant identifier           |
| `error_message`         | Text        | NULLABLE                  | Error details if scan failed            |
| `started_at`            | DateTime    | NULLABLE                  | When scan execution started             |
| `completed_at`          | DateTime    | NULLABLE                  | When scan finished                      |
| `total_items`           | Integer     | DEFAULT 0                 | Total items to process                  |
| `processed_items`       | Integer     | DEFAULT 0                 | Items successfully processed            |
| `failed_items`          | Integer     | DEFAULT 0                 | Items that failed processing            |
| `success_rate`          | String      | NULLABLE                  | Calculated success percentage           |
| `batch_size`            | Integer     | DEFAULT 50                | Processing batch size                   |
| `created_at`            | DateTime    | NOT NULL                  | Record creation timestamp               |
| `updated_at`            | DateTime    | NOT NULL                  | Record last update timestamp            |

**Indexes:**
```sql
-- Performance indexes
CREATE INDEX idx_scan_status_created ON scan_jobs(status, created_at);
CREATE INDEX idx_scan_id_status ON scan_jobs(scan_id, status);
CREATE INDEX idx_scan_type_status ON scan_jobs(scan_type, status);
CREATE INDEX idx_scan_org_status ON scan_jobs(organization_id, status);
```

---

### 2. [ResultTable] Table (Completely Customizable)

**Purpose**: Store scan results and extracted data - **CUSTOMIZE FIELDS FOR YOUR DATA TYPE**

| **Column Name**         | **Type**    | **Constraints**           | **Description**                          |
|-------------------------|-------------|---------------------------|------------------------------------------|
| `id`                    | String      | PRIMARY KEY               | Unique result identifier                 |
| `scan_job_id`           | String      | FOREIGN KEY, NOT NULL     | Reference to scan_jobs.id               |
| `[custom_field_1]`      | String/JSON | CUSTOMIZABLE              | **Replace with your data fields**       |
| `[custom_field_2]`      | String/JSON | CUSTOMIZABLE              | **Replace with your data fields**       |
| `[custom_field_3]`      | String/JSON | CUSTOMIZABLE              | **Replace with your data fields**       |
| `[custom_field_4]`      | String/JSON | CUSTOMIZABLE              | **Replace with your data fields**       |
| `[custom_field_5]`      | String/JSON | CUSTOMIZABLE              | **Replace with your data fields**       |
| `[custom_field_n]`      | String/JSON | CUSTOMIZABLE              | **Add as many fields as needed**        |
| `created_at`            | DateTime    | NOT NULL                  | Record creation timestamp               |
| `updated_at`            | DateTime    | NOT NULL                  | Record last update timestamp            |

**🎯 EXAMPLES - Replace with YOUR custom fields:**

**For User Extraction:**
```sql
CREATE TABLE user_results (
    id VARCHAR PRIMARY KEY,
    scan_job_id VARCHAR NOT NULL REFERENCES scan_jobs(id),
    user_id VARCHAR NOT NULL,
    username VARCHAR,
    email VARCHAR,
    display_name VARCHAR,
    department VARCHAR,
    status VARCHAR,
    last_login TIMESTAMP,
    permissions JSON,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

**For Project Extraction:**
```sql
CREATE TABLE project_results (
    id VARCHAR PRIMARY KEY,
    scan_job_id VARCHAR NOT NULL REFERENCES scan_jobs(id),
    project_id VARCHAR NOT NULL,
    project_key VARCHAR,
    project_name VARCHAR,
    description TEXT,
    project_type VARCHAR,
    lead_email VARCHAR,
    created_date TIMESTAMP,
    components JSON,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

**For Calendar Events:**
```sql
CREATE TABLE calendar_events (
    id VARCHAR PRIMARY KEY,
    scan_job_id VARCHAR NOT NULL REFERENCES scan_jobs(id),
    event_id VARCHAR NOT NULL,
    title VARCHAR,
    organizer_email VARCHAR,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    location VARCHAR,
    attendees JSON,
    is_virtual BOOLEAN,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

**For Generic JSON Storage:**
```sql
CREATE TABLE scan_results (
    id VARCHAR PRIMARY KEY,
    scan_job_id VARCHAR NOT NULL REFERENCES scan_jobs(id),
    result_data JSON NOT NULL,  -- Store everything in JSON
    result_type VARCHAR,        -- Optional: categorize results
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

**Indexes (Customize based on your fields):**
```sql
-- Basic performance indexes
CREATE INDEX idx_result_scan_job ON [result_table](scan_job_id);

-- CUSTOMIZE THESE based on your actual fields:
CREATE INDEX idx_result_custom_field ON [result_table]([your_main_id_field]);
CREATE INDEX idx_result_search ON [result_table]([your_searchable_field]);
CREATE INDEX idx_result_filter ON [result_table]([your_filter_field]);

-- Examples for different data types:
-- For users: CREATE INDEX idx_user_email ON user_results(email);
-- For projects: CREATE INDEX idx_project_key ON project_results(project_key);  
-- For events: CREATE INDEX idx_event_time ON calendar_events(start_time);
```

---

---

## 🔗 Relationships

### Primary Relationships
```sql
-- ScanJob to Results (One-to-Many)
scan_jobs.id ← [result_table].scan_job_id
```

### Cascade Behavior
- **DELETE ScanJob**: Cascades to delete all related results

---

## 📊 Common Queries

### Basic Scan Management

```sql
-- Get scan job with status
SELECT id, scan_id, status, scan_type, total_items, processed_items 
FROM scan_jobs 
WHERE scan_id = 'your-scan-id';

-- Get active scans
SELECT scan_id, status, started_at, scan_type 
FROM scan_jobs 
WHERE status IN ('running', 'pending') 
ORDER BY created_at DESC;

-- Get scan progress
SELECT 
    scan_id,
    total_items,
    processed_items,
    CASE 
        WHEN total_items > 0 THEN ROUND((processed_items * 100.0 / total_items), 2)
        ELSE 0 
    END as progress_percentage
FROM scan_jobs 
WHERE scan_id = 'your-scan-id';
```

### Results Management (Customize field names)

```sql
-- Get paginated results (REPLACE field names with yours)
SELECT id, [your_id_field], [your_name_field], [your_status_field]
FROM [result_table] 
WHERE scan_job_id = 'job-id'
ORDER BY created_at 
LIMIT 100 OFFSET 0;

-- Count results by type (REPLACE with your categorization field)
SELECT [your_category_field], COUNT(*) as count
FROM [result_table] 
WHERE scan_job_id = 'job-id'
GROUP BY [your_category_field];

-- Search results (CUSTOMIZE based on your searchable fields)
SELECT * FROM [result_table] 
WHERE scan_job_id = 'job-id' 
AND [your_searchable_field] LIKE '%search_term%';

-- Example queries for different data types:

-- For user results:
-- SELECT user_id, username, email FROM user_results WHERE scan_job_id = 'job-id';

-- For project results:  
-- SELECT project_key, project_name FROM project_results WHERE scan_job_id = 'job-id';

-- For calendar events:
-- SELECT event_id, title, start_time FROM calendar_events WHERE scan_job_id = 'job-id';
```

### Control Operations

```sql
-- Get scan job status and basic info
SELECT scan_id, status, started_at, completed_at, error_message
FROM scan_jobs 
WHERE scan_id = 'your-scan-id';

-- Cancel a scan (update status)
UPDATE scan_jobs 
SET status = 'cancelled', 
    completed_at = CURRENT_TIMESTAMP,
    error_message = 'Cancelled by user'
WHERE scan_id = 'your-scan-id' 
AND status IN ('pending', 'running');
```

---

## 🛠️ Implementation Examples

### Creating a New Scan Job

```sql
-- Create scan job
INSERT INTO scan_jobs (
    id, scan_id, status, scan_type, config, organization_id, batch_size
) VALUES (
    'uuid-1', 'my-scan-001', 'pending', 'user_extraction', 
    '{"auth": {"token": "..."}, "filters": {...}}', 
    'org-123', 100
);
```

### Adding Results (Customize with your fields)

```sql
-- Insert scan results - REPLACE with YOUR field names and values
INSERT INTO [result_table] (
    id, scan_job_id, [your_field_1], [your_field_2], [your_field_3]
) VALUES 
('uuid-3', 'uuid-1', '[value_1]', '[value_2]', '[value_3]'),
('uuid-4', 'uuid-1', '[value_1]', '[value_2]', '[value_3]');

-- Examples for different data types:

-- For user extraction:
-- INSERT INTO user_results (id, scan_job_id, user_id, username, email, department)
-- VALUES ('uuid-3', 'uuid-1', 'user-001', 'john.doe', 'john@example.com', 'Engineering');

-- For project extraction:
-- INSERT INTO project_results (id, scan_job_id, project_id, project_key, project_name, project_type)
-- VALUES ('uuid-3', 'uuid-1', 'proj-001', 'ENG', 'Engineering Project', 'software');

-- For calendar extraction:
-- INSERT INTO calendar_events (id, scan_job_id, event_id, title, organizer_email, start_time)
-- VALUES ('uuid-3', 'uuid-1', 'evt-001', 'Team Meeting', 'manager@example.com', '2024-01-15 10:00:00');

-- Update scan job progress
UPDATE scan_jobs 
SET processed_items = processed_items + 2,
    updated_at = CURRENT_TIMESTAMP
WHERE id = 'uuid-1';
```

### Status Updates

```sql
-- Start scan
UPDATE scan_jobs 
SET status = 'running', 
    started_at = CURRENT_TIMESTAMP 
WHERE scan_id = 'my-scan-001';

-- Complete scan
UPDATE scan_jobs 
SET status = 'completed', 
    completed_at = CURRENT_TIMESTAMP,
    success_rate = CASE 
        WHEN total_items > 0 THEN ROUND(((total_items - failed_items) * 100.0 / total_items), 2)::TEXT || '%'
        ELSE '100%' 
    END
WHERE scan_id = 'my-scan-001';
```

---

## 🔧 Customization Options

### Result Table Naming
Replace `[result_table]` with your preferred name:
- `scan_results` (generic)
- `user_results` (specific to user scans)
- `extraction_results` (for data extraction)
- `calendar_events` (for calendar data)
- `project_data` (for project information)

### Result Table Customization Examples

**Replace `[result_table]` and customize fields for your specific data:**

**1. User/People Data:**
```sql
CREATE TABLE user_results (
    id VARCHAR PRIMARY KEY,
    scan_job_id VARCHAR REFERENCES scan_jobs(id),
    user_id VARCHAR UNIQUE,
    username VARCHAR,
    email VARCHAR,
    display_name VARCHAR,
    department VARCHAR,
    job_title VARCHAR,
    manager_email VARCHAR,
    status VARCHAR, -- active, inactive, suspended
    last_login TIMESTAMP,
    permissions JSON,
    profile_data JSON,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

**2. Project/Repository Data:**
```sql  
CREATE TABLE project_results (
    id VARCHAR PRIMARY KEY,
    scan_job_id VARCHAR REFERENCES scan_jobs(id),
    project_id VARCHAR UNIQUE,
    project_key VARCHAR,
    project_name VARCHAR,
    description TEXT,
    project_type VARCHAR, -- software, business, etc.
    lead_email VARCHAR,
    team_members JSON,
    project_status VARCHAR,
    created_date TIMESTAMP,
    last_updated TIMESTAMP,
    settings JSON,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

**3. Issue/Ticket Data:**
```sql
CREATE TABLE issue_results (
    id VARCHAR PRIMARY KEY,  
    scan_job_id VARCHAR REFERENCES scan_jobs(id),
    issue_id VARCHAR UNIQUE,
    issue_key VARCHAR,
    title VARCHAR,
    description TEXT,
    issue_type VARCHAR,
    priority VARCHAR,
    status VARCHAR,
    assignee_email VARCHAR,
    reporter_email VARCHAR,
    created_date TIMESTAMP,
    updated_date TIMESTAMP,
    resolved_date TIMESTAMP,
    labels JSON,
    custom_fields JSON,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

**4. Calendar/Event Data:**
```sql
CREATE TABLE calendar_events (
    id VARCHAR PRIMARY KEY,
    scan_job_id VARCHAR REFERENCES scan_jobs(id),
    event_id VARCHAR UNIQUE,
    calendar_id VARCHAR,
    title VARCHAR,
    description TEXT,
    organizer_name VARCHAR,
    organizer_email VARCHAR,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    location VARCHAR,
    is_virtual BOOLEAN,
    meeting_url VARCHAR,
    attendees JSON,
    event_type VARCHAR, -- meeting, appointment, etc.
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

**5. Generic/Flexible Data (when structure varies):**
```sql
CREATE TABLE scan_results (
    id VARCHAR PRIMARY KEY,
    scan_job_id VARCHAR REFERENCES scan_jobs(id),
    object_id VARCHAR, -- ID from source system
    object_type VARCHAR, -- user, project, issue, etc.
    object_name VARCHAR, -- Display name
    raw_data JSON NOT NULL, -- Complete API response
    processed_data JSON, -- Cleaned/normalized data
    extraction_metadata JSON, -- Processing info, batch, etc.
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

### Additional Columns (Optional Customizations)

**For ScanJob Table:**
```sql
-- Add service-specific columns
ALTER TABLE scan_jobs ADD COLUMN service_name VARCHAR(50);
ALTER TABLE scan_jobs ADD COLUMN api_version VARCHAR(20);
ALTER TABLE scan_jobs ADD COLUMN rate_limit_remaining INTEGER;
ALTER TABLE scan_jobs ADD COLUMN priority_level VARCHAR(20) DEFAULT 'normal';
ALTER TABLE scan_jobs ADD COLUMN max_retries INTEGER DEFAULT 3;
```

---

## 📈 Performance Considerations

### Indexing Strategy
- **Primary Operations**: Index on `scan_id`, `status`, and `created_at`
- **Filtering**: Index on `organization_id`, `scan_type`, `result_type`
- **Pagination**: Composite indexes on frequently queried column combinations
- **Foreign Keys**: Always index foreign key columns

### Data Retention
```sql
-- Archive completed scans older than 90 days
CREATE TABLE scan_jobs_archive AS SELECT * FROM scan_jobs WHERE FALSE;

-- Move old data
INSERT INTO scan_jobs_archive 
SELECT * FROM scan_jobs 
WHERE status = 'completed' 
AND completed_at < CURRENT_DATE - INTERVAL '90 days';

-- Clean up
DELETE FROM scan_jobs 
WHERE status = 'completed' 
AND completed_at < CURRENT_DATE - INTERVAL '90 days';
```

### Large Result Sets
```sql
-- Partition result table by scan_job_id for very large datasets
CREATE TABLE [result_table] (
    -- columns as defined above
) PARTITION BY HASH (scan_job_id);

-- Create partitions
CREATE TABLE [result_table]_p0 PARTITION OF [result_table] FOR VALUES WITH (modulus 4, remainder 0);
CREATE TABLE [result_table]_p1 PARTITION OF [result_table] FOR VALUES WITH (modulus 4, remainder 1);
-- etc.
```

---

## 🛡️ Data Integrity

### Constraints
```sql
-- Ensure valid status values
ALTER TABLE scan_jobs ADD CONSTRAINT check_valid_status 
CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled'));

-- Ensure valid priority levels
ALTER TABLE scan_controls ADD CONSTRAINT check_valid_priority 
CHECK (priority_level IN ('low', 'normal', 'high', 'urgent'));

-- Ensure positive values
ALTER TABLE scan_jobs ADD CONSTRAINT check_positive_counts 
CHECK (total_items >= 0 AND processed_items >= 0 AND failed_items >= 0);
```

### Triggers
```sql
-- Auto-update timestamps
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_scan_jobs_updated_at 
    BEFORE UPDATE ON scan_jobs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
```

---

### Usage Guidelines

### Best Practices
1. **Use appropriate batch sizes** for your data volume to manage memory and performance
2. **Implement proper error handling** and store error details in `error_message`
3. **Regular cleanup** of old scan jobs and results based on retention policies
4. **Monitor scan progress** using the progress tracking fields (`total_items`, `processed_items`)
5. **Use JSON config** to store flexible scan parameters and authentication details

### Common Patterns
- **Progress Tracking**: Update `processed_items` and `failed_items` as scan progresses
- **Error Recovery**: Store detailed error information in `error_message` field
- **Flexible Configuration**: Use JSON `config` field for scan parameters, auth details, filters
- **Status Management**: Use clear status transitions (pending → running → completed/failed/cancelled)
- **Data Organization**: Use meaningful `scan_id` values for easy identification

---

**Database Schema Version**: 1.0  
**Last Updated**: [Current Date]  
**Compatible With**: PostgreSQL, MySQL, SQLite, SQL Server