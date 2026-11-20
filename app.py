from datetime import datetime
from functools import wraps
from io import BytesIO
import os
from pathlib import Path
import secrets

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.utils import safe_join


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
TEAM_UPLOAD_DIR = UPLOAD_DIR / "equipo"
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_UPLOAD_BYTES = 3 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES + 1024 * 1024

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
TEAM_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Todo reclamo vive unicamente en memoria y se pierde al reiniciar Flask.
reclamos = []

presentacion_equipo = {
    "titulo": "¿Quiénes somos?",
    "texto": (
        "Somos vecinos y estudiantes comprometidos con Las Heras que creen que "
        "una plaza cuidada fortalece la convivencia. Queremos escuchar a la "
        "comunidad y hacer visibles los problemas de nuestros espacios públicos."
    ),
    "objetivo": (
        "Nuestro objetivo es facilitar reclamos claros sobre seguridad, limpieza "
        "e infraestructura, para que cada barrio pueda participar y construir "
        "soluciones junto al municipio."
    ),
    "participacion": (
        "Cada reporte suma. Participá, contanos qué necesita tu plaza y ayudanos "
        "a cuidar el espacio común de todos."
    ),
    "fotografia": None,
}


def csrf_token():
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_hex(32)
        session["csrf_token"] = token
    return token


app.jinja_env.globals["csrf_token"] = csrf_token


