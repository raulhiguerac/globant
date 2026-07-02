WITH dept_hires AS (
    SELECT
        d.id,
        d.department,
        COUNT(*) AS hired
    FROM pg.public.employees e
    JOIN pg.public.departments d ON e.department_id = d.id
    WHERE EXTRACT(YEAR FROM e.hiring_datetime) = 2021
    GROUP BY d.id, d.department
),
mean_hires AS (
    SELECT AVG(hired) AS mean FROM dept_hires
)
SELECT
    dh.id,
    dh.department,
    dh.hired
FROM dept_hires dh, mean_hires
WHERE dh.hired > mean_hires.mean
ORDER BY dh.hired DESC
