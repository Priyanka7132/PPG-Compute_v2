# auth_handler.py

import datetime
import jwt
from passlib.context import CryptContext
from flask import request, jsonify
from functools import wraps
from ppg.utils.app_utils import AppUtils

class AuthHandler:
    pwdContext = CryptContext(schemes=['bcrypt'])
    secret = "secretKey"  # Replace or load from config

    def getPasswordHash(self, password):
        return self.pwdContext.hash(password)

    def verifyPassword(self, pwd, hashedPwd):
        return self.pwdContext.verify(pwd, hashedPwd)

    def encodeToken(self, userId):
        payload = {
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=4),
            'iat': datetime.datetime.utcnow(),
            'sub': userId
        }
        return jwt.encode(payload, self.secret, algorithm="HS256")

    def decodeToken(self, token):
        try:
            payload = jwt.decode(token, self.secret, algorithms=['HS256'])
            return payload['sub']
        except jwt.ExpiredSignatureError:
            return "Expired"
        except jwt.InvalidTokenError:
            return "Invalid"

    @staticmethod
    def auth_required(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith("Bearer "):
                return AppUtils.responseWithoutData(0, 400, "Authorization header missing or malformed")
            token = auth_header.split(" ")[1]
            auth = AuthHandler()
            user_id = auth.decodeToken(token)
            if user_id == "Expired":
                return AppUtils.responseWithoutData(0, 401, "Expired token")
            elif user_id == "Invalid":
                return AppUtils.responseWithoutData(0, 403, "Invalid token")

            request.user_id = user_id
            return f(*args, **kwargs)
        return wrapper
