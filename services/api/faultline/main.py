import jwt
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from . import schemas as s
from .config import Settings, get_settings
from .db import database
from .models import (
    AuditEvent,
    Environment,
    Membership,
    Project,
    ProjectGrant,
    RefreshToken,
    SessionFamily,
    User,
    Workspace,
    now,
)
from .security import DUMMY_HASH, audit, digest, issue, new_session, passwords, throttle

bearer = HTTPBearer(auto_error=False)
ROLE_RANK = {'viewer': 1, 'investigator': 2, 'maintainer': 3}


def create_app(settings: Settings | None = None):
    settings = settings or get_settings()
    engine, session_factory = database(settings.database_url)
    app = FastAPI(title='Faultline API', version='0.1.0')
    app.state.engine = engine
    app.state.sessions = session_factory
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=['GET', 'POST', 'PUT', 'DELETE'],
        allow_headers=['Authorization', 'Content-Type'],
    )

    @app.middleware('http')
    async def secure_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Cache-Control'] = 'no-store'
        return response

    def db_session():
        with session_factory() as db:
            yield db

    def current_user(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db=Depends(db_session)
    ):
        unauthorized = HTTPException(
            401, 'Your session has expired. Please sign in.', headers={'WWW-Authenticate': 'Bearer'}
        )
        if not credentials:
            raise unauthorized
        try:
            claims = jwt.decode(
                credentials.credentials,
                settings.jwt_secret,
                algorithms=['HS256'],
                audience=settings.jwt_audience,
                issuer=settings.jwt_issuer,
                options={'require': ['sub', 'sid', 'exp', 'iat', 'jti', 'type']},
            )
            if claims['type'] != 'access':
                raise unauthorized
            family = db.get(SessionFamily, claims['sid'])
            if not family or family.revoked or family.expires_at <= now() or family.user_id != claims['sub']:
                raise unauthorized
            user = db.get(User, claims['sub'])
            if not user:
                raise unauthorized
            return user
        except jwt.InvalidTokenError:
            raise unauthorized from None

    def member(db, user, workspace_id, manage=False):
        membership = db.get(Membership, (workspace_id, user.id))
        if not membership:
            raise HTTPException(404, 'Workspace not found.')
        if manage and membership.role not in ('owner', 'admin'):
            raise HTTPException(403, 'Workspace administrator access is required.')
        return membership

    def project_access(db, user, project_id, minimum='viewer'):
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(404, 'Project not found.')
        membership = member(db, user, project.workspace_id)
        grant = db.get(ProjectGrant, (project_id, user.id))
        role = 'maintainer' if membership.role in ('owner', 'admin') else grant.role if grant else None
        if not role:
            raise HTTPException(404, 'Project not found.')
        if ROLE_RANK[role] < ROLE_RANK[minimum]:
            raise HTTPException(403, 'Project maintainer access is required.')
        return project, role

    def commit(db, detail='This record already exists.'):
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, detail) from None

    def limit(request, db, category, email=None):
        throttle(db, settings, category + '-ip', request.client.host if request.client else 'unknown')
        if email:
            throttle(db, settings, category + '-account', email)

    @app.get('/health/live', tags=['Health'])
    def live() -> dict[str, str]:
        return {'status': 'ok'}

    @app.get('/health/ready', tags=['Health'])
    def ready(db=Depends(db_session)) -> dict[str, str]:
        try:
            db.execute(text('SELECT 1'))
            # Readiness also checks that migrations ran; the API never creates tables itself.
            db.execute(text('SELECT version_num FROM alembic_version'))
        except SQLAlchemyError:
            raise HTTPException(503, 'Database is unavailable or migrations are missing.') from None
        queue = 'not_configured'
        if settings.redis_url:
            from redis import Redis, RedisError

            try:
                with Redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1) as redis:
                    redis.ping()
                queue = 'ready'
            except RedisError:
                raise HTTPException(503, 'Redis is unavailable.') from None
        return {'status': 'ready', 'database': engine.dialect.name, 'queue': queue}

    @app.post('/auth/register', response_model=s.Tokens, status_code=201, tags=['Identity'])
    def register(body: s.Registration, request: Request, db=Depends(db_session)):
        email = str(body.email).lower()
        limit(request, db, 'register', email)
        if db.scalar(select(User).where(User.email == email)):
            raise HTTPException(409, 'An account with this email already exists.')
        user = User(email=email, name=body.name, password_hash=passwords.hash(body.password))
        db.add(user)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, 'An account with this email already exists.') from None
        tokens = new_session(db, user, settings)
        audit(db, user.id, 'identity.register', user.id)
        commit(db)
        return tokens

    @app.post('/auth/login', response_model=s.Tokens, tags=['Identity'])
    def login(body: s.Login, request: Request, db=Depends(db_session)):
        email = str(body.email).lower()
        limit(request, db, 'login', email)
        user = db.scalar(select(User).where(User.email == email))
        valid = passwords.verify(body.password, user.password_hash if user else DUMMY_HASH)
        if not user or not valid:
            raise HTTPException(401, 'Email or password is incorrect.')
        tokens = new_session(db, user, settings)
        audit(db, user.id, 'identity.login', user.id)
        commit(db)
        return tokens

    @app.post('/auth/refresh', response_model=s.Tokens, tags=['Identity'])
    def refresh(body: s.Refresh, request: Request, db=Depends(db_session)):
        limit(request, db, 'refresh')
        token = db.get(RefreshToken, digest(body.refresh_token))
        if not token:
            raise HTTPException(401, 'Invalid refresh token.')
        # Lock the family before re-reading the token; concurrent rotations cannot both succeed.
        family = db.scalar(select(SessionFamily).where(SessionFamily.id == token.family_id).with_for_update())
        db.refresh(token)
        if family.revoked or family.expires_at <= now():
            raise HTTPException(401, 'Session expired or revoked.')
        if token.consumed:
            family.revoked = True
            audit(db, family.user_id, 'identity.refresh_reuse', family.id)
            db.commit()
            raise HTTPException(401, 'Refresh reuse detected. Sign in again.')
        token.consumed = True
        tokens = issue(db, db.get(User, family.user_id), family, settings)
        commit(db)
        return tokens

    @app.post('/auth/logout', status_code=204, tags=['Identity'])
    def logout(body: s.Refresh, request: Request, db=Depends(db_session)):
        limit(request, db, 'logout')
        token = db.get(RefreshToken, digest(body.refresh_token))
        if token:
            family = db.get(SessionFamily, token.family_id)
            family.revoked = True
            audit(db, family.user_id, 'identity.logout', family.id)
            commit(db)
        return Response(status_code=204)

    @app.get('/auth/me', response_model=s.UserOut, tags=['Identity'])
    def me(user=Depends(current_user)):
        return user

    @app.get('/workspaces', response_model=list[s.WorkspaceOut], tags=['Workspaces'])
    def workspaces(user=Depends(current_user), db=Depends(db_session)):
        rows = db.execute(
            select(Workspace, Membership.role)
            .join(Membership)
            .where(Membership.user_id == user.id)
            .order_by(Workspace.created_at, Workspace.id)
        )
        return [s.WorkspaceOut(id=w.id, name=w.name, role=role) for w, role in rows]

    @app.post('/workspaces', response_model=s.WorkspaceOut, status_code=201, tags=['Workspaces'])
    def create_workspace(body: s.Named, user=Depends(current_user), db=Depends(db_session)):
        workspace = Workspace(name=body.name)
        db.add(workspace)
        db.flush()
        db.add(Membership(workspace_id=workspace.id, user_id=user.id, role='owner'))
        audit(db, user.id, 'workspace.create', workspace.id, workspace.id)
        commit(db)
        return s.WorkspaceOut(id=workspace.id, name=workspace.name, role='owner')

    @app.get('/workspaces/{workspace_id}/members', response_model=list[s.MemberOut], tags=['Workspaces'])
    def members(workspace_id: str, user=Depends(current_user), db=Depends(db_session)):
        member(db, user, workspace_id, manage=True)
        rows = db.execute(
            select(User, Membership.role).join(Membership).where(Membership.workspace_id == workspace_id)
        )
        return [s.MemberOut(user_id=u.id, name=u.name, email=u.email, role=role) for u, role in rows]

    @app.post(
        '/workspaces/{workspace_id}/members', response_model=s.MemberOut, status_code=201, tags=['Workspaces']
    )
    def add_member(
        workspace_id: str, body: s.MemberInput, user=Depends(current_user), db=Depends(db_session)
    ):
        actor = member(db, user, workspace_id, manage=True)
        if body.role == 'admin' and actor.role != 'owner':
            raise HTTPException(403, 'Only the owner can appoint administrators.')
        target = db.scalar(select(User).where(User.email == str(body.email).lower()))
        if not target:
            raise HTTPException(404, 'Ask this person to create an account first.')
        db.add(Membership(workspace_id=workspace_id, user_id=target.id, role=body.role))
        audit(db, user.id, 'membership.add', target.id, workspace_id)
        commit(db, 'This user is already a workspace member.')
        return s.MemberOut(user_id=target.id, name=target.name, email=target.email, role=body.role)

    @app.delete('/workspaces/{workspace_id}/members/{user_id}', status_code=204, tags=['Workspaces'])
    def remove_member(workspace_id: str, user_id: str, user=Depends(current_user), db=Depends(db_session)):
        actor = member(db, user, workspace_id, manage=True)
        target = db.get(Membership, (workspace_id, user_id))
        if not target:
            raise HTTPException(404, 'Member not found.')
        if target.role == 'owner' or (target.role == 'admin' and actor.role != 'owner'):
            raise HTTPException(403, 'This membership cannot be removed by your role.')
        # Remove grants as well; rejoining must not restore old privileges.
        grants = db.scalars(
            select(ProjectGrant)
            .join(Project)
            .where(Project.workspace_id == workspace_id, ProjectGrant.user_id == user_id)
        ).all()
        for grant in grants:
            db.delete(grant)
        db.delete(target)
        audit(db, user.id, 'membership.remove', user_id, workspace_id)
        commit(db)
        return Response(status_code=204)

    @app.get('/workspaces/{workspace_id}/projects', response_model=list[s.ProjectOut], tags=['Projects'])
    def projects(workspace_id: str, user=Depends(current_user), db=Depends(db_session)):
        membership = member(db, user, workspace_id)
        rows = db.scalars(
            select(Project)
            .where(Project.workspace_id == workspace_id)
            .order_by(Project.created_at, Project.id)
        ).all()
        result = []
        for project in rows:
            grant = db.get(ProjectGrant, (project.id, user.id))
            role = 'maintainer' if membership.role in ('owner', 'admin') else grant.role if grant else None
            if role:
                result.append(
                    s.ProjectOut(id=project.id, workspace_id=workspace_id, name=project.name, role=role)
                )
        return result

    @app.post(
        '/workspaces/{workspace_id}/projects', response_model=s.ProjectOut, status_code=201, tags=['Projects']
    )
    def create_project(workspace_id: str, body: s.Named, user=Depends(current_user), db=Depends(db_session)):
        member(db, user, workspace_id, manage=True)
        project = Project(workspace_id=workspace_id, name=body.name)
        db.add(project)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, 'A project with this name already exists in this workspace.') from None
        db.add(Environment(project_id=project.id, name='production'))
        audit(db, user.id, 'project.create', project.id, workspace_id)
        commit(db)
        return s.ProjectOut(id=project.id, workspace_id=workspace_id, name=project.name, role='maintainer')

    @app.get('/projects/{project_id}', response_model=s.ProjectOut, tags=['Projects'])
    def get_project(project_id: str, user=Depends(current_user), db=Depends(db_session)):
        project, role = project_access(db, user, project_id)
        return s.ProjectOut(id=project.id, workspace_id=project.workspace_id, name=project.name, role=role)

    @app.put('/projects/{project_id}/grants/{user_id}', response_model=s.GrantInput, tags=['Projects'])
    def set_grant(
        project_id: str, user_id: str, body: s.GrantInput, user=Depends(current_user), db=Depends(db_session)
    ):
        project, _ = project_access(db, user, project_id, 'maintainer')
        member(db, user, project.workspace_id, manage=True)
        target = db.get(Membership, (project.workspace_id, user_id))
        if not target:
            raise HTTPException(404, 'Workspace member not found.')
        if target.role in ('owner', 'admin'):
            raise HTTPException(409, 'Workspace administrators already have maintainer access.')
        grant = db.get(ProjectGrant, (project_id, user_id))
        if grant:
            grant.role = body.role
        else:
            db.add(ProjectGrant(project_id=project_id, user_id=user_id, role=body.role))
        audit(db, user.id, f'project.grant.{body.role}', user_id, project.workspace_id)
        commit(db)
        return body

    @app.delete('/projects/{project_id}/grants/{user_id}', status_code=204, tags=['Projects'])
    def revoke_grant(project_id: str, user_id: str, user=Depends(current_user), db=Depends(db_session)):
        project, _ = project_access(db, user, project_id, 'maintainer')
        member(db, user, project.workspace_id, manage=True)
        grant = db.get(ProjectGrant, (project_id, user_id))
        if grant:
            db.delete(grant)
            audit(db, user.id, 'project.grant.revoke', user_id, project.workspace_id)
            commit(db)
        return Response(status_code=204)

    @app.get('/projects/{project_id}/environments', response_model=list[s.EnvironmentOut], tags=['Projects'])
    def environments(project_id: str, user=Depends(current_user), db=Depends(db_session)):
        project_access(db, user, project_id)
        return db.scalars(
            select(Environment).where(Environment.project_id == project_id).order_by(Environment.name)
        ).all()

    @app.post(
        '/projects/{project_id}/environments',
        response_model=s.EnvironmentOut,
        status_code=201,
        tags=['Projects'],
    )
    def create_environment(
        project_id: str, body: s.Named, user=Depends(current_user), db=Depends(db_session)
    ):
        project, _ = project_access(db, user, project_id, 'maintainer')
        environment = Environment(project_id=project_id, name=body.name)
        db.add(environment)
        audit(db, user.id, 'environment.create', project_id, project.workspace_id)
        commit(db, 'An environment with this name already exists.')
        return environment

    @app.get('/workspaces/{workspace_id}/audit', response_model=list[s.AuditOut], tags=['Workspaces'])
    def audit_log(workspace_id: str, user=Depends(current_user), db=Depends(db_session)):
        member(db, user, workspace_id, manage=True)
        return db.scalars(
            select(AuditEvent)
            .where(AuditEvent.workspace_id == workspace_id)
            .order_by(AuditEvent.created_at.desc(), AuditEvent.id)
            .limit(100)
        ).all()

    return app
