# Mi Plaza Segura

Aplicación web funcional para registrar reclamos vecinales sobre las plazas de Las Heras, Mendoza. Está desarrollada con Flask, Jinja2, Tailwind CSS y JavaScript, con una interfaz retro inspirada en videojuegos pixel art.

## Requisitos

- Python 3.10 o superior
- pip

## Instalación

Desde la raíz del repositorio:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

En Windows, activar el entorno con:

```bat
.venv\Scripts\activate
```

## Ejecución

```bash
python app.py
```

Abrir `http://localhost:5000` en el navegador.

## Rutas principales

- `/` — Inicio
- `/reclamos` — Formulario y listado de reclamos
- `/sobre-nosotros` — Presentación del equipo
- `/sobre-nosotros/editar` — Edición protegida de la presentación
- `/admin/reclamos` — Gestión protegida de estados

La edición y el panel usan autenticación HTTP Basic. Para habilitarlos, configurá credenciales propias y una clave secreta antes de iniciar Flask. Sin credenciales administrativas, las rutas de administración permanecen deshabilitadas.

```bash
export ADMIN_USERNAME="tu_usuario"
export ADMIN_PASSWORD="tu_clave_segura"
export SECRET_KEY="una_clave_aleatoria_larga"
python app.py
```

En Windows PowerShell:

```powershell
$env:SECRET_KEY="una_clave_aleatoria_larga"
$env:ADMIN_USERNAME="tu_usuario"
$env:ADMIN_PASSWORD="tu_clave_segura"
python app.py
```

## Almacenamiento y límites

Los reclamos se guardan solamente en una lista global de Python mientras Flask permanece activo. Se pierden al reiniciar o detener el servidor y no comparten estado entre varios procesos.

Las imágenes de reclamos y del equipo se guardan en `static/uploads`; solo se aceptan imágenes JPG, JPEG, PNG o WebP verificadas, de hasta 3 MB y 20 megapíxeles. Los archivos reciben nombres aleatorios seguros y se vuelven a codificar para descartar metadatos. Los nombres de quienes reclaman solo se muestran en el panel protegido de administración. No se utiliza ninguna base de datos ni archivo externo para guardar los registros.

El servidor de desarrollo se ejecuta en un único proceso, sin recargador automático, para mantener los reclamos en una sola lista de memoria.

## Detener el servidor

Presionar `Ctrl+C` en la terminal donde se ejecuta Flask.
