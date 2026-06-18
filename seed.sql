-- Seed data for Handholding Content Engine

INSERT INTO users (email, name, created_at) VALUES
  ('user@example.com', 'Test User', NOW());

INSERT INTO niches (user_id, name, audience, monetization_angle, notes, created_at) VALUES
  (1, 'Personal Finance for Gen Z', 'Ages 18-30 interested in wealth building', 'Ad revenue + affiliate products', 'Focus on practical tips, not theory', NOW());

INSERT INTO competitor_inputs (niche_id, title_or_url, notes, created_at) VALUES
  (1, 'How to Save $10,000 in 3 Months', 'Strong hook, shows ROI upfront', NOW()),
  (1, 'The Money Habits of Millionaires', 'Mystery angle hooks people', NOW()),
  (1, 'Passive Income Ideas That Actually Work', 'Pattern interrupt every 60 seconds', NOW()),
  (1, 'I Tracked My Spending for 30 Days...', 'Personal journey format', NOW()),
  (1, 'Top 5 Money Mistakes Gen Z Makes', 'Educational + entertainment', NOW());
