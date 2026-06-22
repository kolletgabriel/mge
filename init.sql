CREATE TABLE IF NOT EXISTS roles (
    id INT2 NOT NULL,
    title TEXT NOT NULL UNIQUE,

    PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS users (
    id INT8 GENERATED ALWAYS AS IDENTITY,
    mail TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    hashed_password TEXT NOT NULL,
    role_id INT2 NOT NULL,

    PRIMARY KEY (id),
    FOREIGN KEY (role_id) REFERENCES roles(id),
    UNIQUE (id, role_id)
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
    role_id INT2 GENERATED ALWAYS AS (2) STORED,
    class_id INT8 NOT NULL,

    PRIMARY KEY (id, class_id),
    FOREIGN KEY (class_id) REFERENCES classes(id),
    FOREIGN KEY (id, role_id) REFERENCES users(id, role_id)
);


CREATE TABLE IF NOT EXISTS class_assistants (
    id INT8 NOT NULL,
    role_id INT2 GENERATED ALWAYS AS (1) STORED,
    class_id INT8 NOT NULL,

    PRIMARY KEY (id, class_id),
    FOREIGN KEY (class_id) REFERENCES classes(id),
    FOREIGN KEY (id, role_id) REFERENCES users(id, role_id)
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
    role_id INT2 GENERATED ALWAYS AS (1) STORED,
    session_id INT8 NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    PRIMARY KEY (id, session_id),
    FOREIGN KEY (session_id) REFERENCES review_sessions(id),
    FOREIGN KEY (id, role_id) REFERENCES users(id, role_id)
);


CREATE TABLE IF NOT EXISTS session_participants (
    id INT8 NOT NULL,
    session_id INT8 NOT NULL,
    confirmed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    attended BOOL NOT NULL DEFAULT FALSE,

    PRIMARY KEY (id, session_id),
    FOREIGN KEY (id, session_id) REFERENCES session_applicants(id, session_id)
);


-- Views:


CREATE OR REPLACE VIEW class_user_refs AS
WITH cte AS (
    SELECT class_id
        ,id AS user_id
        ,role_id
    FROM class_professors
    UNION ALL
    SELECT class_id
        ,id AS user_id
        ,role_id
    FROM class_assistants
)
SELECT cte.class_id
    ,c.title AS class_title
    ,cte.user_id
    ,u.mail
    ,u.name
    ,cte.role_id
    ,r.title AS role_title
FROM cte
    JOIN classes AS c ON c.id = cte.class_id
    JOIN users AS u ON u.id = cte.user_id
    JOIN roles AS r ON r.id = cte.role_id;


CREATE OR REPLACE VIEW session_applicants_status AS
WITH ranked AS (
    SELECT sa.id
        ,sa.session_id
        ,rs.max_participants
        ,row_number() OVER (
            PARTITION BY sa.session_id
            ORDER BY sa.applied_at, sa.id
        ) AS application_position
    FROM session_applicants AS sa
        JOIN review_sessions AS rs ON rs.id = sa.session_id
)
SELECT id
    ,session_id
    ,(application_position <= max_participants) AS confirmed
    ,CASE
        WHEN application_position > max_participants
        THEN application_position - max_participants
    END AS waitlist_position
FROM ranked;


CREATE OR REPLACE VIEW current_users AS
WITH professor_classes AS (
    SELECT cp.id
        ,jsonb_agg(
            jsonb_build_object('id', c.id, 'title', c.title)
            ORDER BY c.title, c.id
        ) AS classes
    FROM class_professors AS cp
        JOIN classes AS c ON c.id = cp.class_id
    GROUP BY cp.id
), assistant_classes AS (
    SELECT ca.id
        ,jsonb_agg(
            jsonb_build_object('id', c.id, 'title', c.title)
            ORDER BY c.title, c.id
        ) AS classes
    FROM class_assistants AS ca
        JOIN classes AS c ON c.id = ca.class_id
    GROUP BY ca.id
)
SELECT u.id
    ,u.name
    ,u.mail
    ,u.role_id
    ,r.title AS role_title
    ,CASE u.role_id
        WHEN 0 THEN jsonb_build_object('global', TRUE)
        WHEN 1 THEN jsonb_build_object(
            'assists', COALESCE(ac.classes, '[]'::JSONB)
        )
        WHEN 2 THEN jsonb_build_object(
            'teaches', COALESCE(pc.classes, '[]'::JSONB)
        )
    END AS scope
FROM users AS u
    LEFT JOIN roles AS r ON r.id = u.role_id
    LEFT JOIN professor_classes AS pc ON pc.id = u.id
    LEFT JOIN assistant_classes AS ac ON ac.id = u.id;


-- Seeds:


INSERT INTO roles
VALUES
    (0, 'Administrador'),
    (1, 'Aluno'),
    (2, 'Professor')
ON CONFLICT DO NOTHING;
