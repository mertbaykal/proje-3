SELECT MAX(date) AS last_date
FROM daily_data
WHERE symbol_id = ?;