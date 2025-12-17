from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-=o&n*svev4)483cuyo%y)60caqh$8p4d6s-b(21l3slzp%9(#2'
DEBUG = True
ALLOWED_HOSTS = ['*']
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
CSRF_TRUSTED_ORIGINS = ["http://127.0.0.1", "http://localhost"]
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# Application definition

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "django.contrib.humanize",
    'formtools',
    'account.apps.AccountConfig',
    'core',
    'sales.apps.SalesConfig',
    'partners',
    "shipments.apps.ShipmentsConfig",
    'geo',
    'projects',
    'purchases',
    "sales_configuration",
]

INSTALLED_APPS += ["rest_framework", "corsheaders"]


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    

]

MIDDLEWARE = ["corsheaders.middleware.CorsMiddleware", *MIDDLEWARE]

CORS_ALLOWED_ORIGINS = [
    "http://cargochains.test",   # origin WordPress lokal-mu
]

# CSRF tidak diperlukan untuk GET autocomplete, tapi aman kalau ditambah juga
CSRF_TRUSTED_ORIGINS = [
    "http://cargochains.test",
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        "DIRS": [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

try:
    import MySQLdb
except Exception:
    import pymysql; pymysql.install_as_MySQLdb()

DB_ENGINE = os.environ.get('DB_ENGINE', 'mysql')

DATABASES = {
    "default": {
         'ENGINE': 'django.db.backends.mysql',
        "NAME": "cargochains",
        "USER": "root",
        "PASSWORD": "",         # kosongkan kalau default Laragon
        "HOST": "127.0.0.1",
        "PORT": "3306",
        "OPTIONS": {
            "charset": "utf8mb4",
        },
    }
}

TIME_ZONE = "Asia/Jakarta"
USE_TZ = True



# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS = [ BASE_DIR / "static" ] 
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


LOGIN_URL = "account:login"
LOGIN_REDIRECT_URL = "account:dashboard"
LOGOUT_REDIRECT_URL = "account:login"


JAZZMIN_SETTINGS = {
    "site_title": " Cargochains Admin",
    "site_header": "Cargochains",
    "site_brand": "Cargochains",
    "login_logo": "adminlte/img/logo_small.png",
}


SESSION_COOKIE_AGE = 10 * 60

# Jika ingin timeout diperpanjang setiap request (idle/sliding timeout)
SESSION_SAVE_EVERY_REQUEST = True   # ← perpanjang saat user aktif

# Kalau mau logout saat browser ditutup (opsional)
SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # True = habis saat browser ditutup

# Keamanan (disarankan)
SESSION_COOKIE_SECURE = True         # aktifkan di produksi (HTTPS)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"      # atau "Strict" sesuai kebutuhan


WKHTMLTOPDF_CMD = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"



MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"