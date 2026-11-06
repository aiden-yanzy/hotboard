BEGIN;
UPDATE sources SET enabled=false, updated_at=now()
 WHERE engine='custom' AND src_id IN ('gcores','qbitai','oschina');
COMMIT;
