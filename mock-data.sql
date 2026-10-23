-- ============================================================
-- VIDEO SEARCH — MOCK DATASET (10 students)
-- Run AFTER schema.sql.
-- These are test records. Replace with real data when ready.
-- ============================================================

insert into public.videos (
  student_name, first_name, last_name,
  school_name, event_name, event_year,
  program_name, degree_name,
  thumbnail_url, smugmug_url, download_url,
  status, is_active
) values

-- Dallas Commencement 2025
(
  'Maria Rodriguez', 'Maria', 'Rodriguez',
  'Western Governors University', 'Dallas Commencement', 2025,
  'Business Administration', 'Master of Business Administration',
  'https://placehold.co/640x360/193029/ffffff?text=Maria+Rodriguez',
  'https://fatfish.smugmug.com/WGU/Commencement-Weekends/Dallas-2025/Maria-Rodriguez/',
  'https://fatfish.smugmug.com/WGU/Commencement-Weekends/Dallas-2025/Maria-Rodriguez/download/',
  'live', true
),
(
  'James Chen', 'James', 'Chen',
  'Western Governors University', 'Dallas Commencement', 2025,
  'Computer Science', 'Bachelor of Science',
  'https://placehold.co/640x360/193029/ffffff?text=James+Chen',
  'https://fatfish.smugmug.com/WGU/Commencement-Weekends/Dallas-2025/James-Chen/',
  'https://fatfish.smugmug.com/WGU/Commencement-Weekends/Dallas-2025/James-Chen/download/',
  'live', true
),
(
  'Aisha Johnson', 'Aisha', 'Johnson',
  'Western Governors University', 'Dallas Commencement', 2025,
  'Nursing', 'Bachelor of Science',
  'https://placehold.co/640x360/193029/ffffff?text=Aisha+Johnson',
  'https://fatfish.smugmug.com/WGU/Commencement-Weekends/Dallas-2025/Aisha-Johnson/',
  'https://fatfish.smugmug.com/WGU/Commencement-Weekends/Dallas-2025/Aisha-Johnson/download/',
  'live', true
),
(
  'Michael Williams', 'Michael', 'Williams',
  'Western Governors University', 'Dallas Commencement', 2025,
  'Cybersecurity and Information Assurance', 'Master of Science',
  'https://placehold.co/640x360/193029/ffffff?text=Michael+Williams',
  'https://fatfish.smugmug.com/WGU/Commencement-Weekends/Dallas-2025/Michael-Williams/',
  'https://fatfish.smugmug.com/WGU/Commencement-Weekends/Dallas-2025/Michael-Williams/download/',
  'live', true
),

-- Chicago Commencement 2025
(
  'Sarah Park', 'Sarah', 'Park',
  'Western Governors University', 'Chicago Commencement', 2025,
  'Healthcare Management', 'Bachelor of Science',
  'https://placehold.co/640x360/7842E8/ffffff?text=Sarah+Park',
  'https://fatfish.smugmug.com/WGU/Commencement-Weekends/Chicago-2025/Sarah-Park/',
  'https://fatfish.smugmug.com/WGU/Commencement-Weekends/Chicago-2025/Sarah-Park/download/',
  'live', true
),
(
  'David Martinez', 'David', 'Martinez',
  'Western Governors University', 'Chicago Commencement', 2025,
  'Data Analytics', 'Master of Science',
  'https://placehold.co/640x360/7842E8/ffffff?text=David+Martinez',
  'https://fatfish.smugmug.com/WGU/Commencement-Weekends/Chicago-2025/David-Martinez/',
  'https://fatfish.smugmug.com/WGU/Commencement-Weekends/Chicago-2025/David-Martinez/download/',
  'live', true
),
(
  'Emily Thompson', 'Emily', 'Thompson',
  'Western Governors University', 'Chicago Commencement', 2025,
  'Accounting', 'Bachelor of Science',
  'https://placehold.co/640x360/7842E8/ffffff?text=Emily+Thompson',
  'https://fatfish.smugmug.com/WGU/Commencement-Weekends/Chicago-2025/Emily-Thompson/',
  'https://fatfish.smugmug.com/WGU/Commencement-Weekends/Chicago-2025/Emily-Thompson/download/',
  'live', true
),

-- Las Vegas Commencement 2025
(
  'Carlos Rivera', 'Carlos', 'Rivera',
  'Western Governors University', 'Las Vegas Commencement', 2025,
  'Software Engineering', 'Bachelor of Science',
  'https://placehold.co/640x360/0d6630/ffffff?text=Carlos+Rivera',
  'https://fatfish.smugmug.com/WGU/Commencement-Weekends/Las-Vegas-2025/Carlos-Rivera/',
  'https://fatfish.smugmug.com/WGU/Commencement-Weekends/Las-Vegas-2025/Carlos-Rivera/download/',
  'live', true
),
(
  'Priya Patel', 'Priya', 'Patel',
  'Western Governors University', 'Las Vegas Commencement', 2025,
  'Healthcare Management', 'Master of Business Administration',
  'https://placehold.co/640x360/0d6630/ffffff?text=Priya+Patel',
  'https://fatfish.smugmug.com/WGU/Commencement-Weekends/Las-Vegas-2025/Priya-Patel/',
  'https://fatfish.smugmug.com/WGU/Commencement-Weekends/Las-Vegas-2025/Priya-Patel/download/',
  'live', true
),
(
  'Tyler Anderson', 'Tyler', 'Anderson',
  'Western Governors University', 'Las Vegas Commencement', 2025,
  'Information Technology Management', 'Bachelor of Science',
  'https://placehold.co/640x360/0d6630/ffffff?text=Tyler+Anderson',
  'https://fatfish.smugmug.com/WGU/Commencement-Weekends/Las-Vegas-2025/Tyler-Anderson/',
  'https://fatfish.smugmug.com/WGU/Commencement-Weekends/Las-Vegas-2025/Tyler-Anderson/download/',
  'live', true
);

-- Verify
select id, student_name, event_name, event_year, status, is_active from public.videos order by last_name;
