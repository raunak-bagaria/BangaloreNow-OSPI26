-- Check if pg_cron is enabled
SELECT * FROM pg_extension WHERE extname = 'pg_cron';

-- Enable if missing (run in SQL Editor as postgres role)
CREATE EXTENSION IF NOT EXISTS pg_cron;

SELECT cron.schedule(
  'cleanup-old-events',           -- job name
  '0 2 * * *',                    -- cron: daily at 2 AM UTC
  $$DELETE FROM public.events 
    WHERE "endDate" < NOW() 
    OR ("endDate" IS NULL AND "startDate" < NOW() - INTERVAL '7 days')$$
);

-- Verify if it is scheduled
SELECT * FROM cron.job;

-- To check execution history
SELECT * FROM cron.job_run_details 
ORDER BY start_time DESC 
LIMIT 10;