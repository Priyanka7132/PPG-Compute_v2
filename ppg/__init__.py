from flask import Flask,request
from ppg import service as service
from flask_cors import CORS

def create_app(config):
  app = Flask(__name__)
  CORS(app)
  #import service through blueprint
  app.register_blueprint(service.service_url,url_prefix='/service')
  if Flask(__name__) == "__main__":
    app.run(debug=True,host= '127.0.0.1')

  return app

