from sqlmodel import select

from app.models import empresa_usuario


def _login(client, username, password="secreto-123"):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def test_login_200_emite_token(contexto, client):
    ctx = contexto()
    r = _login(client, ctx["usuario"].username)
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"]
    assert body["usuario"]["rol"] in {"admin", "contable"}


def test_login_credenciales_invalidas_401(contexto, client):
    ctx = contexto()
    assert _login(client, ctx["usuario"].username, password="incorrecta").status_code == 401
    assert _login(client, "no-existe", "secreto-123").status_code == 401


def test_login_usuario_inactivo_401(client, make_usuario):
    make_usuario("desact", activo=False)
    assert _login(client, "desact").status_code == 401


def test_auth_me_devuelve_empresas(contexto, client):
    ctx = contexto()
    r = client.get("/api/v1/auth/me", headers=ctx["headers"])
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == ctx["usuario"].username
    assert ctx["empresa"].id in body["empresas"]


def test_crear_empresa_201_asocia_admin(client, make_usuario, session):
    admin = make_usuario("admin_boss", rol="admin")
    from app.services.seguridad import create_access_token

    headers = {"Authorization": f"Bearer {create_access_token(admin.username)}"}
    r = client.post(
        "/api/v1/empresas",
        headers=headers,
        json={"cif": "B99999999", "razon_social": "Beta SL", "nombre_comercial": "Beta"},
    )
    assert r.status_code == 201
    vinculo = session.execute(
        select(empresa_usuario.c.rol_especifico).where(
            empresa_usuario.c.empresa_id == r.json()["id"]
        )
    ).all()
    assert len(vinculo) == 1
    assert vinculo[0]._mapping["rol_especifico"] == "admin"


def test_crear_empresa_rol_contable_403(contexto, client, make_usuario):
    ctx = contexto()
    contable = make_usuario("solo_contable", rol="contable")
    token = ctx["headers"].copy()
    from app.services.seguridad import create_access_token

    token["Authorization"] = f"Bearer {create_access_token(contable.username)}"
    r = client.post(
        "/api/v1/empresas",
        headers=token,
        json={"cif": "B88888888", "razon_social": "Gamma SL"},
    )
    assert r.status_code == 403


def test_get_empresas_solo_las_propias(contexto, client, make_usuario, make_empresa):
    ctx = contexto()
    otro = make_usuario("otro_user")
    make_empresa(otro, cif="C11111111", razon_social="Ajena SL")
    r = client.get("/api/v1/empresas", headers=ctx["headers"])
    assert r.status_code == 200
    ids = [e["id"] for e in r.json()]
    assert ctx["empresa"].id in ids
    assert len(ids) == 1


def test_contexto_ajeno_403(contexto, client, make_usuario, make_empresa):
    ctx = contexto()
    otro = make_usuario("ajeno")
    otra = make_empresa(otro, cif="D22222222", razon_social="Ajena2 SL")
    r = client.get("/api/v1/ejercicios", headers={**ctx["headers"], "X-Empresa-Id": str(otra.id)})
    assert r.status_code == 403


def test_crear_ejercicio_201_abierto(contexto, client):
    ctx = contexto(rol="admin")
    h = {**ctx["headers"], "X-Empresa-Id": str(ctx["empresa"].id)}
    r = client.post(
        "/api/v1/ejercicios",
        headers=h,
        json={"anio": 2027, "fecha_inicio": "2027-01-01", "fecha_fin": "2027-12-31"},
    )
    assert r.status_code == 201
    assert r.json()["estado"] == "abierto"


def test_crear_ejercicio_anio_duplicado_409(contexto, client):
    ctx = contexto(rol="admin")
    h = {**ctx["headers"], "X-Empresa-Id": str(ctx["empresa"].id)}
    r = client.post(
        "/api/v1/ejercicios",
        headers=h,
        json={"anio": 2026, "fecha_inicio": "2026-01-01", "fecha_fin": "2026-12-31"},
    )
    assert r.status_code == 409


def test_listar_ejercicios_del_contexto(contexto, client):
    ctx = contexto()
    h = {**ctx["headers"], "X-Empresa-Id": str(ctx["empresa"].id)}
    r = client.get("/api/v1/ejercicios", headers=h)
    assert r.status_code == 200
    assert any(e["id"] == ctx["ejercicio"].id for e in r.json())


def test_crear_ejercicio_siembra_pgc_base(contexto, client, session):
    from app.models import Cuenta
    from app.pgc import PGC_BASE

    ctx = contexto(rol="admin")
    h = {**ctx["headers"], "X-Empresa-Id": str(ctx["empresa"].id)}
    r = client.post(
        "/api/v1/ejercicios",
        headers=h,
        json={"anio": 2029, "fecha_inicio": "2029-01-01", "fecha_fin": "2029-12-31"},
    )
    assert r.status_code == 201
    ej_id = r.json()["id"]
    cuentas = session.exec(select(Cuenta).where(Cuenta.ejercicio_id == ej_id)).all()
    assert len(cuentas) == len(PGC_BASE)
    by_codigo = {c.codigo: c for c in cuentas}
    assert by_codigo["1"].nivel == 1
    assert by_codigo["43"].nivel == 2
    assert by_codigo["430"].nivel == 3
