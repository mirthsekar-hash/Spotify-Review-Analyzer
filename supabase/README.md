# Supabase Migrations

## Apply Phase 1.2 schema

1. Open your [Supabase SQL Editor](https://supabase.com/dashboard)
2. Select your project
3. Paste the contents of `migrations/001_initial_schema.sql`
4. Click **Run**

## Verify

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'reviews', 'review_analysis', 'themes', 'segments',
    'root_causes', 'unmet_needs', 'embeddings', 'pipeline_runs'
  );
```

You should see 8+ tables including `pipeline_runs`.

## Test from Python

After migration and `.env` are configured:

```powershell
$env:RUN_DB_INTEGRATION=1
pytest tests/test_db_integration.py -v
```
