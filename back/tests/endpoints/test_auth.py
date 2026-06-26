from uuid import uuid4

from pytest import mark


def test_register_user_success(test_client):
    mail = f'{uuid4()}@example.com'
    registration = {
        'mail': f' {mail} ',
        'name': ' New Student ',
        'password': 'password123',
    }
    res = test_client.post('/register', json=registration)

    assert res.status_code == 201
    assert res.cookies.get('session')
    assert res.json() == {
        'id': res.json()['id'],
        'mail': mail,
        'name': 'New Student',
        'role_id': 1,
        'role_title': 'Aluno',
        'scope': {'assists': []},
    }

    test_client.cookies.clear()


def test_register_user_failure_duplicate_mail(test_client):
    test_client.cookies.clear()
    registration = {
        'mail': f'{uuid4()}@example.com',
        'name': 'New Student',
        'password': 'password123',
    }

    res = test_client.post('/register', json=registration)
    test_client.cookies.clear()
    res2 = test_client.post('/register', json=registration)

    assert res.status_code == 201
    assert res2.status_code == 409
    assert not test_client.cookies.get('session')


def test_register_user_failure_invalid_mail(test_client):
    test_client.cookies.clear()
    registration = {
        'mail': 'not-an-email',
        'name': 'New Student',
        'password': 'password123',
    }
    res = test_client.post('/register', json=registration)

    assert res.status_code == 422
    assert not test_client.cookies.get('session')


def test_register_user_failure_short_password(test_client):
    test_client.cookies.clear()
    registration = {
        'mail': f'{uuid4()}@example.com',
        'name': 'New Student',
        'password': 'short',
    }
    res = test_client.post('/register', json=registration)

    assert res.status_code == 422
    assert not test_client.cookies.get('session')


def test_login_root_user_success(test_client):
    creds = {'mail': 'admin@admin.com', 'password': 'admin123'}
    res = test_client.post('/login', json=creds)

    assert res.status_code == 200
    assert res.cookies.get('session')
    assert res.json()['role_id'] == 0
    assert res.json()['scope'] == {'global': True}


def test_login_root_user_failure_wrong_pw(test_client):
    creds = {'mail': 'admin@admin.com', 'password': 'admi'}
    res = test_client.post('/login', json=creds)

    assert res.status_code == 401
    assert not res.cookies.get('session')


def test_login_failure_nonexistent_user(test_client):
    creds = {'mail': 'hgkjdfhgdskjh@asdg.com', 'password': 'admi'}
    res = test_client.post('/login', json=creds)

    assert res.status_code == 401
    assert not res.cookies.get('session')


@mark.anyio
async def test_auth_failure_absent_cookie(test_client):
    res = test_client.get('/me')

    assert res.status_code == 401


def test_auth_failure_unsigned_cookie(test_client):
    test_client.cookies['session'] = 'bad_session'
    res = test_client.get('/me')

    assert res.status_code == 401


@mark.anyio
async def test_auth_failure_signed_malformed_cookie(
    test_client,
    signed_malformed_session_token,
):
    test_client.cookies['session'] = signed_malformed_session_token
    res = test_client.get('/me')

    assert res.status_code == 401


def test_auth_failure_valid_cookie_without_session_row(
    test_client,
    signed_session_token,
):
    test_client.cookies['session'] = signed_session_token
    res = test_client.get('/me')

    assert res.status_code == 401


@mark.anyio
@mark.usefixtures('revoked_auth_session')
async def test_auth_failure_revoked_session_row(
    test_client,
    signed_session_token,
):
    test_client.cookies['session'] = signed_session_token
    res = test_client.get('/me')

    assert res.status_code == 401


@mark.anyio
async def test_auth_success_valid_cookie_and_session_row(authed_test_client):
    res = authed_test_client.get('/me')

    assert res.status_code == 200


@mark.anyio
async def test_logout_deletes_session_cookie(authed_test_client):
    res = authed_test_client.post('/logout')

    assert res.status_code == 204
    assert 'session=' in res.headers['set-cookie']
    assert 'expires=Thu, 01 Jan 1970 00:00:00 GMT' in res.headers['set-cookie']


@mark.anyio
async def test_logout_prevents_access(authed_test_client):
    res = authed_test_client.post('/logout')
    res2 = authed_test_client.get('/me')

    assert res.status_code == 204
    assert res2.status_code == 401


def test_logout_status_code_no_session(test_client):
    res = test_client.post('/logout')

    assert res.status_code == 204


@mark.anyio
async def test_logout_status_code_with_session(authed_test_client):
    res = authed_test_client.post('/logout')

    assert res.status_code == 204
