-- Only exercised on a newly created synthetic database in this candidate.
CREATE TABLE rr_feedback (
 feedback_id TEXT PRIMARY KEY,
 device TEXT NOT NULL,
 client_request_id TEXT NOT NULL,
 revision INTEGER NOT NULL DEFAULT 1 CHECK(revision = 1),
 payload_json TEXT NOT NULL,
 payload_sha256 TEXT NOT NULL,
 body_sha256 TEXT NOT NULL,
 accepted_at TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','agent_read','processed')),
 ack_json TEXT,
 result_json TEXT,
 UNIQUE(device, client_request_id)
);
CREATE TABLE rr_feedback_attachment (
 feedback_id TEXT NOT NULL REFERENCES rr_feedback(feedback_id),
 attachment_id TEXT NOT NULL,
 content_type TEXT NOT NULL,
 sha256 TEXT NOT NULL,
 data BLOB NOT NULL,
 PRIMARY KEY(feedback_id, attachment_id)
);
