-- Drop tables if they exist (in reverse dependency order)
DROP TABLE IF EXISTS  notifications, reports, resource_authors, authors, resources, payments, users, plans;

-- Create Plans table
CREATE TABLE plans (
    id SERIAL PRIMARY KEY,
    name VARCHAR(20) UNIQUE NOT NULL,
    description TEXT,
    price_rs INTEGER NOT NULL,
    duration_days INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(15) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    roles VARCHAR(10) NOT NULL DEFAULT 'user',
    subscription_status VARCHAR(20) DEFAULT 'inactive',
    plan_id INTEGER REFERENCES plans(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

-- Create Payments table
CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    plan_id INTEGER REFERENCES plans(id),
    amount FLOAT NOT NULL,
    date DATE NOT NULL,
    expiry_date DATE NOT NULL,
    khalti_token VARCHAR(255) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

-- Create Resources table
CREATE TABLE resources (
   id SERIAL PRIMARY KEY,
   title TEXT NOT NULL,
   content TEXT NOT NULL,
   file_path TEXT NULL,
   file_url TEXT NULL,
   publication_date DATE,
   publisher VARCHAR(50),
   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
   updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
   deleted_at TIMESTAMP
);

-- Create Authors table
CREATE TABLE authors (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    title VARCHAR(50) NULL,
    degree VARCHAR(100) NULL,
    affiliation VARCHAR(255) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Resource-Authors join table
CREATE TABLE resource_authors (
    resource_id INTEGER REFERENCES resources(id) ON DELETE CASCADE,
    author_id INTEGER REFERENCES authors(id) ON DELETE CASCADE,
    PRIMARY KEY (resource_id, author_id)
);

-- Create Reports table
CREATE TABLE reports (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  submitted_document TEXT,
  unique_score FLOAT NOT NULL,
  total_exact_score FLOAT NOT NULL,
  total_partial_score FLOAT NOT NULL,
  words INTEGER,
  characters INTEGER,
  citation_status TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

-- Create Notifications table
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    event_type VARCHAR(50),
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- create expired token table
CREATE TABLE blacklisted_tokens (
    id SERIAL PRIMARY KEY,
    token TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL
);

-- CREATE TABLE password_reset_tokens (
--     id SERIAL PRIMARY KEY,
--     user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
--     otp_code VARCHAR(10) NOT NULL,
--     expires_at TIMESTAMP NOT NULL,
--     used BOOLEAN DEFAULT FALSE,
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- );

