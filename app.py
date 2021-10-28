import os
import datetime
import smtplib, ssl
from email.message import EmailMessage
from flask_restful import Api
from flask import Flask
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask import request, send_from_directory
from flask_restful import Resource
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity
from flask_sqlalchemy import SQLAlchemy
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
import subprocess

UPLOAD_FOLDER = os.getcwd() + "/uploads/"

db = SQLAlchemy()

user_task = db.Table('user_task',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key = True),
    db.Column('task_id', db.Integer, db.ForeignKey('task.id'), primary_key = True))

class Task(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    fileName = db.Column(db.String(128))
    newFormat = db.Column(db.String(128))
    timeStamp = db.Column(db.String(128))
    status = db.Column(db.String(128))
    user = db.relationship('User', secondary = 'user_task', back_populates="tasks")

class User(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(128))
    password1 = db.Column(db.String(128))
    password2 = db.Column(db.String(128))
    email = db.Column(db.String(128))
    tasks = db.relationship('Task', secondary = 'user_task', back_populates="user")

#SE SERIALIZARAN LAS CLASES PARA CONVERTIR EN JSON

class UserSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = User
        include_relationships = True
        load_instance = True

class TaskSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Task
        include_relationships = True
        load_instance = True

task_schema = TaskSchema()

class SignupView(Resource):

    def post(self):
        if request.json:
            new_user = User(username=request.json["username"], password1=request.json["password1"], password2=request.json["password2"], email=request.json["email"])
            db.session.add(new_user)
            db.session.commit()
            return 'El usuario se creo exitosamente', 201
        else:
            return {"message":"Bad Request"}, 400

class LoginView(Resource):

    def post(self):
        user = User.query.filter(User.username == request.json["username"], User.password1 == request.json["password"]).first()
        db.session.commit()

        if user is None:
            return {"message": "El usuario o contrasena incorrecta"}, 404
        else:
            token_de_acceso = create_access_token(identity = user.id)
            return {"token": token_de_acceso}

class GetCreateTasksView(Resource):

    @jwt_required()
    def post(self):
        if request.json:
            now = datetime.datetime.now()
            new_task = Task(fileName=request.json["fileName"], newFormat=request.json["newFormat"], timeStamp=now.strftime("%m/%d/%Y %H:%M:%S"), status= "uploaded", )
            user = User.query.get_or_404(get_jwt_identity())
            user.tasks.append(new_task)
            db.session.add(new_task)
            db.session.commit()
            return 'La tarea se creo exitosamente', 201
        else:
            return 'Bad Request', 400

    @jwt_required()
    def get(self):
        user = User.query.get_or_404(get_jwt_identity())
        def temp_schema(task):
            return task_schema.dump(task)
        return list(map(temp_schema, user.tasks))

class GetPutDeleteTaskByIdView(Resource):

    @jwt_required()
    def get(self, id_task):
        return task_schema.dump(Task.query.get_or_404(id_task)), 200

    @jwt_required()
    def put(self, id_task):

        task_to_update = Task.query.get_or_404(id_task)

        if task_to_update.status == 'processed':
            file_name = task_to_update.fileName.split(".")[0]
            file_processed = file_name + "." + task_to_update.newFormat

            task_to_update.newFormat = request.json.get("newFormat",task_to_update.newFormat)
            task_to_update.status = 'uploaded'

            os.remove(UPLOAD_FOLDER + file_processed)

        db.session.commit()

        return task_schema.dump(task_to_update)

    @jwt_required()
    def delete(self, id_task):
        task = Task.query.get_or_404(id_task)

        file_name = task.fileName.split(".")[0]
        new_file = file_name + "." + task.newFormat

        if os.path.exists(UPLOAD_FOLDER + task.fileName):
            os.remove(UPLOAD_FOLDER + task.fileName)
        
        if os.path.exists(UPLOAD_FOLDER + new_file):
            os.remove(UPLOAD_FOLDER + new_file)

        db.session.delete(task)
        db.session.commit()
        return {"message":"La tarea fue eliminada"}, 204

class GetFileView(Resource):

    @jwt_required()
    def get(self, filename):
        task = Task.query.filter(Task.fileName == filename).first()

        if task is None:
            return {"message":"El archivo no existe"}, 404
        else:
            return send_from_directory(directory=UPLOAD_FOLDER, filename=task.fileName)

class CronjobView(Resource):

    def sendEmail(self, message, receiver):
        SMTP_PORT = 465
        SMTP_SERVER = "smtp.gmail.com"
        SMTP_USERNAME = "misomazf@gmail.com"
        SMTP_PASSWORD = "Misomazf123456"

        subject = "Cloud Conversion Tool - Tarea ejecutada correctamente"
        context = ssl.create_default_context()
        
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = SMTP_USERNAME
        msg['To'] = receiver
        msg.set_content(message, subtype='html')

        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)

    def email_template_convertion_success(self, task):
        messageTemplate = '''
        <!DOCTYPE html>
        <html>
            <body>
                <p>La conversion de formato fue realizado correctamente</p>
                <br/>
                <p>Tarea: {0}</p>
                <p>Archivo: {1}</p>
                <p>Nuevo formato: {2}</p>
            </body>
        </html>
        '''
        return messageTemplate.format(task.id, task.fileName, task.newFormat)


    def get(self):
        query_tasks = Task.query.filter(Task.status == "uploaded")
        print("Tareas para convertir: {count}".format(count = query_tasks.count()))
        if query_tasks.count() > 0:
            for task in query_tasks:
                print("TaskId: " + str(task.id))
                print("Filename: "+ task.fileName)
                print("NewFormat: "+ task.newFormat)
            
                file_name = task.fileName.split(".")[0]
                new_file = file_name + "." + task.newFormat

                print("Email" + task.user[0].email)
                receiver = task.user[0].email

                emailMessage = self.email_template_convertion_success(task)
                subprocess.call(['ffmpeg', '-y', '-i', UPLOAD_FOLDER + task.fileName, UPLOAD_FOLDER + new_file], shell=True)
                task.status = "processed"
                print(task.status)
                db.session.commit()
                self.sendEmail(emailMessage, receiver)

                print("=====================================================")
        return 'Running....', 200

def create_app(config_name):
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@127.0.0.1:5432/postgres'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY']='frase-secreta'
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 3600
    app.config['PROPAGATE_EXCEPTIONS'] = True
    return app

app = create_app('default')
app_context = app.app_context()
app_context.push()

db.init_app(app)
db.create_all()

cors = CORS(app)

api = Api(app)

api.add_resource(SignupView, '/api/auth/signup')
api.add_resource(LoginView, '/api/auth/login')
api.add_resource(GetCreateTasksView, '/api/tasks')
api.add_resource(GetPutDeleteTaskByIdView, '/api/tasks/<int:id_task>')
api.add_resource(GetFileView, '/api/files/<filename>')
api.add_resource(CronjobView, '/api/cronjob')

jwt = JWTManager(app)