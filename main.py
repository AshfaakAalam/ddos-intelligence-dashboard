from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from cloudflare import get_attack_data
from processor import process_attack_data


from fastapi import Form
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from database import SessionLocal, User
from werkzeug.security import generate_password_hash, check_password_hash

from datetime import datetime, timezone

app = FastAPI()
app.add_middleware(
    SessionMiddleware,
    secret_key="change-this-secret-key"
)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(
    request=request,
    name="index.html"
)


@app.get("/register")
def register_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="register.html"
    )


@app.post("/register")
def register(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...)
):

    database = SessionLocal()

    existing_user = database.query(User).filter(
        User.username == username
    ).first()

    if existing_user:

        database.close()

        return {
            "message": "Username already exists"
        }

    password_hash = generate_password_hash(password)

    user = User(
        username=username,
        email=email,
        password_hash=password_hash
    )

    database.add(user)
    database.commit()

    database.close()

    return RedirectResponse(
        "/login",
        status_code=303
    )

@app.get("/login")
def login_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="login.html"
    )


@app.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):

    database = SessionLocal()

    user = database.query(User).filter(
        User.username == username
    ).first()

    if user is None:

        database.close()

        return {
            "message": "Invalid username or password"
        }

    password_correct = check_password_hash(
        user.password_hash,
        password
    )

    if not password_correct:

        database.close()

        return {
            "message": "Invalid username or password"
        }

    request.session["user_id"] = user.id
    request.session["username"] = user.username

    database.close()

    return RedirectResponse(
        "/dashboard",
        status_code=303
    )

@app.get("/dashboard")
def dashboard(request: Request):

    if "user_id" not in request.session:

        return RedirectResponse(
            "/login",
            status_code=303
        )

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html"
    )

@app.get("/logout")
def logout(request: Request):

    request.session.clear()

    return RedirectResponse(
        "/",
        status_code=303
    )


@app.get("/api/attacks")
def attacks():

    data = get_attack_data()

    processed_data = process_attack_data(data)

    source_countries = set()
    target_countries = set()

    for attack in processed_data:
        source_countries.add(attack["source_country"])
        target_countries.add(attack["target_country"])

    return {
        "attacks": processed_data,
        "source_country_count": len(source_countries),
        "target_country_count": len(target_countries),
        "last_updated": datetime.now(timezone.utc).isoformat()
    }