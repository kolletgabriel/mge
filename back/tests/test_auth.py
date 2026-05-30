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


def test_auth_success(test_client):
    creds = {'mail': 'admin@admin.com', 'password': 'admin'}
    res = test_client.post('/login', json=creds)
    session_cookie = res.cookies['session']

    test_client.cookies = {'session': session_cookie}
    res2 = test_client.get('/')

    assert res2.status_code == 200
    assert {'id', 'name', 'role'} == set(res2.json().keys())

    test_client.cookies.clear()


def test_auth_failure_no_cookie(test_client):
    res = test_client.get('/')

    assert res.status_code == 401


def test_auth_failure_bad_cookie(test_client):
    test_client.cookies = {'session': 'bad_session'}
    res = test_client.get('/')

    assert res.status_code == 401

    test_client.cookies.clear()
