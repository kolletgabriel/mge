CREATE TABLE IF NOT EXISTS users (
    id INT8 GENERATED ALWAYS AS IDENTITY,
    mail TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    hashed_password TEXT NOT NULL,
    role_id INT2 NOT NULL DEFAULT 1,

    PRIMARY KEY (id),
    UNIQUE (id, role_id),
    CONSTRAINT valid_user_role CHECK (role_id IN (0, 1, 2))
);


CREATE TABLE IF NOT EXISTS auth_sessions (
    id UUID NOT NULL DEFAULT uuidv4(),
    user_id INT8 NOT NULL,
    revoked_at TIMESTAMPTZ,

    PRIMARY KEY (id),
    UNIQUE (id, user_id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);


CREATE TABLE IF NOT EXISTS classes (
    id INT8 GENERATED ALWAYS AS IDENTITY,
    title TEXT NOT NULL UNIQUE,

    PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS class_professors (
    id INT8 NOT NULL,
    role_id INT2 NOT NULL DEFAULT 2,
    class_id INT8 NOT NULL,

    PRIMARY KEY (id, class_id),
    FOREIGN KEY (class_id) REFERENCES classes(id),
    FOREIGN KEY (id, role_id) REFERENCES users(id, role_id),
    CONSTRAINT class_professor_must_be_professor CHECK (role_id = 2)
);


CREATE TABLE IF NOT EXISTS class_assistants (
    id INT8 NOT NULL,
    role_id INT2 NOT NULL DEFAULT 1,
    class_id INT8 NOT NULL,

    PRIMARY KEY (id, class_id),
    FOREIGN KEY (class_id) REFERENCES classes(id),
    FOREIGN KEY (id, role_id) REFERENCES users(id, role_id),
    CONSTRAINT class_assistant_must_be_student CHECK (role_id = 1)
);


CREATE TABLE IF NOT EXISTS review_sessions (
    id INT8 GENERATED ALWAYS AS IDENTITY,
    class_id INT8 NOT NULL,
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    location TEXT NOT NULL DEFAULT 'online',
    max_participants INT2 NOT NULL DEFAULT 5,

    PRIMARY KEY (id),
    UNIQUE (id, class_id),
    FOREIGN KEY (class_id) REFERENCES classes(id),
    CONSTRAINT must_end_after_start CHECK (ends_at > starts_at),
    CONSTRAINT must_have_max_participants CHECK (max_participants > 0)
);


CREATE TABLE IF NOT EXISTS session_assistants (
    id INT8 NOT NULL,
    class_id INT8 NOT NULL,
    session_id INT8 NOT NULL,

    PRIMARY KEY (id, session_id),
    FOREIGN KEY (id, class_id) REFERENCES class_assistants(id, class_id),
    FOREIGN KEY (session_id, class_id) REFERENCES review_sessions(id, class_id)
);


CREATE TABLE IF NOT EXISTS session_applicants (
    id INT8 NOT NULL,
    role_id INT2 NOT NULL DEFAULT 1,
    session_id INT8 NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    PRIMARY KEY (id, session_id),
    FOREIGN KEY (session_id) REFERENCES review_sessions(id),
    FOREIGN KEY (id, role_id) REFERENCES users(id, role_id),
    CONSTRAINT session_applicant_must_be_student CHECK (role_id = 1)
);


CREATE TABLE IF NOT EXISTS session_participants (
    id INT8 NOT NULL,
    session_id INT8 NOT NULL,
    confirmed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    attended BOOL NOT NULL DEFAULT FALSE,

    PRIMARY KEY (id, session_id),
    FOREIGN KEY (id, session_id) REFERENCES session_applicants(id, session_id),
    FOREIGN KEY (session_id) REFERENCES review_sessions(id)
);


-- Views:


CREATE OR REPLACE VIEW session_applicants_status AS
WITH ranked AS (
    SELECT sa.id AS user_id
        ,sa.session_id
        ,sa.applied_at
        ,rs.max_participants
        ,row_number() OVER (
            PARTITION BY sa.session_id
            ORDER BY sa.applied_at, sa.id
        ) AS application_position
    FROM session_applicants AS sa
        JOIN review_sessions rs ON rs.id = sa.session_id
)
SELECT *
    ,application_position <= max_participants AS is_confirmed
    ,CASE
        WHEN application_position > max_participants
        THEN application_position - max_participants
        ELSE NULL
    END AS waitlist_position
FROM ranked;


CREATE OR REPLACE VIEW current_users AS
WITH professor_classes AS (
    SELECT cp.id AS user_id
        ,jsonb_agg(
            jsonb_build_object(
                'id', c.id,
                'title', c.title
            )
            ORDER BY c.title, c.id
        ) AS classes
    FROM class_professors AS cp
        JOIN classes AS c ON c.id = cp.class_id
    GROUP BY cp.id
), assistant_classes AS (
    SELECT ca.id AS user_id
        ,jsonb_agg(
            jsonb_build_object(
                'id', c.id,
                'title', c.title
            )
            ORDER BY c.title, c.id
        ) AS classes
    FROM class_assistants AS ca
        JOIN classes AS c ON c.id = ca.class_id
    GROUP BY ca.id
)
SELECT u.id
    ,u.mail
    ,u.name
    ,u.role_id
    ,CASE u.role_id
        WHEN 0 THEN 'admin'
        WHEN 1 THEN 'student'
        WHEN 2 THEN 'professor'
    END AS role
    ,CASE u.role_id
        WHEN 0 THEN jsonb_build_object('global', true)
        WHEN 1 THEN jsonb_build_object(
            'assistant_for',
            COALESCE(ac.classes, '[]'::jsonb)
        )
        WHEN 2 THEN jsonb_build_object(
            'classes',
            COALESCE(pc.classes, '[]'::jsonb)
        )
    END AS scope
FROM users AS u
    LEFT JOIN professor_classes AS pc ON pc.user_id = u.id
    LEFT JOIN assistant_classes AS ac ON ac.user_id = u.id;


-- Seeds:


INSERT INTO users(mail, name, hashed_password, role_id)
VALUES
    ('admin@admin.com', 'Administrador', '$argon2id$v=19$m=8,t=1,p=1$ouYiVdoURx4$Oc8DFg', 0)
ON CONFLICT DO NOTHING;
