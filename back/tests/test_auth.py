from pytest import mark


def test_login_root_user_success(test_client):
    creds = {'mail': 'admin@admin.com', 'password': 'admin'}
    res = test_client.post('/login', json=creds)

    assert res.status_code == 204
    assert res.cookies.get('session')


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
async def test_auth_success(authed_test_client):
    res2 = authed_test_client.get('/')

    assert res2.status_code == 200


def test_auth_failure_no_cookie(test_client):
    res = test_client.get('/')

    assert res.status_code == 401


@mark.anyio
async def test_auth_failure_bad_cookie(authed_test_client):
    authed_test_client.cookies['session'] = 'bad_session'
    res = authed_test_client.get('/')

    assert res.status_code == 401


@mark.anyio
async def test_logout_deletes_session_cookie(authed_test_client):
    res = authed_test_client.post('/logout')

    assert res.status_code == 204
    assert 'session=' in res.headers['set-cookie']
    assert 'expires=Thu, 01 Jan 1970 00:00:00 GMT' in res.headers['set-cookie']


@mark.anyio
async def test_logout_prevents_access(authed_test_client):
    res = authed_test_client.post('/logout')
    res2 = authed_test_client.get('/')

    assert res.status_code == 204
    assert res2.status_code == 401


def test_logout_status_code_no_session(test_client):
    res = test_client.post('/logout')

    assert res.status_code == 204


@mark.anyio
async def test_logout_status_code_with_session(authed_test_client):
    res = authed_test_client.post('/logout')

    assert res.status_code == 204
