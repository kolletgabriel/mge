-- Schema


CREATE TABLE IF NOT EXISTS roles (
    id INT8 GENERATED ALWAYS AS IDENTITY (START WITH 0 MINVALUE 0),
    description TEXT UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS users (
    id INT8 GENERATED ALWAYS AS IDENTITY (START WITH 0 MINVALUE 0),
    mail TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    hashed_password TEXT NOT NULL,
    role_id INT REFERENCES roles(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    PRIMARY KEY (id)
);


-- Seeds:


INSERT INTO roles(description)
VALUES
    ('admin'),
    ('student'),
    ('assistant'),
    ('prof'),
    ('coord')
ON CONFLICT DO NOTHING;

INSERT INTO users(mail, name, hashed_password, role_id)
VALUES
    ('admin@admin.com', 'Administrador', '$argon2id$v=19$m=8,t=1,p=1$ouYiVdoURx4$Oc8DFg', 0)
ON CONFLICT DO NOTHING;
