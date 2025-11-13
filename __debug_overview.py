from app import create_app
app = create_app()
with app.app_context():
    client = app.test_client()
    resp = client.get('/hrdoctrack/overview')
    print('status:', resp.status_code)
    print('body snippet:', resp.data[:200])
