import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    # Jika dijalankan langsung di environment production, gunakan waitress (Windows)
    # atau gunicorn (Linux).
    try:
        from waitress import serve
        port = int(os.getenv('FLASK_PORT', 5000))
        host = os.getenv('FLASK_HOST', '127.0.0.1')
        print(f"[*] Melayani Flask via Waitress Production WSGI di http://{host}:{port}")
        serve(app, host=host, port=port)
    except ImportError:
        # Fallback jika waitress belum diinstall
        host = os.getenv('FLASK_HOST', '127.0.0.1')
        port = int(os.getenv('FLASK_PORT', 5000))
        print(f"[i] Waitress tidak ditemukan, menjalankan dengan server standar di http://{host}:{port}")
        app.run(host=host, port=port, debug=False)