def csrf_protected(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if request.method == "POST":
            supplied = request.form.get("csrf_token", "")
            if not supplied or supplied != session.get("csrf_token"):
                abort(400)
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        username = os.environ.get("ADMIN_USERNAME")
        password = os.environ.get("ADMIN_PASSWORD")
        if not username or not password:
            abort(503)

        auth = request.authorization
        if (
            not auth
            or not secrets.compare_digest(auth.username.encode(), username.encode())
            or not secrets.compare_digest(auth.password.encode(), password.encode())
        ):
            response = app.response_class("Acceso restringido", 401)
            response.headers["WWW-Authenticate"] = 'Basic realm="Administracion"'
            return response
        return view(*args, **kwargs)

    return wrapped


def extension_permitida(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def guardar_imagen(file_storage, carpeta):
    if not file_storage or not file_storage.filename:
        return None
    if not extension_permitida(file_storage.filename):
        raise ValueError("Formato no permitido. Usá JPG, PNG o WebP.")

    file_storage.stream.seek(0, os.SEEK_END)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size == 0:
        raise ValueError("La fotografía está vacía.")
    if size > MAX_UPLOAD_BYTES:
        raise ValueError("La fotografía supera el límite de 3 MB.")

    extension_formato = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
    extensiones_formato = {"JPEG": {"jpg", "jpeg"}, "PNG": {"png"}, "WEBP": {"webp"}}
    try:
        image = Image.open(file_storage.stream)
        formato = image.format
        if formato not in extension_formato:
            raise ValueError("El archivo debe ser una imagen JPG, PNG o WebP válida.")
        if image.width * image.height > MAX_IMAGE_PIXELS:
            raise ValueError("La imagen tiene demasiados píxeles.")
        if file_storage.filename.rsplit(".", 1)[1].lower() not in extensiones_formato[formato]:
            raise ValueError("La extensión del archivo no coincide con su formato.")
        image.verify()

        file_storage.stream.seek(0)
        image = ImageOps.exif_transpose(Image.open(file_storage.stream))
        if formato == "JPEG" and image.mode not in {"RGB", "L"}:
            image = image.convert("RGB")
        elif formato == "WEBP" and image.mode not in {"RGB", "RGBA"}:
            image = image.convert("RGBA" if "A" in image.getbands() else "RGB")

        output = BytesIO()
        if formato == "WEBP":
            image.save(output, format=formato, quality=90, method=6)
        else:
            image.save(output, format=formato, optimize=True)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("El archivo debe ser una imagen JPG, PNG o WebP válida.") from exc

    image_bytes = output.getvalue()
    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise ValueError("La imagen procesada supera el límite de 3 MB.")

    filename = f"{secrets.token_hex(16)}.{extension_formato[formato]}"
    ruta = carpeta / filename
    ruta.write_bytes(image_bytes)
    return filename


@app.context_processor
def navigation_context():
    return {"active_page": request.endpoint}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/reclamos", methods=["GET", "POST"])
@csrf_protected
def reclamos_view():
    errors = {}
    values = {}
    categorias = [
        "Seguridad",
        "Iluminación",
        "Limpieza",
        "Juegos infantiles",
        "Bancos y mobiliario",
        "Infraestructura",
        "Otros",
    ]

    if request.method == "POST":
        values = {
            "nombre": request.form.get("nombre", "").strip(),
            "plaza": request.form.get("plaza", "").strip(),
            "ubicacion": request.form.get("ubicacion", "").strip(),
            "categoria": request.form.get("categoria", "").strip(),
            "descripcion": request.form.get("descripcion", "").strip(),
        }

        if not values["plaza"]:
            errors["plaza"] = "Indicá el nombre de la plaza."
        elif len(values["plaza"]) > 120:
            errors["plaza"] = "El nombre de la plaza no puede superar los 120 caracteres."
        if not values["ubicacion"]:
            errors["ubicacion"] = "Indicá la dirección o ubicación."
        elif len(values["ubicacion"]) > 200:
            errors["ubicacion"] = "La ubicación no puede superar los 200 caracteres."
        if len(values["nombre"]) > 100:
            errors["nombre"] = "El nombre no puede superar los 100 caracteres."
        if values["categoria"] not in categorias:
            errors["categoria"] = "Seleccioná una categoría válida."
        if not values["descripcion"]:
            errors["descripcion"] = "Describí el problema."
        elif len(values["descripcion"]) > 1500:
            errors["descripcion"] = "La descripción no puede superar los 1500 caracteres."

        fotografia = None
        if not errors and request.files.get("fotografia") and request.files["fotografia"].filename:
            try:
                fotografia = guardar_imagen(request.files["fotografia"], UPLOAD_DIR)
            except ValueError as exc:
                errors["fotografia"] = str(exc)

        if not errors:
            reclamo = {
                "id": len(reclamos) + 1,
                "nombre": values["nombre"] or "Vecino anónimo",
                "plaza": values["plaza"],
                "ubicacion": values["ubicacion"],
                "categoria": values["categoria"],
                "descripcion": values["descripcion"],
                "fotografia": fotografia,
                "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "estado": "Pendiente",
            }
            reclamos.append(reclamo)
            flash("¡RECLAMO REGISTRADO! Gracias por ayudar a mejorar nuestras plazas.")
            return redirect(url_for("reclamos_view"))

    return render_template(
        "reclamos.html",
        reclamos=reclamos,
        categorias=categorias,
        errors=errors,
        values=values,
    )


@app.route("/sobre-nosotros")
def sobre_nosotros():
    return render_template("sobre_nosotros.html", equipo=presentacion_equipo)


@app.route("/sobre-nosotros/editar", methods=["GET", "POST"])
@csrf_protected
@admin_required
def editar_sobre_nosotros():
    errors = {}
    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        texto = request.form.get("texto", "").strip()
        objetivo = request.form.get("objetivo", "").strip()
        participacion = request.form.get("participacion", "").strip()
        if not titulo or not texto or not objetivo or not participacion:
            errors["general"] = "Completá todos los campos de presentación."

        fotografia = presentacion_equipo["fotografia"]
        if not errors and request.files.get("fotografia") and request.files["fotografia"].filename:
            try:
                fotografia = guardar_imagen(request.files["fotografia"], TEAM_UPLOAD_DIR)
            except ValueError as exc:
                errors["fotografia"] = str(exc)

        if not errors:
            presentacion_equipo.update(
                titulo=titulo,
                texto=texto,
                objetivo=objetivo,
                participacion=participacion,
                fotografia=fotografia,
            )
            flash("Presentación del equipo actualizada.")
            return redirect(url_for("sobre_nosotros"))

    return render_template("sobre_nosotros.html", equipo=presentacion_equipo, editar=True, errors=errors)


@app.route("/admin/reclamos")
@admin_required
def administrar_reclamos():
    return render_template("admin_reclamos.html", reclamos=reclamos)


@app.route("/admin/reclamos/<int:reclamo_id>/estado", methods=["POST"])
@csrf_protected
@admin_required
def cambiar_estado(reclamo_id):
    reclamo = next((item for item in reclamos if item["id"] == reclamo_id), None)
    if reclamo is None:
        abort(404)

    nuevo_estado = request.form.get("estado", "")
    if nuevo_estado not in {"Pendiente", "En proceso", "Resuelto"}:
        abort(400)
    reclamo["estado"] = nuevo_estado
    flash(f"Estado del reclamo #{reclamo_id} actualizado.")
    return redirect(url_for("administrar_reclamos"))


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    safe_path = safe_join(str(UPLOAD_DIR), filename)
    if not safe_path:
        abort(404)
    response = send_from_directory(UPLOAD_DIR, filename)
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.errorhandler(400)
def bad_request(error):
    return render_template("error.html", codigo=400, mensaje="La solicitud no es válida."), 400


@app.errorhandler(404)
def not_found(error):
    return render_template("error.html", codigo=404, mensaje="Esta página no existe."), 404


@app.errorhandler(413)
def too_large(error):
    return render_template(
        "error.html",
        codigo=413,
        mensaje="El archivo supera el límite permitido de 3 MB.",
    ), 413


@app.errorhandler(500)
def internal_error(error):
    return render_template(
        "error.html",
        codigo=500,
        mensaje="Ocurrió un error inesperado. Intentá nuevamente.",
    ), 500


@app.errorhandler(503)
def service_unavailable(error):
    return render_template(
        "error.html",
        codigo=503,
        mensaje="La administración no está configurada en este servidor.",
    ), 503


if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=5000)
