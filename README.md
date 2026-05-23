# FastAPI S3 + RDS

Aplicación FastAPI que permite subir y consultar imágenes usando Amazon S3 y Amazon RDS (MySQL). Desplegada en AWS Lambda mediante imagen Docker almacenada en Amazon ECR.

**Autor:** Samuel Giraldo Jimenez  
**Materia:** Sistemas Operativos

---

## Arquitectura

```
Cliente → Lambda (URL pública) → FastAPI (Mangum)
                                    ├── Amazon S3 (almacenamiento de imágenes)
                                    └── Amazon RDS MySQL (registro de metadata)
```

## Tecnologías

- **Python 3.12** + **FastAPI**
- **boto3** — SDK de AWS para S3
- **SQLAlchemy** + **PyMySQL** — ORM y driver para MySQL
- **Mangum** — Adaptador ASGI para AWS Lambda
- **Docker** — Contenerización con imagen base de Lambda
- **Amazon S3** — Almacenamiento de imágenes
- **Amazon RDS** — Base de datos MySQL (Free Tier)
- **Amazon ECR** — Registro de imagen Docker
- **AWS Lambda** — Ejecución serverless con URL pública

---

## Endpoints

### POST `/upload`

Sube una imagen al bucket S3 y registra la metadata en RDS.

**Parámetros (form-data):**
| Campo    | Tipo   | Descripción                          |
|----------|--------|--------------------------------------|
| usuario  | string | Nombre del usuario                   |
| file     | file   | Imagen en formato PNG o JPG/JPEG     |

**Validaciones:**
- Solo acepta archivos `image/png`, `image/jpeg`, `image/jpg`
- Formato inválido retorna HTTP 415

**Respuesta exitosa (200):**
```json
{
  "message": "Imagen subida exitosamente",
  "id": 1,
  "usuario": "samuel",
  "s3_path": "samuel/foto.jpg",
  "created_at": "2026-05-23 17:30:04"
}
```

### GET `/image/{usuario}/{filename}`

Consulta la imagen en la base de datos y retorna una URL prefirmada de S3.

**Parámetros (path):**
| Campo    | Tipo   | Descripción               |
|----------|--------|---------------------------|
| usuario  | string | Nombre del usuario        |
| filename | string | Nombre del archivo        |

**Respuesta exitosa (200):**
```json
{
  "usuario": "samuel",
  "filename": "foto.jpg",
  "s3_path": "samuel/foto.jpg",
  "presigned_url": "https://...",
  "created_at": "2026-05-23 17:30:04"
}
```

**Errores:**
- Usuario o imagen no encontrados → HTTP 404

---

## Estructura del proyecto

```
fastapi-s3-rds/
├── main.py              # Aplicación FastAPI con endpoints POST y GET
├── requirements.txt     # Dependencias de Python
├── Dockerfile           # Imagen Docker basada en Lambda Python 3.12
├── .gitignore           # Archivos excluidos del repositorio
└── README.md            # Este archivo
```

---

## Ejecución local

### Requisitos previos

- Python 3.10+
- AWS CLI configurado (`aws configure`)
- Docker instalado
- Bucket S3 creado
- Instancia RDS MySQL creada y accesible públicamente

### Correr con Python

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 9000
```

Abrir `http://localhost:9000/docs` para ver el Swagger UI.

### Correr con Docker

```bash
docker build -t fastapi-s3-rds .
docker run -d -p 9000:8080 \
  -e AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id) \
  -e AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key) \
  -e AWS_DEFAULT_REGION=us-east-1 \
  --name fastapi-container \
  fastapi-s3-rds
```

---

## Despliegue en AWS

### 1. Crear instancia RDS (MySQL)

- Engine: MySQL Community
- Template: Free Tier (`db.t4g.micro`)
- Acceso público: Sí
- Security Group: abrir puerto 3306 (0.0.0.0/0)

### 2. Subir imagen a ECR

```bash
# Login en ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

# Build para plataforma correcta
docker buildx build --platform linux/amd64 --provenance=false --output type=docker -t fastapi-s3-rds .

# Tag y push
docker tag fastapi-s3-rds:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/fastapi-s3-rds:latest
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/fastapi-s3-rds:latest
```

### 3. Crear función Lambda

- Tipo: Container image
- Imagen: seleccionar desde ECR (`fastapi-s3-rds:latest`)
- Arquitectura: x86_64

### 4. Configuraciones necesarias

- **Timeout:** 30 segundos (Configuración general)
- **Permisos:** agregar `AmazonS3FullAccess` al rol de ejecución
- **URL de función:** crear con Auth type NONE

### 5. Probar

Abrir la URL de la función Lambda + `/docs` para acceder al Swagger UI.

---

## Variables de entorno

| Variable     | Valor por defecto                                          |
|--------------|-----------------------------------------------------------|
| DB_HOST      | taller-so-db.ccj4u488skun.us-east-1.rds.amazonaws.com    |
| DB_USER      | admin                                                     |
| DB_PASS      | (configurado en RDS)                                      |
| DB_NAME      | taller_so                                                 |
| DB_PORT      | 3306                                                      |
| S3_BUCKET    | user-1038868860-ueia-so                                   |
| AWS_REGION   | us-east-1                                                 |

---

## Recursos AWS utilizados

| Servicio | Recurso                        |
|----------|--------------------------------|
| S3       | user-1038868860-ueia-so        |
| RDS      | taller-so-db (MySQL, Free Tier)|
| ECR      | fastapi-s3-rds                 |
| Lambda   | fastapi-s3-rds                 |
